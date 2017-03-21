from __future__ import absolute_import, print_function
from assemyaml.constructor import LocatableBool, LocatableNull
from unittest import TestCase


class TestLocatableBool(TestCase):
    def test_bool(self):
        self.assertTrue(LocatableBool(True))
        self.assertFalse(LocatableBool(False))

    def test_eq(self):
        self.assertEqual(LocatableBool(True), LocatableBool(True))
        self.assertEqual(LocatableBool(True), True)
        self.assertEqual(LocatableBool(False), LocatableBool(False))
        self.assertEqual(LocatableBool(False), False)

        self.assertEqual(LocatableBool(1), LocatableBool(True))
        self.assertEqual(LocatableBool(1), True)
        self.assertEqual(LocatableBool(0), LocatableBool(False))
        self.assertEqual(LocatableBool(0), False)

        self.assertEqual(LocatableBool(True), 1)
        self.assertEqual(LocatableBool(False), 0)


    def test_ne(self):
        self.assertNotEqual(LocatableBool(True), LocatableBool(False))
        self.assertNotEqual(LocatableBool(True), False)
        self.assertNotEqual(LocatableBool(False), LocatableBool(True))
        self.assertNotEqual(LocatableBool(False), True)

    def test_hash(self):
        d = {LocatableBool(True): 0, LocatableBool(False): 0}
        self.assertEqual(hash(LocatableBool(True)), hash(True))
        self.assertEqual(hash(LocatableBool(False)), hash(False))

    def test_comparisons(self):
        self.assertFalse(LocatableBool(False) < LocatableBool(False))
        self.assertTrue(LocatableBool(False) < LocatableBool(True))
        self.assertTrue(LocatableBool(False) <= LocatableBool(False))
        self.assertTrue(LocatableBool(False) <= LocatableBool(True))
        self.assertTrue(LocatableBool(False) >= LocatableBool(False))
        self.assertFalse(LocatableBool(False) >= LocatableBool(True))
        self.assertFalse(LocatableBool(False) > LocatableBool(False))
        self.assertFalse(LocatableBool(False) > LocatableBool(True))

        self.assertFalse(LocatableBool(False) < False)
        self.assertTrue(LocatableBool(False) < True)
        self.assertTrue(LocatableBool(False) <= False)
        self.assertTrue(LocatableBool(False) <= True)
        self.assertTrue(LocatableBool(False) >= False)
        self.assertFalse(LocatableBool(False) >= True)
        self.assertFalse(LocatableBool(False) > False)
        self.assertFalse(LocatableBool(False) > True)

    def test_repr(self):
        self.assertEqual(repr(LocatableBool(False)), "False")
        self.assertEqual(repr(LocatableBool(True)), "True")

class TestLocatableNull(TestCase):
    def test_bool(self):
        self.assertFalse(LocatableNull(0))

    def test_eq(self):
        self.assertEqual(LocatableNull(0), LocatableNull(0))
        self.assertEqual(LocatableNull(0), None)

    def test_ne(self):
        self.assertNotEqual(LocatableNull(0), False)
        self.assertNotEqual(LocatableNull(0), True)
        self.assertNotEqual(LocatableNull(0), "")

    def test_hash(self):
        d = {LocatableNull(0): 0}
        self.assertEqual(hash(LocatableNull(0)), hash(None))
