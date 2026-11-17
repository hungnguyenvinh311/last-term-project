"""Composition root: concrete implementations are wired only here."""
import logging
import os
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from Model.application.config.settings import ROOT
from DAO.application.dao.connection import Database
from DAO.application.dao.ProductDAOImpl import ProductDAOImpl
from DAO.application.dao.CategoryDAOImpl import CategoryDAOImpl
from DAO.application.dao.ReportDAOImpl import ReportDAOImpl
from DAO.application.dao.InventoryDAOImpl import InventoryDAOImpl
from Model.application.service.CatalogAdministrationService import CatalogAdministrationService
from Model.application.service.OrderOperationsService import OrderOperationsService
from Model.application.service.ReportingService import ReportingService
from Model.application.service.InventoryService import InventoryService
from Model.application.service.CheckoutPricingService import CheckoutPricingService
from Model.application.integration.storage.ReportExporter import ReportExporter
from Model.application.integration.storage.CatalogueArtifacts import CatalogueArtifacts
from Controller.application.controller.CatalogAdminController import CatalogAdminController
from Controller.application.controller.PaymentOperationsController import PaymentOperationsController
from Controller.application.controller.ReportController import ReportController
from Controller.application.controller.InventoryController import InventoryController
from DAO.application.dao.CustomerDAOImpl import CustomerDAOImpl
from DAO.application.dao.AccountDAOImpl import AccountDAOImpl
from DAO.application.dao.CartDAOImpl import CartDAOImpl
from DAO.application.dao.OrderDAOImpl import OrderDAOImpl
from DAO.application.dao.PaymentDAOImpl import PaymentDAOImpl
from DAO.application.dao.ShipmentDAOImpl import ShipmentDAOImpl
from DAO.application.dao.SearchQueryDAOImpl import SearchQueryDAOImpl
from Model.application.service.AccountService import AccountService
from Model.application.service.ProductService import ProductService
from Model.application.service.CartService import CartService
from Model.application.service.CheckoutService import CheckoutService
from Model.application.service.PaymentService import PaymentService
from Model.application.service.FulfilmentService import FulfilmentService
from Model.application.service.SearchService import SearchService
from Model.application.service.RecommendationService import RecommendationService
from Model.application.ai.IntentExtractorService import IntentExtractorService
from Model.application.ai.MultimodalEmbedderService import MultimodalEmbedderService
from Model.application.config.detector import create_detector
from Model.application.ai.SpeechTranscriberService import SpeechTranscriberService
from Model.application.ai.GeminiClient import GeminiClient
from Model.application.ai.GeminiSpeechTranscriberService import GeminiSpeechTranscriberService
from Model.application.ai.GeminiIntentExtractorService import GeminiIntentExtractorService
from Model.application.context.SearchSessionService import SearchSessionService
from Model.application.retrieval.CandidateRetriever import CandidateRetriever
from Model.application.retrieval.SoftReranker import SoftReranker
from Model.application.integration.storage.LocalMediaStorage import LocalMediaStorage
from Model.application.integration.simulation.SimulatedPaymentGateway import SimulatedPaymentGateway
from Model.application.integration.simulation.SimulatedShippingProvider import SimulatedShippingProvider
from Controller.application.controller.AccountController import AccountController
from Controller.application.controller.ProductController import ProductController
from Controller.application.controller.CartController import CartController
from Controller.application.controller.OrderController import OrderController
from Controller.application.controller.StaffController import StaffController
from Controller.application.controller.SearchRoutesService import SearchRoutesService
from Model.application.errors import DomainError,AIUnavailable

