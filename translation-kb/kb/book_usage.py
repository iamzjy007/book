"""Rebuild and read book-specific, paragraph-level evidence for CUV terms."""

import argparse
import hashlib
import json
import re
import sqlite3
import tempfile
from collections import defaultdict
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import DB, ROOT
from .term_store import term_digest
from .wordstudy import author_prose


BOOKS = {"lori": "Daily_Words_The_Lords_Glory_with_Lori",
         "dydi": "DYDI_Messages_Declaring_Your_Destiny"}
HEADING = re.compile(r"^# Chapter (\d+) · (\d{4}-\d{2}-\d{2}) · .+$", re.M)
SOURCE_URL = re.compile(r"^(?:URL:|原文[:：])\s*(https?://\S+)\s*$", re.M)
REFERENCE_LINE = re.compile(
    r"(?:[1-3]|I{1,3})?\s*[A-Za-z]+(?:\s+[A-Za-z]+){0,3}\.?\s+\d+:\d+[a-c]?"
    r"(?:\s*[-–—,]\s*\d+[a-c]?)*(?:\s+\(?[A-Z]{2,6}\)?)?\.?"
)
ENDNOTE = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\*\*)?[【［（(]?"
                     r"(?:译者注|译者待核实问题|原文修正说明)(?=$|[\s:：】］）)*])")
VERSION = 1


