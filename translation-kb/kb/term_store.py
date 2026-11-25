"""Maintain and query the bilingual idiom tables in bible-style.sqlite3."""
import argparse
import csv
from collections import defaultdict
from contextlib import closing, contextmanager
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import io
from pathlib import Path
import re
import sqlite3


from . import DB
TOKEN = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")


@dataclass(frozen=True)
class Term:
    id: str
    triggers: tuple
    preferred: str
    variants: tuple
    refs: tuple
    cues: tuple
    exclude: tuple
    note: str


@lru_cache(maxsize=4096)
def tokens(text):
    return tuple(m[0].casefold().replace("’", "'") for m in TOKEN.finditer(text))


def split_ref(ref):
    match = re.fullmatch(r"([A-Z0-9]{3})\.([1-9][0-9]*)\.([1-9][0-9]*)", ref)
    if not match:
        raise ValueError(f"惯用语经节格式有误：{ref}")
    return match[1], int(match[2]), int(match[3])


SCHEMA = (
    """CREATE TABLE IF NOT EXISTS idiom(
        id TEXT PRIMARY KEY NOT NULL, ordinal INTEGER NOT NULL UNIQUE,
        preferred TEXT NOT NULL, note TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS idiom_trigger(
        term_id TEXT NOT NULL REFERENCES idiom(id) ON DELETE CASCADE,
        pos INTEGER NOT NULL, phrase TEXT NOT NULL,
        PRIMARY KEY(term_id,pos), UNIQUE(term_id,phrase)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS idiom_trigger_token(
        term_id TEXT NOT NULL, trigger_pos INTEGER NOT NULL,
        token_pos INTEGER NOT NULL, token TEXT NOT NULL,
        PRIMARY KEY(term_id,trigger_pos,token_pos),
        FOREIGN KEY(term_id,trigger_pos) REFERENCES idiom_trigger(term_id,pos) ON DELETE CASCADE
        ) WITHOUT ROWID""",
    "CREATE INDEX IF NOT EXISTS idiom_token_lookup ON idiom_trigger_token(token,term_id)",
    """CREATE INDEX IF NOT EXISTS idiom_first_lookup ON idiom_trigger_token(token,term_id)
       WHERE token_pos=0""",
    """CREATE TABLE IF NOT EXISTS idiom_field(
        term_id TEXT NOT NULL REFERENCES idiom(id) ON DELETE CASCADE,
        kind TEXT NOT NULL CHECK(kind IN ('variants','cues','exclude')),
        pos INTEGER NOT NULL, value TEXT NOT NULL,
        PRIMARY KEY(term_id,kind,pos), UNIQUE(term_id,kind,value)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS idiom_ref(
        term_id TEXT NOT NULL REFERENCES idiom(id) ON DELETE CASCADE,
        pos INTEGER NOT NULL, code TEXT NOT NULL, ch INTEGER NOT NULL, v INTEGER NOT NULL,
        PRIMARY KEY(term_id,pos), UNIQUE(term_id,code,ch,v)) WITHOUT ROWID""",
    "CREATE INDEX IF NOT EXISTS idiom_ref_lookup ON idiom_ref(code,ch,v,term_id)",
    """CREATE TABLE IF NOT EXISTS idiom_meta(
        singleton INTEGER PRIMARY KEY CHECK(singleton=1), sha256 TEXT NOT NULL)""",
)


def chunks(values):
    for start in range(0, len(values), 400):
        yield values[start:start+400]


def placeholders(values):
    return ",".join("?" for _ in values)


@contextmanager
def _snapshot(db):
    """Keep the index lookup and its child rows in the same committed version."""
    if db.in_transaction:
        yield
        return
    db.execute("BEGIN")
    try:
        yield
    finally:
        db.rollback()


def _read(db, ids=None):
    terms = []
    batches = (None,) if ids is None else chunks(sorted(ids))
    for batch in batches:
        params = () if batch is None else batch
        where = "" if batch is None else f" WHERE term_id IN ({placeholders(batch)})"
        fields = defaultdict(lambda: defaultdict(list))
        for key, value in db.execute("SELECT term_id,phrase FROM idiom_trigger"+where+
                                     " ORDER BY term_id,pos", params):
            fields[key]["triggers"].append(value)
        for key, kind, value in db.execute("SELECT term_id,kind,value FROM idiom_field"+where+
                                           " ORDER BY term_id,kind,pos", params):
            fields[key][kind].append(value)
        for key, code, ch, v in db.execute("SELECT term_id,code,ch,v FROM idiom_ref"+where+
                                           " ORDER BY term_id,pos", params):
            fields[key]["refs"].append(f"{code}.{ch}.{v}")
        where = "" if batch is None else f" WHERE id IN ({placeholders(batch)})"
        for key, ordinal, zh, note in db.execute("SELECT id,ordinal,preferred,note FROM idiom"+where, params):
            values = fields[key]
            term = Term(key, tuple(values["triggers"]), zh, tuple(values["variants"]),
                        tuple(values["refs"]), tuple(values["cues"]), tuple(values["exclude"]), note)
            terms.append((ordinal, term))
    return tuple(term for _, term in sorted(terms, key=lambda item: item[0]))


