"""Generate a counterbalanced reading sheet, or score returned choices against the pilot key."""
import argparse
import json
from pathlib import Path
from random import Random


def trial(seed):
    cases = json.loads(Path(__file__).with_name("contrasts.json").read_text("utf8"))
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--answers", type=Path, help='UTF-8 JSON 如 {"1":"A","2":"B",…}；平局填 tie')
    args = parser.parse_args()
    sheet, key = trial(args.seed)
    if not args.answers:
        print(json.dumps(sheet, ensure_ascii=False,indent=2))
    else:
        votes = json.loads(args.answers.read_text("utf-8-sig"))
        if set(votes) != set(key) or any(x not in ("A","B","tie") for x in votes.values()):
            parser.error("需要每道题的 A、B 或 tie")
        for index, (side, category, why) in key.items():
            print(category, "平局" if votes[index]=="tie" else ("一致" if votes[index]==side else "分歧"), why)
