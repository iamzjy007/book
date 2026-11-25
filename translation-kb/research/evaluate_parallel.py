"""Deterministic cross-edition retrieval experiment; supply the KJV JSON locally."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kb.parallel_text import ranked
from scripture import DB

KJV_SHA = "f0b09dc49dfb97bb84f03aae1fbf026485048c3cab31a7a41017e2d86ac1d11c"


def sample(db, file):
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != KJV_SHA:
        raise ValueError("KJV snapshot fingerprint differs")
    books = dict(db.execute("SELECT name,code FROM books WHERE edition='engwebp'"))
    seen = set()
    for book in json.loads(data)["books"]:
        name = book["name"].replace("Revelation of John", "Revelation")
        for roman, arabic in [("III ", "3 "), ("II ", "2 "), ("I ", "1 ")]:
            if name.startswith(roman):
                name = arabic + name[len(roman):]
        code = books[name]
        seen.add(code)
        verses = [((code,ch["chapter"],v["verse"]),v["text"])
                  for ch in book["chapters"] for v in ch["verses"]]
        def sample_key(row):
            return hashlib.sha256(("parallel-v1/" + str(row[0])).encode()).digest()
        yield from sorted(verses, key=sample_key)[:4]
    assert seen == set(books.values())


def exact(db, text):
    words = re.findall("[a-z]+", text.lower())
    for i in range(0, len(words)-7, 4):
        found = db.execute("""SELECT v.code,v.ch,v.first FROM quotes
            JOIN verses v ON v.rowid=quotes.rowid WHERE quotes MATCH ? LIMIT 2""",
            ('"' + ' '.join(words[i:i+8]) + '"',)).fetchall()
        if len(found) == 1:
            return found[0]


def run(db, file, verbose):
    counts = Counter()
    for ref, source in sample(db, file):
        counts["sample"] += 1
        old = exact(db, source)
        matches = ranked(db, source)
        top = matches[0] if matches else None
        emitted = bool(top and top.supported)
        counts["exact_correct"] += old == ref
        counts["exact_wrong"] += old is not None and old != ref
        counts["bm25_top1"] += any(m.bm_rank == 1 and m.ref == ref for m in matches)
        counts["aligned_top1"] += bool(top and top.ref == ref)
        counts["pool24_correct"] += any(m.ref == ref for m in matches)
        chosen = old or (top.ref if emitted else None)
        counts["combined_correct"] += chosen == ref
        counts["combined_wrong"] += chosen is not None and chosen != ref
        counts["combined_abstain"] += chosen is None
        if verbose:
            print(ref, old, top.ref if top else None, chosen)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kjv", type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as db:
        run(db, args.kjv, args.verbose)
