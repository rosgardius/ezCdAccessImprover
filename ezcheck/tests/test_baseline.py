"""Baselines of the audit: the nearest version and the comparison with what is found."""

import tempfile
import unittest
from pathlib import Path

from ezcheck import baseline


class BaselineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        for version in ("13.2.1.1", "13.10", "14.0"):
            baseline.write(version, {"unnamed": {f"TForm/{version}"}}, self.directory)

    def nearest(self, version: str | None) -> str | None:
        found = baseline.nearest(version, self.directory)
        return found.stem if found else None

    def test_nearest(self):
        self.assertEqual(self.nearest("13.2.1.1"), "13.2.1.1")
        self.assertEqual(self.nearest("13.9"), "13.2.1.1")
        self.assertEqual(self.nearest("13.10.1"), "13.10")
        self.assertEqual(self.nearest("15"), "14.0")
        self.assertEqual(self.nearest("12"), "13.2.1.1")

    def test_none(self):
        self.assertIsNone(baseline.nearest("13", self.directory / "empty"))

    def test_written_and_loaded(self):
        found = baseline.load(self.directory / "13.10.json")
        self.assertEqual(found, {"unnamed": ["TForm/13.10"], "windowless": [], "untabbed": []})

    def test_compare_within_the_root(self):
        known = [
            "TMainform[converter]/TPanel[0]",
            "TMainform[converter]/TPanel[1]",
            "TMainform[ripper]/TPanel[0]",
        ]
        found = {"TMainform[converter]/TPanel[1]", "TMainform[converter]/TPanel[2]"}
        new, gone = baseline.compare(known, found, "TMainform[converter]")
        self.assertEqual(new, ["TMainform[converter]/TPanel[2]"])
        self.assertEqual(gone, ["TMainform[converter]/TPanel[0]"])

    def test_root_is_no_prefix_of_another(self):
        new, gone = baseline.compare(["TDSPForm[converter]/TEdit[0]"], set(), "TDSPForm")
        self.assertEqual((new, gone), ([], []))


if __name__ == "__main__":
    unittest.main()
