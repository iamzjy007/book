from contextlib import closing
import sqlite3
import unittest

from kb.parallel_text import best_parallel, scope_terms
from scripture import DB, parallel_notes


class ParallelTests(unittest.TestCase):
    def test_variation_outside_the_training_example(self):
        source = ("Those who wait for the LORD will renew their strength. "
                  "They will mount up with wings like eagles. They will run and be weary.")
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as db:
            hit = best_parallel(db, source)
            self.assertEqual(hit.ref, ("ISA",40,31))
            self.assertNotIn("not", scope_terms(source))
            self.assertIn("not", scope_terms(hit.english))
            self.assertIn("核对否定", " ".join(parallel_notes(db, source)))

    def test_ordinary_subjects(self):
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as db:
            for source in ("The craftsman polished the brass lamp until its surface reflected the light.",
                           "At our exhibition, the voice of a multitude and the appearance of lightning were recorded separately.",
                           "When the orchard failed, the keeper sold his spare tools to buy bread."):
                self.assertIsNone(best_parallel(db, source))

    def test_apocalyptic_portrait(self):
        source = ("the appearance of their countenance as the appearance of the lightning, "
                  "and their eyes as lamps of fire, and their arms and their feet like in color "
                  "to polished brass, and the roaring voice of their words like the voice of a multitude")
        with closing(sqlite3.connect(DB.as_uri()+"?mode=ro",uri=True)) as db:
            hit = best_parallel(db,source)
            self.assertEqual(hit.ref,("DAN",10,6))
            self.assertIn("roaring",hit.residual)
            self.assertIn("beryl",hit.reference_only)
