"""Reproduce release checks and optionally measure book-level retrieval coverage."""
import argparse
from collections import Counter
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import unittest

from lookup import ROOT, chapter, packet
from wordstudy import author_prose, install, packet_notes


def measure(db, f):
    corpus = f.read_text(encoding="utf-8-sig")
    baseline = [re.compile(r"\b"+re.escape(en)+r"\b",re.I) for en, in db.execute(
        "SELECT en FROM terms WHERE kind='搭配'")]
    counts = Counter()
    for entry in re.split(r"(?m)^={10,}[ \t]*$",corpus)[1:]:
        if not entry.strip():
            continue
        parts = entry.strip().split("\n\n",2)
        if len(parts)!=3 or not parts[1].startswith("Date:"):
            raise ValueError("合订本篇章格式无法识别")
        if parts[2].strip()=="[No transcript body]":
            continue
        original = author_prose(parts[2])
        old = any(pattern.search(original) for pattern in baseline)
        notes = packet_notes(db,parts[2])
        counts.update(dict(正文=1,旧搭配=int(old),有义项=int(any("可参「" in n for n in notes)),
                           有全经线索=int(any("全经查词线索" in n for n in notes)),
                           新模块有提示=int(bool(notes)),补充篇数=int(bool(notes) and not old)))
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books",type=Path,help="两部原文合订本所在目录")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT),pattern="test_*.py")
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        raise SystemExit(1)
    with closing(sqlite3.connect((ROOT/"bible-style.sqlite3").as_uri()+"?mode=ro",uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite 完整性检查失败")
        editions = dict(db.execute("SELECT edition,count(DISTINCT code) FROM verses GROUP BY edition"))
        en = db.execute("SELECT count(*) FROM verses WHERE edition='engwebp' AND text<>''").fetchone()[0]
        fts = db.execute("SELECT count(*) FROM word_concordance").fetchone()[0]
        if editions!={"engwebp":66,"cmn-cu89s":66} or en!=fts:
            raise ValueError("经卷或索引未覆盖预期底本")
        with closing(sqlite3.connect(":memory:")) as rebuilt:
            db.backup(rebuilt)
            install(rebuilt)
            for table,order in (("word_senses","code,ch,v,en"),("word_keys","term"),("word_examples","term,verse_id")):
                query = f"SELECT * FROM {table} ORDER BY {order}"
                if db.execute(query).fetchall()!=rebuilt.execute(query).fetchall():
                    raise ValueError("交付索引与重建结果不同："+table)
        print("双语经卷",editions,"英文非空节位",fts)
        if args.books:
            for name in ("Daily_Words_The_Lords_Glory_with_Lori","DYDI_Messages_Declaring_Your_Destiny"):
                print(name,measure(db,args.books/(name+".txt")))
            text = (args.books/"DYDI_Messages_Declaring_Your_Destiny.txt").read_text(encoding="utf-8-sig")
            if packet(chapter(text,3),"dydi")!=(ROOT/"packet-example.md").read_text(encoding="utf-8-sig"):
                raise ValueError("分发示例与当前生成器不一致")


if __name__=="__main__":
    main()
