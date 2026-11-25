"""Offline Scripture lookup. Reference numbers are interpreted in each edition independently."""
import argparse
from collections import defaultdict
from contextlib import closing
import re
import sqlite3
from kb import DB
from kb.term_store import split_ref, terms_containing, tokens
from kb.wordstudy import GROUPS, NEW, STOP, contains, format_pair, lookup as concordance_lookup, packet_notes, author_prose
from kb.parallel_text import best_parallel, scope_terms

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


def suggestions(db, source, lexical_hits=()):
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
            words = re.findall(r"[A-Za-z]+", para.lower())
            for i in range(0, len(words)-7, 4):
                phrase = '"' + " ".join(words[i:i+8]) + '"'
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
    # A sense-aware choice in this packet supersedes an older unqualified
    # substring, e.g. distinguishing "I am" from "you are the light of the world".
    selected = {tokens(hit.fragment) for hit in lexical_hits}
    for en, zh, kind, book, ch, v in db.execute(
        "SELECT t.en,t.zh,t.kind,b.name,t.ch,t.v FROM terms t JOIN books b ON "
        "b.code=t.code AND b.edition='cmn-cu89s' ORDER BY (t.kind='搭配') DESC,length(t.en) DESC,t.en"
    ):
        if kind == "搭配" and en.casefold().removeprefix("the ") in specific:
            continue
        if kind == "搭配" and any(contains(words, tokens(en.casefold().removeprefix("the "))) for words in selected):
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


def query_terms(query, db=None):
    if db is None:
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as connection:
            connection.execute("BEGIN")
            return query_terms(query, connection)
    if not re.fullmatch(r"[A-Za-z'’\s-]+", query) or not tokens(query):
        return (), ()
    needle = tokens(query)
    def entries_with(keys):
        return [(term, tuple(tokens(s) for s in term.triggers)) for term in terms_containing(db, keys)]
    entries = entries_with((needle[0],))
    if len(needle) == 1 and needle[0] in STOP and not any(needle in forms for _, forms in entries):
        return (), ()
    spellings = {needle}
    # Only entries that name the entire query can expand it. E.g. "armor"
    # can reach "armour", but a search for "light" cannot turn into "armor".
    for _, triggers in entries:
        if needle in triggers:
            spellings.update(triggers)
    keys = {s[0] for s in spellings}
    if keys != {needle[0]}:
        entries = entries_with(keys)
    relevant = [(t, bool(spellings.intersection(forms))) for t, forms in entries
                if any(contains(f, s) for f in forms for s in spellings)]
    return sorted(spellings, key=lambda s: (s != needle, len(s), s)), relevant


def classified_word_rows(db, patterns, relevant, group):
    """Partition all parallel English verse hits by editorial evidence, then
    by Chinese co-occurrence. Each verse record belongs to just one bucket."""
    codes = sorted(GROUPS[group]) if group else []
    scope = " AND e.code IN (" + ",".join("?" for _ in codes) + ")" if codes else ""
    expression = " OR ".join('"' + " ".join(p) + '"' for p in patterns)
    rows = db.execute("""
        SELECT e.code,b.name,e.ch,e.first,e.last,e.text,z.text FROM word_concordance f
        JOIN verses e ON e.rowid=f.rowid
        JOIN verses z ON z.edition='cmn-cu89s' AND z.code=e.code AND z.ch=e.ch
                      AND z.first=e.first AND z.last=e.last
        JOIN books b ON b.edition=z.edition AND b.code=z.code
        WHERE word_concordance MATCH ? AND z.text<>'' """ + scope + " ORDER BY e.rowid",
        (expression, *codes))

    by_ref = defaultdict(list)
    for term, direct in relevant:
        for ref in term.refs:
            by_ref[split_ref(ref)].append((term, direct))
    # Each verse has one count. If both a short and a long term cite it,
    # prefer the query's own sense, then the more specific Chinese wording.
    confirmed = defaultdict(list)
    candidates = defaultdict(list)
    direct_labels = set()
    pending = []
    for code, name, ch, lo, hi, en, zh in rows:
        words = tokens(en)
        if not any(contains(words, p) for p in patterns):
            continue  # FTS stems words; count only the declared surface forms.
        row = (code, name, ch, lo, hi, en, zh)
        options = []
        for verse in range(lo, hi + 1):
            for term, direct in by_ref.get((code, ch, verse), ()):
                for wording in (term.preferred, *term.variants):
                    if wording in zh:
                        options.append((direct, wording == term.preferred, len(wording), wording))
        if options:
            direct, _, _, label = max(options)
            confirmed[label].append(row)
            if direct:
                direct_labels.add(label)
        else:
            pending.append(row)

    # Only count as a co-occurrence wording attested at a curated bilingual
    # reference in this same scope. Independent overlapping readings stay open.
    unclassified = []
    for row in pending:
        labels = [label for label in confirmed if label in row[-1]]
        distinct = [label for label in labels if not any(label != x and label in x for x in labels)]
        if len(distinct) == 1:
            candidates[distinct[0]].append(row)
        else:
            unclassified.append(row)
    return confirmed, candidates, unclassified, direct_labels


