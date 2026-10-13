import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp()

from typerace import app  # noqa: E402


class Averages(unittest.TestCase):
    def test_ao5_drops_best_and_worst(self):
        self.assertEqual(app.ao([50, 60, 70, 80, 200], 5), 70)

    def test_trim_counts_match_cstimer(self):
        # ao5/ao12 drop 1 each side, ao25 2, ao50 3, ao100 5
        for n, k in ((5, 1), (12, 1), (25, 2), (50, 3), (100, 5)):
            values = list(range(n))
            self.assertEqual(app.ao(values, n), sum(values[k:n - k]) / (n - 2 * k))

    def test_not_enough_results(self):
        self.assertIsNone(app.ao(list(range(11)), 12))

    def test_best_ao(self):
        self.assertEqual(app.best_ao([60, 70, 80, 90, 100, 110, 50], 5), 90)


class Speed(unittest.TestCase):
    def test_wpm(self):
        self.assertAlmostEqual(app.wpm(300, 36), 100)

    def test_peak_ignores_near_ties(self):
        # steady 60 wpm with two words finished 0.01 s apart
        log, t, c = [(0.0, 0)], 0.0, 0
        for _ in range(30):
            t += 1.2
            c += 6
            log.append((t, c))
        log.insert(15, (log[14][0] + 0.01, log[14][1] + 5))
        log = [(a, b + (5 if i > 15 else 0)) for i, (a, b) in enumerate(log)]
        peak, span = app.best_stretch(log, log[-1][0])
        self.assertLess(peak, 80)
        self.assertGreaterEqual(span, 3)


class Quotes(unittest.TestCase):
    def test_bundled_quotes_load_and_are_typable(self):
        quotes = app.all_quotes()
        self.assertGreater(len(quotes), 5000)
        for qid, text, source in quotes:
            self.assertTrue(text.isascii() and text.isprintable(), qid)
            self.assertEqual(text, " ".join(text.split()), qid)

    def test_typable_converts_punctuation(self):
        self.assertEqual(app.typable("It’s “fine”… really"), 'It\'s "fine"... really')

    def test_picker_no_repeats_until_exhausted(self):
        quotes = [(f"q{i}", f"quote number {i}", "x") for i in range(3)]
        p = app.Picker(quotes, "short")
        first = [p.next()[0] for _ in range(3)]
        self.assertEqual(len(set(first)), 3)
        p.next()                          # all done: starts over without error

    def test_length_mix(self):
        p = app.Picker(app.all_quotes())
        self.assertEqual(set(p.groups), set(app.LENGTHS))


if __name__ == "__main__":
    unittest.main()