def all_terms(db):
    with _snapshot(db):
        return _read(db)


def _by_tokens(db, words, initial):
    ids = set()
    condition = " AND token_pos=0" if initial else ""
    for batch in chunks(sorted(set(words))):
        rows = db.execute(f"SELECT DISTINCT term_id FROM idiom_trigger_token "
                          f"WHERE token IN ({placeholders(batch)})"+condition, batch)
        ids.update(r[0] for r in rows)
    return _read(db, ids)


def candidate_terms(db, first_tokens):
    with _snapshot(db):
        return _by_tokens(db, first_tokens, initial=True)


def terms_containing(db, query_tokens):
    with _snapshot(db):
        return _by_tokens(db, query_tokens, initial=False)


def term_digest(db):
    row = db.execute("SELECT sha256 FROM idiom_meta WHERE singleton=1").fetchone()
    if not row:
        raise ValueError("数据库缺少惯用词校验值")
    return row[0]


def export_terms(entries, stream):
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    keys = tuple(Term.__dataclass_fields__)
    writer.writerow(keys)
    for entry in entries:
        fields = (getattr(entry, key) for key in keys)
        writer.writerow("|".join(value) if isinstance(value, tuple) else value for value in fields)


def _digest(entries):
    stream = io.StringIO(newline="")
    export_terms(entries, stream)
    return hashlib.sha256(stream.getvalue().encode("utf-8")).hexdigest()


