"""Offline regression checks against the distributed SQLite file."""
import sqlite3
import unittest

from lookup import chapter, packet
from scripture import suggestions
from kb.wordstudy import ROOT, lookup, packet_notes


class ScriptureUsage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect((ROOT / "bible-style.sqlite3").as_uri()+"?mode=ro", uri=True)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_context_selects_sense(self):
        cases = [
            ("Greener pastures and still waters await my flock.", "诗篇 23:2", "可安歇的水边"),
            ("The waters are quiet where I lead my flock.", "诗篇 23:2", "可安歇的水边"),
            ("Cast your burden on Me.", "诗篇 55:22", "重担"),
            ("Bear one another’s burdens.", "加拉太书 6:2", "互相担当"),
            ("Each has his own burden.", "加拉太书 6:5", "自己的担子"),
            ("The Lord's peace will guard your heart.", "腓立比书 4:7", "保守"),
            ("Bless His holy name.", "诗篇 103:1", "称颂"),
            ("Bless those who curse you.", "路加福音 6:28", "祝福"),
            ("My sheep know my voice.", "约翰福音 10:27", "认得"),
            ("Let the peace of God rule in your hearts.", "歌罗西书 3:15", "称 God"),
        ]
        for source,ref,wording in cases:
            with self.subTest(source=source):
                notes = "\n".join(packet_notes(self.db,source))
                self.assertIn(ref,notes)
                self.assertIn(wording,notes)

    def test_distinct_actors_and_clauses(self):
        notes = "\n".join(packet_notes(self.db, "Let the peace of God guard your heart."))
        self.assertNotIn("箴言 4:23",notes)
        notes = "\n".join(packet_notes(self.db, "Guard your heart against fear, and let my peace give you rest."))
        self.assertIn("箴言 4:23",notes)
        self.assertNotIn("腓立比书 4:7",notes)

    def test_material_portion_and_bodily_strength(self):
        from kb.wordstudy import match_senses, senses
        entries=senses(self.db)
        for source,ref in (
            ("From the tribute give a portion for the sacrifices of the Lord.","诗篇 73:26"),
            ("By food strength is produced; in food is the foundation of strength.","诗篇 46:1"),
        ):
            self.assertNotIn(ref,{s.ref for s,_ in match_senses(entries,source)})
        for source,ref in (("God is my portion forever.","诗篇 73:26"),("God is our refuge and strength.","诗篇 46:1")):
            self.assertIn(ref,{s.ref for s,_ in match_senses(entries,source)})

    def test_ordinary_language(self):
        for source in (
            "I am looking for a new job and greener pastures.",
            "I photographed the quiet waters from the boat.",
            "The news anchor has a new contract.",
            "The grace period for my lease has been renewed.",
            "The surgeon examined my heart valve.",
            "They renew their strength at the gym after every workout.",
            "I took mustard seed and cumin to the kitchen.",
            "The recital featured the ballad Love Endures Forever.",
            "The team crossed to the other side of the river.",
        ):
            with self.subTest(source=source):
                self.assertEqual(suggestions(self.db,source),[])

    def test_unlisted_term_has_bilingual_evidence(self):
        source = "Wash me with hyssop and make me clean."
        notes = "\n".join(packet_notes(self.db,source))
        self.assertIn("全经查词线索",notes)
        self.assertIn("诗篇 51:7",notes)
        self.assertIn("牛膝草",notes)
        self.assertIn("WEB",notes)
        self.assertNotIn("可参「",notes)

    def test_explicit_citation_keeps_its_own_path(self):
        source = "Now we return to the letter.\n\nRenew your mind.\n\nRomans 12:2 AMPC"
        self.assertEqual(packet_notes(self.db,source),[])
        self.assertIn("罗马书 12:2", "\n".join(suggestions(self.db,source)))

    def test_manual_lookup_and_context(self):
        psalms = "\n".join(lookup(self.db,"mercy","psalms",True))
        self.assertIn("恩惠慈爱",psalms)
        self.assertIn("怜悯",psalms)
        self.assertIn("〔5〕",psalms)
        self.assertNotIn("马太福音",psalms)
        self.assertIn("保守", "\n".join(lookup(self.db,"保守","paul",True)))
        self.assertIn("智慧", "\n".join(lookup(self.db,"wisdom","wisdom")))
        self.assertFalse(lookup(self.db,"xyzzyword","nt"))

    def test_reviewed_chapter_through_normal_entry(self):
        book = ROOT.parent / "Daily_Words_The_Lords_Glory_with_Lori.txt"
        if not book.is_file():
            self.skipTest("本项使用作品目录内的真实章节")
        source = chapter(book.read_text(encoding="utf-8-sig"),129)
        result = packet(source,"lori")
        self.assertIn("我必领你们到青草地上、可安歇的水边",result)
        self.assertIn("用户复评",result)
        self.assertIn("原文「greener pastures」",result)
        self.assertIn("原文「still waters」",result)
        self.assertEqual(result.partition("## 待译原文\n\n")[2].strip(),source.strip())

    def test_all_curated_excerpts_have_two_sources(self):
        missing = self.db.execute("""
            SELECT s.en FROM word_senses s WHERE NOT EXISTS (
              SELECT 1 FROM verses e JOIN verses z USING(code,ch)
              WHERE e.edition='engwebp' AND z.edition='cmn-cu89s'
              AND e.code=s.code AND e.ch=s.ch AND s.v BETWEEN e.first AND e.last
              AND s.v BETWEEN z.first AND z.last AND instr(lower(e.text),lower(s.en))>0
              AND instr(z.text,s.zh)>0)""").fetchall()
        self.assertFalse(missing)


if __name__ == "__main__":
    unittest.main()
