"""Create one named entity/contract per file. Never overwrites existing code."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def write(path, content):
    target=ROOT/path
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists(): target.write_text(content,encoding='utf-8')

entities={
 'Customer':'customerID: int\nfullName: str\nemail: str\nphoneNumber: str | None = None\nshippingAddress: str | None = None',
 'Category':'categoryID: int\ngroupName: str\nsubCategory: str\nspecificationSchema: dict | None = None',
 'Product':'articleID: int\ncategoryID: int\nproductName: str\nprice: Decimal\ncurrency: str\nbrand: str | None = None\ntechnicalSpecs: dict | None = None\nimagePath: str | None = None\nimageEmbedding: list[float] | None = None\ntextEmbedding: list[float] | None = None',
 'Cart':'cartID: int\ncustomerID: int',
 'CartItem':'cartItemID: int\ncartID: int\narticleID: int\nquantity: int',
 'Order':'orderID: int\ncustomerID: int\nstatus: str\ntotalAmount: Decimal\npaymentMethod: str\nshippingAddress: str\nrecipientPhone: str',
 'OrderItem':'orderItemID: int\norderID: int\narticleID: int\nquantity: int\nunitPrice: Decimal\nproductNameSnapshot: str',
 'Payment':'paymentID: int\norderID: int\npaymentMethod: str\namount: Decimal\nstatus: str',
 'Shipment':'shippingID: int\norderID: int\ntrackingNumber: str\ncarrier: str\nstatus: str',
 'SearchQuery':'queryID: int\nqueryType: str\nsearchCriteria: dict\ncustomerID: int | None = None',
 'SearchResult':'queryID: int\narticleID: int\nrank: int\nscore: float',
 'Account':'accountID: int\ncustomerID: int\nemail: str\nrole: str\nisActive: bool',
 'AuthSession':'tokenHash: str\naccountID: int\nexpiresAt: datetime',
}
for name,fields in entities.items():
 write(Path('Model/application/entity')/(name+'.py'),'from dataclasses import dataclass\nfrom decimal import Decimal\nfrom datetime import datetime\n\n@dataclass\nclass '+name+':\n'+''.join('    '+line+'\n' for line in fields.splitlines()))
for name,fields in {'TextQuery':'queryText: str = ""','ImageQuery':'imageReference: str = ""\nselectedRegion: list[float] | None = None','VoiceQuery':'transcribedText: str = ""\naudioReference: str | None = None'}.items():
 write(Path('Model/application/entity')/(name+'.py'),'from dataclasses import dataclass\nfrom .SearchQuery import SearchQuery\n\n@dataclass\nclass '+name+'(SearchQuery):\n'+''.join('    '+line+'\n' for line in fields.splitlines()))

contracts={
 'IEmbedding':['encodeText(self, text: str) -> list[float]','encodeImage(self, image) -> list[float]'],
 'IIntentExtraction':['extractCriteria(self, text: str)'],
 'ITranscription':['transcribe(self, content: bytes, filename: str) -> str'],
 'IImageRegion':['detectProducts(self, image) -> list[dict]','cropRegion(self, image, region)'],
 'ICandidateRetrieval':['retrieveForQuery(self, criteria, vector=None, mode="text")','retrieveAlternatives(self, source)','findFallbackAlternatives(self, source)'],
 'IRanking':['rankForQuery(self, candidates, criteria, limit=12)','rankForProduct(self, candidates, source, limit=8)'],
 'ISearchContext':['getOrCreate(self, key: str)','mergeCriteria(self, key: str, criteria, reset=False)','rememberResults(self, key: str, results)'],
 'IMediaStorage':['saveUpload(self, content: bytes, kind: str) -> str','read(self, reference: str) -> bytes','resolveProductImage(self, reference: str)','deleteExpiredQueryMedia(self, seconds=86400)'],
 'IPaymentGateway':['processPayment(self, orderId: int, amount, scenario: str)'],
 'IShippingProvider':['createShipment(self, orderId: int, address: str)','getStatus(self, trackingNumber: str)'],
 'IProduct':['getDetails(self, articleID: int)','filterProducts(self, category=None, query="")','compareProducts(self, ids)'],
 'ICart':['getCart(self, customerID: int)','addItem(self, customerID: int, articleID: int, quantity: int)','changeQuantity(self, customerID: int, articleID: int, quantity: int)','removeItem(self, customerID: int, articleID: int)'],
 'ICheckout':['submitCheckout(self, customerID: int, payload: dict)','cancelBeforePacking(self, customerID: int, orderID: int)'],
 'IPayment':['payOrder(self, customerID: int, orderID: int, scenario: str)','getPaymentStatus(self, orderID: int)'],
 'IFulfilment':['createShipment(self, orderID: int)','getShipmentStatus(self, orderID: int)'],
 'ISearch':['searchText(self, text: str, contextKey: str, customerID=None, reset=False)','searchVoice(self, text: str, contextKey: str, customerID=None, reset=False)','searchImage(self, content: bytes, region=None, customerID=None)'],
 'IRecommendation':['recommendForProduct(self, articleID: int, limit=8)'],
 'IAccount':['register(self, email: str, password: str, fullName: str)','login(self, email: str, password: str)','authenticate(self, token: str)','logout(self, token: str)'],
}
daos={
 'ProductDAO':['findById(self, articleID: int, connection=None)','findActive(self)','findByCriteria(self, criteria)','findByRepresentation(self, criteria)','findAlternatives(self, source)'],
 'CustomerDAO':['findById(self, customerID: int)','findByEmail(self, email: str)','saveContact(self, customerID: int, values: dict)'],
 'CartDAO':['getCart(self, customerID: int)','save(self, customerID: int, articleID: int, quantity: int, add=False)','findForUpdate(self, customerID: int, connection)'],
 'OrderDAO':['findById(self, orderID: int, connection=None)','findOwned(self, customerID: int, orderID: int)','createWithItems(self, customerID: int, payload: dict)','updateVersioned(self, orderID: int, status: str, version: int)'],
 'SearchQueryDAO':['saveWithResults(self, customerID, queryType: str, criteria: dict, query: dict, results)','findById(self, queryID: int)'],
 'PaymentDAO':['findByOrder(self, orderID: int)','saveSummary(self, orderID: int, outcome)'],
 'ShipmentDAO':['findByOrder(self, orderID: int)','saveSummary(self, orderID: int, outcome)','updateStatus(self, orderID: int, status: str)'],
 'AccountDAO':['register(self, email: str, passwordHash: str, fullName: str, role="customer")','findByEmail(self, email: str)','createSession(self, tokenHash: str, accountID: int, hours: int)','findSession(self, tokenHash: str)','deleteSession(self, tokenHash: str)'],
}
for group,folder in [(contracts,'Model/application/contract'),(daos,'DAO/contract')]:
 for name,methods in group.items():
  write(Path(folder)/(name+'.py'),'from typing import Protocol\n\nclass '+name+'(Protocol):\n'+''.join('    def '+signature+': ...\n' for signature in methods))

if __name__=='__main__': print('Entity and interface files prepared without replacing existing files.')
