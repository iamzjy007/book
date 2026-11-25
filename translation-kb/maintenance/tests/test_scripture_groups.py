"""Regression checks on the published WEB / 和合本 concordance."""
import re
import sqlite3
import unittest

from scripture import DB, word_lookup
from kb.wordstudy import lookup as original_lookup


class GroupedConcordance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_armor_full_corpus_and_evidence_counts(self):
        rows = word_lookup(self.db, "armor")
        self.assertIn("共命中 42 节", rows[0])
        groups = [line for line in rows if line.startswith("「")]
        self.assertTrue(groups[0].startswith("「军装」"))
        self.assertIn("以弗所书 6:11、以弗所书 6:13", groups[0])
        self.assertIn("另见同词 5 节", groups[0])
        assigned = [re.search(r"已核 (\d+) 节.*另见同词 (\d+) 节", g).groups() for g in groups]
        pending = [int(re.search(r"(\d+) 节", s)[1]) for s in rows if s.startswith("待辨译法")]
        self.assertEqual(sum(int(n) for g in assigned for n in g) + sum(pending), 42)
        self.assertLessEqual(sum("\n  WEB" in row for row in rows), 6)

    def test_query_synonyms_scope_and_context(self):
        for query in ("armor", "ARMOUR", "armored up"):
            with self.subTest(query=query):
                rows = word_lookup(self.db, query, "nt", context=True)
                self.assertIn("共命中 5 节", rows[0])
                self.assertIn("已核 2 节（新约 2 节）", rows[2])
                self.assertEqual({s.split("」")[0][1:] for s in rows if s.startswith("「")},
                                 {"军装", "仁义的兵器", "光明的兵器", "盔甲兵器"})
                output = "\n".join(rows)
                for ref in ("罗马书 13:12", "路加福音 11:22", "哥林多后书 6:7", "以弗所书 6:13"):
                    self.assertIn(ref, output)
                self.assertIn("上下文　以弗所书 6:10", output)
                self.assertNotIn("撒母耳记上", output)
        phrase = "\n".join(word_lookup(self.db, "armor of light"))
        self.assertIn("共命中 1 节", phrase)
        self.assertIn("「光明的兵器」", phrase)
        self.assertNotIn("以弗所书", phrase)

    def test_existing_reverse_lookup_and_unrelated_words(self):
        for query, group in (("保守", "wisdom"), ("xyzzyword", "nt")):
            self.assertEqual(word_lookup(self.db, query, group, True),
                             original_lookup(self.db, query, group, True))
        self.assertFalse(any(s.startswith("「军装」") for s in word_lookup(self.db, "armed")))


if __name__ == "__main__":
    unittest.main()
