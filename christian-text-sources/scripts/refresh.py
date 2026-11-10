#!/usr/bin/env python3
"""Rebuild human-readable views and resumable queue from durable records; no network."""
import collections, datetime, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LABELS={'queued':'待检索','fulltext_online':'正文可直达','partial_online':'部分正文可直达','scan_candidate':'扫描入口待核','metadata_only':'仅书目／版本入口','blocked':'访问受阻','needs_review':'待版本复核'}
def save(path, obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n'); tmp.replace(path)
def run():
    manifest=json.loads((ROOT/'inventory/manifest.json').read_text())
    counts=collections.Counter(); rows=[]; queue=[]; ids=set()
    for item in manifest['records']:
        path=ROOT/item['path']; rec=json.loads(path.read_text()); rid=rec['id']; assert rid not in ids; ids.add(rid)
        a=rec['acquisition']; r=rec['source_record']; counts[a['status']]+=1
        for res in a['resources']:
            assert res['url'].startswith(('https://','http://'))
            assert res['kind'] in ['fulltext','partial','scan_candidate','metadata','edition_gateway','restricted']
            if res['kind'] in ['fulltext','partial']:
                assert res.get('coverage') and res.get('edition') and res.get('verification')
        links='；'.join(f"[{x['label']}]({x['url']})" for x in a['resources'] if x['kind'] in ['fulltext','partial','scan_candidate']) or '见档案中的既有出处'
        link=item['path'].replace('record.json','README.md')
        rows.append(f"| {item['sequence']:03d} | [{r['title_zh']}]({link}) | {LABELS[a['status']]} | {links} |")
        lines=[f"# {r['title_zh']}",'',f"- 稳定ID：`{rid}`",f"- 原题：{r['original_title']}",f"- 作者／归属：{r['author_or_attribution']}",f"- 原作语种：{r['language']}",f"- 状态：**{LABELS[a['status']]}**",f"- 原调查：`{rec['source_catalog']}` @ `{rec['source_commit'][:12]}`",'',r.get('cautions',''),'', '## 本轮资源与版源','']
        for x in a['resources']:
            lines += [f"### [{x['label']}]({x['url']})",'',f"类型：`{x['kind']}`；语种：{x.get('language','待核')}。",'',f"版本：{x.get('edition','待核')}。",'',f"覆盖范围：{x.get('coverage','待核')}。",'',f"核验：{x.get('verification','待核')}。",'',f"使用／权利：{x.get('rights_note','公开可访问不等于可再分发或可出版译本；后续按具体版本核实。')}",'']
        if not a['resources']: lines+=['尚未完成本轮正文资源检索。以下仅是原研究出处。','']
        lines+=['## 原研究出处（不自动视作全文）','']+[f"- [{s.get('publisher','来源')}]({s['url']}) — {s.get('read_scope','见原记录')}" for s in r['sources']]
        lines+=['','## 检索记录与断点','']
        for at in a['attempts']: lines.append(f"- {at.get('date','')}：{at.get('query',at.get('url',''))} — {at.get('result','')}")
        lines+=['',f"下一步：{a['next_action']}",'',f"数据：[record.json](record.json)。正文入口核实不代表逐字校勘或翻译已完成。",'']
        (path.parent/'README.md').write_text('\n'.join(lines))
        if a['status']!='fulltext_online': queue.append({'id':rid,'status':a['status'],'next_action':a['next_action'],'record_path':item['path']})
    queue.sort(key=lambda q: (0 if q['status']=='queued' else 1, next(x['sequence'] for x in manifest['records'] if x['id']==q['id'])))
    (ROOT/'CATALOG.md').write_text('# 原始内容获取总目录\n\n共110条原研究档案；一条不一定等于一部完整古书。按在线入口保存，无需下载即可继续阅读。\n\n| 序号 | 书目档案 | 获取状态 | 正文／扫描入口 |\n|---|---|---|---|\n'+'\n'.join(rows)+'\n')
    save(ROOT/'queue.json',{'schema':1,'next_task':queue[0]['id'] if queue else None,'tasks':queue})
    save(ROOT/'progress.json',{'schema':1,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'total':len(ids),'counts':dict(counts),'next_task':queue[0]['id'] if queue else None,'background_process':False,'record_files_are_authoritative':True,'resume_instruction':'先读CONTINUATION.md；优先queue第一个queued项，再按未决版本／受阻资源继续。'})
    print(json.dumps({'total':len(ids),'counts':dict(counts),'next_task':queue[0]['id'] if queue else None},ensure_ascii=False))
if __name__=='__main__': run()
