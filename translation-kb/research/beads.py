"""Make a paired, offline reference packet for one English passage."""
import argparse
from contextlib import closing
import csv
import gzip
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from lookup import packet
from parallel_text import best_parallel, content
from scripture import DB

NAMES = "Gen|Exod|Lev|Num|Deut|Josh|Judg|Ruth|1 Sam|2 Sam|1 Kgs|2 Kgs|1 Chr|2 Chr|Ezra|Neh|Esth|Job|Ps|Prov|Eccl|Song|Isa|Jer|Lam|Ezek|Dan|Hos|Joel|Amos|Obad|Jonah|Mic|Nah|Hab|Zeph|Hag|Zech|Mal|Matt|Mark|Luke|John|Acts|Rom|1 Cor|2 Cor|Gal|Eph|Phil|Col|1 Thess|2 Thess|1 Tim|2 Tim|Titus|Phlm|Heb|Jas|1 Pet|2 Pet|1 John|2 John|3 John|Jude|Rev".split("|")
CODES = "GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SOL ISA JER LAM EZE DAN HOS JOE AMO OBA JON MIC NAH HAB ZEP HAG ZEC MAL MAT MAR LUK JOH ACT ROM 1CO 2CO GAL EPH PHI COL 1TH 2TH 1TI 2TI TIT PHM HEB JAM 1PE 2PE 1JO 2JO 3JO JUD REV".split()
BOOKS = dict(zip(CODES, NAMES))


def links(db, source):
    hit = best_parallel(db, source)
    if not hit:
        return []
    code, chapter, verse = hit.ref
    words = [k for k, _ in content(hit.source)]
    rows = []
    with gzip.open(HERE/"tsk-kjv.tsv.gz", "rt", encoding="utf8") as f:
        for row in csv.DictReader(f,delimiter="\t"):
            if (row["book"],row["chapter"],row["verse"]) != (BOOKS[code],str(chapter),str(verse)):
                continue
            keys = [k for k,_ in content(row["anchor"])]
            if keys and any(words[i:i+len(keys)] == keys for i in range(len(words))):
                rows.append(f"{row['book']} {chapter}:{verse} · {row['anchor']} → {row['references']}")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("--beads",action="store_true")
    parser.add_argument("--focus", help="附上原文中一两句的英中互文线索")
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    source = args.source.read_text("utf-8-sig")
    if args.focus is not None and (not args.focus.strip() or args.focus not in source):
        parser.error("--focus 必须逐字取自原文")
    result = packet(source,"other")
    if args.focus:
        from phrase_echo import echoes
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as db:
            notes = echoes(db, args.focus)
        if notes:
            note = ("## 待审短句的互文线索（实验）\n\n" + args.focus + "\n\n" +
                    "\n\n".join(notes) + "\n\n先对读锚词，再判断能借哪几个中文字。保留作者的人称、意象和新增成分。\n\n")
            result = result.replace("## 待译原文\n",note+"## 待译原文\n",1)
    if args.beads:
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as db:
            rows = links(db, args.focus or source)
        if rows:
            note = "## 词组串珠（实验）\n\n" + "\n\n".join(rows[:4])
            note += "\n\n英文锚词及章节目供查证，主题相连也可能用词不同。来源：CrossReferences.org，TSK，CC BY 4.0。\n\n"
            result = result.replace("## 待译原文\n",note+"## 待译原文\n",1)
    with args.out.open("x", encoding="utf8") as out:
        out.write(result)
