# Workspace organization

The root keeps the application entry point, runtime configuration, dependencies and main architecture packages.

| Directory | Responsibility |
| --- | --- |
| `View`, `Controller`, `Model`, `DAO` | MVC source code |
| `config`, `infrastructure` | Configuration and infrastructure adapters |
| `crawler` | Catalogue acquisition, normalization and import |
| `database` | SQL schemas and inspection queries |
| `scripts` | Administrative commands, data preparation and evaluation tools |
| `tests` | Unit/integration tests, smoke scripts and temporary test artifacts |
| `data` | Product images, manifests, model cache and recorded evaluation results |
| `docs` | Setup, design, implementation notes and original task specification |

SQL previously under `sql/` now lives in `database/`. The importer and documentation use the new location.
The three smoke scripts now live under `tests/smoke/`; their Python import paths were adjusted.
Old root-level pytest/test-output directories were preserved under `tests/artifacts/legacy/`.
Pytest defaults now place temporary files and cache inside `tests/artifacts/` and exclude those files from test discovery.
Product data, historical experiments, private environment files, virtual environments and application packages were preserved.
`workspace_moves.json` records all relocated paths. Previously running terminals should use the new smoke/SQL paths for subsequent commands.
