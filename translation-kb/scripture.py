"""Offline Scripture lookup. Reference numbers are interpreted in each edition independently."""
import argparse
from contextlib import closing
import re
import sqlite3
from pathlib import Path
from wordstudy import GROUPS, lookup as word_lookup, packet_notes, author_prose
from parallel_text import best_parallel, scope_terms

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
    names.update({"psalm": "PSA", "ps": "PSA", "matt": "MAT", "deut": "DEU",
                  "exod": "EXO", "song of songs": "SOL", "revelations": "REV"})
    for name, code in list(names.items()):
        if re.match(r"^[123] ", name):
            digit, title = name.split(" ", 1)
            names[{"1":"i", "2":"ii", "3":"iii"}[digit] + " " + title] = code
    return names


def references(db, source):
    names = aliases(db)
    options = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    segment = r"\d+(?:[ \t]*[-–—][ \t]*\d+)?"
    pattern = rf"(?<!\w)({options})\.?[ \t]*(\d+)[ \t]*[:：][ \t]*({segment}(?:[ \t]*[,、][ \t]*{segment})*)"
    for m in re.finditer(pattern, source, re.I):
        for part in re.split(r"[,、]", m[3]):
            bounds = re.split(r"[-–—]", part)
            yield names[m[1].casefold()], int(m[2]), int(bounds[0]), int(bounds[-1])


def passage(db, code, ch, lo, hi, edition=None):
    result = []
    for name, first, last, text in db.execute(
        "SELECT b.name,v.first,v.last,v.text FROM verses v JOIN books b USING(edition,code) "
        "WHERE v.code=? AND v.ch=? AND v.first<=? AND v.last>=? "
        "AND (? IS NULL OR v.edition=?) ORDER BY v.edition,v.first", (code, ch, hi, lo, edition, edition)
    ):
        label = str(first) if first == last else f"{first}–{last}"
        result.append(f"{name} {ch}:{label}　{text or '〔底本该节无正文〕'}")
    return result


def parallel_notes(db, source):
    hit = best_parallel(db, source)
    if hit is None:
        return []
    code, chapter, verse = hit.ref
    lines = passage(db, code, chapter, verse, verse)
    def show(words):
        return " · ".join(list(dict.fromkeys(words))[:18]) or "无"
    lines.extend([
        "参照依据（同序实词）　" + show(hit.anchors),
        "原段未对齐词　" + show(hit.residual),
        "经文未对齐词　" + show(hit.reference_only),
        "先按原句确定说话者、谁对谁做什么、比喻落在哪里。逐分句借用相合的中文，复核未对齐处是否多译或漏译。",
    ])
    src_scope, ref_scope = scope_terms(hit.source), scope_terms(hit.english)
    if src_scope or ref_scope:
        lines.append("核对否定、条件和语气的管辖范围　原段 " + show(src_scope) + "；经文 " + show(ref_scope))
    return lines


def suggestions(db, source):
    # An explicit reference takes precedence over an inferred verbal parallel.
    notes = []
    count = 0
    supplied_version = re.search(r"\b(?:AMPC|NKJV)\b", source, re.I)
    # Prefer standalone attribution lines to references inside AMPC parentheses.
    citation_lines = "\n".join(line for line in source.splitlines()
                               if re.search(r"\b(?:AMPC|NKJV)\s*$", line, re.I))
    for code, ch, lo, hi in dict.fromkeys(references(db, citation_lines or source)):
        lines = passage(db, code, ch, lo, min(hi,lo+2), "cmn-cu89s" if supplied_version else None)
        if lines:
            notes.extend(lines)
            count += 1
        if count == 2:
            break
    if not notes and not supplied_version:
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
    if not notes and not supplied_version:
        notes.extend(parallel_notes(db, author_prose(source)))
    terms = []
    for pattern, ref, wording, limit in ALLUSIONS:
        if re.search(pattern, source, re.I):
            terms.append(f"- {ref} 用“{wording}”。{limit}")
    specific = {en.casefold() for en, in db.execute("SELECT en FROM word_senses")}
    for en, zh, kind, book, ch, v in db.execute(
        "SELECT t.en,t.zh,t.kind,b.name,t.ch,t.v FROM terms t JOIN books b ON "
        "b.code=t.code AND b.edition='cmn-cu89s' ORDER BY (t.kind='搭配') DESC,length(t.en) DESC,t.en"
    ):
        if kind == "搭配" and en.casefold().removeprefix("the ") in specific:
            continue
        flags = re.I if kind == "搭配" else 0
        term = re.escape(en) if flags else f"(?:{re.escape(en)}|{re.escape(en.upper())})"
        pattern = r"\b" + term + r"\b"
        if en == "Mark":
            pattern += r"(?!\s+(?i:my|your|the|these|those)\b)"
        if re.search(pattern, source, flags):
            terms.append(f"- {en} → {zh}（{kind}，{book} {ch}:{v}）")
            if len(terms) == 8:
                break
    words = packet_notes(db, source)
    if not terms and not notes and not words:
        return []
    return ["## 和合本参照",
            "译名只供辨明为同一人物或地点时采用。同节经文或英文措辞重合只供核对；"
            "保留作者改动的受词、人称与条件。已评阅的本书译法优先。",
            *terms, *notes,
            *(["## 本篇词语与经文用例",
               "先读原句，认清谁对谁说、动作落在谁身上。意思相合时，只借用合适的词或半句，再用自然中文读一遍。"
               "普通用法照常译。作者只写半个意象，就停在那里。经节编号用于核对，勿自行加进译文。",
               *words] if words else [])]


def main():
    parser = argparse.ArgumentParser(description="按章节目或英中文原词离线查经")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ref")
    group.add_argument("--find")
    group.add_argument("--word", help="按中英文词或短语找义项及双语经节")
    parser.add_argument("--collection", choices=tuple(GROUPS), help="限定诗篇、智慧书（诗篇另列）、保罗书信或新约")
    parser.add_argument("--context", action="store_true", help="查词时附同章前后各一节和合本")
    args = parser.parse_args()
    if (args.collection or args.context) and args.word is None:
        parser.error("--collection 和 --context 用于 --word")
    with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as db:
        if args.ref:
            for ref in references(db,args.ref):
                for row in passage(db,*ref):
                    print(row)
        elif args.word is not None:
            query = args.word.strip()
            if not query:
                parser.error("请输入查找词")
            print("\n\n".join(word_lookup(db, query, args.collection, args.context)) or "本范围未检得用例。")
        elif args.find and args.find.strip():
            for name,ch,lo,hi,text in db.execute(
                "SELECT b.name,v.ch,v.first,v.last,v.text FROM verses v JOIN books b USING(edition,code) "
                "WHERE instr(lower(v.text),lower(?))>0 ORDER BY v.rowid LIMIT 20", (args.find,)
            ):
                print(f"{name} {ch}:{lo}" + (f"–{hi}" if hi != lo else "") + "　" + text)


if __name__ == "__main__":
    main()
