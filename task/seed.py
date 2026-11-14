"""Build a fresh snapshot from a clean baseline. Never rebuild over live progress."""
import argparse
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from shared import TASK, REPO, STAGES, canon, enc, read, require, sha
import seed_catalog

def load_sources(db):
    d = REPO/'christian-text-sources'
    m = read(d/'inventory/manifest.json')
    for entry in m['records']:
        rec = read(d/entry['path'])
        rid, a = rec['id'], rec['acquisition']
        require(rid == entry['id'], 'manifest mismatch')
        prov = rec.get('provenance', {})
        scope = prov.get('scope','ancient-christian-literature')
        db.execute('INSERT INTO book(id,project_id,catalog_id,sequence,scope,active_scope,status,next_action,last_checked,record_path,baseline_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (rid,Path(rec['source_catalog']).parent.name,prov.get('catalog_id',rid),rec['sequence'],scope,int(scope==m['active_scope']),a['status'],a['next_action'],a.get('updated_at'),entry['path'],enc(rec)))
        for i,x in enumerate(a['attempts']):
            db.execute('INSERT INTO attempt VALUES(?,?,?,?)',(rid,i,x.get('date'),enc(x)))
        for i,x in enumerate(a['resources']):
            db.execute('INSERT INTO locator VALUES(?,?,?,?,?,?)',(rid,i,x.get('accessed'),x['url'],x['kind'],enc(x)))
    require([r[0] for r in db.execute('SELECT id FROM queue')]==[t['id'] for t in read(d/'queue.json')['tasks']], 'source queue mismatch')

def load_translations(db):
    d = REPO/'christian-text-translations'
    inv = read(d/'inventory/books.json')
    queue = {t['id']:t for t in read(d/'queue.json')['tasks']}
    for r in inv['records']:
        rid = r['id']
        require(sha(canon(REPO/r['record_path']))==r['record_sha256'], 'source drift '+rid)
        t = queue.get(rid,{})
        b = d/'books'/r['slug']
        edition = read(b/'source.json') if (b/'source.json').exists() else None
        review = (b/'review.md').read_text(encoding='utf8') if (b/'review.md').exists() else None
        db.execute('INSERT INTO book(id,sequence,title,source_record,source_sha256,source_commit,inventory_json,queue_order,status,next_action,edition_json,review) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (rid,r['sequence'],r['title'],r['record_path'],r['record_sha256'],inv['source_commit'],enc(r),t.get('order'),t.get('status',r['initial_translation_status']),t.get('next_action'),enc(edition) if edition else None,review))
        if not (b/'record.json').exists():
            continue
        rec = read(b/'record.json')
        bodies = {}
        if (b/'translation.md').exists():
            parts = re.split(r'^### (\S+)[ \t]*$',(b/'translation.md').read_text(encoding='utf8'),flags=re.M)
            bodies = dict(zip(parts[1::2],(v.strip() for v in parts[2::2])))
            require(len(bodies)==len(parts[1::2]),'duplicate block '+rid)
        units = rec.get('units',[])
        require(set(bodies)<=set(u['id'] for u in units),'unregistered text '+rid)
        for i,u in enumerate(units):
            body = bodies.get(u['id'])
            digest = sha(body.encode()) if body else None
            if u['status']=='self_reviewed':
                require(body and digest==u['translation_sha256'],'translation mismatch '+rid+'/'+u['id'])
            db.execute('INSERT INTO unit(book_id,seq,id,source_locator,source_anchor,status,body,body_sha256,reviewed_at) VALUES(?,?,?,?,?,?,?,?,?)',
                       (rid,i,u['id'],u['source_locator'],u['source_anchor'],u['status'],body,digest,rec.get('review',{}).get('date') if u['status']=='self_reviewed' else None))
        require(rec['next_unit']==next((u['id'] for u in units if u['status']!='self_reviewed'),None),'unit cursor mismatch '+rid)
    require(db.execute('SELECT id FROM queue LIMIT 1').fetchone()[0]==read(d/'progress.json')['next_task'],'translation queue mismatch')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=STAGES)
    p.add_argument('output',type=Path,help='New file only')
    a=p.parse_args()
    require(not a.output.exists(),'output exists; choose an unused path')
    dirs={'catalog':['research/christian-literature-catalog','research/modern-christian-resources'],'sources':['christian-text-sources'],'translations':['christian-text-translations','christian-text-sources/books']}[a.stage]
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=REPO).decode('utf8')
    require(not git('status','--porcelain','--',*dirs).strip(),'baseline has local changes')
    commit=git('rev-parse','HEAD').strip()
    tracked=set(git('ls-files','-z','--',*dirs).strip('\0').split('\0'))
    with tempfile.TemporaryDirectory(dir=a.output.parent) as temp:
        path=Path(temp)/'seed.sqlite3'
        db=sqlite3.connect(path)
        try:
            db.executescript((TASK/'common.sql').read_text('utf8'))
            db.executescript((TASK/a.stage/'schema.sql').read_text('utf8'))
            if a.stage=='catalog':
                seed_catalog.load(db,commit,tracked)
            elif a.stage=='sources':
                load_sources(db)
            else:
                load_translations(db)
            for f in sorted(tracked):
                db.execute('INSERT INTO baseline VALUES(?,?,?)',(f,sha(canon(REPO/f)),commit))
            db.commit()
            require(db.execute('PRAGMA integrity_check').fetchone()==('ok',) and not list(db.execute('PRAGMA foreign_key_check')),'invalid snapshot')
        finally:
            db.close()
        with path.open('rb') as src,a.output.open('xb') as dst:
            import shutil
            shutil.copyfileobj(src,dst)

if __name__=='__main__':
    main()
