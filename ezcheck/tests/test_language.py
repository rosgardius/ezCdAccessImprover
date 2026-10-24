"""Reading ezcd's language files and the add-on's own strings, and their keys."""

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ezcheck.addon import facts

_PACKAGE = Path(facts.language.OWN_STRINGS).parent
_OWN_STRING = re.compile(r"""OwnString\(\s*["']([^"']+)["']\s*\)""")


class LanguageFilesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "Language").mkdir()
        self.exe = str(self.root / "ezcd.exe")

    def write(self, name: str, text: str, encoding: str = "utf-16"):
        (self.root / "Language" / name).write_text(text, encoding=encoding)

    def test_strings(self):
        self.write(
            "english.uni",
            "[0]\nEnglish (customizable)\n[172]\nAudio Converter  \n[580]\n\n[801]\n<Total Tracks>\n",
        )
        strings = facts.language.strings(str(self.root / "Language" / "english.uni"))
        self.assertEqual(
            strings, {0: "English (customizable)", 172: "Audio Converter", 801: "<Total Tracks>"}
        )

    def test_files(self):
        self.write("english.uni", "[0]\nEnglish\n")
        self.write("Russian.UNI", "[0]\nRussian\n")
        self.write("readme.txt", "not a language", "utf-8")
        files = facts.language.files(self.exe)
        self.assertEqual(sorted(files), ["Russian", "english"])

    def test_no_language_folder(self):
        with self.assertRaises(OSError):
            facts.language.files(str(self.root / "elsewhere" / "ezcd.exe"))

    def test_own_strings(self):
        (self.root / "russian.txt").write_text(
            "﻿# Translators: a note\npath = Путь\n\nbroken line\nempty =\n  browse=Обзор  \n", encoding="utf-8"
        )
        with mock.patch.object(facts.language, "OWN_STRINGS", str(self.root)):
            self.assertEqual(facts.language.own_strings("russian"), {"path": "Путь", "browse": "Обзор"})
            with self.assertRaises(OSError):
                facts.language.own_strings("klingon")


class OwnStringKeysTest(unittest.TestCase):
    def setUp(self):
        self.english = set(facts.language.own_strings(facts.language.OWN_BASE))

    def test_every_key_of_the_code_is_in_english(self):
        used = {
            key for path in _PACKAGE.rglob("*.py") for key in _OWN_STRING.findall(path.read_text("utf-8"))
        }
        self.assertTrue(used)
        self.assertEqual(used - self.english, set())

    def test_every_key_of_a_translation_is_in_english(self):
        for path in Path(facts.language.OWN_STRINGS).glob("*.txt"):
            with self.subTest(translation=path.stem):
                self.assertEqual(set(facts.language.own_strings(path.stem)) - self.english, set())


if __name__ == "__main__":
    unittest.main()
