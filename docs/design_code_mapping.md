# Design-to-code mapping

The PDF Chapter 4 is the architectural baseline. Account/AuthSession and the account API are the explicitly approved extension. Concrete dependencies are assembled in bootstrap.py.

## Runtime paths

| Feature | Runtime path |
|---|---|
| Text/Voice/Image | MainView ? SearchRoutesService ? ISearch/SearchService ? AI/context contracts ? CandidateRetriever/ProductDAO ? SoftReranker ? SearchQueryDAO ? response |
| Recommendation | MainView details ? SearchRoutesService ? IRecommendation/RecommendationService ? ProductDAO + retrieval + ranking ? response |
| Cart | CartView ? CartController ? ICart/CartService ? CustomerDAO/ProductDAO/CartDAO |
| Checkout | CheckoutView ? OrderController ? ICheckout/CheckoutService ? OrderDAO/CartDAO ? IPayment/IFulfilment |
| Payment/shipping | Services ? provider interfaces ? simulators; summaries through corresponding DAOs |
| Accounts extension | MainView/StaffView ? AccountController/StaffController ? IAccount/AccountService ? AccountDAO/CustomerDAO |

## Source inventory

| Class/interface or view | File | Public operations |
|---|---|---|
| Credentials | `Controller/application/controller/AccountController.py` | Entity/DTO fields |
| Registration | `Controller/application/controller/AccountController.py` | Entity/DTO fields |
| Profile | `Controller/application/controller/AccountController.py` | Entity/DTO fields |
| AccountController | `Controller/application/controller/AccountController.py` | Entity/DTO fields |
| CartChange | `Controller/application/controller/CartController.py` | Entity/DTO fields |
| CartController | `Controller/application/controller/CartController.py` | Entity/DTO fields |
| Checkout | `Controller/application/controller/OrderController.py` | Entity/DTO fields |
| PaymentScenario | `Controller/application/controller/OrderController.py` | Entity/DTO fields |
| OrderController | `Controller/application/controller/OrderController.py` | Entity/DTO fields |
| Comparison | `Controller/application/controller/ProductController.py` | Entity/DTO fields |
| ProductController | `Controller/application/controller/ProductController.py` | Entity/DTO fields |
| TextRequest | `Controller/application/controller/SearchRoutesService.py` | Entity/DTO fields |
| SearchRoutesService | `Controller/application/controller/SearchRoutesService.py` | Entity/DTO fields |
| StatusChange | `Controller/application/controller/StaffController.py` | Entity/DTO fields |
| ActiveChange | `Controller/application/controller/StaffController.py` | Entity/DTO fields |
| StaffController | `Controller/application/controller/StaffController.py` | Entity/DTO fields |
| IntentExtractorService | `Model/application/ai/IntentExtractorService.py` | extractCriteria |
| MultimodalEmbedderService | `Model/application/ai/MultimodalEmbedderService.py` | identity, load, encodeText, encodeImage |
| ObjectDetectorService | `Model/application/ai/ObjectDetectorService.py` | detectProducts, cropRegion |
| SpeechTranscriberService | `Model/application/ai/SpeechTranscriberService.py` | transcribe |
| SearchSessionService | `Model/application/context/SearchSessionService.py` | getOrCreate, mergeCriteria, rememberResults |
| IAccount | `Model/application/contract/IAccount.py` | register, login, authenticate, logout, profile, updateProfile, listAccounts, setActive |
| ICandidateRetrieval | `Model/application/contract/ICandidateRetrieval.py` | retrieveForQuery, retrieveAlternatives, findFallbackAlternatives |
| ICart | `Model/application/contract/ICart.py` | getCart, addItem, changeQuantity, removeItem |
| ICheckout | `Model/application/contract/ICheckout.py` | submitCheckout, cancelBeforePacking, listOrders, getOrder, staffOrders |
| IEmbedding | `Model/application/contract/IEmbedding.py` | encodeText, encodeImage |
| IFulfilment | `Model/application/contract/IFulfilment.py` | createShipment, getShipmentStatus, updateStatus |
| IImageRegion | `Model/application/contract/IImageRegion.py` | detectProducts, cropRegion |
| IIntentExtraction | `Model/application/contract/IIntentExtraction.py` | extractCriteria |
| IMediaStorage | `Model/application/contract/IMediaStorage.py` | validateImage, saveUpload, read, resolveProductImage, deleteExpiredQueryMedia |
| IPayment | `Model/application/contract/IPayment.py` | payOrder, getPaymentStatus |
| IPaymentGateway | `Model/application/contract/IPaymentGateway.py` | processPayment |
| IProduct | `Model/application/contract/IProduct.py` | getDetails, filterProducts, compareProducts, image |
| IRanking | `Model/application/contract/IRanking.py` | rankForQuery, rankForProduct |
| IRecommendation | `Model/application/contract/IRecommendation.py` | recommendForProduct |
| ISearch | `Model/application/contract/ISearch.py` | searchText, searchVoice, searchImage, transcribeVoice, detectImageProducts |
| ISearchContext | `Model/application/contract/ISearchContext.py` | getOrCreate, mergeCriteria, rememberResults |
| IShippingProvider | `Model/application/contract/IShippingProvider.py` | createShipment, getStatus |
| ITranscription | `Model/application/contract/ITranscription.py` | transcribe |
| PaymentOutcome | `Model/application/dto/PaymentOutcome.py` | Entity/DTO fields |
| ProductCandidate | `Model/application/dto/ProductCandidate.py` | Entity/DTO fields |
| RankedProduct | `Model/application/dto/RankedProduct.py` | Entity/DTO fields |
| RecommendationResponse | `Model/application/dto/RecommendationResponse.py` | Entity/DTO fields |
| Region | `Model/application/dto/Region.py` | Entity/DTO fields |
| SearchCriteria | `Model/application/dto/SearchCriteria.py` | to_dict |
| SearchResponse | `Model/application/dto/SearchResponse.py` | Entity/DTO fields |
| ShipmentStatus | `Model/application/dto/ShipmentStatus.py` | Entity/DTO fields |
| Account | `Model/application/entity/Account.py` | Entity/DTO fields |
| AuthSession | `Model/application/entity/AuthSession.py` | Entity/DTO fields |
| Cart | `Model/application/entity/Cart.py` | Entity/DTO fields |
| CartItem | `Model/application/entity/CartItem.py` | Entity/DTO fields |
| Category | `Model/application/entity/Category.py` | Entity/DTO fields |
| Customer | `Model/application/entity/Customer.py` | Entity/DTO fields |
| ImageQuery | `Model/application/entity/ImageQuery.py` | Entity/DTO fields |
| Order | `Model/application/entity/Order.py` | Entity/DTO fields |
| OrderItem | `Model/application/entity/OrderItem.py` | Entity/DTO fields |
| Payment | `Model/application/entity/Payment.py` | Entity/DTO fields |
| Product | `Model/application/entity/Product.py` | Entity/DTO fields |
| SearchQuery | `Model/application/entity/SearchQuery.py` | Entity/DTO fields |
| SearchResult | `Model/application/entity/SearchResult.py` | Entity/DTO fields |
| Shipment | `Model/application/entity/Shipment.py` | Entity/DTO fields |
| TextQuery | `Model/application/entity/TextQuery.py` | Entity/DTO fields |
| VoiceQuery | `Model/application/entity/VoiceQuery.py` | Entity/DTO fields |
| DomainError | `Model/application/errors.py` | Entity/DTO fields |
| AIUnavailable | `Model/application/errors.py` | Entity/DTO fields |
| CandidateRetriever | `Model/application/retrieval/CandidateRetriever.py` | retrieveForQuery, retrieveAlternatives, findFallbackAlternatives |
| SoftReranker | `Model/application/retrieval/SoftReranker.py` | rankForQuery, rankForProduct |
| AccountService | `Model/application/service/AccountService.py` | register, login, authenticate, logout, profile, updateProfile, listAccounts, setActive |
| CartService | `Model/application/service/CartService.py` | getCart, addItem, changeQuantity, removeItem |
| CheckoutService | `Model/application/service/CheckoutService.py` | submitCheckout, cancelBeforePacking, listOrders, getOrder, staffOrders |
| FulfilmentService | `Model/application/service/FulfilmentService.py` | createShipment, getShipmentStatus, updateStatus |
| PaymentService | `Model/application/service/PaymentService.py` | payOrder, getPaymentStatus |
| ProductService | `Model/application/service/ProductService.py` | getDetails, filterProducts, compareProducts, image |
| RecommendationService | `Model/application/service/RecommendationService.py` | recommendForProduct |
| SearchService | `Model/application/service/SearchService.py` | searchText, searchVoice, transcribeVoice, detectImageProducts, searchImage |
| AccountDAOImpl | `DAO/application/dao/AccountDAOImpl.py` | register, findByEmail, createSession, findSession, deleteSession, listAccounts, setActive |
| CartDAOImpl | `DAO/application/dao/CartDAOImpl.py` | findForUpdate, getCart, save |
| Database | `DAO/application/dao/connection.py` | transaction, query |
| CustomerDAOImpl | `DAO/application/dao/CustomerDAOImpl.py` | findById, findByEmail, saveContact |
| OrderDAOImpl | `DAO/application/dao/OrderDAOImpl.py` | findById, findOwned, listOwned, listAll, createWithItems, updateVersioned, cancel |
| PaymentDAOImpl | `DAO/application/dao/PaymentDAOImpl.py` | findByOrder, saveSummary |
| ProductDAOImpl | `DAO/application/dao/ProductDAOImpl.py` | findById, findActive, findByCriteria, findByRepresentation, findAlternatives, saveRepresentation |
| SearchQueryDAOImpl | `DAO/application/dao/SearchQueryDAOImpl.py` | saveWithResults, findById |
| ShipmentDAOImpl | `DAO/application/dao/ShipmentDAOImpl.py` | findByOrder, saveSummary, updateStatus |
| AccountDAO | `DAO/contract/AccountDAO.py` | register, findByEmail, createSession, findSession, deleteSession, listAccounts, setActive |
| CartDAO | `DAO/contract/CartDAO.py` | getCart, save, findForUpdate |
| CustomerDAO | `DAO/contract/CustomerDAO.py` | findById, findByEmail, saveContact |
| OrderDAO | `DAO/contract/OrderDAO.py` | findById, findOwned, createWithItems, updateVersioned, listOwned, listAll, cancel |
| PaymentDAO | `DAO/contract/PaymentDAO.py` | findByOrder, saveSummary |
| ProductDAO | `DAO/contract/ProductDAO.py` | findById, findActive, findByCriteria, findByRepresentation, findAlternatives, saveRepresentation |
| SearchQueryDAO | `DAO/contract/SearchQueryDAO.py` | saveWithResults, findById |
| ShipmentDAO | `DAO/contract/ShipmentDAO.py` | findByOrder, saveSummary, updateStatus |
| SimulatedPaymentGateway | `infrastructure/application/simulation/SimulatedPaymentGateway.py` | processPayment |
| SimulatedShippingProvider | `infrastructure/application/simulation/SimulatedShippingProvider.py` | createShipment, getStatus |
| LocalMediaStorage | `infrastructure/application/storage/LocalMediaStorage.py` | validateImage, saveUpload, resolveProductImage, read, deleteExpiredQueryMedia |
| CartView | `View/application/view/CartView.tsx` | HTTP client only; UI interactions |
| CheckoutView | `View/application/view/CheckoutView.tsx` | HTTP client only; UI interactions |
| MainView | `View/application/view/MainView.tsx` | HTTP client only; UI interactions |
| StaffView | `View/application/view/StaffView.tsx` | HTTP client only; UI interactions |

