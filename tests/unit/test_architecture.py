import ast
from pathlib import Path
from Model.application.config.settings import ROOT

def test_controllers_and_services_have_no_sql_or_database_driver():
    for folder in ['Controller','Model/application/service','Model/application/ai']:
        for file in (ROOT/folder).rglob('*.py'):
            source=file.read_text(encoding='utf-8');tree=ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node,ast.Import): assert not any(a.name.startswith(('mysql','psycopg','sqlite3')) for a in node.names),file
                if isinstance(node,ast.ImportFrom): assert not (node.module or '').startswith(('DAO.application.dao','mysql','psycopg','sqlite3')),file
                if isinstance(node,ast.Constant) and isinstance(node.value,str):
                    assert not node.value.lstrip().upper().startswith(('SELECT ','INSERT INTO ','UPDATE ','DELETE FROM ')),file

def test_entities_are_independent_and_core_interfaces_are_implemented():
    import importlib
    for file in (ROOT/'Model/application/entity').glob('*.py'):
        assert 'DAO' not in file.read_text(encoding='utf-8')
    pairs=[('Model.application.contract.IEmbedding','IEmbedding','Model.application.ai.MultimodalEmbedderService','MultimodalEmbedderService'),
           ('Model.application.contract.ISearch','ISearch','Model.application.service.SearchService','SearchService'),
           ('Model.application.contract.IRecommendation','IRecommendation','Model.application.service.RecommendationService','RecommendationService'),
           ('DAO.contract.ProductDAO','ProductDAO','DAO.application.dao.ProductDAOImpl','ProductDAOImpl')]
    for interface_module,name,implementation_module,implementation in pairs:
        contract=getattr(importlib.import_module(interface_module),name)
        cls=getattr(importlib.import_module(implementation_module),implementation)
        assert all(callable(getattr(cls,n,None)) for n in vars(contract) if not n.startswith('_'))
