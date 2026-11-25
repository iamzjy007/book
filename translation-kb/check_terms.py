"""Compare the English in a translation packet with a Chinese draft, locally."""
import argparse
from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from kb import DB
from kb.grammar import paragraphs
from kb.terms import find_terms, reference_label
from kb.book_usage import usage_hint
from lookup import source_digest


STAMP = re.compile(r"^<!-- translation-kb book=(lori|dydi|other) source-sha256=([a-f0-9]{64}) -->$", re.M)
CHAPTER = re.compile(r"^(?:# Chapter\s+(\d+)\s*·|#?\s*第\s*(\d+)\s*[篇章]\s*[·：:])", re.M)
CITATION = re.compile(r"^[\w .·]+\s*\d+[:：][\d,， –—\-]+\s*[（(]?.{0,24}(?:AMPC|NKJV).{0,16}$", re.I)
DATE = re.compile(r"(?:\d{1,4}[-/.年]\d{1,2}[-/.月]\d{1,4}日?)")


def numbered_body(text):
    """Keep original paragraph numbers for revision.py. Ignore publication furniture."""
    blocks = [(i, p.strip()) for i, p in enumerate(paragraphs(text), 1) if p.strip()]
    body = []
    for i, p in blocks:
        if p.startswith(("原文修正说明", "译者待核实问题", "译者注：")):
            break
        if CITATION.fullmatch(p):
            if body and body[-1][0] == i-1 and body[-1][1].rstrip().endswith(('"', '”', '’', '」', '』')):
                body.pop()
            continue
        if (p.startswith(("#", "Date:", "Video:", "URL:", "日期：", "日期:", "http")) or
                CHAPTER.match(p) or DATE.fullmatch(p) or re.fullmatch(r"[-—= ]+", p) or
                re.fullmatch(r"[-—]+[^\n]+[-—]+", p)):
            continue
        body.append((i, p))
    return body


def read_packet(path):
    packet = path.read_text(encoding="utf-8-sig")
    guide, separator, source = packet.partition("\n## 待译原文\n")
    stamp = STAMP.search(guide)
    if not separator or not stamp:
        raise ValueError("请先用 lookup.py 为本篇生成翻译包，再用该包核对中文稿")
    if source_digest(source) != stamp[2]:
        raise ValueError("翻译包的待译原文已经变动，请从相应原稿重新制包")
    return stamp[1], source.strip()


def select_draft(source, draft):
    from revision import chinese_chapter

    def numbers(text):
        return [int(a or b) for a, b in CHAPTER.findall(text)]
    original, translated = numbers(source), numbers(draft)
    if len(translated) > 1:
        if len(original) != 1:
            raise ValueError("中文是合订本，翻译包须含唯一篇号")
        return chinese_chapter(draft, original[0])
    if original and translated and original != translated:
        raise ValueError("翻译包和中文稿的篇号不同")
    if not re.search(r"[\u3400-\u9fff]", draft):
        raise ValueError("未找到中文译文")
    return draft


def target_matches(term, paragraph):
    # A single character inside a longer word (e.g. 义 in 意义) cannot
    # establish the translation. Surface it separately if it is all we have.
    words = sorted({term.preferred, *term.variants}, key=len, reverse=True)
    pattern = "|".join(re.escape(word) if len(word) > 1 else
                       r"(?<![\u3400-\u9fff])" + re.escape(word) + r"(?![\u3400-\u9fff])"
                       for word in words)
    count = len(re.findall(pattern, paragraph))
    uncertain = any(len(word) == 1 and word in paragraph for word in words)
    return count, uncertain


def audit_terms(source, draft, names, book="other", db=None):
    en, zh = numbered_body(source), numbered_body(draft)
    aligned = len(en) == len(zh) and bool(en)
    findings = []
    checked = 0
    for i, (source_p, english) in enumerate(en):
        by_term = defaultdict(list)
        for hit in find_terms(english, db):
            if hit.supported:
                by_term[hit.term].append(hit)
        for term, hits in by_term.items():
            checked += len(hits)
            target_p, chinese = zh[i] if aligned else (None, "")
            count, single_char = target_matches(term, chinese)
            if aligned and count >= len(hits):
                continue
            first = hits[0]
            before = list(re.finditer(r"\S+", english[:first.start]))[-5:]
            after = list(re.finditer(r"\S+", english[first.end:]))[:6]
            start = before[0].start() if before else first.start
            end = first.end + after[-1].end() if after else first.end
            excerpt = english[start:end]
            findings.append(dict(term=term.id, source_p=source_p, target_p=target_p,
                                 source=excerpt, single_character=single_char,
                                 fragments=list(dict.fromkeys(h.fragment for h in hits)),
                                 occurrences=len(hits), chinese_matches=count if aligned else None,
                                 preferred=term.preferred, variants=list(term.variants),
                                 reference=reference_label(names, term.refs[0]), note=term.note,
                                 book_usage=usage_hint(term.id, book, source, db=db)))
    return dict(aligned=aligned, english_paragraphs=len(en), chinese_paragraphs=len(zh),
                supported_occurrences=checked, findings=findings)


def audit(source, draft, book="other"):
    with closing(sqlite3.connect(DB.as_uri()+"?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        names = dict(db.execute("SELECT code,name FROM books WHERE edition='cmn-cu89s'"))
        return audit_terms(source, draft, names, book, db)


def review_lines(report):
    lines = []
    if not report["aligned"]:
        lines.append(f"英中正文分段无法逐段对应（{report['english_paragraphs']} / {report['chinese_paragraphs']}）。请按英文片段定位中文核对。")
    for item in report["findings"]:
        where = f"英段 {item['source_p']}"
        if item["target_p"] is not None:
            where += f" / 中段 {item['target_p']}，英文 {item['occurrences']} 处、中文候选措辞 {item['chinese_matches']} 处"
        caution = " 段内有相同单字，仍须确认词义。" if item["single_character"] else ""
        observed = f" 同书现译同段见{item['book_usage']}。" if item["book_usage"] else ""
        lines.append(f"- {where}　「{item['source']}」 可参「{item['preferred']}」（{item['reference']}）。{item['note']}{caution}{observed}")
    return lines


def main():
    parser = argparse.ArgumentParser(description="用本篇翻译包逐段核对中文惯用词。")
    parser.add_argument("packet", type=Path)
    parser.add_argument("draft", type=Path, help="独立中文稿，或与翻译包篇号对应的中文合订本")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="有待核项或无法对齐时返回状态码 2")
    args = parser.parse_args()
    try:
        book, source = read_packet(args.packet)
        draft = select_draft(source, args.draft.read_text(encoding="utf-8-sig"))
        report = audit(source, draft, book)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"惯用词核对：原文 {report['supported_occurrences']} 处有语境依据，待核 {len(report['findings'])} 项。")
        print("\n".join(review_lines(report) or ["本轮未检出惯用词差异。"]))
    if args.strict and (report["findings"] or not report["aligned"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
