CREATE TABLE translation_version (
    id INTEGER PRIMARY KEY,
    book_id TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    body TEXT NOT NULL,
    body_sha256 TEXT NOT NULL,
    edition_sha256 TEXT NOT NULL,
    actor TEXT NOT NULL,
    operation TEXT NOT NULL,
    observed_at TEXT,
    request_key TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(book_id,unit_id,version),
    FOREIGN KEY(book_id,unit_id) REFERENCES unit(book_id,id)
);
CREATE TABLE unit_review (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES translation_version(id),
    reviewer TEXT NOT NULL,
    review_type TEXT NOT NULL CHECK(review_type IN ('source_check','style','human')),
    outcome TEXT NOT NULL CHECK(outcome IN ('approved','changes_requested','unresolved')),
    source_evidence_json TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    note TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    request_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX review_by_version ON unit_review(version_id,id);
CREATE VIEW review_queue AS
SELECT u.book_id,u.id AS unit_id,u.seq,v.id AS version_id,v.version,v.body_sha256
FROM unit u JOIN translation_version v ON v.book_id=u.book_id AND v.unit_id=u.id
WHERE u.body IS NOT NULL
AND v.version=(SELECT MAX(x.version) FROM translation_version x WHERE x.book_id=u.book_id AND x.unit_id=u.id)
AND NOT EXISTS (
 SELECT 1 FROM unit_review r WHERE r.version_id=v.id AND r.review_type IN ('source_check','human')
 AND r.outcome='approved' AND r.id=(SELECT MAX(z.id) FROM unit_review z WHERE z.version_id=v.id AND z.review_type=r.review_type)
);
