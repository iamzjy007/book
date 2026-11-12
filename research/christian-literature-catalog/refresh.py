"""Rebuild the reading catalogue from saved worker records; does not run searches."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
WORKERS = ['dydi_a', 'dydi_b', 'dydi_c', 'dydi_d', 'lori_a', 'lori_b', 'root', 'eclavis_a01', 'eclavis_a02']
AREAS = ['叙利亚与阿拉伯传统', '耶稣、福音残篇与使徒传统', '沙漠与东方诸教会', '希腊与拜占庭灵修', '拉丁西方传统', '礼仪、教规与殉道', '科普特启示及伦理文献', 'e-Clavis系统扫描续查', 'e-Clavis系统扫描续查A02']

# AUTO_ROLLING_WORKERS: retain the historic order, append later saved batches.
for _path in sorted((ROOT / 'workers').glob('eclavis_*.json')):
    if _path.stem not in WORKERS:
        WORKERS.append(_path.stem)
        AREAS.append('e-Clavis系统扫描续查' + _path.stem.removeprefix('eclavis_').upper())

def pick(d, *keys, default='待进一步核实'):
    return next((d[k] for k in keys if d.get(k) not in (None, '', [], {})), default)

def prose(v):
    if isinstance(v, str): return v
    if isinstance(v, list): return '；'.join(prose(x) for x in v)
    if isinstance(v, dict): return '；'.join(f'{k}：{prose(x)}' for k, x in v.items())
    return str(v)

def save(name, obj):
    p = ROOT / name
    temp = p.with_suffix(p.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    temp.replace(p)

def main():
    records, snapshots = [], []
    for worker, area in zip(WORKERS, AREAS):
        path = ROOT / 'workers' / (worker + '.json')
        data = json.loads(path.read_text())
        snapshots.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        items = pick(data, 'items', 'entries', 'verified_items', 'works', default=[])
        assert isinstance(items, list), worker
        global_sources = data.get('sources', {})
        if isinstance(global_sources, list): global_sources = {s.get('id', ''): s for s in global_sources}
        for item in items:
            refs = pick(item, 'sources', 'references', default=[])
            sources = []
            for ref in refs:
                if isinstance(ref, str):
                    assert ref in global_sources, (worker, item.get('id'), ref)
                    ref = global_sources[ref]
                assert isinstance(ref, dict) and ref.get('url', '').startswith(('http://', 'https://')), (worker, item.get('id'), ref)
                sources.append(ref)
            assert sources, (worker, item.get('id'), 'missing sources')
            raw_id = item['id']
            entry = {
                'id': worker + ':' + raw_id,
                'area': area,
                'record_kind': 'modern_anthology_gateway' if raw_id == 'east-mingana-mystics' else 'work_or_text_collection_record',
                'title_zh': pick(item, 'title_zh', 'title_zh_working', 'title_zh_provisional'),
                'original_title': pick(item, 'original_title', 'title_original', 'original_or_standard_title', 'title_original_or_standard'),
                'author_or_attribution': pick(item, 'author', 'author_attribution', 'attribution_and_date', 'date_and_attribution', 'authorship_and_textual_issues'),
                'date': pick(item, 'date', 'composition_date', 'composition_date_approx', 'attribution_and_date', 'date_and_attribution'),
                'language': pick(item, 'language', 'languages', 'original_language', 'original_language_and_transmission', 'original_language_and_survival'),
                'synopsis': pick(item, 'synopsis', 'summary', 'description', 'summary_and_value', 'historical_value'),
                'value': pick(item, 'spiritual_or_historical_value', 'historical_and_spiritual_value', 'summary_and_value', default={'historical': item.get('historical_value'), 'spiritual': pick(item, 'spiritual_value', 'devotional_value')}),
                'cautions': pick(item, 'attribution_issues', 'attribution_and_transmission', 'authorship_and_textual_issues', 'attribution_textual_cautions', 'attribution_and_date', 'date_and_attribution'),
                'repository_status': pick(item, 'existing_repo_status', 'repository_status', 'repo_status'),
                'repository_evidence': pick(item, 'repo_evidence', 'repository_evidence', default=item.get('repo_status', '待核')),
                'chinese_availability': pick(item, 'chinese_availability', 'chinese_publication', 'chinese_publication_status', 'chinese_status'),
                'priority': pick(item, 'priority', 'priority_for_next_research', 'recommendation'),
                'next': pick(item, 'next', 'next_step', 'remaining_checks'),
                'sources': sources,
                'worker_record': 'workers/' + worker + '.json',
                'worker_entry_id': raw_id,
                'evidence_limit': '以来源注明的实际阅读层级为准；书目、摘要与简介不等于全文阅读。',
            }
            for key in ('clavis', 'resources', 'relationships'):
                if item.get(key): entry[key] = item[key]
            assert entry['title_zh'] != '待进一步核实' and entry['original_title'] != '待进一步核实'
            records.append(entry)
    # APPLY_RESOURCE_SUPPLEMENTS: enrich existing works without adding duplicate records.
    by_id = {x['id']: x for x in records}
    for worker in WORKERS:
        payload = json.loads((ROOT / 'workers' / (worker + '.json')).read_text())
        for supplement in payload.get('supplements', []):
            target = by_id[supplement['target_id']]
            for resource in supplement.get('resources', []):
                assert resource.get('url', '').startswith(('http://', 'https://'))
                assert resource.get('verified') and resource.get('limits')
            target.setdefault('resources', []).extend(supplement.get('resources', []))
            existing_urls = {s['url'] for s in target['sources']}
            target['sources'].extend(s for s in supplement.get('sources', []) if s['url'] not in existing_urls)
            for key in ('language', 'next', 'clavis'):
                if supplement.get(key): target[key] = supplement[key]
            target.setdefault('resource_supplements', []).append({'worker_record': 'workers/' + worker + '.json', 'id': supplement['id']})
    # The two traditions investigated the same work. Preserve both evidence trails.
    c = next(x for x in records if x['id'] == 'dydi_c:C08')
    d = next(x for x in records if x['id'] == 'dydi_d:climacus-ladder')
    d['supplementary_records'] = [{'worker_record': c['worker_record'], 'worker_entry_id': 'C08', 'chinese_availability': c['chinese_availability'], 'repository_status': c['repository_status']}]
    d['chinese_availability'] = {'greek_group_search': d['chinese_availability'], 'eastern_group_evidence': c['chinese_availability'], 'qualification': '两组调查合并；已有中文出版线索见东方组记录，不再仅以未核实概括。'}
    d['sources'] += [x for x in c['sources'] if x['url'] not in {s['url'] for s in d['sources']}]
    records.remove(c)
    assert len({x['id'] for x in records}) == len(records)
    urls = {s['url'] for x in records for s in x['sources']}
    counts = {'worker_records': len(records) + 1, 'catalogue_records_after_one_merge': len(records), 'modern_anthology_gateways': sum(x['record_kind'] == 'modern_anthology_gateway' for x in records), 'unique_source_urls': len(urls)}
    save('catalog.json', {'schema': 1, 'date_beijing': '2026-11-12', 'phase': 'rolling_followup', 'counts': counts, 'count_limit': '条目包括古代原作、残篇、不同文本集及现代版本入口；不是这么多部新发现或未出版古书。', 'merge_log': [{'from': 'dydi_c:C08', 'into': d['id'], 'reason': '同一John Climacus天梯，合并东方与希腊组证据；不同于Guigo修士天梯、雅各天梯或阶梯之书。'}], 'snapshots': snapshots, 'records': records})
    lines = ['# 古代基督教文献书目目录（滚动更新）', '', f'当前汇总 **{len(records)}条**，合并《神圣攀登的天梯》重复调查一条。含现代文选入口1条；不能把总数当作新增古书数或无中文译本数。各条简介为书目信息层面的概述；并未通读全书。', '', '最新资源路径见 [RESOURCE-PATHS-E13.md](RESOURCE-PATHS-E13.md)，前批路径见 [RESOURCE-PATHS-A01.md](RESOURCE-PATHS-A01.md)，扫描游标见 [eclavis-scan.json](eclavis-scan.json)。详细证据、检索式和限制见链接的工作记录；机器可读索引见 [catalog.json](catalog.json)。中文“未查得”不等于未出版。', '']
    for area in AREAS:
        lines += ['## ' + area, '']
        for x in records:
            if x['area'] != area: continue
            lines += [f"### {x['title_zh']}", '', f"- **原题：** {x['original_title']}", f"- **作者／归属：** {prose(x['author_or_attribution'])}", f"- **年代：** {prose(x['date'])}", f"- **语言：** {prose(x['language'])}", '', prose(x['synopsis']), '', '**价值：** ' + prose(x['value']), '', '**文本注意：** ' + prose(x['cautions']), '', '**仓库情况：** ' + prose(x['repository_status']), '', '**中文线索：** ' + prose(x['chinese_availability']), '', '**下一步：** ' + prose(x['next']), '', '**来源：**']
            for s in x['sources']:
                label = prose(pick(s, 'publisher', 'institution', 'title', 'label', default=s['url']))
                scope = prose(pick(s, 'read_scope', 'actually_read', 'actual_read', 'actual_scope', default='层级详见工作记录'))
                lines.append(f"- [{label}]({s['url']}) — {scope}")
            for resource in x.get('resources', []):
                lines += ['', f"资源路径：[{resource['edition']}]({resource['url']}) — {resource['location']}；{resource['verified']}；{resource['limits']}"]
            for supplement in x.get('resource_supplements', []):
                lines += ['', f"[补充资源调查]({supplement['worker_record']})，补证 `{supplement['id']}`。"]
            lines += ['', f"[完整调查记录]({x['worker_record']})，条目 `{x['worker_entry_id']}`。", '']
    (ROOT / 'CATALOG.md').write_text('\n'.join(lines))
    save('validation.json', {'checks': {'all_worker_json_parse': True, 'catalog_ids_unique': True, 'every_record_has_title_and_original_title': True, 'every_record_has_resolved_source_urls': True, 'known_climacus_duplicate_merged': True}, 'counts': counts, 'limits': '这是文件结构、来源入口及已知重复校验，不证明所有书目信息无误，也不是全网或大陆出版情况的穷尽查证。'})
    scan = json.loads((ROOT / 'eclavis-scan.json').read_text())
    scan_ids = [x['ecca'] for x in scan['records']]
    assert len(scan_ids) == len(set(scan_ids))
    assert [x['ordinal'] for x in scan['records']] == list(range(1, len(scan_ids) + 1))
    catalogue_ids = {x['id'] for x in records}
    assert all(x.get('record_id') in catalogue_ids for x in scan['records'] if x.get('record_id'))
    batches = {}
    for worker in [w for w in WORKERS if w.startswith('eclavis_')]:
        expected = len(json.loads((ROOT / 'workers' / (worker + '.json')).read_text())['items'])
        batch_records = [x for x in records if x['worker_record'] == f'workers/{worker}.json']
        assert len(batch_records) == expected
        assert all(x.get('resources') for x in batch_records)
        assert all(r.get('verified') and r.get('limits') for x in batch_records for r in x['resources'])
        batches[worker] = len(batch_records)
    for json_path in ROOT.rglob('*.json'):
        json.loads(json_path.read_text())
    validation = json.loads((ROOT / 'validation.json').read_text())
    validation['checks'].update(scan_ecca_unique=True, scan_ordinals_contiguous=True, scan_record_ids_resolve=True, resource_locators_have_verification_and_limits=True, all_saved_json_parse=True)
    validation['scan_record_count'] = len(scan_ids)
    validation['batch_catalogue_record_counts'] = batches
    validation['followup_counts'] = json.loads((ROOT / json.loads((ROOT / 'progress.json').read_text())['latest_session']).read_text())['counts']
    save('validation.json', validation)
    print(json.dumps(counts, ensure_ascii=False))

if __name__ == '__main__': main()
