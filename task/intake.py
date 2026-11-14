"""Explicit handoff of one selected resource between adjacent stages."""
import argparse
import sqlite3
from pathlib import Path
from shared import TASK, enc, require, sha
from workflow import one
import json

def transfer(stage,rid,project,src,dst):
    source=sqlite3.connect(src.resolve().as_uri()+'?mode=ro',uri=True)
    dest=sqlite3.connect(dst.resolve().as_uri()+'?mode=rw',uri=True)
    source.row_factory=dest.row_factory=sqlite3.Row
    dest.execute('PRAGMA foreign_keys=ON')
    try:
        source.execute('BEGIN')
        dest.execute('BEGIN IMMEDIATE')
        if stage=='sources':
            r=one(source,'SELECT * FROM resource WHERE project_id=? AND id=?',(project,rid))
            modern=project=='modern-christian-resources'
            key=('modern:' if modern else '')+rid
            existing=dest.execute('SELECT project_id,catalog_id FROM book WHERE id=?',(key,)).fetchone()
            if existing:
                require(tuple(existing)==(project,rid),'ID collision')
                return key,'already registered'
            item=json.loads(r['payload_json'])
            item.update(title_zh=r['title'],record_kind=r['kind'])
            item['catalog_observations']=[json.loads(x[0]) for x in source.execute('SELECT raw_json FROM observation WHERE project_id=? AND resource_id=?',(project,rid))]
            item['catalog_evidence']=[json.loads(x[0]) for x in source.execute('SELECT detail_json FROM evidence WHERE project_id=? AND resource_id=?',(project,rid))]
            baseline=enc({'source_record':item,'source_commit':one(source,'SELECT source_commit FROM project WHERE id=?',(project,))['source_commit'],'snapshot_sha256':sha(enc(item).encode())})
            seq=dest.execute('SELECT MAX(sequence)+1 FROM book').fetchone()[0]
            scope='modern-christian-resources' if modern else 'ancient-christian-literature'
            active=dest.execute('SELECT EXISTS(SELECT 1 FROM book WHERE active_scope=1 AND scope=?)',(scope,)).fetchone()[0]
            dest.execute("INSERT INTO book(id,project_id,catalog_id,sequence,scope,active_scope,status,next_action,record_path,baseline_json) VALUES(?,?,?,?,?,?,'queued',?,?,?)",(key,project,rid,seq,scope,active,'从书目证据核具体版本、正文范围及入口。','sqlite:catalog/'+project+'/'+rid,baseline))
        else:
            key=rid
            b=one(source,'SELECT * FROM book WHERE id=?',(rid,))
            require(b['status']=='fulltext_online','acquisition has no confirmed full-text version')
            existing=dest.execute('SELECT queue_order FROM book WHERE id=?',(rid,)).fetchone()
            if existing and existing['queue_order'] is not None:
                return key,'already registered'
            data={'book':b,'locators':[json.loads(x[0]) for x in source.execute('SELECT detail_json FROM locator WHERE book_id=? ORDER BY seq',(rid,))]}
            require(any(x['kind']=='fulltext' for x in data['locators']),'missing fulltext evidence')
            snapshot=enc(data)
            original=json.loads(b['baseline_json'])
            n,order=dest.execute('SELECT MAX(sequence)+1,MAX(queue_order)+1 FROM book').fetchone()
            values=(original['source_record']['title_zh'],'sqlite:sources/'+rid,sha(snapshot.encode()),original['source_commit'],snapshot,order,'needs_completeness_check','核题页、正文首尾、连续性、范围及权限，再冻结单元。')
            if existing:
                dest.execute('UPDATE book SET title=?,source_record=?,source_sha256=?,source_commit=?,inventory_json=?,queue_order=?,status=?,next_action=?,updated_at=CURRENT_TIMESTAMP,revision=revision+1 WHERE id=?',(*values,rid))
            else:
                dest.execute('INSERT INTO book(title,source_record,source_sha256,source_commit,inventory_json,queue_order,status,next_action,id,sequence) VALUES(?,?,?,?,?,?,?,?,?,?)',(*values,rid,n))
        dest.commit()
        return key,'registered'
    finally:
        source.close()
        dest.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',choices=['sources','translations'])
    p.add_argument('id')
    p.add_argument('--project',choices=['christian-literature-catalog','modern-christian-resources'],default='christian-literature-catalog')
    a=p.parse_args()
    upstream='catalog' if a.target=='sources' else 'sources'
    print(*transfer(a.target,a.id,a.project,TASK/upstream/'state.sqlite3',TASK/a.target/'state.sqlite3'))

