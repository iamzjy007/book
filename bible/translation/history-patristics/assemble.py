"""Build completed books and a human-readable progress page, without marking drafts complete."""
import hashlib,json,re
import pipeline as p

def main():
 m=p.manifest();cp=p.checkpoint(m);statepath=p.ROOT/'assembly-state.json'
 state=p.read(statepath) if statepath.exists() else {};lines=[];finished=[];changed=False
 for i,b in enumerate((b for b in m['sections'] if b['scope']=='included'),1):
  statuses=[p.validate(b,u)[0] for u in b['units']];n=statuses.count('complete');total=len(statuses)
  if n==total:
   files=[p.ROOT/'zh'/b['id']/(u['id']+'.json') for u in b['units']]
   rendering=(p.ROOT/'pipeline.py').read_bytes()
   override_path=p.ROOT/'presentation-overrides.json'
   if override_path.exists():rendering+=override_path.read_bytes()
   sig=hashlib.sha256(b''.join(f.read_bytes() for f in files)+rendering).hexdigest()
   first=p.read(files[0]);title=first['blocks'][0]['zh'];title=re.sub(r'[/\\\n\r:*?"<>|]','_',title)
   filename=f'{i:03}_{title}'
   if b.get('title_zh')!=filename:b['title_zh']=filename;changed=True
   if state.get(b['id'])!=sig or not (p.ROOT/'output'/(filename+'.txt')).exists():p.build(b);state[b['id']]=sig
   legacy=p.ROOT/'output'/(b['id']+'.txt');current=p.ROOT/'output'/(filename+'.txt')
   if legacy!=current and legacy.exists() and current.exists() and legacy.read_bytes()==current.read_bytes():legacy.unlink()
   finished.append(title)
  link=f'[{title}](<output/{filename}.txt>)' if n==total else '—'
  lines.append(f"| {i:03} | {b['title']} | {link} | {n}/{total} | {'完成' if n==total else '进行中' if n else '未开始'} |")
 if changed:p.save(p.ROOT/'manifest.json',m)
 p.save(statepath,state)
 header=f"# 续译进度\n\n已完成 {len(finished)}/54 个书卷或合集条目，{cp['completed_units']}/{cp['included_units']} 个 EPUB 文件单元。文件单元不等于章或节。\n\n下一个断点：`{json.dumps(cp['next'],ensure_ascii=False)}`。\n\n这是程序生成的工作进度，不代表已重新定义典外文献范围。已完成分卷TXT见 `output/`。\n\n| 顺序 | 原文书卷/合集 | 中文成品 | 完成单元 | 状态 |\n|---|---|---|---:|---|\n"
 (p.ROOT/'PROGRESS.md').write_text(header+'\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({'completed_books':len(finished),'completed_units':cp['completed_units'],'total_units':cp['included_units'],'next':cp['next'],'errors':cp['errors']},ensure_ascii=False))
if __name__=='__main__':main()
