"""Validate and assemble the Hebrew-based review independently of the English edition."""
from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
def read(p):return json.loads(p.read_text())
def save(p,v):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def margin_text(x):
 text=(f"第{x.get('near_verse','')}节附近：" if x.get('near_verse') else '')+x['zh']
 if x.get('uncertainty'):text+='\n〔译校说明：'+x['uncertainty']+'〕'
 if x.get('verification') and re.search('待核|不能|未能|尚未|不确定',x['verification']):
  text+='\n〔核对限制：'+x['verification']+'〕'
 return text
def check():
 expected=read(ROOT/'verse-index.json')['chapters']
 for source in read(ROOT/'sources.json')['sources']:
  assert hashlib.sha256((REPO/source['path']).read_bytes()).hexdigest()==source['sha256'],'Hebrew source PDF changed; reconcile before continuing'
 done=[];pending=[];errors=[];records=[]
 for n in range(1,92):
  f=ROOT/f'{n:03}.json'
  if not f.exists():pending.append(n);continue
  try:
   d=read(f);assert d['chapter']==n,'wrong chapter'
   if d.get('status')!='reviewed':pending.append(n);continue
   vs=d['verses'];assert vs and all(re.search('[\u4e00-\u9fff]',x['zh']) for x in vs),'missing Chinese'
   assert len(vs)==expected[str(n)],'incomplete chapter verse index'
   assert [x['verse'] for x in vs]==list(range(1,len(vs)+1)),'verse sequence'
   assert isinstance(d['notes'],list),'notes missing'
   assert isinstance(d['marginalia'],list),'marginalia assessment missing'
   for year,lo,hi in [('1987',15,291),('1625',16,311)]:
    pages=d['source_pages'][year];assert pages and all(isinstance(x,int) and lo<=x<=hi for x in pages),'source page range'
   done.append(n);records.append(d)
  except Exception as e:errors.append({'chapter':n,'error':str(e)});pending.append(n)
 v=read(ROOT/'progress.json');v.update(completed_chapters=done,next_chapter=min(pending) if pending else None,errors=errors,total_chapters=91)
 save(ROOT/'progress.json',v)
 lines=['# 雅煞珥书希伯来文重审进度','',f'已完成 {len(done)}/91 章；下一未完成章：{min(pending) if pending else "无"}。','', '1987版为底本，1625版对校；完成标记同时要求正文、原刊旁注和校勘说明已处理。','', '| 章 | 状态 | 1987扫描页 | 1625扫描页 |','|---:|---|---|---|']
 for n in range(1,92):
  d=next((d for d in records if d['chapter']==n),None)
  lines.append(f'| {n} | '+('已审' if d else '待完成')+' | '+(', '.join(map(str,d['source_pages']['1987'])) if d else '—')+' | '+(', '.join(map(str,d['source_pages']['1625'])) if d else '—')+' |')
 (ROOT/'PROGRESS.md').write_text('\n'.join(lines)+'\n')
 if len(done)==91 and not errors:
  parts=['# 雅煞珥书（希伯来文重审版）','以1987年耶路撒冷版为工作底本，1625年威尼斯版对校。章节和节号沿用此前译本作定位，并非希伯来原刊的节号。正文全91章；原刊旁注与校勘说明另列，旁注是原注者的意见。','1625年现有扫描在第12章、第41—42章交界及第54章相应位置缺叶，缺失部分依据1987年版译出，具体范围见章末说明。少数旁注疑字及难定释义如实标明，不把推测冒称定论。中文参考仅用于对读与措辞借鉴，最终译义依据希伯来文。']
  for d in records:
   chapter=[f"## 第{d['chapter']}章"]
   if d.get('heading') and not re.fullmatch(r'第[0-9一二三四五六七八九十百零〇]+章',d['heading'].strip()):chapter.append(d['heading'])
   chapter.append('\n'.join(f"{x['verse']} {x['zh']}" for x in d['verses']))
   if d['marginalia']:chapter.append('原刊旁注\n\n'+'\n\n'.join(margin_text(x) for x in d['marginalia']))
   if d['notes']:chapter.append('校勘与修订说明\n\n'+'\n\n'.join(d['notes']))
   rendered='\n\n'.join(chapter)
   targets=list(ROOT.glob(f"{d['chapter']:03}_*.txt"))
   assert len(targets)==1,'chapter TXT target missing or ambiguous'
   targets[0].write_text(rendered+'\n')
   parts.append(rendered)
  target=ROOT/'雅煞珥书_希伯来文重审版.txt';target.write_text('\n\n'.join(parts)+'\n')
 print(json.dumps({'completed':len(done),'total':91,'next':min(pending) if pending else None,'errors':errors},ensure_ascii=False))
if __name__=='__main__':check()
