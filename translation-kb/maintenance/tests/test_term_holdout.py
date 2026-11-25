"""Context contrasts found in Lori 64/88 and DYDI 233."""
import unittest

from lookup import packet
from kb.terms import find_terms


class HoldoutTermsTests(unittest.TestCase):
    def test_light_of_the_world_depends_on_the_subject(self):
        for source, expected, ref in (
            ("You are the light of the world.", "世上的光", "MAT.5.14"),
            ("I am the light of the world.", "世界的光", "JOH.8.12"),
        ):
            with self.subTest(source=source):
                matches = [h for h in find_terms(source) if h.supported]
                self.assertEqual([(h.term.preferred, h.term.refs) for h in matches], [(expected, (ref,))])
        self.assertFalse(any(h.supported for h in find_terms("The light of the world.")))

    def test_anointing_an_object_or_receiving_an_anointing(self):
        verb = find_terms("I am anointing you will fresh oil from heavens storeroom.")
        # The source in Lori 88 prints “will” where “with” is expected.
        self.assertTrue(any(h.supported and h.term.id == "anoint" for h in verb))
        self.assertFalse(any(h.term.id == "anointing" for h in verb))
        noun = find_terms("The anointing you received from Him remains in you.")
        self.assertTrue(any(h.supported and h.term.id == "anointing" for h in noun))
        self.assertFalse(any(h.term.id == "anoint" for h in noun))

    def test_walking_and_worshiping_govern_different_expressions(self):
        walking = find_terms("You will walk in Spirit and in truth in unity.")
        self.assertFalse(any(h.term.id == "in-spirit-and-truth" for h in walking))
        worship = find_terms("We worship the Father in spirit and in truth.")
        self.assertTrue(any(h.supported and h.term.preferred == "用心灵和诚实" for h in worship))

    def test_trials_in_court_in_faith_and_in_medicine(self):
        judicial = find_terms("It’s coming! It’s coming! The trials of the century.")
        self.assertTrue(any(h.supported and h.term.id == "judicial-trial" for h in judicial))
        self.assertFalse(any(h.term.id == "trials" for h in judicial))
        faith = find_terms("Perseverance grows in these various trials of faith.")
        self.assertTrue(any(h.supported and h.term.id == "trials" for h in faith))
        self.assertFalse(any(h.term.id == "judicial-trial" for h in faith))
        self.assertFalse(any(h.term.id in {"trials", "judicial-trial"}
                             for h in find_terms("The clinical trials have begun.")))

    def test_lori_64_parallel_reaches_a_reader(self):
        guide = packet("You will be endowed with power from on high. Go glorify My SON.", "lori")
        self.assertIn("从上头来的能力", guide)
        self.assertIn("路加福音 24:49", guide)


if __name__ == "__main__":
    unittest.main()
