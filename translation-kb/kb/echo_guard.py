"""Look up Chinese wording lost in an edit, then check its surrounding context."""
from contextlib import closing
from difflib import SequenceMatcher
from functools import lru_cache
import re
import sqlite3


from . import DB


@lru_cache(maxsize=2048)
def candidates(fragment):
    with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("""
            SELECT z.code, z.ch, z.first, z.text, e.text FROM verses z
            LEFT JOIN verses e ON (e.code,e.ch,e.first)=(z.code,z.ch,z.first)
                AND e.edition='engwebp'
            WHERE z.edition='cmn-cu89s' AND instr(z.text,?)>0 LIMIT 33
        """, (fragment,)).fetchall()
    return rows if len(rows) <= 32 else []


def canonical_names():
    with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("""
            SELECT en, zh, code, ch, v FROM terms
            WHERE kind IN ('人名', '地名') ORDER BY rowid
        """)
        return [(re.compile(r"\b" + re.escape(en) + r"\b", re.I), zh, f"{code} {ch}:{v}")
                for en, zh, code, ch, v in rows]


def check_wording(source, draft, revised, before, after, reason):
    for english, chinese, ref in canonical_names():
        if chinese in draft and revised.count(chinese) < draft.count(chinese) and english.search(source):
            if revised.count(chinese) < len(english.findall(source)):
                raise ValueError(f"拟删规范专名「{chinese}」，请核对 {ref} 及书内异写。")

    if re.search(r"\bevery nation and tongue\b", source, re.I):
        if draft.count("各国各方之民") > revised.count("各国各方之民"):
            raise ValueError("请保留已评定的「各国各方之民」。")
        for wording in ("各国、各方言之民", "各国各方言之民"):
            if revised.count(wording) > draft.count(wording):
                raise ValueError("已评定的并列译法为「各国各方之民」。")

    # Replacing an existing coordinator with a list comma is not an expansion.
    old_separators = len(re.findall(r"、|以及|或是|或者|[和与及或]", before))
    if ("、" in after and after.count("、") > old_separators
            and len(after) > len(before) and re.search(r"\b(?:and|or)\b", source, re.I)):
        if not re.search(r"并列复核【[^】\s][^】]*】", reason):
            raise ValueError(f"请通读改前：{draft}\n改后：{revised}\n"
                             "在理由中填写 并列复核【新增的含义及各项如何衔接】。")


def check_edit(source, draft, before, after, reason):
    start = draft.index(before)
    revised = draft[:start] + after + draft[start + len(before):]
    check_wording(source, draft, revised, before, after, reason)
    hits = {}
    # Include the surroundings so even a one-character edit can damage an echo.
    for pos in range(max(0, start-3), min(len(draft)-3, start+len(before))):
        fragment = draft[pos:pos+4]
        if not re.fullmatch(r"[\u3400-\u9fff]{4}", fragment):
            continue
        if draft.count(fragment) <= revised.count(fragment):
            continue
        for code, chapter, verse, zh, en in candidates(fragment):
            # Exclude the whole contiguous match containing this fragment.
            # The second piece of evidence must come from elsewhere in the verse.
            blocks = SequenceMatcher(None, draft, zh, autojunk=False).get_matching_blocks()
            anchor = next((b for b in blocks if b.a <= pos and pos+4 <= b.a+b.size), None)
            if not anchor:
                continue
            context = [len(s) for b in blocks if b != anchor
                       for s in re.findall(r"[\u3400-\u9fff]{4,}", draft[b.a:b.a+b.size])]
            if context:
                ref = f"{code} {chapter}:{verse}"
                hits[ref] = (sum(context)+anchor.size, zh, en)
    if hits:
        ref = max(hits, key=lambda key: hits[key][0])
        _, zh, en = hits[ref]
        override = re.search(r"经文取舍【([^】]+)】原文【([^】]+)】理由【([^】]+)】", reason)
        if override and override[1] == ref and override[2].strip() and override[2] in source and override[3].strip():
            return
        raise ValueError(f"拟删措辞与上下文呼应 {ref}：{zh} / {en}。请保留；如底本另有含义，"
                         f"在修改理由中填写 经文取舍【{ref}】原文【底本原句】理由【保留旧译会造成的具体误解】")
