"""Versioned translation drafts and reviews, independent of self-review progress."""
import argparse
import json
import sqlite3
from pathlib import Path
from shared import TASK, enc, require, sha


def snapshot(db, book_id, unit_id, actor, operation, observed_at, request_key):
    u = db.execute('SELECT body,body_sha256 FROM unit WHERE book_id=? AND id=?', (book_id, unit_id)).fetchone()
    edition = db.execute('SELECT edition_json FROM book WHERE id=?', (book_id,)).fetchone()[0]
    version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM translation_version WHERE book_id=? AND unit_id=?', (book_id, unit_id)).fetchone()[0]
    db.execute('INSERT INTO translation_version(book_id,unit_id,version,body,body_sha256,edition_sha256,actor,operation,observed_at,request_key) VALUES(?,?,?,?,?,?,?,?,?,?)',
               (book_id, unit_id, version, u[0], u[1], sha(edition.encode()), actor, operation, observed_at, request_key))


def migrate(db):
    require(db.execute('PRAGMA user_version').fetchone()[0] == 2, 'expected schema version 2')
    # DDL and data backfill roll back together on failure.
    db.execute('BEGIN IMMEDIATE')
    with db:
        for statement in (TASK/'translations/review-schema.sql').read_text('utf8').split(';'):
            if statement.strip():
                db.execute(statement)
        for book_id, unit_id, observed in db.execute('SELECT book_id,id,reviewed_at FROM unit WHERE body IS NOT NULL').fetchall():
            snapshot(db, book_id, unit_id, 'unknown (legacy import)', 'legacy_snapshot', observed, None)
        db.execute('PRAGMA user_version=3')


def context(db, book_id):
    pending = db.execute('SELECT * FROM review_queue WHERE book_id=? ORDER BY seq LIMIT 1', (book_id,)).fetchone()
    return {'pending_units': db.execute('SELECT COUNT(*) FROM review_queue WHERE book_id=?', (book_id,)).fetchone()[0],
            'next_review': dict(pending) if pending else None}


def save_review(db, p):
    from workflow import date, nonempty, one
    nonempty(p, 'reviewer', 'review_type', 'outcome', 'review_note', 'next_action')
    date(p['observed_at'])
    v = one(db, 'SELECT * FROM translation_version WHERE id=?', (p['version_id'],))
    require(v['book_id'] == p['id'] and v['unit_id'] == p['unit'], 'review subject mismatch')
    latest = db.execute('SELECT MAX(version) FROM translation_version WHERE book_id=? AND unit_id=?', (p['id'], p['unit'])).fetchone()[0]
    require(v['version'] == latest and v['body_sha256'] == p['body_sha256'], 'reviewed version is stale')
    evidence = p.get('source_evidence', [])
    findings = p.get('findings', [])
    require(isinstance(evidence, list) and isinstance(findings, list), 'evidence and findings must be lists')
    if p['review_type'] in ('source_check', 'human'):
        require(evidence and all(isinstance(e, dict) and e.get('locator') and e.get('checked') for e in evidence), 'provide actual source locators and checks')
    db.execute('INSERT INTO unit_review(version_id,reviewer,review_type,outcome,source_evidence_json,findings_json,note,observed_at,request_key) VALUES(?,?,?,?,?,?,?,?,?)',
               (v['id'], p['reviewer'], p['review_type'], p['outcome'], enc(evidence), enc(findings), p['review_note'], p['observed_at'], p['request_key']))


def verify(db):
    for r in db.execute('SELECT * FROM translation_version'):
        require(sha(r['body'].encode()) == r['body_sha256'], 'historical version hash mismatch')
    for u in db.execute('SELECT * FROM unit WHERE body IS NOT NULL'):
        v = db.execute('SELECT body_sha256 FROM translation_version WHERE book_id=? AND unit_id=? ORDER BY version DESC LIMIT 1', (u['book_id'], u['id'])).fetchone()
        require(v and v[0] == u['body_sha256'], 'current unit differs from latest version')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, default=TASK/'translations/state.sqlite3')
    args = parser.parse_args()
    db = sqlite3.connect(args.db.resolve().as_uri()+'?mode=rw', uri=True)
    db.execute('PRAGMA foreign_keys=ON')
    try:
        if db.execute('PRAGMA user_version').fetchone()[0] == 3:
            print('Already migrated to version 3')
        else:
            backup = args.db.with_suffix('.v2-backup.sqlite3')
            require(not backup.exists(), 'backup already exists')
            with sqlite3.connect(backup) as target:
                db.backup(target)
            migrate(db)
            print('Migrated to version 3; backup:', backup)
    finally:
        db.close()
