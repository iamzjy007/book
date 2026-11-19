"""Compare independently annotated readings of a clause. Input is UTF-8 JSON."""
import argparse
import json
from pathlib import Path


def claims(reading):
    text = reading["text"]
    result = {}
    for clause, slots in reading["clauses"].items():
        if not slots or "predicate" not in slots:
            raise ValueError("each clause requires a predicate")
        for slot, item in slots.items():
            value, span = item
            if not isinstance(value, str) or not value.strip() or not span or span not in text:
                raise ValueError(f"missing evidence for {clause}.{slot}: {span}")
            result[clause, slot] = value
    if not result:
        raise ValueError("no annotated clauses")
    return result


def differences(source, target):
    left, right = claims(source), claims(target)
    rows = []
    for clause, slot in sorted(left.keys() | right.keys()):
        a, b = left.get((clause,slot)), right.get((clause,slot))
        if a != b or a == "?":
            rows.append({"clause":clause, "slot":slot, "source":a, "target":b})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("readings",type=Path)
    data = json.loads(parser.parse_args().readings.read_text("utf-8-sig"))
    for name, reading in data["candidates"].items():
        print(name, json.dumps(differences(data["source"], reading), ensure_ascii=False))
