#!/usr/bin/env python3
"""Idempotently append research records; preserve acquisition state across interruption."""
import datetime
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from refresh import ROOT, save

REPO = ROOT.parent
SOURCE = 'research/modern-christian-resources/catalog.json'
SCOPE = 'modern-christian-resources'

def normalized(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value).casefold())

def canonical_url(value):
    p = urlsplit(value)
    return urlunsplit(('https', p.netloc.casefold().removeprefix('www.'), p.path.rstrip('/'), p.query, ''))

def identity(item):
    # Shared institution/domain alone does not identify a book, column or collection.
    return (normalized(item['title']), tuple(sorted(canonical_url(s['url']) for s in item['sources'])))

def import_catalog(root=ROOT, source_path=None, commit=None):
    source_path = source_path or REPO / SOURCE
    raw = source_path.read_bytes()
    catalog = json.loads(raw)
    manifest_path = root / 'inventory/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    records = {}
    provenance = {}
    identities = {}
    for path in sorted((root / 'books').glob('*/record.json')):
        rec = json.loads(path.read_text())
        records[rec['id']] = (path, rec)
        prov = rec.get('provenance', {})
        if prov.get('source_catalog') == SOURCE:
            provenance[prov['catalog_id']] = rec['id']
            if prov.get('identity'):
                identities[tuple([prov['identity'][0], tuple(prov['identity'][1])])] = rec['id']
        elif rec.get('source_catalog') == SOURCE:
            provenance[rec['source_record'].get('catalog_id', rec['id'])] = rec['id']
    sequence = max([r['sequence'] for _, r in records.values()] + [0])
    previous = manifest.get('additional_sources', {}).get(SCOPE, {})
    if commit is None and previous.get('source_catalog_sha256') == hashlib.sha256(raw).hexdigest():
        commit = previous.get('source_commit')
    commit = commit or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    mapping = []
    added = 0
    for item in catalog['items']:
        original_id = item['catalog_id']
        key = identity(item)
        rid = provenance.get(original_id) or identities.get(key)
        if not rid:
            rid = 'modern:' + original_id
            # Never overwrite a record with an ambiguous ID.
            if rid in records:
                raise ValueError('ID collision without matching provenance: ' + rid)
            sequence += 1
            source_record = {
                'id': rid, 'title_zh': item['title'], 'original_title': item['title'],
                'author_or_attribution': '见原研究完整记录；机构入口不强行归为单一作者',
                'language': '以具体版本／数字对象为准；研究主要为英语资源',
                'record_kind': item['kind'], 'area': item['group'],
                'cautions': '书目／机构介绍不等于正文；样章、单篇、单件影像不能代表全书或整库。',
                'sources': [s for e in [item] + item.get('supplemental_records', []) for s in e['sources']],
                'research_item': item,
            }
            rec = {
                'schema': 1, 'id': rid, 'sequence': sequence,
                'source_catalog': SOURCE, 'source_commit': commit,
                'provenance': {'source_catalog': SOURCE, 'catalog_id': original_id,
                               'scope': SCOPE, 'identity': key,
                               'aliases': [x['catalog_id'] for x in item.get('supplemental_records', [])]},
                'source_record': source_record,
                'acquisition': {'status': 'queued', 'searched': False, 'resources': [], 'attempts': [],
                    'next_action': '沿原研究出处取得具体版本的正文／样章；平台或馆藏先定位具名文章／卷期／单件永久ID。原研究待办：' + str(item['next']),
                    'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()},
            }
            path = root / 'books' / rid.replace(':', '--') / 'record.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            save(path, rec)
            records[rid] = (path, rec)
            provenance[original_id] = rid
            identities[key] = rid
            added += 1
        mapping.append({'catalog_id': original_id, 'target_id': rid,
                        'aliases': [x['catalog_id'] for x in item.get('supplemental_records', [])]})
    # Reconcile orphan records first written before an interrupted manifest update.
    known = {r['id'] for r in manifest['records']}
    for rid, (path, rec) in sorted(records.items(), key=lambda pair: pair[1][1]['sequence']):
        if rid not in known:
            manifest['records'].append({'id': rid, 'sequence': rec['sequence'], 'path': str(path.relative_to(root))})
    manifest.setdefault('additional_sources', {})[SCOPE] = {
        'source_catalog': SOURCE, 'source_commit': commit,
        'source_catalog_sha256': hashlib.sha256(raw).hexdigest(),
        'snapshot': 'inventory/modern-source-catalog.json', 'mapping': 'inventory/modern-import.json',
        'input_count': len(catalog['items']),
    }
    save(root / 'inventory/modern-source-catalog.json', catalog)
    save(manifest_path, manifest)
    result = {'schema': 1, 'source_catalog': SOURCE, 'source_commit': commit,
              'source_catalog_sha256': hashlib.sha256(raw).hexdigest(),
              'records': mapping, 'merged_source_aliases': catalog.get('merges', {})}
    save(root / 'inventory/modern-import.json', result)
    return {'input': len(mapping), 'added': added, 'existing': len(mapping) - added}

if __name__ == '__main__':
    print(json.dumps(import_catalog(), ensure_ascii=False))
