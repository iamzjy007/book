#!/usr/bin/env python3
"""Structural checkpoint verification. Does not judge translation accuracy."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def blocks(text):
    matches = list(re.finditer(r'^### (\S+)\s*$', text, re.M))
    result = {}
    for i, match in enumerate(matches):
        key = match[1]
        if key in result:
            raise ValueError(f'duplicate translation block: {key}')
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[key] = text[match.end():end].strip()
    return result

def write_atomic(path, value):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    inv = read(ROOT / 'inventory/books.json')
    queue = read(ROOT / 'queue.json')
    progress = read(ROOT / 'progress.json')
    records = inv['records']
    assert len(records) == 110 and len({r['id'] for r in records}) == 110
    candidates = {r['id'] for r in records if r['acquisition_status'] == 'fulltext_online'}
    assert len(candidates) == 51
    assert len(queue['tasks']) == 51 and {t['id'] for t in queue['tasks']} == candidates
    assert len({t['id'] for t in queue['tasks']}) == 51
    assert [t['order'] for t in queue['tasks']] == list(range(1, 52))
    for r in records:
        assert digest((REPO / r['record_path']).read_bytes()) == r['record_sha256'], f'source record changed: {r["id"]}'
    completed = reviewed = total = active = 0
    bookrecords = {}
    known_slugs = {r['slug'] for r in records}
    for directory in (ROOT / 'books').iterdir():
        if not directory.is_dir():
            continue
        assert directory.name in known_slugs, f'unknown book: {directory}'
        recordpath = directory / 'record.json'
        assert recordpath.exists(), f'unregistered book directory: {directory}'
        r = read(recordpath)
        assert r['id'] in candidates and r['id'] not in bookrecords
        bookrecords[r['id']] = r
        if r['status'] in ('deferred_incomplete', 'blocked_source'):
            assert r.get('next_action') and r.get('reason')
            continue
        source = read(directory / 'source.json')
        assert source['completeness']['verified'] is True
        assert source['language'] and source['edition'] and source['source_urls']
        assert source['completeness']['scope'] and source['completeness']['limits']
        assert source['artifacts']
        for artifact in source['artifacts']:
            assert artifact['url'] and re.fullmatch(r'[0-9a-f]{64}', artifact['sha256'])
        units = r['units']
        assert units and len({u['id'] for u in units}) == len(units)
        assert len(units) == r['expected_units']
        translation = directory / 'translation.md'
        parsed = blocks(translation.read_text()) if translation.exists() else {}
        assert set(parsed) <= {u['id'] for u in units}, f'unregistered translation blocks: {directory}'
        assert list(parsed) == [u['id'] for u in units if u['id'] in parsed], f'block order differs: {directory}'
        for u in units:
            total += 1
            assert u['source_locator'] and u['source_anchor']
            assert u['status'] in ('pending', 'draft', 'self_reviewed')
            if u['status'] == 'self_reviewed':
                assert parsed.get(u['id']), f'missing translation: {directory}/{u["id"]}'
                assert digest(parsed[u['id']].encode()) == u['translation_sha256'], f'translation changed: {directory}/{u["id"]}'
                assert 'TODO' not in parsed[u['id']] and '待翻译' not in parsed[u['id']]
                reviewed += 1
            elif u['id'] in parsed:
                print(f'RECOVER: {directory.name}/{u["id"]} has text awaiting self review', file=sys.stderr)
        review = (directory / 'review.md').read_text()
        for heading in ('B. 待核清单', 'C. 术语表增补建议', 'D. 本次所依据的底本信息'):
            assert heading in review
        assert r['next_unit'] == next((u['id'] for u in units if u['status'] != 'self_reviewed'), None)
        if r['status'] == 'translated_self_reviewed':
            assert set(parsed) == {u['id'] for u in units}
            assert all(u['status'] == 'self_reviewed' for u in units) and r['next_unit'] is None
            completed += 1
        else:
            active += 1
    derived = []
    for t in queue['tasks']:
        new = dict(t)
        if t['id'] in bookrecords:
            r = bookrecords[t['id']]
            new['status'] = r['status']
            new['next_action'] = r['next_action']
        derived.append(new)
    next_task = next((t['id'] for t in derived if t['status'] not in ('translated_self_reviewed', 'deferred_incomplete', 'blocked_source')), None)
    next_unit = bookrecords[next_task]['next_unit'] if next_task in bookrecords else ('verify_source' if next_task else None)
    newprogress = dict(progress, completed_books=completed, reviewed_units=reviewed, registered_units=total, active_books=active, next_task=next_task, next_unit=next_unit)
    newqueue = dict(queue, tasks=derived)
    if args.refresh:
        write_atomic(ROOT / 'queue.json', newqueue)
        write_atomic(ROOT / 'progress.json', newprogress)
    else:
        assert newqueue == queue, 'queue stale; run --refresh'
        assert newprogress == progress, 'progress stale; run --refresh'
    print(json.dumps(dict(ok=True, records=110, candidates=51, completed_books=completed, reviewed_units=reviewed, registered_units=total, next_task=next_task, next_unit=next_unit), ensure_ascii=False))

if __name__ == '__main__':
    try:
        main()
    except (AssertionError, KeyError, ValueError, OSError) as exc:
        print(f'CHECK FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
