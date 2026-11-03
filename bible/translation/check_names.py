"""Report possible proper-name inconsistencies; human review required."""
import json,re,hashlib
import pipeline as p
m=p.manifest();gloss=p.read(p.ROOT/'glossary.json');terms=gloss['terms'];issues=[]
reviews=p.read(p.ROOT/'name-reviews.json') if (p.ROOT/'name-reviews.json').exists() else {}
contexts=gloss.get('context_terms',{})
for b in m['sections']:
 if b['scope']!='included':continue
 effective={**terms,**contexts.get(b['id'],{})}
 patterns=[(eng,cn,re.compile(r'\b'+re.escape(eng)+r'\b')) for eng,cn in effective.items() if eng not in ['God','Lord','Nisan','Adar'] and re.fullmatch('[A-Z][a-z]+',eng)]
 for u in b['units']:
  f=p.ROOT/'zh'/b['id']/(u['id']+'.json')
  if not f.exists():continue
  t=p.read(f)
  if t.get('reviewed') is not True:continue
  s=p.source_unit(b,u)
  for i,(en,zh) in enumerate(zip(s['blocks'],t['blocks'])):
   for eng,cn,pattern in patterns:
    if not pattern.search(en['text']):continue
    expected=contexts.get(f"{b['id']}:{u['id']}:{en['id']}",{}).get(eng,cn)
    accepted=[expected]+gloss.get('accepted_variants',{}).get(eng,[])
    if any(v in zh['zh'] for v in accepted):continue
    key=f"{b['id']}:{u['id']}:{en['id']}:{eng}"
    radius=reviews.get(key,{}).get('radius',1)
    window=json.dumps(t['blocks'][max(0,i-radius):i+radius+1],ensure_ascii=False,sort_keys=True)
    if reviews.get(key,{}).get('sha256')==hashlib.sha256(window.encode()).hexdigest():continue
    issues.append({'book':b['id'],'unit':u['id'],'block':en['id'],'term':eng,'expected':expected,'zh':zh['zh']})
p.save(p.ROOT/'name-flags.json',issues)
print(json.dumps(issues,ensure_ascii=False))
