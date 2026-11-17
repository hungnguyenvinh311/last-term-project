from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / '.env')
load_dotenv(ROOT / '.env.app')
os.environ.setdefault('HF_HOME', str(ROOT/'data/model_cache'))
os.environ.setdefault('USE_TF', '0')
# Some local tools left a CA-file variable pointing to an uninstalled PostgreSQL.
# Repair only nonexistent paths, keeping TLS verification and valid custom CAs.
for variable in ('SSL_CERT_FILE','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE'):
    configured=os.environ.get(variable)
    if configured and not Path(configured).is_file():
        import certifi
        os.environ[variable]=certifi.where()

def database_options(database=None):
    name = database or os.getenv('APP_DATABASE', 'electronics_ecommerce')
    if name.casefold() in {'ecommerce_relationship_review', 'ecommerce_vn_retailer_demo',
                           'ecommerce_electronics_demo'}:
        raise RuntimeError('This application now uses the separate electronics_ecommerce physical-model schema; import it and set APP_DATABASE before starting.')
    return dict(host=os.getenv('MYSQL_HOST', '127.0.0.1'), port=int(os.getenv('MYSQL_PORT', '3306')),
                user=os.getenv('MYSQL_USER', 'root'), password=os.getenv('MYSQL_PASSWORD', ''),
                database=name, connection_timeout=10, autocommit=False, charset='utf8mb4')
