from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from kb.echo_guard import canonical_names, check_edit


class EchoTests(unittest.TestCase):
    source = "their arms and their feet like in color to polished brass"
    draft = "他们的面貌如闪电，眼睛如火灯，手臂和脚的颜色如光明的铜，说话的轰鸣如大众的声音。"

    def test_vision(self):
        with self.assertRaisesRegex(ValueError, "DAN 10:6"):
            check_edit(self.source, self.draft, "颜色如光明的铜", "颜色如磨亮的铜", "原文说到光泽")

    def test_small_edit(self):
        with self.assertRaisesRegex(ValueError, "DAN 10:6"):
            check_edit(self.source, self.draft, "光明", "磨亮", "")

    def test_workshop(self):
        check_edit("He polished the brass.", "工匠拿出光明的铜。", "拿出光明的铜", "把铜磨亮了", "底本有动作")

    def test_unrelated_change(self):
        check_edit(self.source, self.draft, "眼睛", "眼目", "核实措辞")

    def test_name(self):
        with self.assertRaisesRegex(ValueError, "西奈.*EXO 16:1"):
            check_edit("on Sinai", "在西奈山上", "奈", "乃", "照前文")
        check_edit("on Mount Sinai", "在西乃山", "乃", "奈", "依专名表")

    def test_names_follow_current_database(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bible-style.sqlite3"
            with closing(sqlite3.connect(path)) as db, patch("kb.echo_guard.DB", path):
                db.execute("CREATE TABLE terms(en, zh, kind, code, ch, v)")
                db.executemany("INSERT INTO terms VALUES (?,?,?,?,?,?)", [
                    ("Sinai", "西奈", "地名", "EXO", 16, 1),
                    ("green pastures", "青草地上", "搭配", "PSA", 23, 2),
                    ("Adam", "亚当", "人名", "GEN", 3, 17),
                ])
                db.commit()
                self.assertEqual([zh for _, zh, _ in canonical_names()], ["西奈", "亚当"])
                db.execute("DELETE FROM terms WHERE en='Adam'")
                db.commit()
                self.assertEqual([zh for _, zh, _ in canonical_names()], ["西奈"])

    def test_peoples(self):
        source = "the destinies of every nation and tongue"
        for old, new in [("各国各族", "各国、各方言之民"), ("各国各方之民", "各国各族")]:
            with self.assertRaisesRegex(ValueError, "各国各方之民"):
                check_edit(source, old+"的命运", old, new, "保留并列")
        check_edit(source, "各国各族的命运", "各国各族", "各国各方之民", "用户评定")

    def test_expanded_list(self):
        args = ("priests and singers", "众人前来", "众人", "祭司、歌唱的人")
        with self.assertRaisesRegex(ValueError, "请通读"):
            check_edit(*args, "更准确")
        check_edit(*args, "并列复核【补回两类人的身份，共用谓语前来】")
        check_edit("inventions and innovations", "发明和创新正在来到", "发明和创新正在来到",
                   "新发明、新创意将要问世", "调整汉语谓语")
