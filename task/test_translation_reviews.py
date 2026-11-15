"""Check review invalidation, idempotency and recovery on a live database copy."""
import sqlite3
from shared import TASK, require
from workflow import save
from translation_reviews import verify


def main():
    db = sqlite3.connect(':memory:')
    with sqlite3.connect((TASK/'translations/state.sqlite3').as_uri()+'?mode=ro', uri=True) as source:
        source.backup(db)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    v = db.execute('SELECT * FROM translation_version ORDER BY id LIMIT 1').fetchone()
    rid, unit = v['book_id'], v['unit_id']
    rev = db.execute('SELECT revision FROM book WHERE id=?', (rid,)).fetchone()[0]
    p = dict(id=rid, unit=unit, revision=rev, request_key='test-review', operation='review',
             reviewer='test reviewer', review_type='source_check', outcome='approved',
             version_id=v['id'], body_sha256=v['body_sha256'], observed_at='2026-11-15',
             source_evidence=[dict(locator='fixture', checked='fixture')], findings=[],
             review_note='fixture', next_action='fixture')
    save(db, 'translations', p)
    require(save(db, 'translations', p)['replayed'], 'retry failed')
    require(not db.execute('SELECT 1 FROM review_queue WHERE book_id=? AND unit_id=?',(rid,unit)).fetchone(), 'approval not applied')
    revise = dict(id=rid, unit=unit, revision=rev+1, request_key='test-revise', operation='revise',
                  expected_body_sha256=v['body_sha256'], body=v['body']+'\n测试修订', model='fixture',
                  review_note='fixture', observed_at='2026-11-15', next_action='fixture')
    save(db, 'translations', revise)
    require(db.execute('SELECT 1 FROM review_queue WHERE book_id=? AND unit_id=?',(rid,unit)).fetchone(), 'old approval survived revision')
    p.update(revision=rev+2, request_key='test-stale')
    try:
        save(db, 'translations', p)
    except ValueError:
        pass
    else:
        raise AssertionError('stale review accepted')
    require(db.execute('SELECT COUNT(*) FROM receipt').fetchone()[0] >= 2, 'receipts lost')
    verify(db)
    db.close()
    print('PASS: review, retry, revision history, invalidation and stale-review rollback')


if __name__ == '__main__':
    main()
