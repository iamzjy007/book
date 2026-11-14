PRAGMA foreign_keys=ON;
CREATE TABLE receipt(request_key TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL,subject TEXT NOT NULL,revision INTEGER NOT NULL, payload_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE TABLE baseline(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, source_commit TEXT NOT NULL);
PRAGMA user_version=2;
