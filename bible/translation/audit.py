"""Heuristic triage only; flags require source comparison, not automatic rewriting."""
import json,re,hashlib
import pipeline as p

def main():
 m=p.manifest();issues=[];count=0;words=0
 reviews=p.read(p.ROOT/'audit-reviews.json') if (p.ROOT/'audit-reviews.json').exists() else {}
 for b in m['sections']:
  if b['scope']!='included':continue
  for u in b['units']:
   f=p.ROOT/'zh'/b['id']/(u['id']+'.json')
   if not f.exists():continue
   t=p.read(f)
   if t.get('reviewed') is not True:continue
   s=p.source_unit(b,u)
   for en,zh in zip(s['blocks'],t['blocks']):
    nw=len(re.findall(r'\b[A-Za-z]+\b',en['text']));nc=len(re.findall('[\u4e00-\u9fff]',zh['zh']));count+=1;words+=nw
    approved=reviews.get(f"{b['id']}:{u['id']}:{en['id']}",{}).get('sha256')==hashlib.sha256(zh['zh'].encode()).hexdigest()
    if nw>35 and nc/nw<0.7 and not approved:issues.append({'book':b['id'],'unit':u['id'],'block':en['id'],'reason':f'short {nc} Han / {nw} words'})
    if re.search(r'(?:[A-Za-z]{2,}[ ,.;:\-]+){8,}',zh['zh']):issues.append({'book':b['id'],'unit':u['id'],'block':en['id'],'reason':'long English run'})
 p.save(p.ROOT/'audit-flags.json',issues)
 print(json.dumps({'translated_blocks':count,'source_words_covered':words,'flags':issues},ensure_ascii=False))
if __name__=='__main__':main()
