"""Rebuild local research index; does not fetch, subscribe or publish."""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {'dydi_a':'书籍与作者', 'dydi_b':'事工与讲章', 'dydi_c':'档案与数字馆藏', 'dydi_d':'跨传统灵修', 'lori_a':'刊物与持续媒体', 'lori_b':'多元作者与宣教'}
MERGES = {'dydi_d:d08':'dydi_a:foster-celebration', 'dydi_d:d10':'dydi_a:merton-new-seeds', 'lori_a:la08':'dydi_b:B02'}
def dump(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
def render(value):
    if isinstance(value, str): return value
    return json.dumps(value, ensure_ascii=False)

items = {}
raw_count = 0
for worker, group in GROUPS.items():
    data = json.loads((ROOT/'workers'/f'{worker}.json').read_text())
    for entry in data['items']:
        for field in ('id','title','kind','description','sources','chinese_status','next'):
            assert entry.get(field), (worker, entry.get('id'), field)
        for source in entry['sources']:
            assert source['url'].startswith(('https://','http://')), source
            assert source.get('read_scope'), source
        key = worker+':'+entry['id']
        assert key not in items
        items[key] = {'catalog_id':key, 'group':group, 'record_file':f'workers/{worker}.json', **entry}
        raw_count += 1
for alias, target in MERGES.items():
    extra = items.pop(alias)
    items[target].setdefault('supplemental_records', []).append(extra)
urls = set()
for entry in items.values():
    for record in [entry]+entry.get('supplemental_records',[]):
        urls.update(s['url'] for s in record['sources'])
stats = {'raw_records':raw_count, 'merged_duplicates':len(MERGES), 'catalog_entries':len(items), 'distinct_source_urls':len(urls), 'groups':dict(Counter(x['group'] for x in items.values()))}
dump('catalog.json', {'schema':1,'date':'2026-11-10','status':'phase_1_completed_for_scope','scope':'资源入口与书目初筛，非全书通读；同机构的不同栏目、档案、书籍可能分别收录。','stats':stats,'merges':MERGES,'items':list(items.values())})
lines = ['# 第一阶段资源目录', '', '核查日期：2026-11-10。这里的条目包括书籍、作者、馆藏、事工和频道，不能统称为书籍数量。中文工作译名不代表正式出版书名。', '', f'原始记录 {raw_count} 条；合并重复记录 {len(MERGES)} 条；现有 {len(items)} 项资源、{len(urls)} 个不同来源 URL。来源数量不代表全文阅读数量。', '', '同机构不同层级资源保留关联：CT 主刊与 CT Women，Thurman 著作与档案，González 作者入口与 AETH 中心；不据此声称拥有同等数量的独立机构。', '']
for group in GROUPS.values():
    lines += ['## '+group, '']
    for e in items.values():
        if e['group'] != group: continue
        lines += ['### '+e['title'], '', f"- 稳定 ID：`{e['catalog_id']}`；类型：{e['kind']}", '- 传统／背景：'+render(e.get('tradition','待核')), '- 简介：'+render(e['description']), '- 研究价值：'+render(e.get('value','待核')), '- 中文情况：'+render(e['chinese_status'])]
        for k,label in [('update_evidence','更新证据'),('updates','更新记录'),('subscription','订阅入口'),('access','访问范围'),('access_and_cost','费用边界'),('next','续查位置')]:
            if k in e: lines.append('- '+label+'：'+render(e[k]))
        lines += ['', '来源及实读范围：', '']
        for s in e['sources']: lines.append('- '+s['url']+' — '+s['read_scope'])
        for extra in e.get('supplemental_records',[]):
            lines += ['', f"补充核查记录 `{extra['catalog_id']}`：", '', '- 中文情况：'+render(extra['chinese_status']), '- 下一步：'+render(extra['next'])]
            lines += ['- '+s['url']+' — '+s['read_scope'] for s in extra['sources']]
        lines += ['', f"原始记录：[详见]({e['record_file']})（含检索／限制记录）。", '']
(ROOT/'CATALOG.md').write_text('\n'.join(lines))
print(json.dumps(stats,ensure_ascii=False))
