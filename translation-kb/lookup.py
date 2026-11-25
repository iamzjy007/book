"""Build an offline translation packet from a UTF-8 passage or a collected chapter."""

import argparse
from contextlib import closing
import hashlib
import re
import sqlite3
from pathlib import Path
from scripture import suggestions
from kb import DB, ROOT
from kb.grammar import short_notes
from kb.wordstudy import author_prose
from kb.terms import find_terms, term_notes


def chapter(text, number):
    sections = re.split(r"(?m)^={10,}[ \t]*\r?$", text)
    heading = f"# Chapter {number:03d} · "
    matches = [s.strip() for s in sections if s.strip().startswith(heading)]
    if len(matches) != 1:
        raise ValueError(f"无法唯一定位第 {number:03d} 篇")
    entry = matches[0]
    blocks = entry.split("\n\n", 2)
    if len(blocks) != 3 or not blocks[1].startswith("Date:"):
        raise ValueError("篇章格式无法辨认，请直接提供单篇文本")
    if blocks[2].strip() == "[No transcript body]":
        raise ValueError("该篇无原文正文")
    return blocks[0] + "\n\n" + blocks[2]


def normalize(text):
    return " ".join(text.casefold().replace("’", "'").split())


def packet(source, book, full=False):
    prose = author_prose(source)
    with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        matches = find_terms(prose, db)
        rows = db.execute(
            "SELECT label, pattern, advice, scope, origin FROM rules "
            "WHERE book IN ('all', ?) ORDER BY id", (book,)
        ).fetchall()
        biblical = suggestions(db, source, matches)
        vocabulary = term_notes(db, matches, book, source)
        grammar_notes = short_notes(prose, db=db)
    body = normalize(source)
    hits = []
    for label, pattern, advice, scope, origin in rows:
        if re.search(pattern, body) and not any(advice in hit and origin in hit for hit in hits):
            hits.append(f"- **{label}**　{advice}　适用范围：{scope}（{origin}）")
    return "\n\n".join([
        "# 单篇翻译包",
        f"<!-- translation-kb book={book} source-sha256={source_digest(source)} -->",
        "只翻译末尾待译区。下列候选由英文触发，先核对语境再采用。"
        "本次作品代号为 " + book + "。带篇号的约定按作品和适用范围使用。",
        "## 必读要点",
        "信优先于达，达优先于雅。用现代简体中文保留和合本式的庄重和朗读节奏。"
        "辨明说话者与受话者，随原文切换我、我们、你和你们。保留条件、否定、时间、"
        "确定程度、重复与比喻。避免仿古虚词，勿借熟悉的经句增添内容。",
        "## 本篇用词提示", "\n".join(hits) or "无已收录的特定搭配命中。",
        *vocabulary,
        *biblical,
        *(["## 本篇句法复核", "\n".join(grammar_notes)] if grammar_notes else []),
        "## 复核与交付",
        "请先据本包起草，逐段回看命中的惯用词。定稿时用 check_terms.py 将本包与中文稿对读，"
        "逐条决定采用或保留异译，再把定稿并入合订本。网页版模型可由制包者代跑，将待核清单交回同一模型。",
        "遮住英文，按说话者的口吻通读全段。如果搭配拗口或要读第二遍才知道谁在做什么，就调整语序、停顿或动词。"
        "再对照英文核实人称、意象与应许的范围，只交付定稿。保留标题、日期、段落、编号和引经标注。"
        "影响理解时才加简短译者注。重大疑错只有在上下文足够明确时才修正，并在本篇末尾写“原文修正说明”；"
        "重大歧义无法解决时保留原意，在本篇末尾写“译者待核实问题”。"
        "不写到合订本末尾；术语说明可用“译者注”。",
        *(["## 完整指南", (ROOT / "kb" / "style-guide.md").read_text(encoding="utf-8-sig").strip()] if full else []),
        "## 待译原文", source.strip()
    ]) + "\n"


def source_digest(source):
    return hashlib.sha256(source.strip().replace("\r\n", "\n").encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--book", required=True, choices=["dydi", "lori", "other"])
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--full-guide", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        source = args.source.read_text(encoding="utf-8-sig")
        if args.chapter is not None:
            source = chapter(source, args.chapter)
        elif len(re.findall(r"(?m)^# Chapter \d+ · ", source)) > 1:
            raise ValueError("合订本请用 --chapter 选择一篇")
        if not source.strip():
            raise ValueError("原文为空")
        result = packet(source, args.book, args.full_guide)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(result)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
