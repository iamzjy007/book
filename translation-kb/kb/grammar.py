"""Source pointers and bounded, versioned grammatical review patterns."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3


from . import DB, SOURCES

PATTERN_SOURCE = SOURCES / "syntax-patterns.txt"


def read_pattern_rows(source=PATTERN_SOURCE):
    """Read and validate the editorial source before replacing any stored rows."""
    rows = []
    names = set()
    for number, line in enumerate(Path(source).read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        try:
            name, layer, rest = line.split("|", 2)
            expression, question, boundary = rest.rsplit("|", 2)
            row = (name, layer, expression, question, boundary)
            if not all(field.strip() for field in row) or name in names:
                raise ValueError("字段为空或标识重复")
            re.compile(expression, re.I)
        except (ValueError, re.error) as exc:
            raise ValueError(f"{source} 第 {number} 行句法规则有误：{exc}") from exc
        names.add(name)
        rows.append(row)
    if not rows:
        raise ValueError(f"{source} 缺少句法规则")
    return rows


def install_patterns(db, source=PATTERN_SOURCE):
    rows = read_pattern_rows(source)
    db.execute("SAVEPOINT install_patterns")
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS syntax_patterns(
            position INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, layer TEXT NOT NULL,
            expression TEXT NOT NULL, question TEXT NOT NULL, boundary TEXT NOT NULL)""")
        db.execute("DELETE FROM syntax_patterns")
        db.executemany("INSERT INTO syntax_patterns(position,name,layer,expression,question,boundary) "
                       "VALUES (?,?,?,?,?,?)",
                       ((i, *row) for i, row in enumerate(rows, 1)))
    except BaseException:
        db.execute("ROLLBACK TO install_patterns")
        db.execute("RELEASE install_patterns")
        raise
    db.execute("RELEASE install_patterns")


def patterns(db=None):
    if db is None:
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as connection:
            return patterns(connection)
    rows = db.execute("SELECT name,layer,expression,question,boundary FROM syntax_patterns ORDER BY position")
    return [(name, layer, re.compile(expression, re.I), question, boundary)
            for name, layer, expression, question, boundary in rows]


def paragraphs(text):
    return re.split(r"\n[ \t]*\n", text.strip())


def diagnostics(source, db=None):
    return _diagnostics(source, patterns(db))


def _diagnostics(source, rules):
    results = []
    for i, paragraph in enumerate(paragraphs(source), 1):
        if paragraph.startswith(("#", "Date:", "URL:", "Video:")):
            continue
        for name, layer, pattern, question, boundary in rules:
            match = pattern.search(paragraph)
            if match:
                results.append(dict(rule=name, layer=layer, paragraph=i,
                                    anchor=match[0], question=question, boundary=boundary))
    return results


def short_notes(source, limit=3, *, db=None):
    rules = patterns(db)
    ordered = {p[0]:i for i,p in enumerate(rules)}
    found = sorted(_diagnostics(source, rules), key=lambda x:ordered[x["rule"]])
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


def review_notes(source, phase, *, db=None):
    hits = diagnostics(source, db)
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
