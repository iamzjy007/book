"""Rebuild the scripture tables from the four eBible VPL/USFM ZIPs."""
import argparse
from contextlib import closing
import hashlib
import re
import sqlite3
import zipfile
from pathlib import Path
from kb import DB, SOURCES
from kb.grammar import install_patterns
from kb.term_store import check_store
from kb.wordstudy import install_indexes, install_senses

EDITIONS = ("cmn-cu89s", "engwebp")


def load(db, directory, edition):
    for kind in ("vpl", "usfm"):
        name = f"{edition}_{kind}.zip"
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        db.execute("INSERT INTO sources VALUES (?, ?, ?)", (edition, name, digest))
    with zipfile.ZipFile(directory / f"{edition}_vpl.zip") as archive:
        lines = archive.read(f"{edition}_vpl.txt").decode("utf-8-sig").splitlines()
    texts = {}
    for line in lines:
        book, ref, text = line.split(" ", 2)
        c, v = map(int, ref.split(":"))
        key = (book, c, v)
        if key in texts:
            raise ValueError(f"重复节号 {key}")
        texts[key] = text.strip()
    codes = list(dict.fromkeys(key[0] for key in texts))
    with zipfile.ZipFile(directory / f"{edition}_usfm.zip") as archive:
        files = sorted(f for f in archive.namelist() if re.match(r"(?:0[2-9]|[1-9]\d)-\w{3}.*\.usfm$", f))
        if len(files) != 66 or len(codes) != 66:
            raise ValueError("底本卷数不符")
        for code, filename in zip(codes, files):
            raw = archive.read(filename).decode("utf-8-sig")
            name = re.search(r"(?m)^\\h (.+)", raw)[1].strip()
            usfm = re.match(r"\\id (\w+)", raw)[1]
            db.execute("INSERT INTO books VALUES (?,?,?,?)", (edition, code, usfm, name))
            chapter = 0
            for tag, number in re.findall(r"(?m)^\\([cv]) (\S+)", raw):
                if tag == "c":
                    chapter = int(number)
                    continue
                bounds = list(map(int, number.split("-")))
                text = texts.pop((code, chapter, bounds[0]))
                db.execute("INSERT INTO verses VALUES (?,?,?,?,?,?)",
                           (edition, code, chapter, bounds[0], bounds[-1], text))
    if texts:
        raise ValueError("尚有未识别的经节")


def install_terms(db):
    rows = []
    source = SOURCES / "scripture-terms.txt"
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith("#"):
            continue
        kind, en, zh, code, ref = line.split("|")
        ch, verse = map(int, ref.split(":"))
        editions = dict(db.execute(
            "SELECT edition,text FROM verses WHERE code=? AND ch=? AND first<=? AND last>=?",
            (code, ch, verse, verse)))
        if not (en and zh and re.search(r"\b"+re.escape(en)+r"\b", editions.get("engwebp", ""), re.I)
                and zh in editions.get("cmn-cu89s", "")):
            raise ValueError(f"底本未找到指定措辞：{line}")
        rows.append((en, zh, kind, code, ch, verse))
    if not rows:
        raise ValueError("scripture-terms.txt 缺少译名与搭配")
    db.execute("CREATE TABLE IF NOT EXISTS terms(en TEXT, zh TEXT, kind TEXT, code TEXT, ch INTEGER, v INTEGER, PRIMARY KEY(en,zh))")
    db.execute("DELETE FROM terms")
    db.executemany("INSERT INTO terms VALUES (?,?,?,?,?,?)", rows)


def install_reference_tables(db):
    install_terms(db)
    install_senses(db)
    install_patterns(db)


def main():
    parser = argparse.ArgumentParser(description="重建英中经文，或单独将三份编辑底稿同步到知识库。")
    parser.add_argument("archives", type=Path, nargs="?", help="包含四个底本 ZIP 的目录")
    parser.add_argument("--refresh-rules", action="store_true", help="仅同步译名、词义与句法三表")
    args = parser.parse_args()
    if (args.archives is None) != args.refresh_rules:
        parser.error("请指定底本 ZIP 目录，或单独使用 --refresh-rules")
    mode = "rw" if args.refresh_rules else "rwc"
    with closing(sqlite3.connect(DB.as_uri()+"?mode="+mode, uri=True)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        if args.refresh_rules:
            install_reference_tables(db)
            return
        for table in ("quotes", "verses", "books", "sources"):
            db.execute(f"DROP TABLE IF EXISTS {table}")
        db.execute("CREATE TABLE sources(edition, archive PRIMARY KEY, sha256)")
        db.execute("CREATE TABLE books(edition, code, usfm, name, PRIMARY KEY(edition,code))")
        db.execute("CREATE TABLE verses(edition TEXT,code TEXT,ch INTEGER,first INTEGER,last INTEGER,text TEXT,PRIMARY KEY(edition,code,ch,first))")
        db.execute("CREATE VIRTUAL TABLE quotes USING fts5(text,content='verses',content_rowid='rowid')")
        for edition in EDITIONS:
            load(db, args.archives, edition)
        db.execute("INSERT INTO quotes(rowid,text) SELECT rowid,text FROM verses WHERE edition='engwebp' AND text<>''")
        install_reference_tables(db)
        install_indexes(db)
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='idiom'").fetchone():
            check_store(db)


if __name__ == "__main__":
    main()
