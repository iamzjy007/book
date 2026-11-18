"""Resumable same-model revision, using a private SQLite file per passage."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

from grammar import review_notes, paragraphs
from lookup import ROOT, chapter, normalize, packet
from scripture import references

PHASES = ("语义与经文", "句法与朗读", "定稿对照")
INSTRUCTIONS = (
    "对照相邻原句核实说话者、施受关系、否定、条件、时间与应许的力度。辨别引文和化用。只修有证据的问题。",
    "先遮住英文通读中文，再核原文。留意动宾搭配、过长的定语、平行句与呼告。让全段读起来像同一个人在说话。",
    "逐项核对前轮修改有无引入错义、删去意象或抹平说话者。也核查此前遗漏的问题。没有可说明的改善就交空数组。",
)
CATEGORIES = ("忠实性", "人称", "引经", "词义", "句法", "节奏")
FIELDS = ("source", "before", "after", "reading", "reason", "preserves")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encode(obj):
    return json.dumps(obj, ensure_ascii=False)


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def protected_text(source, draft, literals, book):
    locks = set(literals)
    if any(not t or t not in draft for t in locks):
        raise ValueError("指定保留的措辞须存在于初稿")
    # Find actual Chinese quotations even when spacing or punctuation differs
    # from the electronic edition. Keep the original draft's exact wording.
    with closing(sqlite3.connect((ROOT/"bible-style.sqlite3").as_uri()+"?mode=ro", uri=True)) as kb:
        heading = re.search(r"(?m)^# Chapter (\d+) · ",source)
        for pattern,wording,origin in kb.execute(
            "SELECT pattern,advice,origin FROM rules WHERE book=? AND origin LIKE '用户复评%'",(book,)):
            number = re.search(r"(?:Lori|DYDI)\s+(\d+)", origin)
            if heading and number and int(heading[1])!=int(number[1]):
                continue
            if wording in draft and re.search(pattern,normalize(source)):
                locks.add(wording)
        passages = set()
        for code,ch,lo,hi in references(kb,source):
            for verse, in kb.execute(
                "SELECT text FROM verses WHERE edition='cmn-cu89s' AND code=? AND ch=? AND first<=? AND last>=?",
                (code,ch,hi,lo)):
                han = "".join(re.findall(r"[\u3400-\u9fff]",verse))
                if len(han)>=4:
                    passages.add(han)
        for paragraph in paragraphs(draft):
            positions = [m.start() for m in re.finditer(r"[\u3400-\u9fff]",paragraph)]
            characters = "".join(paragraph[i] for i in positions)
            for han in passages:
                start = characters.find(han)
                while start >= 0:
                    locks.add(paragraph[positions[start]:positions[start+len(han)-1]+1])
                    start = characters.find(han,start+len(han))
    return sorted(locks)


def initialize(path, source, draft, book, locks=(), notes=()):
    if not source.strip() or not draft.strip():
        raise ValueError("原文与初稿均须有正文")
    if isinstance(notes,str) or any(not isinstance(n,str) or not n.strip() for n in notes):
        raise ValueError("校勘说明须逐条提供，每条均须有文字")
    locked = protected_text(source,draft,locks,book)
    # Atomic exclusive creation avoids truncating a previous run.
    with path.open("xb"):
        pass
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE job(source, initial, draft, book, locks, round INTEGER, status, runner, notes)")
        db.execute("CREATE TABLE history(turn INTEGER PRIMARY KEY, request_id UNIQUE, response, result, status)")
        db.execute("INSERT INTO job VALUES (?,?,?,?,?,0,'进行中',NULL,?)", (source,draft,draft,book,encode(locked),encode(list(notes))))


def state(db):
    db.row_factory = sqlite3.Row
    return db.execute("SELECT * FROM job").fetchone()


def request_id(job):
    identity=[job["book"],job["source"],job["draft"],job["locks"],job["round"]]
    if "notes" in job.keys() and job["notes"]!="[]":
        identity.append(job["notes"])
    return digest(encode(identity))


def request(db):
    job = state(db)
    if job["status"] != "进行中":
        raise ValueError("本次审校已结束："+job["status"])
    phase = job["round"] % 3
    notes=json.loads(job["notes"]) if "notes" in job.keys() else []
    history = [[{k:e[k] for k in ("target_p","before","after","reason")} for e in json.loads(r[0])["edits"]]
               for r in db.execute("SELECT response FROM history ORDER BY turn")]
    return dict(request_id=request_id(job), stage=PHASES[phase], instruction=INSTRUCTIONS[phase]+(
                "已有校勘说明是本篇证据。涉及其中的译法时，读清所据版本；只有更直接的证据才能推翻旧判断，并在理由中说明。" if notes else ""),
                editorial_notes=notes,
                source=paragraphs(job["source"]), draft=paragraphs(job["draft"]),
                passage_guide=packet(job["source"],job["book"]).partition("## 待译原文\n")[0],
                syntax=review_notes(job["source"],phase), protected=json.loads(job["locks"]), history=history,
                response_format={
                    "request_id":"照抄本次 request_id", "edits":[{
                        "source_p": "英文段号，从1开始", "source":"该段支持这次修改的英文原片段",
                        "target_p":"中文段号，从1开始", "before":"本段可唯一定位的原有中文",
                        "after":"拟替换中文", "category":"／".join(CATEGORIES),
                        "reading":"用一句话交代谁做什么、向谁、受什么条件限制",
                        "reason":"旧译的具体问题和新译如何修正",
                        "preserves":"与相邻句及原文核对后保住了什么",
                    }]}, output="只回 JSON。每处改动引一句依据，允许一段多处互不重叠的修改。无改进时 edits 交 []。")


def apply_response(db, reply):
    with db:
        db.execute("BEGIN IMMEDIATE")
        job = state(db)
        if not isinstance(reply, dict) or not isinstance(reply.get("request_id"),str):
            raise ValueError("答复缺 request_id")
        prior = db.execute("SELECT response,status FROM history WHERE request_id=?", (reply["request_id"],)).fetchone()
        if prior:
            if json.loads(prior[0]) == reply:
                return prior[1]
            raise ValueError("该轮已有不同答复")
        if job["status"]!="进行中" or reply["request_id"]!=request_id(job):
            raise ValueError("答复与当前底稿或轮次不符")
        edits = reply.get("edits")
        if not isinstance(edits,list):
            raise ValueError("edits 应为数组")
        original, target = paragraphs(job["source"]), paragraphs(job["draft"])
        replacements = {}
        for e in edits:
            if not isinstance(e,dict) or e.get("category") not in CATEGORIES:
                raise ValueError("修改类别无效")
            if any(not isinstance(e.get(k),str) or not e[k].strip() for k in FIELDS):
                raise ValueError("每处修改须填原文、前后译文、语义、理由与回查结果")
            s,t = e.get("source_p"),e.get("target_p")
            if type(s)!=int or type(t)!=int or not 1<=s<=len(original) or not 1<=t<=len(target):
                raise ValueError("段号无效")
            if e["source"] not in original[s-1] or target[t-1].count(e["before"]) != 1:
                raise ValueError("英文证据或中文替换位置无法定位")
            if e["before"] == e["after"] or "\n" in e["after"] or "\r" in e["after"]:
                raise ValueError("请提交段内实际发生的修改")
            start = target[t-1].index(e["before"])
            replacements.setdefault(t-1,[]).append((start,start+len(e["before"]),e["after"]))
        for i,changes in replacements.items():
            old = target[i]
            bound = len(old)
            for start,end,after in sorted(changes, reverse=True):
                if end>bound:
                    raise ValueError("两处修改重叠")
                target[i] = target[i][:start]+after+target[i][end:]
                bound = start
            if any(old.count(lock)!=target[i].count(lock) for lock in json.loads(job["locks"])):
                raise ValueError("修改触及本段已锁定的措辞")
        draft = job["draft"]
        if edits:
            chunks = []
            pos = 0
            for old,new in zip(paragraphs(draft),target):
                start = draft.index(old,pos)
                chunks.extend((draft[pos:start],new))
                pos = start+len(old)
            draft = "".join(chunks)+draft[pos:]
        turn = job["round"]+1
        status = "进行中"
        if edits and (draft==job["initial"] or db.execute("SELECT 1 FROM history WHERE result=?", (draft,)).fetchone()):
            status,draft = "待复核（改稿循环）",job["draft"]
        elif turn%3 == 0 and not edits:
            status = "已收敛"
        elif turn>=6:
            status = "待复核（达到轮次上限）"
        db.execute("INSERT INTO history VALUES (?,?,?,?,?)", (turn,reply["request_id"],encode(reply),draft,status))
        db.execute("UPDATE job SET round=?,draft=?,status=?", (turn,draft,status))
        return status


def run(db, worker, timeout, attempts=3):
    identity = digest(encode([worker,os.getenv("TRANSLATION_MODEL"),os.getenv("TRANSLATION_CHAT_URL")]))
    with db:
        db.execute("BEGIN IMMEDIATE")
        saved = state(db)["runner"]
        if saved and saved != identity:
            raise ValueError("本次作业的模型或适配程序与首次运行不同")
        db.execute("UPDATE job SET runner=?",(identity,))
    while state(db)["status"]=="进行中":
        payload = request(db)
        for attempt in range(attempts):
            try:
                result = subprocess.run(worker,input=encode(payload).encode("utf-8"),capture_output=True,timeout=timeout)
                if result.returncode:
                    raise ValueError(f"模型适配程序退出码 {result.returncode}")
                apply_response(db,json.loads(result.stdout.decode("utf-8-sig")))
                break
            except (ValueError,subprocess.TimeoutExpired) as error:
                if attempt+1 >= attempts:
                    raise ValueError(f"本轮未写入；可从当前轮重试。{error}") from error
                payload["retry_note"] = "请核对本轮原稿和 JSON 字段："+str(error)
    return state(db)["status"]


def chinese_chapter(text, number):
    sections = re.split(r"(?m)(?=^# Chapter \d+ · )",text)
    choices = [s for s in sections if s.startswith(f"# Chapter {number:03d} · ")]
    if len(choices)!=1:
        raise ValueError(f"无法唯一定位中文第 {number:03d} 篇")
    body = re.split(r"(?m)^={10,}[ \t]*$",choices[0],maxsplit=1)[0].strip()
    parts = paragraphs(body)
    if len(parts)>1 and parts[1].startswith(("日期：","日期:","Date:")):
        parts.pop(1)
    if len(parts)<2 or parts[1].strip() in ("［无文字稿正文］","[No transcript body]"):
        raise ValueError("该篇没有中文初稿")
    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action",required=True)
    init = actions.add_parser("init")
    init.add_argument("job",type=Path)
    init.add_argument("source")
    init.add_argument("draft")
    init.add_argument("--book",choices=["other","lori","dydi"],default="other")
    init.add_argument("--chapter",type=int)
    init.add_argument("--protect",action="append",default=[])
    init.add_argument("--note",action="append",default=[],help="本篇已有的版本校勘或评阅说明，可重复提供")
    for action in ("next","apply","export","history","run"):
        child = actions.add_parser(action)
        child.add_argument("job",type=Path)
        if action=="apply":
            child.add_argument("reply")
        if action in ("next","export","history"):
            child.add_argument("--out",type=Path)
        if action=="run":
            child.add_argument("--timeout",type=int,default=300)
            child.add_argument("--attempts",type=int,default=3)
            child.add_argument("--worker",required=True,nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action=="init":
            source, draft = read(args.source),read(args.draft)
            if args.chapter is not None:
                source,draft = chapter(source,args.chapter),chinese_chapter(draft,args.chapter)
            elif any(len(re.findall(r"(?m)^# Chapter \d+ · ",t))>1 for t in (source,draft)):
                raise ValueError("合订本请用 --chapter 选择一篇")
            initialize(args.job,source,draft,args.book,args.protect,args.note)
            return
        with closing(sqlite3.connect(args.job.resolve().as_uri()+"?mode=rw",uri=True)) as db:
            if args.action=="next":
                output = json.dumps(request(db),ensure_ascii=False,indent=2)
            elif args.action=="apply":
                output = apply_response(db,json.loads(read(args.reply)))
            elif args.action=="run":
                worker = args.worker[1:] if args.worker[:1]==["--"] else args.worker
                if not worker or args.timeout<=0 or args.attempts<=0:
                    raise ValueError("请提供可执行适配程序，超时和尝试次数均须为正数")
                output = run(db,worker,args.timeout,args.attempts)
            elif args.action=="export":
                job = state(db)
                if job["status"]!="已收敛":
                    raise ValueError("定稿尚待复核。history 可查看底稿与各轮结果。")
                output = job["draft"]
            else:
                job = state(db)
                output = json.dumps(dict(initial=job["initial"],draft=job["draft"],status=job["status"],
                    rounds=[dict(turn=n,reply=json.loads(r),result=t,status=s) for n,r,t,s in db.execute(
                        "SELECT turn,response,result,status FROM history ORDER BY turn")]), ensure_ascii=False,indent=2)
            if getattr(args,"out",None):
                with args.out.open("x",encoding="utf-8") as f:
                    f.write(output+"\n")
            else:
                print(output)
            if args.action in ("run","apply") and output.startswith("待复核"):
                sys.exit(2)
    except (ValueError,OSError,sqlite3.Error,subprocess.TimeoutExpired) as exc:
        parser.exit(1,str(exc)+"\n")


if __name__=="__main__":
    main()
