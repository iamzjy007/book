"""Offline Scripture lookup. Reference numbers are interpreted in each edition independently."""
import argparse
import re
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().with_name("bible-style.sqlite3")

# Authorial variations in the reviewed books. Pair only the relevant wording.
ALLUSIONS = (
    (r"\bglory poured out (?:of|on) all flesh\b", "约珥书 2:28", "浇灌凡有血气的", "作者此处说荣耀；受词依待译原文。"),
    (r"\bgoodness and mercy shall follow (?:you|me) all the days of (?:your|my) life\b", "诗篇 23:6", "恩惠慈爱随着我", "按作者的受话者调整人称。"),
    (r"\bwalk by faith\b", "哥林多后书 5:7", "行事为人是凭着信心", "独立劝勉可借用搭配；保留原句语气和范围。"),
)

def aliases(db):
    names = {}
    for code, usfm, name in db.execute("SELECT code,usfm,name FROM books"):
        for alias in (code, usfm, name):
            names[alias.casefold()] = code
    names.update({"psalm": "PSA", "song of songs": "SOL", "revelations": "REV"})
    return names


def references(db, source):
    names = aliases(db)
    options = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    pattern = rf"(?<!\w)({options})\.?\s*(\d+)\s*[:：]\s*(\d+)(?:\s*[-–]\s*(\d+))?"
    for m in re.finditer(pattern, source, re.I):
        yield names[m[1].casefold()], int(m[2]), int(m[3]), int(m[4] or m[3])


def passage(db, code, ch, lo, hi):
    result = []
    for name, first, last, text in db.execute(
        "SELECT b.name,v.first,v.last,v.text FROM verses v JOIN books b USING(edition,code) "
        "WHERE v.code=? AND v.ch=? AND v.first<=? AND v.last>=? "
        "ORDER BY v.edition,v.first", (code, ch, hi, lo)
    ):
        label = str(first) if first == last else f"{first}–{last}"
        result.append(f"{name} {ch}:{label}　{text or '〔底本该节无正文〕'}")
    return result


def suggestions(db, source):
    # An explicit reference takes precedence over an inferred verbal parallel.
    notes = []
    count = 0
    for code, ch, lo, hi in dict.fromkeys(references(db, source)):
        lines = passage(db, code, ch, lo, min(hi,lo+1))
        if lines:
            notes.extend(lines)
            count += 1
        if count == 2:
            break
    if not notes:
        for para in source.split("\n"):
            tokens = re.findall(r"[A-Za-z]+", para.lower())
            for i in range(0, len(tokens)-7, 4):
                phrase = '"' + " ".join(tokens[i:i+8]) + '"'
                found = db.execute(
                    "SELECT v.code,v.ch,v.first FROM quotes JOIN verses v ON v.rowid=quotes.rowid "
                    "WHERE quotes MATCH ? LIMIT 2", (phrase,)
                ).fetchall()
                if len(found) == 1:
                    code, ch, v = found[0]
                    notes = passage(db, code, ch, v, v)
                    break
            if notes:
                break
    terms = []
    for pattern, ref, wording, limit in ALLUSIONS:
        if re.search(pattern, source, re.I):
            terms.append(f"- {ref} 用“{wording}”。{limit}")
    for en, zh, kind, book, ch, v in db.execute(
        "SELECT t.en,t.zh,t.kind,b.name,t.ch,t.v FROM terms t JOIN books b ON "
        "b.code=t.code AND b.edition='cmn-cu89s' ORDER BY (t.kind='搭配') DESC,length(t.en) DESC,t.en"
    ):
        flags = re.I if kind == "搭配" else 0
        term = re.escape(en) if flags else f"(?:{re.escape(en)}|{re.escape(en.upper())})"
        if re.search(r"\b"+term+r"\b", source, flags):
            terms.append(f"- {en} → {zh}（{kind}，{book} {ch}:{v}）")
            if len(terms) == 8:
                break
    if not terms and not notes:
        return []
    return ["## 和合本参照",
            "译名只供辨明为同一人物或地点时采用。同节经文或英文措辞重合只供核对；"
            "保留作者改动的受词、人称与条件。已评阅的本书译法优先。",
            *terms, *notes]


def main():
    parser = argparse.ArgumentParser(description="按章节目或英中文原词离线查经")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ref")
    group.add_argument("--find")
    args = parser.parse_args()
    with sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True) as db:
        if args.ref:
            for ref in references(db,args.ref):
                for row in passage(db,*ref):
                    print(row)
        elif args.find.strip():
            for name,ch,lo,hi,text in db.execute(
                "SELECT b.name,v.ch,v.first,v.last,v.text FROM verses v JOIN books b USING(edition,code) "
                "WHERE instr(lower(v.text),lower(?))>0 ORDER BY v.rowid LIMIT 20", (args.find,)
            ):
                print(f"{name} {ch}:{lo}" + (f"–{hi}" if hi != lo else "") + "　" + text)


if __name__ == "__main__":
    main()
