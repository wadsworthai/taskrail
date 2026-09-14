import contextlib
import io
import os
import tempfile
import unittest

from wordstat.__main__ import main


class CliTest(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_prints_one_line_per_statistic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "sample.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("one two three")
            self.assertEqual(self.run_main([path]), (0, "words: 3\n", ""))

    def test_unreadable_file_exits_1(self):
        code, out, err = self.run_main([os.path.join(tempfile.gettempdir(), "wordstat-missing-file")])
        self.assertEqual((code, out), (1, ""))
        self.assertIn("cannot read", err)


if __name__ == "__main__":
    unittest.main()
