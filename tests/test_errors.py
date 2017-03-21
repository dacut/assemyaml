from __future__ import absolute_import, print_function
from assemyaml import run
from contextlib import contextmanager
from six.moves import cStringIO as StringIO
import sys
from unittest import TestCase


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestErrors(TestCase):
    """
    Test cases for error reporting.
    """

    def setUp(self):
        self.oldstderr, sys.stderr = sys.stderr, StringIO()

    def tearDown(self):
        sys.stderr = self.oldstderr

    def test_list_mismatch(self):
        resource = StringIO(
            "[{!Assembly Hello: [A]}, {!Assembly Hello: {Foo: Bar}}]"
        )
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: list at",
                      err.getvalue())

        resource = StringIO("[{!Assembly Hello: [A]}, {!Assembly Hello: X}]")
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: list at",
                      err.getvalue())

        template = StringIO("[{!Transclude Hello: {Foo: Bar}}]")
        resource = StringIO("[{!Assembly Hello: [A]}]")
        with captured_output() as (out, err):
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: list at",
                      err.getvalue())

    def test_dict_mismatch(self):
        resource = StringIO(
            "[{!Assembly Hello: {A: B}}, {!Assembly Hello: [Bar]}]"
        )
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: dict at",
                      err.getvalue())

        resource = StringIO(
            "[{!Assembly Hello: {A: B}}, {!Assembly Hello: X}]"
        )
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: dict at",
                      err.getvalue())

        template = StringIO("[{!Transclude Hello: [Bar]}]")
        resource = StringIO("[{!Assembly Hello: {A: B}}]")
        with captured_output() as (out, err):
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: dict at",
                      err.getvalue())

        template = StringIO("[{!Transclude Hello: X}]")
        resource = StringIO("[{!Assembly Hello: {A: B}}]")
        with captured_output() as (out, err):
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("Mismatched assembly types for Hello: dict at",
                      err.getvalue())


    def test_dict_duplicate(self):
        resource = StringIO(
            "[{!Assembly Hello: {A: B, C: D}}, {!Assembly Hello: {C: D}}]"
        )
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Duplicate key 'C' for assembly Hello: first occurrence at",
            err.getvalue())

        template = StringIO("[{!Transclude Hello: {C: D}}]")
        resource = StringIO("[{!Assembly Hello: {A: B, C: D}}]")
        with captured_output() as (out, err):
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Duplicate key 'C' for assembly Hello: first occurrence at",
            err.getvalue())

    def test_scalar_replacement(self):
        resource = StringIO(
            "[{!Assembly Hello: X}, {!Assembly Hello: [A]}]"
        )
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Cannot set value for assembly Hello: str at", err.getvalue())

        resource = StringIO(
            "[{!Assembly Hello: X}, {!Assembly Hello: X}]"
        )
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Cannot set value for assembly Hello: str at", err.getvalue())

        template = StringIO("[{!Transclude Hello: [A]}]")
        resource = StringIO("[{!Assembly Hello: X}]")
        with captured_output() as (out, err):
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Cannot set value for assembly Hello: str at", err.getvalue())

        template = StringIO("[{!Transclude Hello: X}]")
        resource = StringIO("[{!Assembly Hello: X}]")
        with captured_output() as (out, err):
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Cannot set value for assembly Hello: str at", err.getvalue())

    def test_multiple_assemblies(self):
        resource = StringIO("{!Assembly Hello: X, !Assembly World: Y}")
        with captured_output() as (out, err):
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Assembly must be a single-entry mapping", err.getvalue())

    def test_multiple_transcludes(self):
        template = StringIO("{!Transclude Hello: X, !Transclude World: Y}")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Transclude must be a single-entry mapping", err.getvalue())

    def test_omap_message(self):
        template = StringIO("--- !!omap\nHello")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing an ordered map", err.getvalue())
        self.assertIn("expected a sequence, but found scalar", err.getvalue())

        template = StringIO("--- !!omap\n  - 1")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing an ordered map", err.getvalue())
        self.assertIn(
            "expected a mapping of length 1, but found scalar", err.getvalue())

        template = StringIO("--- !!omap\n  - [1, 2, 3]")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing an ordered map", err.getvalue())
        self.assertIn(
            "expected a mapping of length 1, but found sequence", err.getvalue())

        template = StringIO("--- !!omap\n  - foo: bar\n    baz: 0")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing an ordered map", err.getvalue())
        self.assertIn(
            "expected a single mapping item, but found 2 items", err.getvalue())

    def test_pairs_message(self):
        template = StringIO("--- !!pairs\nHello")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing pairs", err.getvalue())
        self.assertIn("expected a sequence, but found scalar", err.getvalue())

        template = StringIO("--- !!pairs\n  - 1")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing pairs", err.getvalue())
        self.assertIn(
            "expected a mapping of length 1, but found scalar", err.getvalue())

        template = StringIO("--- !!pairs\n  - [1, 2, 3]")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing pairs", err.getvalue())
        self.assertIn(
            "expected a mapping of length 1, but found sequence", err.getvalue())

        template = StringIO("--- !!pairs\n  - foo: bar\n    baz: 0")
        with captured_output() as (out, err):
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn("while constructing pairs", err.getvalue())
        self.assertIn(
            "expected a single mapping item, but found 2 items", err.getvalue())
