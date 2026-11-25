"""Local, verse-backed translation choices. Offsets always refer to the input."""
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
import re
import sqlite3

from . import DB
from .term_store import TOKEN, Term, all_terms, candidate_terms, split_ref, tokens
from .wordstudy import NEW, contains


CLAUSE = re.compile(r"[^.!?;:\n]+")
DIVINE_PRONOUN = re.compile(r"\b(?:My|Me|Your|His)\b")


def load_terms():
    """Complete catalogue for maintenance and callers that explicitly request it."""
    with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as db:
        return all_terms(db)


def trigger_index(db, words):
    index = defaultdict(list)
    for term in candidate_terms(db, words):
        for phrase in dict.fromkeys(tokens(s) for s in term.triggers):
            if phrase[0] in words:
                index[phrase[0]].append((phrase, term))
    return index


@dataclass(frozen=True)
class Hit:
    term: Term
    fragment: str
    start: int
    end: int
    supported: bool
    cue_count: int


def find_terms(text, db=None):
    """Prefer context-supported expressions, then the most specific span."""
    if db is None:
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as connection:
            return find_terms(text, connection)
    words_in_text = {m[0].casefold().replace("’", "'") for m in TOKEN.finditer(text)}
    index = trigger_index(db, words_in_text)
    result = []
    clauses = list(CLAUSE.finditer(text))
    for number, clause in enumerate(clauses):
        positions = list(TOKEN.finditer(clause[0]))
        literal = tuple(m[0].replace("’", "'") for m in positions)
        words = tuple(w.casefold() for w in literal)
        adjacent = []
        for neighbor in (number-1, number+1):
            if not 0 <= neighbor < len(clauses):
                continue
            first, last = sorted((clause, clauses[neighbor]), key=lambda m: m.start())
            if "\n" not in text[first.end():last.start()]:
                neighbor_words = tokens(clauses[neighbor][0])
                adjacent.append(neighbor_words[-10:] if neighbor < number else neighbor_words[:10])
        candidates = []
        for i, word in enumerate(words):
            for phrase, term in index.get(word, ()):
                end = i + len(phrase)
                if words[i:end] != phrase:
                    continue
                nearby = slice(max(0, i-10), end+10)
                window = words[nearby]
                if any(contains(window, tokens(s)) for s in term.exclude):
                    continue
                local = sum(contains(literal[nearby], tuple(TOKEN.findall(s)))
                            if DIVINE_PRONOUN.search(s) else contains(window, tokens(s))
                            for s in term.cues)
                # Only explicitly marked expressions may resolve an isolated
                # mention from an adjacent sentence. Same-sentence cues win.
                nearby_cue = any(s.startswith("~") and any(contains(n, tokens(s)) for n in adjacent)
                                 for s in term.cues)
                cues = 2 * local + int(nearby_cue)
                start_char = clause.start() + positions[i].start()
                end_char = clause.start() + positions[end-1].end()
                hit = Hit(term, text[start_char:end_char], start_char, end_char,
                          bool(cues or not term.cues), cues)
                candidates.append((i, end, hit))
        occupied = set()
        by_span = defaultdict(list)
        for i, end, hit in candidates:
            by_span[i, end].append(hit)
        def span_priority(item):
            (i, end), hits = item
            return not any(h.supported for h in hits), i-end, i
        for (i, end), hits in sorted(by_span.items(), key=span_priority):
            if any(pos in occupied for pos in range(i, end)):
                continue
            occupied.update(range(i, end))
            best = max((h.supported, h.cue_count) for h in hits)
            winners = [h for h in hits if (h.supported, h.cue_count) == best]
            # Equally plausible different senses are leads for the translator.
            ambiguous = len({h.term.preferred for h in winners}) > 1
            for h in winners:
                result.append(Hit(h.term, h.fragment, h.start, h.end, h.supported and not ambiguous, h.cue_count))
    return sorted(result, key=lambda h: h.start)


def reference_label(names, ref):
    code, ch, verse = split_ref(ref)
    return f"{names[code]} {ch}:{verse}"


def term_notes(db, hits, book, source):
    from .book_usage import BOOKS, available, usage_hint

    groups = defaultdict(list)
    for hit in hits:
        groups[hit.term].append(hit)
    if not groups:
        return []
    names = dict(db.execute("SELECT code,name FROM books WHERE edition='cmn-cu89s'"))
    def priority(item):
        term, hits = item
        return (any(h.supported for h in hits),
                max(len(tokens(h.fragment)) for h in hits) > 1,
                any(split_ref(ref)[0] in NEW for ref in term.refs),
                len(hits), max(len(tokens(h.fragment)) for h in hits))
    lines = []
    additional = []
    tentative = []
    for term, hits in sorted(groups.items(), key=priority, reverse=True):
        supported = [h for h in hits if h.supported]
        if not supported and len(tentative) >= 2:
            continue
        fragments = " / ".join(dict.fromkeys(h.fragment for h in (supported or hits)))
        ref = reference_label(names, term.refs[0])
        label = "可取" if supported else "可能相关，先辨义"
        if supported and len(lines) >= 12:
            additional.append(f"{fragments} → {term.preferred}（{ref}）")
            continue
        observed = usage_hint(term.id, book, source, db=db) if supported else ""
        target = lines if supported else tentative
        target.append(f"- {fragments} → **{term.preferred}**（{label}，{ref}）。{term.note}" +
                      (f" 同书现译同段见{observed}。" if observed else ""))
    if additional:
        lines.append("其余有语境依据的用词：" + "；".join(additional) + "。")
    if book in BOOKS and not available(db, book):
        lines.append("本书译例索引缺失或与词表版本不同。本包只列经文依据，可用 python -m kb.book_usage 重建本书用例。")
    return ["## 和合本惯用词与短语", "先核原句所指，再取相合的措辞。人称、动作和修饰语以本篇英文为准。", *lines, *tentative]
