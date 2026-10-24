"""The table of the sets of facts and the choice of a set by version."""

import dataclasses
import typing
import unittest
from unittest import mock

from ezcheck.addon import facts


def _unset_fields(value: object, path: str) -> list[str]:
    """The fields of the set or group, its groups' too, that hold ``None`` or a value of another class than
    their annotation."""
    found = []
    hints = typing.get_type_hints(type(value))
    for field in dataclasses.fields(value):
        item = getattr(value, field.name)
        hint = hints[field.name]
        origin = typing.get_origin(hint) or hint
        if item is None or (isinstance(origin, type) and not isinstance(item, origin)):
            found.append(f"{path}.{field.name}")
        elif dataclasses.is_dataclass(item):
            found += _unset_fields(item, f"{path}.{field.name}")
    return found


class TableTest(unittest.TestCase):
    def test_every_set_has_every_field(self):
        for known in facts.VERSIONS:
            with self.subTest(since=known.since):
                self.assertEqual(_unset_fields(known, "facts"), [])

    def test_sets_from_oldest_to_newest(self):
        versions = [known.since for known in facts.VERSIONS]
        self.assertEqual(versions, sorted(set(versions)))
        self.assertLessEqual(versions[-1], facts.LAST_TESTED)

    def test_newer_set_changes_something(self):
        for older, newer in zip(facts.VERSIONS, facts.VERSIONS[1:], strict=False):
            with self.subTest(since=newer.since):
                self.assertNotEqual(dataclasses.replace(newer, since=older.since), older)

    def test_replace_keeps_the_other_fields(self):
        first = facts.VERSIONS[0]
        newer = dataclasses.replace(first, since=(99,), vcl=dataclasses.replace(first.vcl, text=0))
        for field in dataclasses.fields(first):
            if field.name not in ("since", "vcl"):
                self.assertEqual(getattr(newer, field.name), getattr(first, field.name), field.name)
        self.assertEqual(dataclasses.replace(newer.vcl, text=first.vcl.text), first.vcl)


class SelectTest(unittest.TestCase):
    def setUp(self):
        first = facts.VERSIONS[0]
        self.old = dataclasses.replace(first, since=(13, 0))
        self.new = dataclasses.replace(first, since=(13, 2, 1), vcl=dataclasses.replace(first.vcl, text=0))
        patches = (
            mock.patch.object(facts, "VERSIONS", (self.old, self.new)),
            mock.patch.object(facts, "LAST_TESTED", (13, 2, 5)),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def check(self, version: str | None, match: facts.Match, chosen: facts.Facts):
        selection = facts.select(version)
        self.assertEqual(selection.match, match)
        self.assertIs(selection.facts, chosen)

    def test_versions_with_sets(self):
        self.check("13.0", facts.Match.KNOWN, self.old)
        self.check("13.2.0.9", facts.Match.KNOWN, self.old)
        self.check("13.2.1", facts.Match.KNOWN, self.new)
        self.check("13.2.1.1", facts.Match.KNOWN, self.new)
        self.check("13.2.5", facts.Match.KNOWN, self.new)

    def test_newer_than_tested(self):
        self.check("13.2.5.1", facts.Match.NEWER, self.new)
        self.check("14", facts.Match.NEWER, self.new)

    def test_older_than_the_first_set(self):
        self.check("12.9.9", facts.Match.OLDER, self.old)

    def test_unreadable(self):
        self.check(None, facts.Match.UNKNOWN, self.new)
        self.check("", facts.Match.UNKNOWN, self.new)
        self.check("version", facts.Match.UNKNOWN, self.new)


if __name__ == "__main__":
    unittest.main()
