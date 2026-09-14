import unittest

from wordstat import stats


class StatsTest(unittest.TestCase):
    def test_counts_words_separated_by_single_spaces(self):
        self.assertEqual(stats("one two three"), {"words": 3})

    def test_empty_text_has_no_words(self):
        self.assertEqual(stats(""), {"words": 0})


if __name__ == "__main__":
    unittest.main()