## Database naming map

| Design name | Implemented name | Reason |
|---|---|---|
| Products.articleID | Products.articleID | Approved integer key |
| representationUpdatedAt | Products.representationUpdateAt | Preserve existing imported column; map explicitly |
| SearchResult.rank | SearchResults.rankPosition | SQL-safe column mapped to response rank |
| seachResults | SearchResults | Correct documented spelling in new table |
| text/image/voice query_id | queryID | Shared primary/foreign key, consistent with parent |
| Customer.Age | Customer.dateOfBirth | Birth date is persistent; age is derivable |
| Order concurrency version | Orders.version | Supporting field for versioned status updates |
| Account/AuthSession | Accounts/AuthSessions | Approved account management extension |

DAO implementations map database rows into Product entities or domain/result values. SearchResult rank/score belong to a query, not to the Product catalogue. No recommendation entity/table or customer-profile recommender is added.

Data Access is separated from business services; Model services depend on DAO contracts, and DAO implementations depend on entity/value definitions. Entity modules never import DAO or Controller.


## Gemini implementation substitution

| Existing contract | Active implementation | Supporting component |
|---|---|---|
| ITranscription | Model/application/ai/GeminiSpeechTranscriberService.py | GeminiClient.py REST adapter |
| IIntentExtraction | Model/application/ai/GeminiIntentExtractorService.py | GeminiClient.py; validated schema; rule fallback |

