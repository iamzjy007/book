"""Find recurring names and close verbal parallels throughout the selected books."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import json
import re
import sqlite3

from scan import KB, wordstudy

WORDS = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")


def words(text):
    return tuple(x.lower().replace("’", "'") for x in WORDS.findall(text))


def shingles(tokens):
    return {tokens[i:i+6] for i in range(len(tokens)-5)}


def survey(cache):
    with closing(sqlite3.connect(cache, timeout=60)) as db, closing(
            sqlite3.connect((KB/"bible-style.sqlite3").as_uri()+"?mode=ro", uri=True)) as kb:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS parallels(id INTEGER PRIMARY KEY,ref,en,zh,common,coverage);
          CREATE TABLE IF NOT EXISTS name_use(id INTEGER,en,zh,present,PRIMARY KEY(id,en,zh));
        """)
        verses = {}
        index = defaultdict(list)
        for rid, name, ch, number, en, zh in kb.execute("""
            SELECT e.rowid,b.name,e.ch,e.first,e.text,z.text FROM verses e
            JOIN books b ON b.edition='cmn-cu89s' AND b.code=e.code
            JOIN verses z ON z.edition=b.edition AND z.code=e.code AND z.ch=e.ch
                AND z.first=e.first AND z.last=e.last
            WHERE e.edition='engwebp' AND e.text<>'' AND z.text<>''"""):
            tokens = words(en)
            verses[rid] = (name,ch,number,en,zh,tokens)
            for fragment in shingles(tokens):
                index[fragment].append(rid)
        mappings = dict(kb.execute("SELECT en,zh FROM terms WHERE kind IN ('地名','人名')"))
        names = re.compile(r"\b(?:"+"|".join(re.escape(n) for n in sorted(mappings,key=len,reverse=True))+r")\b")
        with db:
            db.execute("DELETE FROM parallels")
            db.execute("DELETE FROM name_use")
            for row, en, zh in db.execute("SELECT rowid,en,zh FROM corpus WHERE kind IN ('verse','p')"):
                findings = {(n,mappings[n],int(mappings[n] in zh)) for n in names.findall(en)}
                db.executemany("INSERT INTO name_use VALUES (?,?,?,?)",((row,*f) for f in findings))
                tokens = words(en)
                hits = Counter(r for key in shingles(tokens) if len(index.get(key,()))<=8 for r in index.get(key,()))
                best = None
                for rid,_ in hits.most_common(12):
                    name,ch,v,eng,cn,target = verses[rid]
                    match = SequenceMatcher(None,tokens,target,autojunk=False)
                    overlap = max((m.size for m in match.get_matching_blocks()),default=0)
                    coverage = overlap/len(tokens)
                    if overlap<8 or (coverage<0.35 and overlap<16):
                        continue
                    rank = (overlap,match.ratio(),-rid)
                    if best is None or rank>best[0]:
                        best = rank,(row,f"{name} {ch}:{v}",eng,cn,overlap,coverage)
                if best:
                    db.execute("INSERT INTO parallels VALUES (?,?,?,?,?,?)",best[1])
        for t in ("parallels","name_use"):
            print(t,db.execute(f"SELECT count(*) FROM {t}").fetchone()[0])


def scan_phrases(cache):
    # Reuse the published context and sense rules. Keep negative results so an interrupted
    # sweep resumes after its last completed source paragraph.
    wordstudy.forms=lru_cache(maxsize=50000)(wordstudy.forms)
    with closing(sqlite3.connect(cache,timeout=60)) as db, closing(
            sqlite3.connect((KB/"bible-style.sqlite3").as_uri()+"?mode=ro",uri=True)) as kb:
        db.execute("CREATE TABLE IF NOT EXISTS phrase_check(id INTEGER PRIMARY KEY,fragment,ref,neighbors,en,zh)")
        rows=db.execute("""SELECT rowid,en,terms FROM corpus WHERE kind IN ('verse','p')
                           AND rowid NOT IN (SELECT id FROM phrase_check) ORDER BY rowid""").fetchall()
        for i,(row,en,terms) in enumerate(rows,1):
            used={" ".join(wordstudy.forms(t["en"])) for t in json.loads(terms)}
            result=wordstudy.discover(kb,en,used,set())
            record=(row,None,None,None,None,None)
            if result:
                _,frag,neighbors,(name,ch,v,last,eng,cn)=result
                ref=f"{name} {ch}:{v}"+(f"–{last}" if last!=v else "")
                record=(row,frag,ref,", ".join(neighbors),eng,cn)
            db.execute("INSERT INTO phrase_check VALUES (?,?,?,?,?,?)",record)
            if i%32==0:
                db.commit()
        db.commit()
        print("phrase_check",db.execute("SELECT count(*),count(ref) FROM phrase_check").fetchone())


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("cache",type=Path)
    cli.add_argument("--phrases",action="store_true")
    args=cli.parse_args()
    if args.phrases:
        scan_phrases(args.cache)
    else:
        survey(args.cache)
