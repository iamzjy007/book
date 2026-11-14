"""Run inside a framework directory, or specify --db PATH and --stage NAME."""
import argparse
import datetime
import json
import sqlite3
import sys
from pathlib import Path
from shared import TASK, REPO, STAGES, NOW, canon, enc, read, require, sha

def one(db, sql, args=()):
    row=db.execute(sql,args).fetchone()
    require(row is not None,'record does not exist')
    return dict(row)

def nonempty(obj,*keys):
    for key in keys:
        require(isinstance(obj.get(key),str) and obj[key].strip(),f'missing text: {key}')

def url(x):
    require(isinstance(x,str) and x.startswith(('https://','http://')),'missing HTTP(S) URL')

def date(x):
    require(isinstance(x,str),'expected a date or timestamp')
    if len(x)==10:
        datetime.date.fromisoformat(x)
    else:
        require(datetime.datetime.fromisoformat(x.replace('Z','+00:00')).tzinfo is not None,'timestamp needs UTC offset')
    return x

def next_unit(db,rid):
    return db.execute("SELECT * FROM unit WHERE book_id=? AND status!='self_reviewed' ORDER BY seq LIMIT 1",(rid,)).fetchone()

def resume(db,stage,rid,project):
    if stage=='catalog':
        project=project or 'christian-literature-catalog'
        if rid is None:
            rid=one(db,'SELECT recommended_task FROM project WHERE id=?',(project,))['recommended_task']
        r=one(db,'SELECT * FROM resume WHERE project_id=? AND task_id=?',(project,rid))
        r['cursor']=json.loads(r.pop('cursor_json') or 'null')
        r['protocol']=f'research/{project}/PLAN.md'
        r['latest_save']=db.execute('SELECT payload_json FROM receipt WHERE request_key=(SELECT request_key FROM checkpoint WHERE project_id=? AND task_id=? AND revision=?)',(project,rid,r['revision'])).fetchone()
        if r['latest_save']:
            r['latest_save']=json.loads(r['latest_save'][0])
        return r
    if rid is None:
        row=db.execute('SELECT id FROM queue LIMIT 1').fetchone()
        if not row:
            return {'queue':'empty'}
        rid=row['id']
    r=one(db,'SELECT * FROM book WHERE id=?',(rid,))
    if stage=='sources':
        original=json.loads(r.pop('baseline_json'))
        r['catalog_record']=original['source_record']
        r['source_commit']=original['source_commit']
        for table in ('attempt','locator'):
            r[table]=[json.loads(x[0]) for x in db.execute(f'SELECT detail_json FROM {table} WHERE book_id=? ORDER BY seq',(rid,))]
    else:
        r.pop('inventory_json')
        r['edition']=json.loads(r.pop('edition_json') or 'null')
        u=next_unit(db,rid)
        r['next_unit']=dict(u) if u else None
        if u:
            r['neighbors']=[dict(row) for row in db.execute('SELECT id,source_locator,source_anchor,body FROM unit WHERE book_id=? AND seq IN (?,?) ORDER BY seq',(rid,u['seq']-1,u['seq']+1))]
    return r

