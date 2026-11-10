#!/usr/bin/env python3
"""Resumable candidate discovery, not full-text verification (stdlib only).
Run: python christian-text-sources/scripts/discover.py --limit 5
"""
import argparse, datetime, json, urllib.parse, urllib.request
from pathlib import Path
from refresh import ROOT, save, run

def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'BookSourceResearch/1.0 (bibliographic verification)'})
    with urllib.request.urlopen(request,timeout=20) as response:
        return json.load(response)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=5); args=ap.parse_args()
    manifest=json.loads((ROOT/'inventory/manifest.json').read_text())
    processed=0
    for item in manifest['records']:
        path=ROOT/item['path']; rec=json.loads(path.read_text()); a=rec['acquisition']
        if any(x.get('method')=='internet_archive_title_search' for x in a['attempts']): continue
        title=rec['source_record']['original_title'].split(' / ')[0].split(';')[0].replace('"','')
        query='title:("'+title+'") AND mediatype:texts'
        url='https://archive.org/advancedsearch.php?'+urllib.parse.urlencode({'q':query,'output':'json','rows':3,'fl[]':['identifier','title','creator','year']},doseq=True)
        attempt={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'internet_archive_title_search','query':query,'url':url}
        try:
            data=get(url)['response']; attempt['num_found']=data['numFound']; attempt['candidates']=data['docs']; attempt['result']='标题索引候选；未经作品身份、正文范围和访问权限核实，不能计为取得全文。'
        except Exception as e:
            attempt['result']='索引请求失败：'+str(e)
        a['attempts'].append(attempt); a['updated_at']=attempt['date']
        a['discovery_pass_done']=True
        # A search hit alone never changes acquisition.status or counts as human searching.
        save(path,rec); processed+=1;print(rec['id'],attempt.get('num_found','error'),flush=True)
        if processed>=args.limit: break
    run()
if __name__=='__main__':main()
