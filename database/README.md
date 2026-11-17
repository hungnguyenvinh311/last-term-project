# Database SQL

- `004_electronics_physical_data_model.sql` is the current target schema generated from the Physical Data Model in `Minor thesis`. It creates the isolated `electronics_ecommerce` database and the electronics e-commerce tables and keys. Use it for the redesigned application.
- `001_catalog.sql` and `002_application.sql` describe the earlier schema and are retained for the existing implementation's regression tests. Do not apply them after the new physical model: they use different table names and relations.
- `002_example_queries.sql` is read-only documentation, not a migration.

The new physical model is separate from the old migrations. The application must connect to `electronics_ecommerce` after the SQL is installed; it must not point at the legacy schema after its DAOs are switched. `scripts/import_catalog_to_physical_schema.py` previews and can explicitly copy the existing catalogue to an empty target without deleting or modifying source data. Database connection code stays in `DAO/application/dao`; catalogue transfer tools stay in `scripts`.
