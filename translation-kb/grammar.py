"""Source pointers and bounded, versioned grammatical review patterns."""
from functools import lru_cache
from pathlib import Path
import re


@lru_cache(maxsize=1)
def patterns():
    rows = []
    source = Path(__file__).with_name("syntax-patterns.txt")
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, layer, rest = line.split("|", 2)
        expression, question, boundary = rest.rsplit("|", 2)
        rows.append((name, layer, re.compile(expression, re.I), question, boundary))
    return rows


def paragraphs(text):
    return re.split(r"\n[ \t]*\n", text.strip())


def diagnostics(source):
    results = []
    for i, paragraph in enumerate(paragraphs(source), 1):
        if paragraph.startswith(("#", "Date:", "URL:", "Video:")):
            continue
        for name, layer, pattern, question, boundary in patterns():
            match = pattern.search(paragraph)
            if match:
                results.append(dict(rule=name, layer=layer, paragraph=i,
                                    anchor=match[0], question=question, boundary=boundary))
    return results


def short_notes(source, limit=3):
    ordered = {p[0]:i for i,p in enumerate(patterns())}
    found = sorted(diagnostics(source), key=lambda x:ordered[x["rule"]])
    seen = set()
    notes = []
    for hit in found:
        if hit["rule"] in seen:
            continue
        seen.add(hit["rule"])
        notes.append(f'- 「{hit["anchor"]}」　{hit["question"]}')
        if len(notes)==limit:
            break
    return notes


def review_notes(source, phase):
    hits = diagnostics(source)
    focus = {"parallel","purpose-chain","shared-object","beneficiary","register"} if phase == 1 else {
        "ellipsis","negated-speech","condition","passive","voice","time","vocative"}
    ordered = sorted(hits,key=lambda h:h["rule"] not in focus)
    seen = set()
    result = []
    for h in ordered:
        if h["rule"] in seen:
            continue
        seen.add(h["rule"])
        result.append(h)
        if len(result)==8:
            break
    return result