def read_batch(path):
    """Read an editorial interchange file. Queries never depend on this file."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t", strict=True)
        if reader.fieldnames != list(Term.__dataclass_fields__):
            raise ValueError(f"{path} 的惯用词列名不符")
        for row in reader:
            if None in row or None in row.values():
                raise ValueError(f"{path} 第 {reader.line_num} 行列数不符")
            for field in ("triggers", "variants", "refs", "cues", "exclude"):
                row[field] = tuple(s.strip() for s in row[field].split("|") if s.strip())
            yield Term(**row)


def _verify_term(db, term):
    if not all((term.id.strip(), term.triggers, term.preferred.strip(), term.refs, term.note.strip())):
        raise ValueError(f"惯用词条目缺少必填内容：{term.id}")
    for field in (term.triggers, term.variants, term.refs, term.cues, term.exclude):
        if len(set(field)) != len(field):
            raise ValueError(f"惯用词条目有重复值：{term.id}")
    if any(not tokens(s) for s in (*term.triggers, *term.cues, *term.exclude)):
        raise ValueError(f"英文检索字段没有英文词：{term.id}")
    def compact(text):
        return re.sub(r"[\s\[\]]", "", text)
    forms = tuple(tokens(s) for s in term.triggers)
    english_match = False
    for ref in term.refs:
        code, ch, v = split_ref(ref)
        verses = dict(db.execute(
            "SELECT edition,text FROM verses WHERE code=? AND ch=? AND ? BETWEEN first AND last",
            (code, ch, v)))
        en, zh = verses.get("engwebp"), verses.get("cmn-cu89s")
        if not en or not zh:
            raise ValueError(f"{term.id} 在 {ref} 找不到双语经文")
        if not any(compact(s) in compact(zh) for s in (term.preferred, *term.variants)):
            raise ValueError(f"{term.id} 在 {ref} 找不到所列中文措辞")
        words = tokens(en)
        english_match |= any(words[i:i+len(form)] == form for form in forms for i in range(len(words)))
    if not english_match:
        raise ValueError(f"{term.id} 在所引经文中找不到所列英文词形")


def _write(db, term):
    for pos, phrase in enumerate(term.triggers):
        db.execute("INSERT INTO idiom_trigger VALUES (?,?,?)", (term.id,pos,phrase))
        db.executemany("INSERT INTO idiom_trigger_token VALUES (?,?,?,?)",
                       ((term.id,pos,i,w) for i,w in enumerate(tokens(phrase))))
    for kind in ("variants", "cues", "exclude"):
        db.executemany("INSERT INTO idiom_field VALUES (?,?,?,?)",
                       ((term.id,kind,i,s) for i,s in enumerate(getattr(term, kind))))
    db.executemany("INSERT INTO idiom_ref VALUES (?,?,?,?,?)",
                   ((term.id,i,*split_ref(ref)) for i,ref in enumerate(term.refs)))


def import_terms(db, paths, update=False):
    """Apply a batch together. No term outside these inputs is changed."""
    files = []
    for item in map(Path, paths):
        files.extend(sorted(item.glob("*.tsv")) if item.is_dir() else [item])
    if not files:
        raise ValueError("没有找到待导入的 TSV")
    nested = db.in_transaction
    db.execute("PRAGMA foreign_keys=ON")
    if not db.execute("PRAGMA foreign_keys").fetchone()[0]:
        raise ValueError("请在开启写事务前启用 SQLite 外键")
    db.execute("SAVEPOINT import_idioms" if nested else "BEGIN IMMEDIATE")
    try:
        for statement in SCHEMA:
            db.execute(statement)
        ordinal = db.execute("SELECT coalesce(max(ordinal),0) FROM idiom").fetchone()[0]
        seen = set()
        for path in files:
            for term in read_batch(path):
                if term.id in seen:
                    raise ValueError(f"同一批次重复定义：{term.id}")
                seen.add(term.id)
                _verify_term(db, term)
                if db.execute("SELECT 1 FROM idiom WHERE id=?", (term.id,)).fetchone():
                    if not update:
                        raise ValueError(f"已存在 {term.id}；修订已有词条请使用 --update")
                    db.execute("UPDATE idiom SET preferred=?,note=? WHERE id=?", (term.preferred,term.note,term.id))
                    for table in ("idiom_trigger", "idiom_field", "idiom_ref"):
                        db.execute(f"DELETE FROM {table} WHERE term_id=?", (term.id,))
                else:
                    ordinal += 1
                    db.execute("INSERT INTO idiom VALUES (?,?,?,?)", (term.id,ordinal,term.preferred,term.note))
                _write(db, term)
        if not seen:
            raise ValueError("批次中没有惯用词条目")
        checksum = _digest(all_terms(db))
        db.execute("INSERT INTO idiom_meta VALUES (1,?) ON CONFLICT(singleton) DO UPDATE SET sha256=excluded.sha256",
                   (checksum,))
        db.execute("RELEASE import_idioms" if nested else "COMMIT")
        return len(seen)
    except BaseException:
        if nested:
            db.execute("ROLLBACK TO import_idioms")
            db.execute("RELEASE import_idioms")
        else:
            db.rollback()
        raise


def check_store(db):
    with _snapshot(db):
        return _check_store(db)


def _check_store(db):
    terms = all_terms(db)
    if not terms or _digest(terms) != term_digest(db):
        raise ValueError("数据库中的惯用词与校验值不一致")
    for table in ("idiom_trigger", "idiom_trigger_token", "idiom_field", "idiom_ref"):
        if db.execute(f"PRAGMA foreign_key_check({table})").fetchone():
            raise ValueError(f"惯用语表出现无对应上级的记录：{table}")
    expected = []
    for term in terms:
        _verify_term(db, term)
        for i, phrase in enumerate(term.triggers):
            expected.extend((term.id,i,j,w) for j,w in enumerate(tokens(phrase)))
    stored = db.execute("SELECT term_id,trigger_pos,token_pos,token FROM idiom_trigger_token "
                        "ORDER BY term_id,trigger_pos,token_pos").fetchall()
    if sorted(expected) != list(map(tuple, stored)):
        raise ValueError("英文词形索引与惯用词不一致")
    return len(terms)


def main():
    parser = argparse.ArgumentParser(description="在知识库内维护有双语经文依据的惯用词。")
    parser.add_argument("--db", type=Path, default=DB)
    actions = parser.add_subparsers(dest="action", required=True)
    load = actions.add_parser("import", help="导入 TSV 文件或目录中的 TSV，整批核验并写入")
    load.add_argument("paths", nargs="+", type=Path)
    load.add_argument("--update", action="store_true", help="允许修订输入中指定的已有 ID")
    actions.add_parser("export", help="导出一份 UTF-8 TSV").add_argument("output", type=Path)
    actions.add_parser("check", help="核对经节、检索索引及词表摘要")
    args = parser.parse_args()
    mode = "rw" if args.action == "import" else "ro"
    try:
        with closing(sqlite3.connect(args.db.resolve().as_uri()+"?mode="+mode, uri=True)) as db:
            if args.action == "import":
                print(f"已写入 {import_terms(db,args.paths,args.update)} 条惯用语。")
            elif args.action == "export":
                entries = all_terms(db)
                with args.output.open("x", encoding="utf-8", newline="") as stream:
                    export_terms(entries, stream)
                print(f"已导出 {len(entries)} 条惯用语。")
            else:
                print(f"通过校验，共 {check_store(db)} 条惯用语。")
    except (ValueError, OSError, csv.Error, sqlite3.Error) as error:
        parser.exit(1, str(error)+"\n")


if __name__ == "__main__":
    main()
