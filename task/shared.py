import hashlib
import json
from pathlib import Path

TASK = Path(__file__).resolve().parent
REPO = TASK.parent
STAGES = ('catalog', 'sources', 'translations')
NOW = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"

def enc(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canon(path):
    return path.read_bytes().replace(b'\r\n', b'\n')

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def require(test, message):
    if not test:
        raise ValueError(message)

