#!/usr/bin/env python3
"""Offline extraction, validation, checkpointing and assembly; does not call models."""
from pathlib import Path
import argparse, hashlib, json, re, zipfile, xml.etree.ElementTree as ET
from functools import lru_cache
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent.parent/'The Ultimate Ethiopian Bible in English.epub'
X='{http://www.w3.org/1999/xhtml}'; N='{http://www.daisy.org/z3986/2005/ncx/}'; O='{http://www.idpf.org/2007/opf}'
def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
 tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(p)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def inventory():
 with zipfile.ZipFile(SOURCE) as z:
  opf=ET.fromstring(z.read('OEBPS/content.opf'))
  items={e.get('id'):e.get('href') for e in opf.findall(O+'manifest/'+O+'item')}
  spine=[items[e.get('idref')] for e in opf.findall(O+'spine/'+O+'itemref')]
  ncx=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.ncx'))))
  points=ncx.findall(N+'navMap/'+N+'navPoint');entries=[]
  titles=[p.findtext(N+'navLabel/'+N+'text') for p in points]
  a=titles.index('GENESIS');b=titles.index('REVELATION');assert b-a+1==66
  start=titles.index('APOCRYPHAL ESTHER');end=titles.index('THE SIBYLLINE ORACLES')
  deferred={'SEVEN EPISTLES OF IGNATIUS','EPISTLE OF POLYCARP TO THE PHILIPPIANS','EPISTLE OF MATHETES TO DIOGNETUS','EXPOSITION OF THE ORACLES OF THE LORD','APOLOGY OF ARISTIDES','APOLOGY FOR CHRISTIANITY'}
  boundary={'1 CLEMENT','2 CLEMENT','MARTYRDOM OF POLYCARP','ACTS OF PERPETUA AND FELICITAS'}
  for i,p in enumerate(points):
   title=titles[i];href=p.find(N+'content').get('src').split('#')[0]
   lo=spine.index(href); hi=spine.index(points[i+1].find(N+'content').get('src').split('#')[0]) if i+1<len(points) else len(spine)
   state='excluded_editorial'
   if a<=i<=b:state='excluded_canonical_66'
   elif start<=i<=end or title=='JASHER':state='included'
   elif end<i<titles.index('ABOUT THE BIBLE'):state='deferred_history_patristics'
   if title in deferred:state='deferred_history_patristics'
   if title in boundary:state='scope_review'
   sid=re.sub('[^a-z0-9]+','-',title.lower()).strip('-')
   units=[]
   labels={q.find(N+'content').get('src').split('#')[0]:q.findtext(N+'navLabel/'+N+'text') for q in p.iter(N+'navPoint')}
   for f in spine[lo:hi]:units.append({'id':Path(f).stem,'href':'OEBPS/'+f,'label':labels.get(f,'Continuation'),'sha256':sha(z.read('OEBPS/'+f))})
   entries.append({'id':sid,'title':title,'source_order':i+1,'scope':state,'units':units})
 return {'schema':1,'source':SOURCE.name,'source_sha256':sha(SOURCE.read_bytes()),'scope_decision':'Only extracanonical texts; defer history and patristics. Boundary works remain scope_review. Hermas explicitly included.','sections':entries}
def manifest():
 m=read(ROOT/'manifest.json')
 if sha(SOURCE.read_bytes())!=m['source_sha256']:raise ValueError('Source EPUB changed: reconcile before resuming; do not reset progress.')
 return m
@lru_cache(maxsize=2)
def archive(path,mtime,size):return zipfile.ZipFile(path)
def source_unit(book,unit):
 stat=SOURCE.stat();raw=archive(str(SOURCE),stat.st_mtime_ns,stat.st_size).read(unit['href'])
 assert sha(raw)==unit['sha256']
 body=ET.fromstring(raw).find(X+'body');blocks=[];assets=[];skipped=[]
 def clean(t):return re.sub(r'\s+',' ',t).strip()
 def add(e):
  tag=e.tag.split('}')[-1];text=clean(''.join(e.itertext()))
  for img in e.iter(X+'img'):assets.append(dict(img.attrib))
  if not text:return
  if tag=='p' and e.findall('.//'+X+'a') and re.fullmatch(r'[\d\s–—,.:;\-]+',text):
   skipped.append({'kind':'chapter_navigation','text':text});return
  # Verse markers in this edition are span.class_s1ZWT. Preserve grouping.
  encoded=''
  def walk(node):
   nonlocal encoded
   mark=node.tag==X+'span' and node.get('class')=='class_s1ZWT' and re.fullmatch(r'\d+',clean(''.join(node.itertext())))
   if mark:encoded+='\x1e'+clean(''.join(node.itertext()))+'\x1f'
   else:
    encoded+=node.text or ''
    for c in node:walk(c);encoded+=c.tail or ''
  walk(e)
  parts=re.split(r'\x1e(\d+)\x1f',encoded);group=len(blocks)+1
  if len(parts)>1:
   if clean(parts[0]):blocks.append({'kind':tag,'text':clean(parts[0]),'group':group})
   for j in range(1,len(parts),2):blocks.append({'kind':'verse','verse':parts[j],'text':clean(parts[j+1]),'group':group})
  else:blocks.append({'kind':tag,'text':text,'group':group})
 def visit(e):
  tag=e.tag.split('}')[-1]
  if tag in ['p','h1','h2','h3','h4','h5','h6','tr'] or not len(e):add(e)
  else:
   if (e.text or '').strip():blocks.append({'kind':'text','text':clean(e.text),'group':len(blocks)+1})
   for c in e:
    visit(c)
    if (c.tail or '').strip():blocks.append({'kind':'text','text':clean(c.tail),'group':len(blocks)+1})
 for e in body:visit(e)
 for i,v in enumerate(blocks,1):v['id']=f'p{i:04}'
 return {'book_id':book['id'],'unit_id':unit['id'],'source_href':unit['href'],'source_sha256':unit['sha256'],'label':unit['label'],'blocks':blocks,'assets':assets,'skipped_navigation':skipped}
