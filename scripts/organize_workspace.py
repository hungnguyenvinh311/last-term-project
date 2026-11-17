"""One-time, non-destructive workspace organization; paths stay inside ROOT."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def run():
    moves = []
    def move(source, destination):
        source, destination = ROOT / source, ROOT / destination
        for path in (source, destination):
            path.resolve().relative_to(ROOT.resolve())
        if not source.exists():
            return
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        moves.append([str(source.relative_to(ROOT)), str(destination.relative_to(ROOT))])

    for filename in ('001_catalog.sql', '002_example_queries.sql'):
        move('sql/' + filename, 'database/' + filename)
    if (ROOT / 'sql').exists() and not any((ROOT / 'sql').iterdir()):
        (ROOT / 'sql').rmdir()
    for filename in ('ai_smoke.py', 'ai_api_smoke.py', 'browser_smoke.py'):
        move('scripts/' + filename, 'tests/smoke/' + filename)
        path = ROOT / 'tests/smoke' / filename
        path.write_text(path.read_text(encoding='utf-8').replace('resolve().parents[1]', 'resolve().parents[2]'), encoding='utf-8')
    move('AGENT_ECOMMERCE_CRAWL_MYSQL_CLASS_DIAGRAM.md', 'docs/AGENT_ECOMMERCE_CRAWL_MYSQL_CLASS_DIAGRAM.md')
    for path in list(ROOT.iterdir()):
        if path.is_dir() and (path.name.startswith('.pytest') or path.name.startswith('pytest-cache-files-') or path.name.startswith('test-output-')):
            move(path.name, 'tests/artifacts/legacy/' + path.name)
    # Update text references only; never read environment files or generated data.
    files = [ROOT / 'README.md']
    for directory in ('docs', 'crawler', 'tests', 'scripts'):
        files.extend((ROOT / directory).rglob('*.md'))
        files.extend((ROOT / directory).rglob('*.py'))
    for path in files:
        if path == Path(__file__).resolve() or 'artifacts' in path.relative_to(ROOT).parts:
            continue
        content = path.read_text(encoding='utf-8')
        updated = content.replace('sql/001_catalog.sql', 'database/001_catalog.sql').replace('sql/002_example_queries.sql', 'database/002_example_queries.sql')
        for filename in ('ai_smoke.py', 'ai_api_smoke.py', 'browser_smoke.py'):
            updated = updated.replace('scripts/' + filename, 'tests/smoke/' + filename).replace('scripts\\' + filename, 'tests\\smoke\\' + filename)
        if updated != content:
            path.write_text(updated, encoding='utf-8')
    (ROOT / 'docs/workspace_moves.json').write_text(json.dumps(moves, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Organized {len(moves)} paths; no data files deleted.')


if __name__ == '__main__':
    run()
