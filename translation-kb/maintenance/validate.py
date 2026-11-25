"""Reproduce release checks and optionally measure book-level retrieval coverage."""
import argparse
from collections import Counter
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from kb import ROOT
from kb.book_usage import build as build_usage, load_index
from kb.term_store import check_store
from kb.terms import find_terms
from kb.wordstudy import author_prose, install_indexes, packet_notes
from lookup import chapter, packet
from .build_scripture import install_reference_tables


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
        eligible = find_terms(original, db)
        counts.update(dict(正文=1,旧搭配=int(old),有义项=int(any("可参「" in n for n in notes)),
                           有全经线索=int(any("全经查词线索" in n for n in notes)),
                           词义与经文模块有提示=int(bool(notes)),该模块补充篇数=int(bool(notes) and not old),
                           惯用语有据篇数=int(any(h.supported for h in eligible))))
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books",type=Path,help="两部原文合订本所在目录")
    args = parser.parse_args()
    tests = Path(__file__).resolve().with_name("tests")
    suite = unittest.defaultTestLoader.discover(str(tests), pattern="test_*.py", top_level_dir=str(ROOT))
    if not suite.countTestCases():
        raise SystemExit(f"未在 {tests} 找到回归测试")
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        raise SystemExit(1)
    with closing(sqlite3.connect((ROOT/"bible-style.sqlite3").as_uri()+"?mode=ro",uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite 完整性检查失败")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("数据库外键检查失败")
        print("库内惯用词",check_store(db))
        editions = dict(db.execute("SELECT edition,count(DISTINCT code) FROM verses GROUP BY edition"))
        en = db.execute("SELECT count(*) FROM verses WHERE edition='engwebp' AND text<>''").fetchone()[0]
        fts = db.execute("SELECT count(*) FROM word_concordance").fetchone()[0]
        if editions!={"engwebp":66,"cmn-cu89s":66} or en!=fts:
            raise ValueError("经卷或索引未覆盖预期底本")
        with closing(sqlite3.connect(":memory:")) as rebuilt:
            db.backup(rebuilt)
            install_reference_tables(rebuilt)
            install_indexes(rebuilt)
            for table,order in (("terms","rowid"),("word_senses","rowid"),("syntax_patterns","position"),
                                ("word_keys","term"),("word_examples","term,verse_id")):
                query = f"SELECT * FROM {table} ORDER BY {order}"
                if db.execute(query).fetchall()!=rebuilt.execute(query).fetchall():
                    raise ValueError("交付索引与重建结果不同："+table)
        print("双语经卷",editions,"英文非空节位",fts)
        usage = load_index(db)
        if set(usage) != {"lori","dydi"}:
            raise ValueError("同书用例缺失或与当前词表不符，请运行 python -m kb.book_usage")
        if args.books:
            with TemporaryDirectory() as tmp:
                rebuilt_usage = build_usage(args.books, Path(tmp)/"usage.json", db=db)
                if rebuilt_usage["books"] != usage:
                    raise ValueError("同书索引与按本次底稿重建的结果不一致，请运行 python -m kb.book_usage")
            for book, name, number, example in (
                    ("dydi","DYDI_Messages_Declaring_Your_Destiny",3,"examples/dydi-003.md"),
                    ("lori","Daily_Words_The_Lords_Glory_with_Lori",133,"examples/lori-133.md")):
                print(name,measure(db,args.books/(name+".txt")))
                text = (args.books/(name+".txt")).read_text(encoding="utf-8-sig")
                if packet(chapter(text,number),book)!=(ROOT/example).read_text(encoding="utf-8-sig"):
                    raise ValueError(f"分发示例与当前生成器不一致：{example}")


if __name__=="__main__":
    main()
