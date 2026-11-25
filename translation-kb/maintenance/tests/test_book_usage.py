import unittest
import sqlite3
import re
from types import SimpleNamespace
from unittest.mock import patch

from kb import book_usage as usage


ARMOR = SimpleNamespace(id="spiritual-armor", preferred="军装", variants=("全副军装",))


def hits(text):
    return [SimpleNamespace(term=ARMOR, start=match.start(), end=match.end(), supported=False)
            for match in re.finditer(r"\barmor\b", text, re.I)]


class BookUsageTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("CREATE TABLE idiom(id TEXT PRIMARY KEY)")
        self.db.execute("INSERT INTO idiom VALUES (?)", (ARMOR.id,))
        digest = patch.object(usage, "term_digest", return_value="test-version")
        self.digest = digest.start()
        self.addCleanup(digest.stop)

    def install(self, index):
        data = {"version": usage.VERSION, "term_sha256": self.digest.return_value,
                "books": {"lori": dict(index, files={}), "dydi": dict(
                    aligned_chapters=0, eligible_paragraphs=0, skipped={}, files={}, signatures={}, terms={})}}
        usage.store_usage(self.db, data)
        return data["books"]

    def test_only_traceable_paragraphs(self):
        en = {
            1: usage.Chapter("2026-01-01", "one", ["Wear armor. Armor up!", "“Wear armor.”", "Ephesians 6:11 NKJV"]),
            2: usage.Chapter("2026-01-02", "two", ["Armor and artillery."]),
            3: usage.Chapter("2026-01-03", "three", ["Armor up."]),
            4: usage.Chapter("2026-01-04", "four", ["Armor up."]),
            5: usage.Chapter("2026-01-05", "five", ["No armor.", "Armor up."]),
        }
        zh = {
            1: usage.Chapter("2026-01-01", "one", ["穿上全副军装，穿上军装！", "“穿上军装。”", "以弗所书6:11 NKJV"]),
            2: usage.Chapter("2026-01-02", "two", ["装甲与火炮。（译者注：军装用于属灵语境。）"]),
            3: usage.Chapter("2026-01-03", "different-url", ["军装"]),
            4: usage.Chapter("2026-01-04", "four", ["军装", "军装"]),
            5: usage.Chapter("2026-01-05", "five", ["没有盔甲。", "披上军装。"]),
        }
        index = usage.observations(en, zh, hits)
        self.assertEqual(index["terms"][ARMOR.id], {"军装": [[1, 1], [5, 2]]})
        self.assertEqual(index["skipped"], {"source_mismatch": [3], "paragraph_mismatch": [4]})
        expected = self.install(index)
        self.assertEqual(usage.load_index(self.db), expected)
        hint = usage.usage_hint(ARMOR.id, "lori", "# Chapter 001 · 2026-01-01 · Title\n\n...", db=self.db)
        self.assertEqual(hint, "「军装」1段（如005篇第2段）")
        self.assertEqual(usage.usage_hint(ARMOR.id, "lori", " ".join(en[1].paragraphs), db=self.db), hint)
        self.assertFalse(usage.usage_hint(ARMOR.id, "lori", "Armor.", db=self.db))
        self.assertFalse(usage.usage_hint(ARMOR.id, "dydi", "", 1, db=self.db))

    def test_usage_snapshot_rollback_and_term_version(self):
        base = usage.observations({1:usage.Chapter("a", "a", ["My armor."])},
                                  {1:usage.Chapter("a", "a", ["我的军装。"])}, hits)
        expected = self.install(base)
        # A half-written rebuild must not replace a usable snapshot.
        with self.assertRaises(sqlite3.IntegrityError):
            self.install(dict(base, terms={"unknown": {"误": [[1,1]]}}))
        self.assertEqual(usage.load_index(self.db), expected)
        self.digest.return_value = "changed"
        self.assertFalse(usage.available(self.db, "lori"))
        self.assertFalse(usage.usage_hint(ARMOR.id, "lori", "", 2, db=self.db))

    def test_known_reprints_omitted_for_both_heading_and_body(self):
        en = {i: usage.Chapter("a", str(i), [p]) for i, p in
              ((1, "My armor."), (2, "My armor."), (3, "Take your armor."))}
        zh = {i: usage.Chapter("a", str(i), ["军装。"]) for i in en}
        self.install(usage.observations(en, zh, hits))
        for source in ("# Chapter 001 · 2020-01-01 · Title\n\nMy armor.", "My armor.",
                       "# Chapter 004 · 2020-01-01 · New copy\n\nMy armor."):
            self.assertEqual(usage.usage_hint(ARMOR.id, "lori", source, db=self.db), "「军装」1段（如003篇第1段）")

    def test_single_character_and_ambiguous_variants(self):
        r = SimpleNamespace(preferred="义", variants=("公义", "公正"))
        self.assertIsNone(usage.observed_form("生命的意义", r))
        self.assertEqual(usage.observed_form("行公义。", r), "公义")
        self.assertIsNone(usage.observed_form("公正与公义", r))

    def test_ambiguous_span_cannot_establish_either_sense(self):
        second = SimpleNamespace(id="physical-armor", preferred="盔甲", variants=())
        def ambiguous(text):
            a, b = hits(text)
            return [a, b, SimpleNamespace(term=second, start=a.start, end=a.end, supported=False)]
        source = {1: usage.Chapter("2026-01-01", "one", ["Armor, and now your armor."])}
        target = {1: usage.Chapter("2026-01-01", "one", ["盔甲和军装。"])}
        found = usage.observations(source, target, ambiguous)["terms"]
        # Second, unambiguous occurrence still provides one same-paragraph observation.
        self.assertEqual(found, {ARMOR.id: {"军装": [[1, 1]]}})
        self.assertFalse(usage.observations(source, target, lambda p: ambiguous(p)[::2])["terms"])

    def test_lookup_unknown_phrase_without_substrings_or_independent_quotes(self):
        en = {1: usage.Chapter("2026-01-01", "one", [
            "A disarming speech.", "A strong arm.", "A strong  arm in battle.",
            "“A strong arm.”", "Galatians 4:7"])}
        zh = {1: usage.Chapter("2026-01-01", "one", [
            "一席和气的话。", "有力的臂膀。", "争战有力的膀臂。", "“大能的膀臂。”", "加拉太书4:7"])}
        result = list(usage.examples(en, zh, "Arm", 5))
        self.assertEqual([r[1] for r in result], [2, 3])
        self.assertEqual(list(usage.examples(en, zh, "strong arm", 1)), [result[0]])
        self.assertEqual(list(usage.examples(en, zh, "arm", 4, chapter=2)), [])

    def test_editorial_tail_excluded_from_lookup_and_counts(self):
        en = {1: usage.Chapter("2026-01-01", "one", ["Wear armor.", "Armor up."])}
        for label in ("译者注：同处又见“军装”。", "译者待核实问题", "原文修正说明\narmor 疑有误。"):
            with self.subTest(label=label):
                zh = {1: usage.Chapter("2026-01-01", "one",
                                       ["穿上军装。", "要作好准备。", label, "注内出现军装。"])}
                self.assertEqual(usage.observations(en, zh, hits)["terms"], {ARMOR.id: {"军装": [[1, 1]]}})
                self.assertEqual([r[3] for r in usage.examples(en, zh, "armor")],
                                 ["穿上军装。", "要作好准备。"])

    def test_duplicate_chapter_rejected(self):
        sample = "# Chapter 001 · 2026-01-01 · Title\n\nURL: https://example.com/book\n\nWord."
        with self.assertRaises(ValueError):
            usage.read_chapters(sample + "\n==========\n" + sample)


if __name__ == "__main__":
    unittest.main()