def word_lookup(db, query, group=None, context=False):
    patterns, relevant = query_terms(query, db)
    if not relevant:
        return concordance_lookup(db, query, group, context)
    confirmed, candidates, unclassified, direct_labels = classified_word_rows(db, patterns, relevant, group)
    total = sum(map(len, confirmed.values())) + sum(map(len, candidates.values())) + len(unclassified)
    scope_names = {None: "全经", "nt": "新约二十七卷", "paul": "保罗书信", "psalms": "诗篇", "wisdom": "智慧书"}
    if not total:
        fallback = concordance_lookup(db, query, group, context)
        if fallback:
            fallback.insert(0, f"{scope_names[group]}内，所列英文词式未检得节界一致的双语经节。以下另列词义及近似用例。")
        return fallback
    lines = [f"查词范围　{scope_names[group]}，WEB 与和合本节界一致，共命中 {total} 节。"
             + "所查英文词式有 " + "、".join(" ".join(p) for p in patterns) + "。",
             "“已核”统计词条所引经节，每节只计一次。“另见同词”指英文和中文措辞同节出现，须对读辨义。有新约依据的译法优先显示。"]

    def priority(label):
        nt = sum(row[0] in NEW for row in confirmed[label])
        return (not nt, label not in direct_labels, -nt, -len(confirmed[label]), label)

    examples = []
    for label in sorted(confirmed, key=priority):
        refs = sorted(confirmed[label], key=lambda r: r[0] not in NEW)
        summary = "、".join(f"{r[1]} {r[2]}:{r[3]}" + (f"–{r[4]}" if r[3] != r[4] else "")
                           for r in refs[:4])
        if len(refs) > 4:
            summary += " 等"
        nt = sum(r[0] in NEW for r in refs)
        lines.append(f"「{label}」　已核 {len(refs)} 节（新约 {nt} 节），另见同词 {len(candidates[label])} 节。{summary}")
        examples.append(refs[0])
    if unclassified:
        lines.append(f"待辨译法　{len(unclassified)} 节。")
        examples.append(next((r for r in unclassified if r[0] in NEW), unclassified[0]))
    for label in sorted(confirmed, key=priority):
        examples.extend(confirmed[label])
        examples.extend(candidates[label])
    examples.extend(unclassified)
    for row in list(dict.fromkeys(examples))[:6]:
        code, _, ch, lo, hi, _, _ = row
        example = format_pair(row[1:])
        if context:
            example += "\n  上下文　" + " ".join(passage(db, code, ch, max(1, lo - 1), hi + 1, "cmn-cu89s"))
        lines.append(example)
    # Earlier reviewed senses can have a useful source where WEB uses another
    # word (e.g. loving kindness in Ps 23:6 when looking up 'mercy'). They are
    # additional sense notes and must never inflate the literal census above.
    older = [note for note in concordance_lookup(db, query, group, context)
             if not note.startswith("同词经节　")]
    if older:
        lines.extend(["原有词义提示（单列，不重复计数）", *older])
    return lines


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
        db.execute("BEGIN")
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