def catalog_save(db,p):
    project,rid=p['project'],p['id']
    args=(project,rid)
    current=one(db,'SELECT revision,cursor_json FROM resume WHERE project_id=? AND task_id=?',args)
    require(current['revision']==p['revision'],'stale checkpoint')
    when=date(p['observed_at'])
    nonempty(p,'next_action','finding')
    for r in p.get('resources',[]):
        nonempty(r,'id','title','kind')
        db.execute('INSERT INTO resource(project_id,id,title,kind,payload_json,observed_at) VALUES(?,?,?,?,?,?)',(project,r['id'],r['title'],r['kind'],enc(r),when))
    for o in p.get('observations',[]):
        nonempty(o,'id','resource_id','finding')
        db.execute('INSERT INTO observation(project_id,legacy_id,resource_id,source_file,raw_json,observed_at) VALUES(?,?,?,?,?,?)',(project,o['id'],o['resource_id'],'receipt:'+p['request_key'],enc(o),when))
        db.execute(f'UPDATE resource SET updated_at={NOW} WHERE project_id=? AND id=?',(project,o['resource_id']))
    require(p.get('sources'),'provide actual source evidence')
    for e in p['sources']:
        url(e['url'])
        nonempty(e,'read_scope')
        db.execute('INSERT OR IGNORE INTO source VALUES(?)',(e['url'],))
        if e.get('resource_id'):
            db.execute('INSERT INTO evidence(project_id,resource_id,url,origin,detail_json,observed_at) VALUES(?,?,?,?,?,?)',(project,e['resource_id'],e['url'],p['request_key'],enc(e),when))
    cursor=p['cursor']
    if rid=='eclavis-systematic':
        old=json.loads(current['cursor_json'])
        scan=p['scan']
        nonempty(scan,'ecca','decision','title')
        url(scan['url'])
        last=db.execute('SELECT MAX(ordinal) FROM scan_item WHERE project_id=? AND task_id=?',args).fetchone()[0] or 0
        require(str(scan['ecca'])==str(old['next_ecca']) and scan['ordinal']==last+1,'index order changed: reconcile before advancing')
        require(str(cursor['last_completed_ecca'])==scan['ecca'] and cursor.get('next_ecca')!=scan['ecca'],'cursor must follow verified scan')
        require('next_ecca' in cursor and set(old)<=set(cursor),'preserve cursor fields and open questions')
        if cursor['next_ecca'] is not None:
            nonempty(cursor,'next_title','next_url')
            url(cursor['next_url'])
        db.execute('INSERT INTO scan_item(project_id,task_id,ordinal,external_id,decision,resource_id,payload_json,observed_at) VALUES(?,?,?,?,?,?,?,?)',(*args,last+1,scan['ecca'],scan['decision'],scan.get('resource_id'),enc(scan),when))
    db.execute('INSERT INTO checkpoint(project_id,task_id,revision,request_key,cursor_json,next_action) VALUES(?,?,?,?,?,?)',(*args,p['revision']+1,p['request_key'],enc(cursor),p['next_action']))
    db.execute(f'UPDATE task SET updated_at={NOW} WHERE project_id=? AND task_id=?',args)
    if 'task_status' in p:
        nonempty(p,'task_status')
        db.execute('UPDATE task SET current_status=? WHERE project_id=? AND task_id=?',(p['task_status'],*args))
    if 'recommended_task' in p:
        one(db,'SELECT 1 FROM task WHERE project_id=? AND task_id=?',(project,p['recommended_task']))
        db.execute('UPDATE project SET recommended_task=? WHERE id=?',(p['recommended_task'],project))

def source_save(db,p):
    rid=p['id']
    nonempty(p,'next_action','status')
    require(p['status'] in ('fulltext_online','partial_online','metadata_only','scan_candidate','blocked','needs_review'),'invalid acquisition status')
    require(p.get('attempts'),'at least one actual check required')
    for table,items in [('attempt',p['attempts']),('locator',p.get('locators',[]))]:
        seq=db.execute(f'SELECT COALESCE(MAX(seq),-1)+1 FROM {table} WHERE book_id=?',(rid,)).fetchone()[0]
        for i,x in enumerate(items,seq):
            if table=='attempt':
                nonempty(x,'result')
                require(x.get('query') or x.get('url'),'record query or URL')
                db.execute('INSERT INTO attempt VALUES(?,?,?,?)',(rid,i,date(x['date']),enc(x)))
            else:
                url(x['url'])
                require(x['kind'] in ('fulltext','partial','metadata','scan_candidate','edition_gateway','restricted'),'invalid locator kind')
                if x['kind'] in ('fulltext','partial'):
                    nonempty(x,'edition','coverage','verification')
                db.execute('INSERT INTO locator VALUES(?,?,?,?,?,?)',(rid,i,date(x['accessed']),x['url'],x['kind'],enc(x)))
    if p['status'] in ('fulltext_online','partial_online'):
        one(db,'SELECT 1 FROM locator WHERE book_id=? AND kind=?',(rid,p['status'].split('_')[0]))
    db.execute(f'UPDATE book SET status=?,next_action=?,last_checked=?,revision=revision+1,updated_at={NOW} WHERE id=?',(p['status'],p['next_action'],date(p['observed_at']),rid))

