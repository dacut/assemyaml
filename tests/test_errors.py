from __future__ import absolute_import, print_function
from assemyaml import run
from contextlib import contextmanager
from six.moves import cStringIO as StringIO
import sys
from testfixtures import LogCapture
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
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!map value at", err)
        self.assertIn("into !!seq value at", err)

        resource = StringIO("[{!Assembly Hello: [A]}, {!Assembly Hello: X}]")
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!str value at", err)
        self.assertIn("into !!seq value at", err)

        template = StringIO("[{!Transclude Hello: {Foo: Bar}}]")
        resource = StringIO("[{!Assembly Hello: [A]}]")
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!seq value at", err)
        self.assertIn("into !!map value at", err)

    def test_dict_mismatch(self):
        resource = StringIO(
            "[{!Assembly Hello: {A: B}}, {!Assembly Hello: [Bar]}]"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!seq value at", err)
        self.assertIn("into !!map value at", err)

        resource = StringIO(
            "[{!Assembly Hello: {A: B}}, {!Assembly Hello: X}]"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!str value at", err)
        self.assertIn("into !!map value at", err)

        template = StringIO("[{!Transclude Hello: [Bar]}]")
        resource = StringIO("[{!Assembly Hello: {A: B}}]")
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!map value at", err)
        self.assertIn("into !!seq value at", err)

        template = StringIO("[{!Transclude Hello: X}]")
        resource = StringIO("[{!Assembly Hello: {A: B}}]")
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!map value at", err)
        self.assertIn("into !!str value at", err)

    def test_dict_duplicate(self):
        resource = StringIO(
            "[{!Assembly Hello: {A: B, C: D}}, {!Assembly Hello: {C: D}}]"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge duplicate mapping key 'C' at", err)
        self.assertIn("into existing mapping at", err)

        template = StringIO("[{!Transclude Hello: {C: D}}]")
        resource = StringIO("[{!Assembly Hello: {A: B, C: D}}]")
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge duplicate mapping key 'C' at", err)
        self.assertIn("into existing mapping at", err)

    def test_set_mismatch(self):
        resource = StringIO(
            "- !Assembly Hello: !!set\n"
            "    ? A\n"
            "- !Assembly Hello: [bar]"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!seq value at", err)
        self.assertIn("into !!set value at", err)

        resource = StringIO(
            "- !Assembly Hello: !!set\n"
            "    ? A\n"
            "- !Assembly Hello: X"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!str value at", err)
        self.assertIn("into !!set value at", err)

        template = StringIO("[{!Transclude Hello: [Bar]}]")
        resource = StringIO(
            "- !Assembly Hello: !!set\n"
            "    ? A\n"
        )
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!set value at", err)
        self.assertIn("into !!seq value at", err)

        template = StringIO("[{!Transclude Hello: X}]")
        resource = StringIO(
            "- !Assembly Hello: !!set\n"
            "    ? A\n"
        )
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!set value at", err)
        self.assertIn("into !!str value at", err)

    def test_scalar_replacement(self):
        resource = StringIO(
            "[{!Assembly Hello: X}, {!Assembly Hello: [A]}]"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!seq value at", err)
        self.assertIn("into !!str value at", err)

        resource = StringIO(
            "[{!Assembly Hello: X}, {!Assembly Hello: X}]"
        )
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!str value at", err)
        self.assertIn("into !!str value at", err)

        template = StringIO("[{!Transclude Hello: [A]}]")
        resource = StringIO("[{!Assembly Hello: X}]")
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!str value at", err)
        self.assertIn("into !!seq value at", err)

        template = StringIO("[{!Transclude Hello: X}]")
        resource = StringIO("[{!Assembly Hello: X}]")
        with LogCapture() as l:
            result = run(template, [resource], StringIO(), True)
        self.assertEquals(result, 1)
        err = str(l)
        self.assertIn("Cannot merge !!str value at", err)
        self.assertIn("into !!str value at", err)

    def test_multiple_assemblies(self):
        resource = StringIO("{!Assembly Hello: X, !Assembly World: Y}")
        with LogCapture() as l:
            result = run(StringIO(""), [resource], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Assembly must be a single-entry mapping", str(l))

    def test_multiple_transcludes(self):
        template = StringIO("{!Transclude Hello: X, !Transclude World: Y}")
        with LogCapture() as l:
            result = run(template, [], StringIO(), True)
        self.assertEquals(result, 1)
        self.assertIn(
            "Transclude must be a single-entry mapping", str(l))
