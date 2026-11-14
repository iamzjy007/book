"""Exercise the shipped databases on disposable copies, with fresh CLI processes."""
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from shared import TASK, STAGES, require
from intake import transfer

def run(directory,stage,cmd,*args,ok=True):
    r=subprocess.run([sys.executable,'-B','-X','utf8',str(TASK/'workflow.py'),cmd,'--stage',stage,'--db',str(directory/(stage+'.db')),*map(str,args)],encoding='utf8',capture_output=True)
    require((r.returncode==0)==ok,r.stderr or r.stdout)
    return json.loads(r.stdout) if ok else None

def main():
    with tempfile.TemporaryDirectory() as temp:
        d=Path(temp)
        for stage in STAGES:
            shutil.copyfile(TASK/stage/'state.sqlite3',d/(stage+'.db'))
            run(d,stage,'verify')
        def save(stage,p,ok=True):
            f=d/'input.json'
            f.write_text(json.dumps(p,ensure_ascii=False),'utf8')
            return run(d,stage,'save',f,ok=ok)
        base={'revision':0,'request_key':'test','observed_at':'2026-11-14','next_action':'fixture'}
        r=run(d,'catalog','resume','--id','eclavis-systematic')
        require(r['cursor']['next_ecca']=='518','unexpected seed')
        cursor=dict(r['cursor'],last_completed_ecca='518',next_ecca='TEST')
        p=dict(base,project=r['project_id'],id=r['task_id'],finding='fixture',cursor=cursor,sources=[{'url':'https://example.org','read_scope':'fixture'}],scan={'ordinal':178,'ecca':'518','title':'fixture','decision':'fixture','url':'https://example.org'})
        save('catalog',p)
        require(save('catalog',p)['replayed'],'retry failed')
        save('catalog',dict(p,request_key='stale'),False)
        require(run(d,'catalog','resume','--id',r['task_id'])['cursor']==cursor,'wrong cursor')
        r=run(d,'sources','resume')
        require(r['id']=='modern:dydi_c:MC04','source starting point')
        p=dict(base,id=r['id'],status='fulltext_online',attempts=[{'query':'fixture','result':'fixture','date':'2026-11-14'}])
        save('sources',p,False)
        require(run(d,'sources','resume')['attempt']==r['attempt'],'partial write')
        p['locators']=[{'url':'https://example.org','kind':'fulltext','edition':'fixture','coverage':'fixture','verification':'fixture','accessed':'2026-11-14'}]
        save('sources',p)
        require(run(d,'sources','resume')['id']=='modern:dydi_c:MC05','queue did not advance')
        transfer('translations',r['id'],'',d/'sources.db',d/'translations.db')
        require(transfer('translations',r['id'],'',d/'sources.db',d/'translations.db')[1]=='already registered','duplicate intake')
        r=run(d,'translations','resume')
        require(r['id']=='lori_b:lb13' and r['next_unit']['id']=='VII.1-6','translation starting point')
        p=dict(base,id=r['id'],unit=r['next_unit']['id'],operation='draft',body='临时测试',review_note='测试')
        save('translations',p)
        require(run(d,'translations','resume')['next_unit']['body']==p['body'],'draft lost')
        save('translations',dict(p,revision=1,request_key='review',operation='self_reviewed'))
        require(run(d,'translations','resume')['next_unit']['id']!=p['unit'],'unit did not advance')
        rid='modern:dydi_c:MC04'
        p=dict(base,id=rid,operation='freeze',request_key='freeze',edition={'edition':'fixture','language':'test','source_urls':['https://example.org'],'artifacts':[{'url':'https://example.org','sha256':'0'*64}],'completeness':{'verified':True,'scope':'test','limits':'test'}},units=[{'id':'I','source_anchor':'a','source_locator':'p1'}])
        save('translations',p)
        save('translations',dict(base,id=rid,operation='self_reviewed',unit='I',body='测试',review_note='测试',revision=1,request_key='last'))
        require(run(d,'translations','resume','--id',rid)['status']=='translated_self_reviewed','completion failed')
        transfer('sources','eclavis_e15:ECCA-343','christian-literature-catalog',d/'catalog.db',d/'sources.db')
        for stage in STAGES:
            run(d,stage,'verify')
    print('PASS: baseline, rollback, retries, restart, handoffs, draft recovery and completion')

if __name__=='__main__':
    main()
