"""Regression tests for the translation packet and the draft that follows it."""
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from check_terms import audit, read_packet, select_draft, target_matches
from lookup import ROOT, chapter, packet
from kb.terms import find_terms, load_terms, split_ref, tokens
from kb.wordstudy import NEW, contains


class TermTests(unittest.TestCase):
    def test_every_reference_has_bilingual_text_and_chinese_evidence(self):
        db = sqlite3.connect((ROOT/"bible-style.sqlite3").as_uri()+"?mode=ro", uri=True)
        self.addCleanup(db.close)
        books = set()
        def compact(t):
            return re.sub(r"[\s\[\]]", "", t)
        for term in load_terms():
            english_examples = []
            for ref in term.refs:
                code, ch, v = split_ref(ref)
                books.add(code)
                with self.subTest(term=term.id, ref=ref):
                    verses = dict(db.execute(
                        "SELECT edition,text FROM verses WHERE code=? AND ch=? AND ? BETWEEN first AND last",
                        (code,ch,v)))
                    self.assertTrue(verses.get("engwebp"))
                    english_examples.append(tokens(verses["engwebp"]))
                    chinese = compact(verses["cmn-cu89s"])
                    self.assertTrue(any(compact(s) in chinese for s in (term.preferred, *term.variants)))
            with self.subTest(term=term.id):
                self.assertTrue(any(contains(verse, tokens(trigger)) for verse in english_examples for trigger in term.triggers))
        self.assertEqual(NEW & books, NEW)

    def test_two_spiritual_forms_and_material_contrasts(self):
        for english in ("Wear My armor.", "Be armoured up in praise and worship."):
            self.assertTrue(any(h.term.preferred=="军装" and h.supported for h in find_terms(english)))
        for english in ("The museum bought a suit of armor.", "They sent armor and artillery.",
                        "A column of armored vehicles arrived.", "The knight wore my armor."):
            self.assertFalse(any(h.term.preferred=="军装" and h.supported for h in find_terms(english)))
        hits = find_terms("Put on the armour of light.")
        self.assertEqual([h.term.preferred for h in hits], ["光明的兵器"])
        self.assertEqual([h.term.preferred for h in find_terms("Put on the whole armor of God.")], ["全副军装"])
        self.assertFalse(find_terms("Cables supply electrical power from above."))

    def test_weak_clue_and_locality(self):
        hits = find_terms("A hiding place is waiting. The Lord has spoken.")
        self.assertTrue(any(h.term.id=="hiding-place" and not h.supported for h in hits))
        self.assertFalse(audit("A hiding place is waiting.", "有一处藏身的地方。")["findings"])
        report = audit("Be armored up in worship.\n\nWear My armor.", "要以敬拜为盔甲。\n\n穿上我的军装。")
        self.assertTrue(report["aligned"])
        self.assertEqual([f["target_p"] for f in report["findings"] if f["term"]=="armor"], [1])
        self.assertIn(report["findings"][0]["source"], "Be armored up in worship.")
        report = audit("Wear My armor. Wear My armor.", "穿上我的军装，再披上盔甲。")
        self.assertEqual([(f["occurrences"], f["chinese_matches"]) for f in report["findings"]], [(2,1)])
        report = audit("Wear My armor.\n\nKeep watch.", "穿上我的军装，警醒。")
        self.assertFalse(report["aligned"])
        self.assertIsNone(report["findings"][0]["target_p"])
        righteousness = next(t for t in load_terms() if t.id=="righteousness")
        self.assertEqual(target_matches(righteousness, "这件事很有意义。"), (0,True))

    def test_real_chapter_and_one_click_check(self):
        src = ROOT.parent/"Daily_Words_The_Lords_Glory_with_Lori.txt"
        if not src.exists():
            self.skipTest("本项需 Lori 合订本")
        source = chapter(src.read_text(encoding="utf-8-sig"), 133)
        guide = packet(source, "lori")
        vocabulary = guide.split("## 和合本惯用词与短语", 1)[1].split("## ", 1)[0]
        for phrase in ("军装","藏身之处","从上头来的能力","被掳的得释放","事交托"):
            self.assertIn(phrase, vocabulary)
        self.assertRegex(vocabulary, r"同书现译同段见「军装」[1-9]\d*段")
        # One good use must not mask the other occurrence in a different paragraph.
        source = "You are armored up in praise and worship.\n\nYou wear My armor."
        self.assertEqual(len(audit(source, "以赞美和敬拜作盔甲。\n\n你们穿戴我的盔甲。")["findings"]), 2)
        self.assertEqual(audit(source, "以赞美和敬拜作军装。\n\n你们穿戴我的军装。")["findings"], [])
        with TemporaryDirectory() as directory:
            path = Path(directory)/"单篇.md"
            path.write_text(guide, encoding="utf-8")
            self.assertEqual(read_packet(path), ("lori", chapter(src.read_text(encoding="utf-8-sig"), 133).strip()))
            path.write_text(guide + "different source", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_packet(path)
        with self.assertRaises(ValueError):
            select_draft("# Chapter 133 · Here", "# Chapter 132 · 另篇\n\n正文")


if __name__ == "__main__":
    unittest.main()
