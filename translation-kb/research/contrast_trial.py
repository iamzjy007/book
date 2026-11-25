"""Generate a counterbalanced reading sheet, or score returned choices against the pilot key."""
import argparse
import json
from pathlib import Path
from random import Random
import sys


def cases_from_file():
    return json.loads(Path(__file__).with_name("contrasts.json").read_text("utf8"))


def trial(seed):
    cases = [case for case in cases_from_file() if not case.get("control")]
    rng = Random(seed)
    rng.shuffle(cases)
    sides = list("AB" * ((len(cases)+1)//2))[:len(cases)]
    rng.shuffle(sides)
    sheet, key = [], {}
    for i, (c, side) in enumerate(zip(cases, sides), 1):
        labels = ("A","B") if side == "A" else ("B","A")
        sheet.append({"id":str(i),"source":c["source"],labels[0]:c["faithful"],labels[1]:c["foil"]})
        key[str(i)] = (side,c["id"],c["criterion"])
    # Keep display order independent of which wording is preferred.
    return [{k:r[k] for k in ("id","source","A","B")} for r in sheet], key


def compare_term_alerts():
    """Run the production term checker on each labelled translation separately."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from check_terms import audit

    results = []
    for case in cases_from_file():
        result = {"id": case["id"]}
        for side in ("faithful", "foil"):
            report = audit(case["source"], case[side])
            if not report["aligned"]:
                raise ValueError(f"{case['id']} 的英中段落无法对应")
            result[side] = [item["term"] for item in report["findings"]]
        results.append(result)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=17)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--answers", type=Path, help='UTF-8 JSON 如 {"1":"A","2":"B",…}；平局填 tie')
    mode.add_argument("--audit-terms", action="store_true", help="比较惯用词审校对两份候选译文各报了哪些词")
    args = parser.parse_args()
    if args.audit_terms:
        print(json.dumps(compare_term_alerts(), ensure_ascii=False, indent=2))
    elif not args.answers:
        sheet, _ = trial(args.seed)
        print(json.dumps(sheet, ensure_ascii=False,indent=2))
    else:
        _, key = trial(args.seed)
        votes = json.loads(args.answers.read_text("utf-8-sig"))
        if set(votes) != set(key) or any(x not in ("A","B","tie") for x in votes.values()):
            parser.error("需要每道题的 A、B 或 tie")
        for index, (side, category, why) in key.items():
            print(category, "平局" if votes[index]=="tie" else ("一致" if votes[index]==side else "分歧"), why)
