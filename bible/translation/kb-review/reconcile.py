"""Apply evidence-backed editorial decisions to canonical JSON and verify compiled TXT."""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json

from scan import HERE, TRANSLATION, pipeline, selected


def content_hash(text):
    return sha256(text.encode("utf-8")).hexdigest()


def reconcile(apply=False):
    report=json.loads((HERE/"changes.json").read_text(encoding="utf-8"))
    for number in (2,3):
        followup=HERE/f"round-{number}"/"changes.json"
        if not followup.exists():
            break
        later=json.loads(followup.read_text(encoding="utf-8"))
        if later["epub_sha256"]!=report["epub_sha256"]:
            raise ValueError("两轮使用的底本不同")
        indexed={(e["book"],e["unit"],e["block"]):e for e in report["edits"]}
        for e in later["edits"]:
            key=e["book"],e["unit"],e["block"]
            if key in indexed and indexed[key]["after"]!=e["before"]:
                raise ValueError("两轮中文底稿未衔接："+str(key))
            indexed[key]=e
        report={**report,"baseline":later["baseline"],"edits":list(indexed.values())}
    if report["epub_sha256"]!=pipeline.manifest()["source_sha256"]:
        raise ValueError("英文底本与审校记录不同")
    edits=defaultdict(list)
    identities=set()
    for e in report["edits"]:
        key=e["book"],e["unit"],e["block"]
        if key in identities or e["before"]==e["after"]:
            raise ValueError(key)
        identities.add(key)
        edits[key[:2]].append(e)
    prepared={}
    books=selected()
    targets={}
    visited=set()
    with TemporaryDirectory(prefix="ethiopic-assembly-") as tmp:
        for b in books:
            name=b["id"]
            target=TRANSLATION/"output"/(b["title_zh"]+".txt")
            targets[name]=target
            mirror=Path(pipeline.build({**b,"title_zh":str(Path(tmp)/name)}))
            old=target.read_text(encoding="utf-8")
            if mirror.read_text(encoding="utf-8")!=old and content_hash(old)!=report["baseline"].get(name):
                raise ValueError("TXT 有未纳入段落译稿的其他改动："+name)
            for u in b["units"]:
                group=edits.get((name,u["id"]))
                if not group:
                    continue
                f=TRANSLATION/"zh"/name/(u["id"]+".json")
                data=pipeline.read(f)
                en={s["id"]:s["text"] for s in pipeline.source_unit(b,u)["blocks"]}
                zh={s["id"]:s for s in data["blocks"]}
                for e in group:
                    block=e["block"]
                    visited.add((name,u["id"],block))
                    if en[block]!=e["en"] or zh[block]["zh"] not in (e["before"],e["after"],*e.get("earlier",[])):
                        raise ValueError(f"原文或中文底稿有变 {name}/{u['id']}/{block}")
                    zh[block]["zh"]=e["after"]
                prepared[f]=data
        if visited!=identities:
            raise ValueError("存在未能定位的修改")
        if apply:
            for f,data in prepared.items():
                if pipeline.read(f)!=data:
                    pipeline.save(f,data)
            signatures=pipeline.read(TRANSLATION/"assembly-state.json")
            for b in books:
                if not any(key[0]==b["id"] for key in edits):
                    continue
                # Build outside output first. Replace each completed TXT atomically.
                generated=Path(pipeline.build({**b,"title_zh":str(Path(tmp)/b["id"])}))
                target=targets[b["id"]]
                if target.read_bytes()!=generated.read_bytes():
                    staged=target.with_suffix(".kb-review.tmp")
                    staged.write_bytes(generated.read_bytes())
                    staged.replace(target)
                files=[TRANSLATION/"zh"/b["id"]/(u["id"]+".json") for u in b["units"]]
                signatures[b["id"]]=sha256(b"".join(f.read_bytes() for f in files)).hexdigest()
            pipeline.save(TRANSLATION/"assembly-state.json",signatures)
        for b in books:
            name=b["id"]
            mirrored=Path(pipeline.build({**b,"title_zh":str(Path(tmp)/name)}))
            if targets[name].read_text(encoding="utf-8")!=mirrored.read_text(encoding="utf-8"):
                raise ValueError("汇编不一致："+name)
            for u in b["units"]:
                if (name,u["id"]) in edits:
                    f=TRANSLATION/"zh"/name/(u["id"]+".json")
                    if pipeline.read(f)!=prepared[f]:
                        raise ValueError("尚有经核定的修改未写入："+name)
    print(f"核对 {len(books)} 份正式 TXT，{len(visited)} 处修改，{len(prepared)} 个改动单元。")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--apply",action="store_true")
    reconcile(cli.parse_args().apply)