def create_app(database=None,overrides=None):
    overrides=overrides or {};db=Database(database)
    products=ProductDAOImpl(db);customers=CustomerDAOImpl(db);carts=CartDAOImpl(db)
    pricing=CheckoutPricingService()
    orders=OrderDAOImpl(db,carts,pricing);payments=PaymentDAOImpl(db);shipments=ShipmentDAOImpl(db)
    accounts=AccountService(AccountDAOImpl(db),customers)
    media=overrides.get('media') or LocalMediaStorage();embedder=overrides.get('embedder') or MultimodalEmbedderService()
    detector=overrides.get('detector') or create_detector()
    gemini=overrides.get('gemini') or GeminiClient()
    speech_provider=os.getenv('APP_TRANSCRIBE_PROVIDER','gemini').lower()
    intent_provider=os.getenv('APP_INTENT_PROVIDER','gemini').lower()
    if speech_provider not in {'gemini','openai'} or intent_provider not in {'gemini','rules'}:
        raise RuntimeError('Unknown AI provider; check APP_TRANSCRIBE_PROVIDER / APP_INTENT_PROVIDER')
    transcriber=overrides.get('transcriber') or (GeminiSpeechTranscriberService(gemini) if speech_provider=='gemini' else SpeechTranscriberService())
    intent=overrides.get('intent') or (GeminiIntentExtractorService(gemini,IntentExtractorService()) if intent_provider=='gemini' else IntentExtractorService())
    from Model.application.config.ranking import load_search_weights
    retriever=CandidateRetriever(products,embedder);ranking=SoftReranker(embedder.identity,load_search_weights())
    payment=PaymentService(payments,orders,SimulatedPaymentGateway())
    fulfilment=FulfilmentService(shipments,orders,SimulatedShippingProvider())
    checkout=CheckoutService(orders,payment,fulfilment)
    search=SearchService(intent,transcriber,detector,embedder,SearchSessionService(),retriever,ranking,SearchQueryDAOImpl(db),media)
    recommendation=RecommendationService(products,retriever,ranking)
    # Isolated test databases must never invalidate the primary catalogue's label files.
    primary_catalogue=db.options['database']==os.getenv('APP_DATABASE','ecommerce_relationship_review') and not db.options['database'].startswith('ecommerce_test_')
    artifacts=overrides.get('catalogueArtifacts') or (CatalogueArtifacts() if primary_catalogue else None)
    def catalogue_changed(articleID):
        if artifacts: artifacts.invalidateLabels(articleID)
        with search._cache_lock: search._cache.clear()
    catalogue=CatalogAdministrationService(products,CategoryDAOImpl(db),media,catalogue_changed)
    operations=OrderOperationsService(orders,customers,checkout,payments)
    reporting=ReportingService(ReportDAOImpl(db))
    inventory=InventoryService(InventoryDAOImpl(db))
    app=FastAPI(title='Electronics AI Commerce',version='0.1.0')
    app.state.services=dict(db=db,accounts=accounts,products=products,search=search,recommendation=recommendation,embedder=embedder,detector=detector,inventory=inventory)
    for controller in [AccountController(accounts),ProductController(ProductService(products,media)),
                       CartController(CartService(carts,customers,products,pricing),accounts),OrderController(checkout,fulfilment,accounts),
                       CatalogAdminController(catalogue,accounts),ReportController(reporting,ReportExporter(),accounts),
                       InventoryController(inventory,accounts),
                       StaffController(checkout,fulfilment,accounts),SearchRoutesService(search,recommendation,accounts),
                       PaymentOperationsController(operations,accounts,payment)]:
        app.include_router(controller.router)
    @app.exception_handler(DomainError)
    async def domain_error(request,exc): return JSONResponse({'detail':exc.message},status_code=exc.status)
    @app.exception_handler(AIUnavailable)
    async def ai_error(request,exc): return JSONResponse({'detail':str(exc),'code':'AI_UNAVAILABLE'},status_code=503)
    @app.exception_handler(Exception)
    async def internal_error(request,exc):
        logging.getLogger('commerce').error('Request failed: %s',type(exc).__name__)
        return JSONResponse({'detail':'Hệ thống chưa xử lý được yêu cầu. Hãy kiểm tra database/cấu hình.'},status_code=500)
    @app.get('/api/health')
    def health():
        db.query('SELECT 1 AS ok',one=True)
        from Model.application.retrieval.representations import metadata
        rows=db.query("SELECT COUNT(*) AS products,SUM(imageEmbedding<>'[]' AND textEmbedding<>'[]') AS embedded FROM Product",one=True)
        return {'status':'ok','simulation':True,'encoder':embedder.identity,'products':rows['products'],'embeddedProducts':int(rows['embedded'] or 0),
                'embeddingManifestCompatible':metadata().get('identity')==embedder.identity,
                'transcriptionProvider':speech_provider,'intentProvider':intent_provider,
                'detectorProvider':getattr(detector,'kind','owlvit'),
                'detectorPadding':getattr(detector,'padding',False),
                'detectorDevice':getattr(detector,'device','cpu'),
                'detectorLabelPolicy':getattr(detector,'labelPolicy','raw'),
                'geminiConfigured':bool(gemini.configuration('intent')[0])}
    @app.middleware('http')
    async def upload_limit(request:Request,call_next):
        length=request.headers.get('content-length')
        if length and (not length.isdigit() or int(length)>24*1024*1024):
            return JSONResponse({'detail':'Tệp yêu cầu quá lớn'},status_code=413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        if request.url.path.startswith('/api/') and not request.url.path.endswith('/image'):
            response.headers['Cache-Control']='no-store'
        return response
    dist=ROOT/'View/dist'
    if dist.is_dir():
        app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
        @app.get('/')
        def index(): return FileResponse(dist/'index.html')
    if not overrides.get('disableBackgroundJobs',False):
        import asyncio
        from starlette.concurrency import run_in_threadpool
        async def expire_holds_loop():
            while True:
                await asyncio.sleep(30)
                try:
                    await run_in_threadpool(orders.expireHolds)
                except Exception as exc:
                    logging.getLogger('commerce').warning('Hold expiry sweep failed: %s',type(exc).__name__)
        @app.on_event('startup')
        async def start_expiry_worker():
            app.state.hold_expiry_task=asyncio.create_task(expire_holds_loop())
        @app.on_event('shutdown')
        async def stop_expiry_worker():
            task=getattr(app.state,'hold_expiry_task',None)
            if task:
                task.cancel()
    return app

app=create_app()

if __name__=='__main__':
    import os,uvicorn
    uvicorn.run('bootstrap:app',host=os.getenv('APP_HOST','127.0.0.1'),port=int(os.getenv('APP_PORT','8008')))
