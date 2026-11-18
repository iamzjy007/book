import json
import os
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from grammar import diagnostics
from lookup import ROOT
from revision import apply_response, chinese_chapter, initialize, protected_text, request, run, state


def proposal(db, before, after):
    p = request(db)
    edit = dict(source_p=1, target_p=1, source=p["source"][0], before=before, after=after,
                category="句法", reading="一人向另一人说话", reason="检验段内定位", preserves="主体相同")
    return dict(request_id=p["request_id"], edits=[edit])


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def job(self, name="sample", source="I will answer you.", draft="我会回答你。", locks=()):
        path = Path(self.temp.name)/(name+".db")
        initialize(path,source,draft,"other",locks)
        db = sqlite3.connect(path)
        self.addCleanup(db.close)
        return db

    def test_trace_replays_from_book_sources(self):
        for case in json.loads((ROOT/"revision-cases.json").read_text(encoding="utf-8")):
            with self.subTest(case=case["id"]):
                base = ("Daily_Words_The_Lords_Glory_with_Lori" if case["book"]=="lori"
                        else "DYDI_Messages_Declaring_Your_Destiny")
                for suffix,field in (("","source"),("_zh","baseline")):
                    f = ROOT.parent/(base+suffix+".txt")
                    if f.is_file():
                        part = f.read_text(encoding="utf-8-sig").split("# Chapter "+case["id"][-3:]+" · ",1)[1]
                        self.assertIn(case[field],part.split("# Chapter ",1)[0])
                path = Path(self.temp.name)/(case["id"]+".db")
                initialize(path,case["source"],case["baseline"],case["book"],case["protected"])
                with closing(sqlite3.connect(path)) as db:
                    for edits in case["rounds"]:
                        apply_response(db,dict(request_id=request(db)["request_id"],edits=edits))
                    self.assertEqual(state(db)["draft"],case["final"])
                    self.assertEqual(state(db)["status"],"已收敛")

    def test_invalid_overlapping_stale_and_duplicate_edits(self):
        db = self.job()
        original = proposal(db,"回答","回应")
        for invalid in ({**original,"request_id":"过期"},
                        {**original,"edits":[{**original["edits"][0],"source":"other"}]},
                        {**original,"edits":original["edits"]*2}):
            with self.assertRaises(ValueError):
                apply_response(db,invalid)
        self.assertEqual(state(db)["round"],0)
        apply_response(db,original)
        apply_response(db,original)
        self.assertEqual(state(db)["round"],1)
        with self.assertRaises(ValueError):
            apply_response(db,{**original,"edits":[]})

    def test_edition_notes_persist_and_old_jobs_resume(self):
        path=Path(self.temp.name)/"edition.db"
        initialize(path,"A child of three weeks.","一个三周大的孩子。","other",notes=["本节指幼童的年龄。"])
        with closing(sqlite3.connect(path)) as db:
            first=request(db)
            self.assertEqual(first["editorial_notes"],["本节指幼童的年龄。"])
            apply_response(db,{"request_id":first["request_id"],"edits":[]})
            self.assertEqual(request(db)["editorial_notes"],first["editorial_notes"])
            db.execute("ALTER TABLE job DROP COLUMN notes")
            self.assertEqual(request(db)["editorial_notes"],[])

    def test_protects_user_wording_and_existing_scripture(self):
        db = self.job(source="John 11:35. I will answer you.", draft="耶稣哭了。\n\n我必回答你。",locks=["我必"])
        self.assertTrue(any("耶稣哭了" in t for t in json.loads(state(db)["locks"])))
        explicit = proposal(db,"我必","我们会")
        explicit["edits"][0]["target_p"]=2
        with self.assertRaises(ValueError):
            apply_response(db,explicit)
        db = self.job("quote","Psalm 23:2 NKJV","他使我躺卧在青草地上，领我在可安歇的水边。")
        self.assertTrue(json.loads(state(db)["locks"]))
        with self.assertRaises(ValueError):
            apply_response(db,proposal(db,"可安歇的水边","平静的水旁"))
        approved = "我必领你们到青草地上、可安歇的水边。"
        self.assertIn(approved,protected_text("I will lead you to greener pastures and still waters.",approved,(),"lori"))

    def test_bilingual_chapter_selection(self):
        text = "# Chapter 001 · A\n\n日期：昨天\n\n第一篇。\n\n==========\n# Chapter 002 · B\n\n第二篇。"
        self.assertEqual(chinese_chapter(text,1),"# Chapter 001 · A\n\n第一篇。")
        with self.assertRaises(ValueError):
            chinese_chapter(text,3)

    def test_layout_and_cycle_detection(self):
        db = self.job(draft="我会回答你。\n\n\n\n下一段。\n")
        apply_response(db,proposal(db,"回答","回应"))
        self.assertEqual(state(db)["draft"],"我会回应你。\n\n\n\n下一段。\n")
        self.assertIn("改稿循环",apply_response(db,proposal(db,"回应","回答")))
        self.assertIn("回应",state(db)["draft"])

    def test_limit_and_fail_closed_export_state(self):
        db = self.job()
        for i in range(6):
            before = state(db)["draft"]
            apply_response(db,proposal(db,before,before+str(i)))
        self.assertIn("上限",state(db)["status"])
        with self.assertRaises(ValueError):
            request(db)

    def test_cross_article_grammar(self):
        samples = [
            ("He will show you whom to seek out and listen to.", "shared-object",True),
            ("Listen to him and ask who he is.", "shared-object",False),
            ("I came to prepare you for the journey.", "purpose-chain",True),
            ("They will prepare the meal together.", "purpose-chain",False),
            ("Did I say I would give a date? I never said when.", "negated-speech",True),
            ("I never left you.", "negated-speech",False),
            ("I will, my child.", "ellipsis",True),
            ("I will give you rest.", "ellipsis",False),
        ]
        for text,rule,expected in samples:
            with self.subTest(text=text):
                self.assertEqual(any(h["rule"]==rule for h in diagnostics(text)),expected)

    def test_unattended_http_retry_and_resume(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                req = json.loads(body["messages"][1]["content"])
                received.append((body["model"],req["stage"],self.path,"retry_note" in req))
                reply = {"request_id":req["request_id"],"edits":[]}
                msg = json.dumps(reply) if len(received)>1 else "no json"
                result = json.dumps({"choices":[{"message":{"content":msg}}]}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(result)
        server = HTTPServer(("127.0.0.1",0),Handler)
        thread = Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
            with patch.dict(os.environ,TRANSLATION_CHAT_URL=url,TRANSLATION_MODEL="protocol-test",NO_PROXY="127.0.0.1"):
                db = self.job()
                worker = [sys.executable,str(ROOT/"model_worker.py")]
                self.assertEqual(run(db,worker,10),"已收敛")
                self.assertEqual(run(db,worker,10),"已收敛")
                self.assertEqual(len(received),4)
                self.assertTrue(received[1][-1])
                self.assertEqual(len({r[0] for r in received}),1)
                self.assertTrue(all(r[2]=="/v1/chat/completions" for r in received))
                with patch.dict(os.environ,TRANSLATION_MODEL="different-model"), self.assertRaises(ValueError):
                    run(db,worker,10)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__=="__main__":
    unittest.main()
