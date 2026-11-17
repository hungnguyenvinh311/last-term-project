from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "database" / "004_electronics_physical_data_model.sql"


def sql_text():
    return SCHEMA.read_text(encoding="utf-8")


def test_erd_sql_has_all_must_feature_tables():
    sql = sql_text()
    tables = {name.lower() for name in re.findall(r"CREATE\s+TABLE\s+`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\(", sql, re.I)}
    assert tables == {
        "user", "customer", "employee", "account", "authsession", "auditlog",
        "cart", "cartitem", "order", "orderitem", "payment", "paymentevent",
        "invoice", "shipment", "category", "product", "mobilephone", "laptop",
        "tablet", "smartwatch", "headphones", "inventory", "stockcommitment",
        "stockmovement", "stockreceipt", "searchquery", "textquery", "voicequery",
        "imagequery", "searchresult",
    }


def test_erd_sql_preserves_identity_inventory_and_payment_guards():
    sql = re.sub(r"\s+", " ", sql_text()).lower()
    required = [
        "unique index uq_account_userid on account (userid)",
        "unique index uq_paymentevent_paymentid_eventkey on paymentevent (paymentid, eventkey)",
        "foreign key (inventoryarticleid) references inventory (articleid)",
        "foreign key (orderid) references `order` (orderid)",
        "foreign key (articleid) references product (articleid)",
    ]
    for fragment in required:
        assert fragment in sql


def test_physical_schema_is_non_destructive_and_embeddings_are_persisted():
    sql = sql_text()
    upper = sql.upper()
    assert not re.search(r"\b(DROP|TRUNCATE)\s+(DATABASE|TABLE)\b", upper)
    product = re.search(r"CREATE TABLE PRODUCT \((.*?)\);", upper, re.S)
    assert product is not None
    assert "IMAGEEMBEDDING TEXT NOT NULL" in product.group(1)
    assert "TEXTEMBEDDING TEXT NOT NULL" in product.group(1)