Bootstrap injects these into SearchService. Controllers, DAOs and entities do not depend on Google response structures. OpenAI SpeechTranscriberService remains an optional inactive adapter. SearchCriteria adds provider/warning metadata, stored in the existing criteria JSON without new columns.

## Existing-schema commerce extension — 2026-11-05

These classes extend the implementation using the approved MVC direction. They are not claimed to be already drawn individually in the original PDF. Existing entities and the 16-table ERD remain unchanged.

| Responsibility | View / Controller | Service contract and implementation | DAO / infrastructure |
|---|---|---|---|
| Catalogue administration | staff/CatalogAdminView; CatalogAdminController | ICatalogAdministration / CatalogAdministrationService | ProductDAO.save/findAll, CategoryDAO/CategoryDAOImpl; IMediaStorage.saveProductImage; CatalogueArtifacts |
| Account administration | staff/AccountAdminView; StaffController | IAccount / AccountService.createStaff,setActive | AccountDAO/AccountDAOImpl, AuthSessions |
| Checkout pricing | CartView, CheckoutView; CartController, OrderController | ICheckoutPricing / CheckoutPricingService; ICheckout / CheckoutService | OrderDAOImpl receives pricing contract; calculates against locked product rows and writes existing order/payment totals |
| Staff order support | staff/SalesOrdersView; PaymentOperationsController | IOrderOperations / OrderOperationsService | OrderDAO, CustomerDAO, PaymentDAO |
| Fulfilment | staff/FulfilmentView; StaffController | IFulfilment / FulfilmentService | ShipmentDAO/ShipmentDAOImpl, existing shipping simulator |
| COD confirmation | staff/CODConfirmationView; PaymentOperationsController | IOrderOperations / OrderOperationsService.confirmCOD | PaymentDAO.confirmCOD / PaymentDAOImpl: locks Orders, Payments and Shipments |
| Reports | staff/ReportsView; ReportController | IReporting / ReportingService; IReportExport / ReportExporter | ReportDAO/ReportDAOImpl reads Orders, OrderItems, Products, Payments; CSV/PDF responses |
| Customer profile | ProfileView; AccountController | IAccount / AccountService.updateProfile | CustomerDAO/CustomerDAOImpl updates existing DOB/contact fields |

bootstrap.py remains the composition root. Controllers depend on service interfaces; services depend on DAO interfaces; SQL stays in DAO implementations. ProductUpdate, CategoryUpdate and CODConfirmation validate request data; they are not persistent entity classes. Package grouping does not imply additional physical tiers or services.

