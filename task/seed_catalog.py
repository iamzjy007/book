import json, hashlib
from pathlib import Path
from shared import REPO, enc

def load(db,commit,tracked):
    for name in ('christian-literature-catalog','modern-christian-resources'):
        d = REPO/'research'/name
        def read(n):
            return json.loads((d/n).read_text('utf-8'))
        queue, catalog = read('queue.json'),read('catalog.json')
        ancient = 'records' in catalog
        db.execute('INSERT INTO project VALUES(?,?,?)',(name,queue['next_task'],commit))
        db.execute('INSERT INTO protocol VALUES(?,?,?,?)',(name,1,(d/'PLAN.md').read_text('utf-8'),(d/'CONTINUATION.md').read_text('utf-8')))
        for f in sorted(d.rglob('*')):
            if f.is_file() and f.relative_to(REPO).as_posix() in tracked:
                data=f.read_bytes()
                db.execute('INSERT INTO source_file VALUES(?,?,?,?)',(name,f.relative_to(d).as_posix(),hashlib.sha256(data).hexdigest(),data))
        for t in queue['tasks']:
            db.execute('INSERT INTO task(project_id,task_id,title,imported_status,protocol_version,legacy_json) VALUES(?,?,?,?,?,?)',(name,t['id'],t['title'],t['status'],1,enc(t)))
            db.execute('INSERT INTO checkpoint(project_id,task_id,revision,request_key,cursor_json,next_action) VALUES(?,?,?,?,?,?)',(name,t['id'],0,'import',enc(t['cursor']) if t.get('cursor') is not None else None,t.get('next','')))
        aliases = {x['from']:x['into'] for x in catalog['merge_log']} if ancient else catalog['merges']
        files = [x['path'].replace('\\','/') for x in catalog['snapshots']] if ancient else sorted({x['record_file'] for x in catalog['items']})
        for item in catalog.get('records',catalog.get('items')):
            rid=item['id' if ancient else 'catalog_id']
            db.execute('INSERT INTO resource(project_id,id,kind,title,payload_json) VALUES(?,?,?,?,?)',(name,rid,item['record_kind' if ancient else 'kind'],item['title_zh' if ancient else 'title'],enc(item)))
            for rec in [item]+item.get('supplemental_records',[]):
                for s in rec['sources']:
                    db.execute('INSERT OR IGNORE INTO source VALUES(?)',(s['url'],))
                    db.execute('INSERT INTO evidence(project_id,resource_id,url,origin,detail_json) VALUES(?,?,?,?,?)',(name,rid,s['url'],rec.get('catalog_id',rid),enc(s)))
        for f in files:
            worker=read(f)
            entries=next(worker[k] for k in ('items','entries','verified_items','works') if k in worker)
            when = next((worker[k] for k in ('research_date_beijing','checked_date_beijing','date_beijing','date') if worker.get(k)), None)
            for item in entries:
                key=Path(f).stem+':'+item['id']
                db.execute('INSERT INTO observation(project_id,legacy_id,resource_id,source_file,raw_json) VALUES(?,?,?,?,?)',(name,key,aliases.get(key,key),f,enc(item)))
                db.execute('UPDATE observation SET observed_at=? WHERE project_id=? AND legacy_id=?',(when,name,key))
                if key not in aliases:
                    db.execute('UPDATE resource SET observed_at=? WHERE project_id=? AND id=?',(when,name,key))
        for row in db.execute('SELECT id,detail_json FROM evidence WHERE project_id=?',(name,)).fetchall():
            detail=json.loads(row[1])
            db.execute('UPDATE evidence SET observed_at=? WHERE id=?',(detail.get('accessed') or detail.get('access_date'),row[0]))
        if ancient:
            for s in read('eclavis-scan.json')['records']:
                db.execute('INSERT INTO scan_item(project_id,task_id,ordinal,external_id,decision,resource_id,payload_json) VALUES(?,?,?,?,?,?,?)',(name,'eclavis-systematic',s['ordinal'],s['ecca'],s['decision'],s.get('record_id'),enc(s)))
                batch=s.get('batch')
                if not batch:
                    first=read('sessions/2026-11-10-eclavis-a01.json')
                    if s['ordinal']<=first['counts']['index_positions_scanned']:
                        batch=first['id']
                session=d/'sessions'/((batch or '')+'.json')
                when=read(session.relative_to(d)).get('date_beijing') if session.exists() else None
                db.execute('UPDATE scan_item SET observed_at=? WHERE project_id=? AND ordinal=?',(when,name,s['ordinal']))
