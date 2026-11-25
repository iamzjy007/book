"""Exercise portable recoverability, batch updates and selective idiom lookups."""
from dataclasses import replace
import hashlib
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from kb.term_store import (Term, all_terms, candidate_terms, check_store, export_terms,
                        import_terms, read_batch, term_digest, terms_containing)


ARMOR = Term("armor", ("armor", "ArmOr", "armored up"), "军装", ("全副军装",),
             ("EPH.6.11",), ("praise",), ("steel",), "属灵装备。")
LIGHT = Term("light-armor", ("the armor of light",), "光明的兵器", (),
             ("ROM.13.12",), (), (), "光明的兵器。")


class TermStoreTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE verses(edition,code,ch,first,last,text)")
        self.db.executemany("INSERT INTO verses VALUES (?,?,?,?,?,?)", [
            ("engwebp","EPH",6,11,11,"Put on the whole armor of God."),
            ("cmn-cu89s","EPH",6,11,11,"要穿戴神所赐的全副军装。"),
            ("engwebp","ROM",13,12,12,"Let's put on the armor of light."),
            ("cmn-cu89s","ROM",13,12,12,"带上光明的兵器。")])
        self.db.commit()
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)

    def write(self, name, *entries):
        path = self.folder/name
        with path.open("w", encoding="utf-8", newline="") as stream:
            export_terms(entries, stream)
        return path

    def test_indexed_lookup_roundtrip_and_digest(self):
        path = self.write("all.tsv", ARMOR, LIGHT)
        self.assertEqual(import_terms(self.db,[path]), 2)
        self.assertEqual(term_digest(self.db), hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(all_terms(self.db), (ARMOR,LIGHT))
        self.assertEqual(candidate_terms(self.db, ["armor"]), (ARMOR,))
        self.assertEqual(terms_containing(self.db, ["armor"]), (ARMOR,LIGHT))
        self.assertEqual(terms_containing(self.db, ["unknown"]), ())
        self.assertEqual(candidate_terms(self.db, []), ())
        self.assertEqual(list(read_batch(self.write("roundtrip.tsv", *all_terms(self.db)))), [ARMOR, LIGHT])
        self.db.row_factory = sqlite3.Row
        self.assertEqual(check_store(self.db), 2)

    def test_latest_update_replaces_only_one_terms_forms(self):
        path = self.write("all.tsv", ARMOR, LIGHT)
        import_terms(self.db,[path])
        before = term_digest(self.db)
        revised = replace(ARMOR, triggers=("armor", "suit of armor"), cues=("spirit",))
        patch = self.write("update.tsv", revised)
        with self.assertRaisesRegex(ValueError, "--update"):
            import_terms(self.db,[patch])
        self.assertEqual(term_digest(self.db), before)
        import_terms(self.db,[patch],update=True)
        self.assertEqual(all_terms(self.db), (revised,LIGHT))
        self.assertEqual(candidate_terms(self.db,["suit"]), (revised,))
        self.assertFalse(candidate_terms(self.db,["armored"]))
        self.assertNotEqual(term_digest(self.db), before)
        self.assertEqual(check_store(self.db), 2)

    def test_failed_evidence_and_duplicate_ids_roll_back_the_whole_directory(self):
        self.write("01.tsv", ARMOR)
        for invalid in (
            replace(LIGHT, refs=("ROM.13.99",)),
            replace(LIGHT, preferred="不见于该节"),
            replace(LIGHT, triggers=("no such English words",)),
            replace(LIGHT, id=ARMOR.id),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.write("02.tsv", invalid)
                import_terms(self.db,[self.folder])
            self.assertFalse(self.db.execute("SELECT name FROM sqlite_master WHERE name='idiom'").fetchone())
        self.write("02.tsv",LIGHT)
        self.assertEqual(import_terms(self.db,[self.folder]), 2)
        revised = replace(ARMOR, note="新的说明。")
        with self.assertRaises(ValueError):
            import_terms(self.db,[self.write("update.tsv",revised,replace(LIGHT,refs=("ROM.19.5",)))],update=True)
        self.assertEqual(all_terms(self.db),(ARMOR,LIGHT))

    def test_missing_tokens_detected(self):
        import_terms(self.db,[self.write("seed.tsv", ARMOR)])
        self.db.execute("DELETE FROM idiom_trigger_token WHERE token='up'")
        with self.assertRaisesRegex(ValueError,"索引"):
            check_store(self.db)


if __name__ == "__main__":
    unittest.main()
