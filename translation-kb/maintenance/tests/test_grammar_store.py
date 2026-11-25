"""Regression checks for editing, compiling and reading grammar rules."""
from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from kb import grammar


class GrammarStoreTests(unittest.TestCase):
    def test_order_and_review_without_editorial_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "kb.sqlite3"
            source = root / "patterns.txt"
            source.write_text("later|语义|give|问动作|边界\n"
                              "early|语法|if|unless|问条件|边界\n", encoding="utf-8")
            with closing(sqlite3.connect(store)) as db:
                grammar.install_patterns(db, source)
            source.unlink()
            with patch.object(grammar, "DB", store):
                text = "Unless I give."
                self.assertEqual([h["rule"] for h in grammar.diagnostics(text)], ["later", "early"])
                self.assertEqual(grammar.short_notes(text, limit=1), ["- 「give」　问动作"])
                self.assertEqual([h["anchor"] for h in grammar.review_notes(text, 0)], ["give", "Unless"])

    def test_atomic_replacement_and_outer_transaction(self):
        with TemporaryDirectory() as directory, closing(sqlite3.connect(":memory:")) as db:
            path = Path(directory) / "patterns.txt"
            original = "old|层|old|问句|边界\n"
            path.write_text(original, encoding="utf-8")
            grammar.install_patterns(db, path)
            for invalid in (original + original, "new|层|[|问句|边界\n", "# empty\n"):
                path.write_text(invalid, encoding="utf-8")
                with self.assertRaises(ValueError):
                    grammar.install_patterns(db, path)
                self.assertEqual([p[0] for p in grammar.patterns(db)], ["old"])
            db.execute("""CREATE TRIGGER reject_bad_rule BEFORE INSERT ON syntax_patterns
                          WHEN new.name='bad' BEGIN SELECT raise(ABORT,'test'); END""")
            db.execute("BEGIN")
            path.write_text("new|层|one|问句|边界\nbad|层|two|问句|边界\n", encoding="utf-8")
            with self.assertRaises(sqlite3.IntegrityError):
                grammar.install_patterns(db, path)
            self.assertTrue(db.in_transaction)
            self.assertEqual([p[0] for p in grammar.patterns(db)], ["old"])
            path.write_text("new|层|one|问句|边界\n", encoding="utf-8")
            grammar.install_patterns(db, path)
            self.assertEqual([p[0] for p in grammar.patterns(db)], ["new"])
            db.rollback()
            self.assertEqual([p[0] for p in grammar.patterns(db)], ["old"])