def translation_save(db,p,book):
    rid=p['id']
    nonempty(p,'next_action')
    when=date(p['observed_at'])
    require(book['queue_order'] is not None,'outside frozen translation intake')
    if book['source_record'].startswith('sqlite:'):
        require(sha(book['inventory_json'].encode())==book['source_sha256'],'frozen acquisition snapshot differs')
    else:
        require(sha(canon(REPO/book['source_record']))==book['source_sha256'],'frozen source record differs')
    op=p['operation']
    if op=='freeze':
        require(not book['edition_json'],'edition already frozen')
        e=p['edition']
        nonempty(e,'language','edition')
        require(e['completeness']['verified'] is True,'edition incompletely verified')
        nonempty(e['completeness'],'scope','limits')
        require(e['source_urls'] and e['artifacts'] and p['units'],'provide sources, fingerprints and complete unit plan')
        for link in e['source_urls']:
            url(link)
        for a in e['artifacts']:
            url(a['url'])
            import re
            require(re.fullmatch('[0-9a-f]{64}',a['sha256']),'invalid artifact hash')
        for i,u in enumerate(p['units']):
            nonempty(u,'id','source_locator','source_anchor')
            db.execute("INSERT INTO unit(book_id,seq,id,source_locator,source_anchor,status) VALUES(?,?,?,?,?,'pending')",(rid,i,u['id'],u['source_locator'],u['source_anchor']))
        db.execute('UPDATE book SET edition_json=? WHERE id=?',(enc(e),rid))
        status='ready'
    elif op in ('blocked_source','deferred_incomplete'):
        nonempty(p,'reason')
        status=op
    elif op in ('draft','self_reviewed'):
        u=next_unit(db,rid)
        require(book['edition_json'] and u and u['id']==p['unit'],'save first unfinished frozen unit')
        nonempty(p,'body','review_note')
        body=p['body'].replace('\r\n','\n').strip()
        if op=='self_reviewed':
            require('TODO' not in body and '待翻译' not in body,'unfinished text')
        db.execute(f'UPDATE unit SET status=?,body=?,body_sha256=?,reviewed_at=?,updated_at={NOW} WHERE book_id=? AND id=?',(op,body,sha(body.encode()),when if op=='self_reviewed' else None,rid,p['unit']))
        status='translating' if next_unit(db,rid) else 'translated_self_reviewed'
    else:
        raise ValueError('unknown translation operation')
    note=p.get('review_note') or p.get('reason') or '登记底本及单元'
    db.execute(f"UPDATE book SET status=?,next_action=?,revision=revision+1,review=COALESCE(review,'')||?,updated_at={NOW} WHERE id=?",(status,p['next_action'],'\n'+when+' '+note,rid))

def save(db,stage,p):
    nonempty(p,'request_key','id')
    require(isinstance(p['revision'],int) and p['revision']>=0,'invalid expected revision')
    payload=enc(p)
    digest=sha(payload.encode())
    db.execute('BEGIN IMMEDIATE')
    with db:
        r=db.execute('SELECT * FROM receipt WHERE request_key=?',(p['request_key'],)).fetchone()
        if r:
            require(r['payload_sha256']==digest,'request key reused with different content')
            return {'revision':r['revision'],'replayed':True}
        if stage=='catalog':
            catalog_save(db,p)
        else:
            b=one(db,'SELECT * FROM book WHERE id=?',(p['id'],))
            require(b['revision']==p['revision'],'stale revision: resume again')
            if stage=='sources':
                source_save(db,p)
            else:
                require(b['status']!='translated_self_reviewed','already completed')
                translation_save(db,p,b)
        rev=p['revision']+1
        db.execute('INSERT INTO receipt(request_key,payload_sha256,subject,revision,payload_json) VALUES(?,?,?,?,?)',(p['request_key'],digest,p['id'],rev,payload))
        return {'revision':rev,'request_key':p['request_key']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['resume','save','verify','export'])
    p.add_argument('input',nargs='?',type=Path)
    p.add_argument('--id')
    p.add_argument('--project')
    p.add_argument('--stage',choices=STAGES,default=Path.cwd().name)
    p.add_argument('--db',type=Path)
    a=p.parse_args()
    require(a.stage in STAGES,'enter a framework directory or supply --stage')
    path=a.db or TASK/a.stage/'state.sqlite3'
    mode='rw' if a.command=='save' else 'ro'
    db=sqlite3.connect(path.resolve().as_uri()+'?mode='+mode,uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        if a.command=='save':
            require(a.input,'provide a UTF-8 JSON file')
            result=save(db,a.stage,read(a.input))
        elif a.command=='resume':
            result=resume(db,a.stage,a.id,a.project)
        elif a.command=='export':
            require(a.stage=='translations' and a.id,'export requires a translation book ID')
            book=one(db,'SELECT title FROM book WHERE id=?',(a.id,))
            print('# '+book['title']+'\n')
            for u in db.execute('SELECT id,body FROM unit WHERE book_id=? AND body IS NOT NULL ORDER BY seq',(a.id,)):
                print('### '+u['id']+'\n\n'+u['body']+'\n')
            return
        else:
            require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not list(db.execute('PRAGMA foreign_key_check')),'database integrity failure')
            for file in db.execute('SELECT path,sha256 FROM baseline'):
                require(sha(canon(REPO/file['path']))==file['sha256'],'legacy baseline changed: '+file['path'])
            if a.stage=='translations':
                for u in db.execute('SELECT * FROM unit WHERE body IS NOT NULL OR status="self_reviewed"'):
                    require(u['body'] and sha(u['body'].encode())==u['body_sha256'],'unit hash mismatch: '+u['id'])
            result={'verified':True,'receipts':db.execute('SELECT count(*) FROM receipt').fetchone()[0]}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        db.close()

if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,TypeError,sqlite3.Error,OSError) as e:
        sys.exit('ERROR: '+str(e))
