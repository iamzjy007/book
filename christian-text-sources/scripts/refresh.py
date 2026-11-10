#!/usr/bin/env python3
"""Rebuild human-readable views and resumable queue from durable records; no network."""
import collections, datetime, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LABELS={'queued':'待检索','fulltext_online':'正文可直达','partial_online':'部分正文可直达','scan_candidate':'扫描入口待核','metadata_only':'仅书目／版本入口','blocked':'访问受阻','needs_review':'待版本复核'}
def save(path, obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n'); tmp.replace(path)
def write_text(path, value):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(value); tmp.replace(path)

def run():
    manifest=json.loads((ROOT/'inventory/manifest.json').read_text())
    counts=collections.Counter(); rows=[]; queue=[]; ids=set(); sequences=set(); paths=set()
    for item in manifest['records']:
        path=ROOT/item['path']; rec=json.loads(path.read_text()); rid=rec['id']; assert rid not in ids; ids.add(rid)
        assert rid == item['id'] and rec['sequence'] == item['sequence'], rid
        assert item['sequence'] not in sequences and item['path'] not in paths, rid
        sequences.add(item['sequence']); paths.add(item['path'])
        a=rec['acquisition']; r=rec['source_record']; assert a['status'] in LABELS; counts[a['status']]+=1
        if a['status']=='fulltext_online': assert any(x['kind']=='fulltext' for x in a['resources']), rid
        if a['status']=='partial_online': assert any(x['kind']=='partial' for x in a['resources']), rid
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
            for key, title in [('direct_file','直接数据文件'),('parts','分册／章节'),('sample_urls','抽查页')]:
                values=x.get(key,[])
                if isinstance(values,str): values=[values]
                if values:
                    lines += [title+'：','']
                    for v in values:
                        u=v if isinstance(v,str) else v['url']
                        label=str(v.get('number','页面')) if isinstance(v,dict) else '页面'
                        lines.append(f'- [{label}]({u})')
                    lines.append('')
        if not a['resources']: lines+=['尚未完成本轮正文资源检索。以下仅是原研究出处。','']
        lines+=['## 原研究出处（不自动视作全文）','']+[f"- [{s.get('publisher','来源')}]({s['url']}) — {s.get('read_scope','见原记录')}" for s in r['sources']]
        lines+=['','## 检索记录与断点','']
        for at in a['attempts']: lines.append(f"- {at.get('date','')}：{at.get('query',at.get('url',''))} — {at.get('result','')}")
        lines+=['',f"下一步：{a['next_action']}",'',f"数据：[record.json](record.json)。正文入口核实不代表逐字校勘或翻译已完成。",'']
        write_text(path.parent/'README.md', '\n'.join(lines))
        if a['status']!='fulltext_online': queue.append({'id':rid,'status':a['status'],'next_action':a['next_action'],'record_path':item['path'], 'scope':rec.get('provenance',{}).get('scope','ancient-christian-literature'), 'sequence':item['sequence'], 'updated_at':a.get('updated_at','')})
    # New scope first; unfinished imported tasks survive every refresh. For revisits,
    # oldest attempt first prevents repeatedly retrying the same blocked record.
    active=manifest.get('active_scope')
    queue.sort(key=lambda q: (0 if q['scope']==active else 1, 0 if q['status']=='queued' else 1,
                             '' if q['status']=='queued' else q['updated_at'], q['sequence']))
    write_text(ROOT/'CATALOG.md', f'# 原始内容获取总目录\n\n共{len(ids)}条资源档案，涵盖古代与近现代研究；包括书籍、作者、事工、期刊和馆藏入口，不能统称为完整书籍。按在线路径保存，具体范围见各档案。\n\n| 序号 | 书目档案 | 获取状态 | 正文／扫描入口 |\n|---|---|---|---|\n'+'\n'.join(rows)+'\n')
    scope_counts={}
    modern_rows=[]
    for item in manifest['records']:
        rec=json.loads((ROOT/item['path']).read_text())
        scope=rec.get('provenance',{}).get('scope','ancient-christian-literature')
        stats=scope_counts.setdefault(scope, collections.Counter())
        stats[rec['acquisition']['status']]+=1
        if scope=='modern-christian-resources':
            a=rec['acquisition']; r=rec['source_record']
            links='；'.join(f"[{x['label']}]({x['url']})" for x in a['resources']) or '尚未执行内容获取，原研究出处见独立档案'
            modern_rows.append(f"| {item['sequence']:03d} | [{r['title_zh']}]({item['path'].replace('record.json','README.md')}) | {r.get('record_kind','')} | {LABELS[a['status']]} | {links} |")
    if modern_rows:
        summary=scope_counts['modern-christian-resources']
        write_text(ROOT/'MODERN-PROGRESS.md', '# 近现代资源内容获取进度\n\n' + f"共{sum(summary.values())}条去重资源；已初检{sum(summary.values())-summary.get('queued',0)}条、待初检{summary.get('queued',0)}条。部分正文{summary.get('partial_online',0)}条、仅书目／版本入口{summary.get('metadata_only',0)}条。书籍、作者、文章平台、期刊及馆藏分列；单篇全文不代表全站或全书取得。\n\n" + f"下一任务：`{queue[0]['id'] if queue else None}`。断点以[queue.json](queue.json)、各条record及[最新阶段报告](REPORT.md)为准。\n\n" + '| 序号 | 资源档案 | 原研究类型 | 获取状态 | 已核资源及渠道 |\n|---|---|---|---|---|\n'+'\n'.join(modern_rows)+'\n')
    save(ROOT/'queue.json',{'schema':1,'active_scope':active,'next_task':queue[0]['id'] if queue else None,'tasks':queue})
    save(ROOT/'progress.json',{'schema':1,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'total':len(ids),'active_scope':active,'scope_counts':{k:dict(v) for k,v in scope_counts.items()},'counts':dict(counts),'next_task':queue[0]['id'] if queue else None,'background_process':False,'record_files_are_authoritative':True,'initial_pass_complete':not counts.get('queued',0),'direct_text_records':counts.get('fulltext_online',0)+counts.get('partial_online',0),'no_verified_text_records':sum(counts.get(k,0) for k in ['metadata_only','scan_candidate','blocked','needs_review']),'resume_instruction':'先读CONTINUATION.md；优先queue第一个queued项，再按未决版本／受阻资源继续。'})
    print(json.dumps({'total':len(ids),'active_scope':active,'scope_counts':{k:dict(v) for k,v in scope_counts.items()},'counts':dict(counts),'next_task':queue[0]['id'] if queue else None},ensure_ascii=False))
if __name__=='__main__': run()
