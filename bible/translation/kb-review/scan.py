"""Build a local review index from the named EPUB and the matching Chinese edition."""
from collections import Counter
from contextlib import closing
from functools import lru_cache
from pathlib import Path
import argparse
import json
import re
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
TRANSLATION = HERE.parent
KB = TRANSLATION.parents[1]/"translation-kb"
sys.path[:0] = [str(TRANSLATION),str(KB)]
import pipeline
import wordstudy
from grammar import diagnostics

SELECTION = {1,3,5,6,7,8,9,10,11,12,13,14,15,17,18,19,43,52,84,89}
ANCIENT = re.compile("汝|尔等|尔曹|汝辈|焉|兮|矣|繄|欤|岂曰|盖因|夫惟|乃[是以当如]")
CALQUE = re.compile("进行(?:了|着)?[\u4e00-\u9fff]{2}|的情况下|就这一点而言|在某种程度上|有关于|拥有着|之事实|使得他们|使得他|藉由|取决于|关于这件事情|所进行的|对于此")


def selected():
    return [b for b in pipeline.manifest()["sections"] if b.get("title_zh") and
            int(b["title_zh"].split("_",1)[0]) in SELECTION]


def build(cache):
    wordstudy.forms = lru_cache(4096)(wordstudy.forms)
    books = selected()
    if len(books)!=20:
        raise ValueError("实体书目与审校范围不同")
    with closing(sqlite3.connect((KB/"bible-style.sqlite3").as_uri()+"?mode=ro",uri=True)) as kb:
        entries=wordstudy.senses(kb)
        with closing(sqlite3.connect(cache)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS corpus(book,work,unit,block,label,verse,kind,en,zh,
                        terms,syntax,flags,similarity REAL,PRIMARY KEY(book,unit,block))""")
            for b in books:
                work=b["title_zh"].split("_",1)[1]
                for u in b["units"]:
                    status,err=pipeline.validate(b,u)
                    if status!="complete":
                        raise ValueError((b["id"],u["id"],err))
                    english=pipeline.source_unit(b,u)["blocks"]
                    chinese=pipeline.read(TRANSLATION/"zh"/b["id"]/(u["id"]+".json"))["blocks"]
                    label=u["label"]
                    for s,t in zip(english,chinese):
                        en,zh=s["text"],t["zh"]
                        if b["id"]=="1-baruch" and s["kind"]=="h2" and en=="EPISTLE OF JEREMIAH":
                            work="耶利米书信"
                        if s["kind"] in ("h1","h2","h3","h4"):
                            label=en
                        hits=wordstudy.match_senses(entries,en)
                        terms=[dict(ref=e.ref,en=frag,zh=e.zh,note=e.usage) for e,frag in hits[:4]]
                        syn=[h["rule"] for h in diagnostics(en)]
                        flags=[]
                        if ANCIENT.search(zh):flags.append("文言")
                        if CALQUE.search(zh):flags.append("搭配")
                        if re.search(r"\b(?:not|never|neither|nor|no one)\b",en,re.I) and not re.search("不|没|无|未|莫|毋|岂|难|免|非|休|勿|别|乏|缺|绝|拒|停|失|离|谁|徒|戒|除|禁止",zh):
                            flags.append("否定")
                        if len(en.split())>=24 and len(re.findall(r"[\u3400-\u9fff]",zh))/len(en.split())<0.69:
                            flags.append("短译")
                        if re.search(r"\b(?:how long|how many|why (?:do|are|did|have)|what (?:will|shall|have))\b",en,re.I) and "?" in en and not re.search("[？?]|何|为什|怎|岂|难道|几|多久|吗",zh):
                            flags.append("问句")
                        if any(e.zh not in zh for e,_ in hits):flags.append("用例")
                        fields=(b["id"],work,u["id"],s["id"],label,s.get("verse"),s["kind"],en,zh,
                                json.dumps(terms,ensure_ascii=False),",".join(syn),",".join(flags))
                        prior=db.execute("SELECT en,zh FROM corpus WHERE book=? AND unit=? AND block=?",
                                         (b["id"],u["id"],s["id"])).fetchone()
                        if prior and prior!=(en,zh):
                            raise ValueError("这个索引保存了另一稿的对齐记录。请给新稿指定新的 SQLite 路径。")
                        db.execute("INSERT OR IGNORE INTO corpus VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL)",fields)
                db.commit()
                print(b["id"],flush=True)
            print(dict(db.execute("SELECT work,count(*) FROM corpus GROUP BY work")))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    args=parser.parse_args()
    build(args.cache)