def validate(b,u):
 f=ROOT/'zh'/b['id']/(u['id']+'.json')
 if not f.exists():return 'pending',None
 try:
  t=read(f);s=source_unit(b,u)
  assert t['book_id']==b['id'] and t['unit_id']==u['id'],'identity mismatch'
  assert t['source_sha256']==u['sha256'],'source mismatch'
  assert [x['id'] for x in t['blocks']]==[x['id'] for x in s['blocks']],'block IDs/count/order mismatch'
  assert all(isinstance(x['zh'],str) and x['zh'].strip() and (re.search('[\u4e00-\u9fff]',x['zh']) or (not re.search(r'[A-Za-z0-9]',en['text']) and not re.search(r'[A-Za-z0-9]',x['zh'])) or (re.fullmatch(r'\d+[.]',en['text'].strip()) and x['zh'].strip()==en['text'].strip())) for en,x in zip(s['blocks'],t['blocks'])),'empty/non-Chinese translation'
  assert isinstance(t['notes'],list) and isinstance(t['references'],list),'notes/references missing'
  if t.get('reviewed') is not True:return 'draft',None
  assert not s['assets'] or t.get('assets_reviewed') is True,'images require review'
  assert not any(re.search('TODO|待翻译|译文待补',x['zh']) for x in t['blocks']),'placeholder'
  return 'complete',None
 except Exception as e:return 'invalid',str(e)
def checkpoint(m):
 records=[];errors=[];n=0;total=0;next_unit=None
 for b in m['sections']:
  if b['scope']!='included':continue
  for u in b['units']:
   state,error=validate(b,u);total+=1;n+=state=='complete'
   r={'book_id':b['id'],'unit_id':u['id'],'label':u['label'],'status':state}
   records.append(r)
   if error:errors.append({**r,'error':error})
   if state!='complete' and next_unit is None:next_unit=r
 # Do not silently pass an unresolved scope boundary in reading order.
 positions={b['id']:i for i,b in enumerate(m['sections'])}
 first_review=next((b for b in m['sections'] if b['scope']=='scope_review'),None)
 if first_review and (next_unit is None or positions[first_review['id']]<positions[next_unit['book_id']]):
  next_unit={'book_id':first_review['id'],'status':'scope_review','message':'Clarify inclusion before advancing past this work.'}
 save(ROOT/'progress.json',{'schema':1,'source_sha256':m['source_sha256'],'completed_units':n,'included_units':total,'next':next_unit,'errors':errors,'units':records})
 return {'completed_units':n,'included_units':total,'next':next_unit,'errors':errors}
def build(b):
 texts=[];notes=[]
 overrides=read(ROOT/'presentation-overrides.json') if (ROOT/'presentation-overrides.json').exists() else {}
 for u in b['units']:
  state,err=validate(b,u)
  if state!='complete':raise ValueError(f"{u['id']}: {state} {err}")
  s=source_unit(b,u);t=read(ROOT/'zh'/b['id']/(u['id']+'.json'))
  chunk=[];prev=None
  for en,zh in zip(s['blocks'],t['blocks']):
   val=zh['zh'];kind=en['kind']
   override=overrides.get('/'.join([b['id'],u['id'],en['id']]))
   if override:
    assert override['source_sha256']==s['source_sha256'],'presentation source changed'
    assert kind=='verse' and en['verse']==override['expected_marker'],'presentation marker changed'
    assert override['action']=='join_previous' and chunk and prev==en['group'],'invalid presentation join'
    chunk[-1]+=val
    prev=en['group']
    continue
   if kind.startswith('h') and kind[1:].isdigit():chunk.append('\n'+'#'*int(kind[1:])+' '+val+'\n')
   elif kind=='verse':
    if prev!=en['group']:chunk.append('')
    chunk.append(en['verse']+' '+val)
   else:chunk.append('\n'+val+'\n')
   prev=en['group']
  texts.append('\n'.join(chunk).strip());notes.extend(t['notes'])
 if notes:texts.append('## 原文修正说明与译者注\n\n'+'\n\n'.join(notes))
 out='\n\n'.join(texts)+'\n';title=b.get('title_zh',b['id'])
 p=ROOT/'output'/(title+'.txt');p.write_text(out,encoding='utf-8')
 return str(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['init','status','next','source','build']);p.add_argument('book',nargs='?');p.add_argument('unit',nargs='?');a=p.parse_args()
 if a.command=='init':
  assert not (ROOT/'manifest.json').exists(),'Manifest exists; never overwrite a live project.'
  save(ROOT/'manifest.json',inventory())
 m=manifest()
 if a.command in ['init','status','next']:print(json.dumps(checkpoint(m),ensure_ascii=False,indent=2));return
 b=next(b for b in m['sections'] if b['id']==a.book)
 if a.command=='source':print(json.dumps(source_unit(b,next(u for u in b['units'] if u['id']==a.unit)),ensure_ascii=False,indent=2))
 if a.command=='build':print(build(b))
if __name__=='__main__':main()
