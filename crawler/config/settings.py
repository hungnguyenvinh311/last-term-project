from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
CATEGORIES = {"Smartphone": 1, "Laptop": 2, "Tablet": 3, "Headphones": 4, "Smartwatch": 5}

def database_options():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    return dict(host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE', 'ecommerce_electronics_demo'),
                connection_timeout=5, autocommit=False)