def fingerprint(text):
    normalized = " ".join(text.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class Chapter:
    date: str
    url: str
    paragraphs: list


def read_chapters(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chapters = {}
    for section in re.split(r"(?m)^={10,}[ \t]*\r?$", text):
        blocks = re.split(r"\n\s*\n", section.strip())
        header = HEADING.fullmatch(blocks[0])
        if not header:
            if section.lstrip().startswith("# Chapter "):
                raise ValueError("无法识别篇标题")
            continue
        number = int(header[1])
        if number in chapters:
            raise ValueError(f"篇号重复：{number}")
        url = SOURCE_URL.search(blocks[1]) if len(blocks) > 1 else None
        chapters[number] = Chapter(header[2], url[1] if url else "", blocks[2:])
    if not chapters:
        raise ValueError("未找到合订本篇标题")
    return chapters


def eligible(paragraphs, index):
    p = paragraphs[index]
    # Reuse the packet's independent-quotation filter, including the next citation.
    window = paragraphs[index:index + 2]
    if any(REFERENCE_LINE.fullmatch(part.strip()) for part in window):
        return False
    pair = "\n\n".join(window)
    if not author_prose(pair).startswith(p):
        return False
    return not (index == len(paragraphs) - 1 and p.startswith(('"', "“")))


def observed_form(text, term):
    # A lone character such as 义 can occur as part of 意义. It cannot establish usage.
    forms = [form for form in (term.preferred, *term.variants) if len(form) >= 2 and form in text]
    if not forms:
        return None
    # 军装 within 全副军装 supports the base wording. Two unrelated forms in one
    # paragraph cannot be individually linked to the source and are left unresolved.
    primary = term.preferred
    if primary in forms and all(primary in form or form in primary for form in forms):
        return primary
    longest = max(forms, key=len)
    return longest if all(form in longest for form in forms) else None


def aligned_chapters(en_chapters, zh_chapters, skipped):
    for number in sorted(en_chapters.keys() | zh_chapters.keys()):
        en, zh = en_chapters.get(number), zh_chapters.get(number)
        if en is None or zh is None:
            skipped["unpaired"].append(number)
            continue
        if not en.url or en.date != zh.date or en.url != zh.url:
            skipped["source_mismatch"].append(number)
            continue
        # Notes can be a heading followed by several paragraphs, or a single
        # paragraph beginning with a label. Only the preceding body can be paired.
        notes_start = next((i for i, p in enumerate(zh.paragraphs) if ENDNOTE.match(p)), None)
        if notes_start is not None:
            zh = Chapter(zh.date, zh.url, zh.paragraphs[:notes_start])
        if not en.paragraphs or en.paragraphs == ["[No transcript body]"] or not zh.paragraphs:
            skipped["empty"].append(number)
            continue
        if len(en.paragraphs) != len(zh.paragraphs):
            skipped["paragraph_mismatch"].append(number)
            continue
        yield number, en, zh


def aligned_paragraphs(en, zh):
    for i, (source, target) in enumerate(zip(en.paragraphs, zh.paragraphs)):
        if eligible(en.paragraphs, i):
            target = re.split(r"[（(]\s*译者注\s*[:：]", target, maxsplit=1)[0]
            yield i + 1, source, target


def examples(en_chapters, zh_chapters, query, limit=4, chapter=None):
    words = query.strip().replace("’", "'").split()
    if not words or not any(re.search(r"[a-zA-Z]", word) for word in words):
        raise ValueError("请输入要查找的英文词或短语")
    if limit < 1:
        raise ValueError("用例条数须为正整数")
    expression = r"(?<!\w)" + r"\s+".join(re.escape(w) for w in words) + r"(?!\w)"
    pattern = re.compile(expression, re.I)
    count = 0
    for number, en, zh in aligned_chapters(en_chapters, zh_chapters, defaultdict(list)):
        if chapter is not None and number != chapter:
            continue
        for p, source, target in aligned_paragraphs(en, zh):
            if pattern.search(source.replace("’", "'")):
                yield number, p, source, target
                count += 1
                if count == limit:
                    return


def observations(en_chapters, zh_chapters, find_terms):
    rows = defaultdict(lambda: defaultdict(list))
    signatures = defaultdict(list)
    for number, en in en_chapters.items():
        if en.paragraphs:
            signatures[fingerprint(" ".join(en.paragraphs))].append(number)
    skipped = defaultdict(list)
    aligned = paragraph_count = 0
    for number, en, zh in aligned_chapters(en_chapters, zh_chapters, skipped):
        aligned += 1
        for p, source, target in aligned_paragraphs(en, zh):
            paragraph_count += 1
            by_span = defaultdict(dict)
            for hit in find_terms(source):
                by_span[hit.start, hit.end][hit.term.id] = hit.term
            # The target paragraph may contain both candidate translations somewhere.
            # It cannot tell us which sense owns an ambiguous occurrence.
            unique_terms = {term_id: term for choices in by_span.values() if len(choices) == 1
                            for term_id, term in choices.items()}
            for term_id, term in unique_terms.items():
                form = observed_form(target, term)
                if form:
                    rows[term_id][form].append([number, p])
    return {"aligned_chapters": aligned, "eligible_paragraphs": paragraph_count,
            "skipped": dict(skipped), "signatures": dict(signatures), "terms": dict(rows)}


def text_digest(data):
    # Hash logical corpus contents, independent of UTF-8 BOM and newline convention.
    source = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def read_book(corpus_root, book):
    paths = [corpus_root / (BOOKS[book] + suffix) for suffix in (".txt", "_zh.txt")]
    contents = [p.read_bytes() for p in paths]
    en, zh = (read_chapters(data.decode("utf-8-sig")) for data in contents)
    hashes = {path.name: text_digest(data) for path, data in zip(paths, contents)}
    return en, zh, hashes


@contextmanager
def connection(db=None, path=DB, writable=False):
    if db is not None:
        yield db
        return
    mode = "rw" if writable else "ro"
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode="+mode, uri=True)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn


@contextmanager
def transaction(db):
    # A savepoint works both standalone and inside the initial migration.
    db.execute("SAVEPOINT book_usage_snapshot")
    try:
        yield
    except BaseException:
        db.execute("ROLLBACK TO book_usage_snapshot")
        raise
    finally:
        db.execute("RELEASE book_usage_snapshot")


def snapshot(db, corpus_root):
    from .terms import find_terms

    result = {"version": VERSION, "term_sha256": term_digest(db), "books": {}}
    for book in BOOKS:
        en, zh, hashes = read_book(corpus_root, book)
        report = observations(en, zh, lambda source: find_terms(source, db=db))
        report["files"] = hashes
        result["books"][book] = report
    return result


def write_json(result, out):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=out.parent, delete=False) as f:
            temp = Path(f.name)
            json.dump(result, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\n")
        temp.replace(out)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def build(corpus_root, out, db=None):
    """Build an optional interchange file without changing the database."""
    with connection(db) as conn, transaction(conn):
        result = snapshot(conn, corpus_root)
    write_json(result, out)
    return result


def store_usage(db, data):
    """Atomically install a freshly built or validated historical snapshot."""
    with transaction(db):
        if data.get("version") != VERSION or data.get("term_sha256") != term_digest(db):
            raise ValueError("用例快照与本库惯用词版本不符，请用当前底稿重建")
        if set(data["books"]) != set(BOOKS):
            raise ValueError("用例快照缺少作品或含未知作品")
        db.execute("""CREATE TABLE IF NOT EXISTS usage_book(
            book TEXT PRIMARY KEY, version INTEGER NOT NULL, term_sha256 TEXT NOT NULL,
            aligned_chapters INTEGER NOT NULL, eligible_paragraphs INTEGER NOT NULL,
            skipped TEXT NOT NULL, files TEXT NOT NULL) WITHOUT ROWID""")
        db.execute("""CREATE TABLE IF NOT EXISTS usage_chapter(
            book TEXT NOT NULL REFERENCES usage_book(book), chapter INTEGER NOT NULL,
            signature TEXT NOT NULL, PRIMARY KEY(book,chapter)) WITHOUT ROWID""")
        db.execute("""CREATE INDEX IF NOT EXISTS usage_chapter_signature
            ON usage_chapter(book,signature,chapter)""")
        db.execute("""CREATE TABLE IF NOT EXISTS usage_example(
            book TEXT NOT NULL, term_id TEXT NOT NULL REFERENCES idiom(id) ON DELETE CASCADE,
            chapter INTEGER NOT NULL, paragraph INTEGER NOT NULL CHECK(paragraph>0), form TEXT NOT NULL,
            PRIMARY KEY(book,term_id,chapter,paragraph),
            FOREIGN KEY(book,chapter) REFERENCES usage_chapter(book,chapter)) WITHOUT ROWID""")
        for table in ("usage_example", "usage_chapter", "usage_book"):
            db.execute(f"DELETE FROM {table}")
        for book, report in data["books"].items():
            db.execute("INSERT INTO usage_book VALUES (?,?,?,?,?,?,?)",
                       (book, VERSION, data["term_sha256"], report["aligned_chapters"], report["eligible_paragraphs"],
                        json.dumps(report["skipped"]), json.dumps(report["files"])))
            db.executemany("INSERT INTO usage_chapter VALUES (?,?,?)",
                           ((book, i, signature) for signature, numbers in report["signatures"].items() for i in numbers))
            db.executemany("INSERT INTO usage_example VALUES (?,?,?,?,?)",
                           ((book, term_id, ch, p, form) for term_id, forms in report["terms"].items()
                            for form, locations in forms.items() for ch, p in locations))
        # The caller can also supply an existing connection with FK enforcement disabled.
        if db.execute("PRAGMA foreign_key_check(usage_example)").fetchone() is not None:
            raise ValueError("用例引用了缺失的惯用词或篇号")


def rebuild(db, corpus_root):
    with transaction(db):
        data = snapshot(db, corpus_root)
        store_usage(db, data)
    return data


def available(db, book):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usage_book'").fetchone():
        return False
    row = db.execute("SELECT version, term_sha256 FROM usage_book WHERE book=?", (book,)).fetchone()
    return bool(row and row[0] == VERSION and row[1] == term_digest(db))


def load_index(db=None):
    """Materialize full reports for validation/export. Ordinary lookups use the indexes."""
    result = {}
    with connection(db) as conn, transaction(conn):
        for book in BOOKS:
            if not available(conn, book):
                continue
            aligned, paragraphs, skipped, files = conn.execute("""SELECT aligned_chapters,
                eligible_paragraphs,skipped,files FROM usage_book WHERE book=?""",(book,)).fetchone()
            signatures = defaultdict(list)
            for signature, ch in conn.execute(
                    "SELECT signature,chapter FROM usage_chapter WHERE book=? ORDER BY chapter",(book,)):
                signatures[signature].append(ch)
            terms = {}
            for tid, form, ch, p in conn.execute("""SELECT term_id,form,chapter,paragraph
                    FROM usage_example WHERE book=? ORDER BY term_id,chapter,paragraph""",(book,)):
                terms.setdefault(tid, {}).setdefault(form, []).append([ch, p])
            result[book] = dict(aligned_chapters=aligned, eligible_paragraphs=paragraphs,
                                skipped=json.loads(skipped), files=json.loads(files),
                                signatures=dict(signatures), terms=terms)
    return result


def current_chapters(db, book, source, chapter_number):
    heading = HEADING.search(source)
    if chapter_number is None and heading:
        chapter_number = int(heading[1])
    # A differently numbered reprint can still match the body of an older chapter.
    signature = fingerprint(source[heading.end():] if heading else source)
    same = db.execute("""SELECT chapter FROM usage_chapter WHERE book=? AND
        signature IN (?, (SELECT signature FROM usage_chapter WHERE book=? AND chapter=?))""",
        (book, signature, book, chapter_number))
    omitted = {row[0] for row in same}
    if chapter_number is not None:
        omitted.add(chapter_number)
    return sorted(omitted)


def usage_hint(term_id, book, source, chapter_number=None, *, db=None):
    """One short line of same-book observations. Suppress unidentifiable excerpts."""
    if book not in BOOKS:
        return ""
    with connection(db) as conn, transaction(conn):
        if not available(conn, book):
            return ""
        omit = current_chapters(conn, book, source, chapter_number)
        if not omit:
            return ""
        # Group just this book/term's observations, retaining a real example
        # from the first matching chapter for each of its three commonest forms.
        marks = ",".join("?" for _ in omit)
        rows = conn.execute(f"""WITH peers AS (
            SELECT form,chapter,paragraph FROM usage_example
            WHERE book=? AND term_id=? AND chapter NOT IN ({marks})),
            counts AS (SELECT form,count(*) AS n,min(chapter) AS first_ch FROM peers
                        GROUP BY form ORDER BY n DESC,form LIMIT 3)
            SELECT c.form,c.n,c.first_ch,min(p.paragraph) FROM counts c JOIN peers p
                ON p.form=c.form AND p.chapter=c.first_ch
            GROUP BY c.form,c.n,c.first_ch ORDER BY c.n DESC,c.form""", (book, term_id, *omit))
        return "、".join(f"「{form}」{n}段（如{ch:03d}篇第{p}段）" for form,n,ch,p in rows)


def main():
    parser = argparse.ArgumentParser(description="将两书的同段译法用例写入知识库，查询时排除本篇。")
    parser.add_argument("--corpus-root", type=Path, default=ROOT.parent)
    parser.add_argument("--db", type=Path, default=DB, help="SQLite 知识库")
    parser.add_argument("--out", type=Path, help="按当前底稿另存 JSON 快照；配合 --check 核对指定快照")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="核对已存用例版本与两书英中底稿")
    mode.add_argument("--examples", metavar="英文词或短语", help="按输入词形查英中对齐的现译段落")
    parser.add_argument("--book", choices=BOOKS)
    parser.add_argument("--chapter", type=int, help="反查时限定篇号")
    parser.add_argument("--limit", type=int, help="最多显示的平行段数，默认四段")
    args = parser.parse_args()
    if args.examples is None and any(arg is not None for arg in (args.book, args.chapter, args.limit)):
        parser.error("--book、--chapter 和 --limit 用于 --examples")
    if args.examples is not None and not args.book:
        parser.error("查本书段例请用 --book 指定作品")
    try:
        if args.examples is not None:
            en, zh, _ = read_book(args.corpus_root, args.book)
            limit = 4 if args.limit is None else args.limit
            rows = list(examples(en, zh, args.examples, limit, args.chapter))
            print("按所输英文词形匹配。每例列出同篇同段的原文和现译，供核对词义。")
            for ch, p, source, target in rows:
                print(f"\n{args.book.upper()} 第{ch:03d}篇第{p}段\n{source}\n{target}")
            if not rows:
                print("在可对齐的正文中未找到该词形。")
            return
        if args.out is not None and args.out.resolve() == args.db.resolve():
            raise ValueError("JSON 快照和 SQLite 知识库须使用不同的文件名")
        with connection(path=args.db, writable=not args.check and args.out is None) as db, transaction(db):
            if args.check:
                if args.out is None:
                    reports = load_index(db)
                else:
                    data = json.loads(args.out.read_text(encoding="utf-8"))
                    if data.get("version") != VERSION or data.get("term_sha256") != term_digest(db):
                        raise ValueError("词表或用例版本已变更，请重新生成同书用例")
                    reports = data["books"]
                if set(reports) != set(BOOKS):
                    raise ValueError("同书用例缺失或版本不符，请重新生成同书用例")
                for book, base in BOOKS.items():
                    for suffix in (".txt", "_zh.txt"):
                        path = args.corpus_root / (base + suffix)
                        if text_digest(path.read_bytes()) != reports[book]["files"].get(path.name):
                            raise ValueError(f"{path.name} 已变更，请重新生成同书用例")
            elif args.out is not None:
                reports = build(args.corpus_root, args.out, db)["books"]
            else:
                reports = rebuild(db, args.corpus_root)["books"]
    except (OSError, ValueError, KeyError, sqlite3.Error) as error:
        parser.exit(1, str(error) + "\n")
    for book, report in reports.items():
        print(f"{book}：对齐 {report['aligned_chapters']} 篇，"
              f"{len(report['terms'])} 个义项有英中同段用例。")


if __name__ == "__main__":
    main()
