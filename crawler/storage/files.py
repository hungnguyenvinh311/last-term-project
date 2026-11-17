from pathlib import Path
import json
import os
import tempfile

def load_json(path, default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def save_json(path, value):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=p.parent, prefix=p.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
        os.replace(tmp,p)
    finally:
        if Path(tmp).exists(): Path(tmp).unlink()
