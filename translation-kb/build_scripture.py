"""Rebuild the scripture tables from the four eBible VPL/USFM ZIPs."""
import argparse
from contextlib import closing
import hashlib
import re
import sqlite3
import zipfile
from pathlib import Path
from wordstudy import install as install_wordstudy

ROOT = Path(__file__).resolve().parent
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path)
    args = parser.parse_args()
    with closing(sqlite3.connect(ROOT / "bible-style.sqlite3")) as db, db:
        db.execute("BEGIN IMMEDIATE")
        for table in ("quotes", "verses", "books", "sources", "terms"):
            db.execute(f"DROP TABLE IF EXISTS {table}")
        db.execute("CREATE TABLE sources(edition, archive PRIMARY KEY, sha256)")
        db.execute("CREATE TABLE books(edition, code, usfm, name, PRIMARY KEY(edition,code))")
        db.execute("CREATE TABLE verses(edition TEXT,code TEXT,ch INTEGER,first INTEGER,last INTEGER,text TEXT,PRIMARY KEY(edition,code,ch,first))")
        db.execute("CREATE VIRTUAL TABLE quotes USING fts5(text,content='verses',content_rowid='rowid')")
        db.execute("CREATE TABLE terms(en TEXT, zh TEXT, kind TEXT, code TEXT, ch INTEGER, v INTEGER, PRIMARY KEY(en,zh))")
        for edition in EDITIONS:
            load(db, args.archives, edition)
        db.execute("INSERT INTO quotes(rowid,text) SELECT rowid,text FROM verses WHERE edition='engwebp' AND text<>''")
        # Keep only explicit mappings with evidence in both editions at the supplied reference.
        for line in (ROOT / "scripture-terms.txt").read_text(encoding="utf8").splitlines():
            if not line or line.startswith("#"):
                continue
            kind, en, zh, code, ref = line.split("|")
            ch, verse = map(int, ref.split(":"))
            editions = dict(db.execute("SELECT edition,text FROM verses WHERE code=? AND ch=? AND first<=? AND last>=?", (code,ch,verse,verse)))
            if not re.search(r"\b"+re.escape(en)+r"\b", editions["engwebp"], re.I) or zh not in editions["cmn-cu89s"]:
                raise ValueError(line)
            db.execute("INSERT INTO terms VALUES (?,?,?,?,?,?)", (en,zh,kind,code,ch,verse))
        install_wordstudy(db)


if __name__ == "__main__":
    main()
