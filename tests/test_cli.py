from __future__ import absolute_import, print_function
from assemyaml import main
from assemyaml.types import UnknownLocalTag
from contextlib import contextmanager
from json import load as json_load, loads as json_loads
from logging import getLogger
from os.path import dirname, exists
from shutil import rmtree
from six import string_types
from six.moves import cStringIO as StringIO
import sys
from tempfile import mkdtemp
from unittest import TestCase
from yaml import add_constructor, add_representer, load_all as yaml_load_all


log = getLogger("test_cli")


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestCLI(TestCase):
    def setUp(self):
        self.testdir = dirname(__file__) + "/cli/"
        self.tempdir = mkdtemp()
        self.maxDiff = 10000

    def tearDown(self):
        rmtree(self.tempdir)

    def run_docs(self, template_filename, resource_filenames=(),
                 expected_returncode=0, expected_filename=None,
                 expected_errors=None, template_arg=False, local_tags=True,
                 output_filename=None, long_parameters=True,
                 format=None):
        args = []

        if not local_tags:
            args += ["--no-local-tag" if long_parameters else "-n"]

        if output_filename is not None:
            args += ["--output" if long_parameters else "-o", output_filename]

        if format is not None:
            args += ["--format" if long_parameters else "-f", format]

        if template_arg:
            args += ["--template" if long_parameters else "-t",
                     self.testdir + template_filename]
        else:
            args += [self.testdir + template_filename]

        args += [self.testdir + r for r in resource_filenames]
        log.info("Starting CLI with args=%s", args)
        with captured_output() as (out, err):
            result = main(args)
        log.info("CLI returned with code %d" % result)

        out = out.getvalue()
        err = err.getvalue()

        sys.stdout.write(out)
        sys.stderr.write(err)
        sys.stdout.flush()
        sys.stderr.flush()

        log.debug(err)

        self.assertEquals(result, expected_returncode)

        if expected_filename is not None:
            add_constructor(None, UnknownLocalTag.yaml_constructor)
            add_representer(UnknownLocalTag, UnknownLocalTag.represent)
            if output_filename:
                with open(output_filename, "r") as fd:
                    if format == "json":
                        actual = json_load(fd)
                    else:
                        actual = list(yaml_load_all(fd))
            else:
                if format == "json":
                    actual = json_loads(out)
                else:
                    actual = list(yaml_load_all(out))

            with open(self.testdir + expected_filename, "r") as fd:
                if format == "json":
                    expected = json_load(fd)
                else:
                    expected = list(yaml_load_all(fd))

            self.assertEquals(actual, expected)

        if expected_errors is not None:
            if isinstance(expected_errors, string_types):
                self.assertIn(expected_errors, err)
            else:
                for error in expected_errors:
                    self.assertIn(error, err)
        return

    def test_basic(self):
        self.run_docs(
            template_filename="basic-template.yml",
            resource_filenames=["basic-resource-1.yml"],
            expected_filename="basic-expected.yml")
        self.run_docs(
            template_filename="basic-template.yml",
            resource_filenames=["basic-resource-1.yml"],
            expected_filename="basic-expected.yml",
            template_arg=True)
        self.run_docs(
            template_filename="basic-template.yml",
            resource_filenames=["basic-resource-1.yml"],
            expected_filename="basic-expected.yml",
            output_filename=self.tempdir + "basic-actual.yml")
        self.run_docs(
            template_filename="basic-template.yml",
            resource_filenames=["basic-resource-1.yml"],
            expected_filename="basic-expected.yml",
            template_arg=True,
            output_filename=self.tempdir + "basic-actual.yml")

    def test_globaltag(self):
        self.run_docs(
            template_filename="globaltag-template.yml",
            resource_filenames=["globaltag-resource-1.yml"],
            expected_filename="globaltag-expected.yml",
            local_tags=False)
        self.run_docs(
            template_filename="globaltag-template.yml",
            resource_filenames=["globaltag-resource-1.yml"],
            expected_filename="globaltag-expected.yml",
            template_arg=True,
            local_tags=False)

    def test_json(self):
        self.run_docs(
            template_filename="noset-template.yml",
            resource_filenames=["noset-resource-1.yml"],
            expected_filename="noset-expected.json",
            format="json")

    def test_multidoc(self):
        self.run_docs(
            template_filename="multidoc-template.yml",
            expected_filename="multidoc-expected.yml")
        self.run_docs(
            template_filename="multidoc-template.yml",
            expected_filename="multidoc-expected.json",
            format="json",
            expected_errors=("Warning: multiple documents are not supported "
                             "with JSON output"))

    def test_unknown_local_tags_template(self):
        self.run_docs(
            template_filename="unknown-tags-template.yml",
            expected_returncode=0)

        self.run_docs(
            template_filename="unknown-tags-template.yml",
            resource_filenames=["unknown-tags-resource.yml"],
            expected_returncode=0)

    def test_cloudformation(self):
        self.run_docs(
            template_filename="cloudformation-template.yml",
            expected_filename="cloudformation-expected.yml",
            expected_returncode=0)

    def test_bad_args(self):
        with captured_output() as (out, err):
            result = main(["-x"])

        self.assertEquals(result, 2)
        err = err.getvalue()
        self.assertIn("option -x not recognized", err)
        self.assertIn("Usage:", err)

    def test_bad_format(self):
        with captured_output() as (out, err):
            result = main(["-f", "qwerty"])

        self.assertEquals(result, 2)
        err = err.getvalue()
        self.assertIn("Invalid output format 'qwerty': valid types are", err)
        self.assertIn("Usage:", err)

    def test_help(self):
        with captured_output() as (out, err):
            result = main(["-h"])

        self.assertEquals(result, 0)
        out = out.getvalue()
        err = err.getvalue()
        self.assertIn("Usage:", out)

    def test_unwritable_output(self):
        self.run_docs(
            template_filename="basic-template.yml",
            expected_returncode=1,
            expected_errors="Unable to open / for writing",
            output_filename="/")

    def test_unreadable_input(self):
        self.run_docs(
            template_filename="missing",
            resource_filenames=["basic-resource-1.yml"],
            expected_returncode=1,
            expected_errors=("Unable to open", "for reading:"))

        self.run_docs(
            template_filename="basic-template.yml",
            resource_filenames=["missing"],
            expected_returncode=1,
            expected_errors=("Unable to open", "for reading:"))

    def test_no_args(self):
        with captured_output() as (out, err):
            result = main([])

        self.assertEquals(result, 2)
        err = err.getvalue()
        self.assertIn("Missing template filename", err)
        self.assertIn("Usage:", err)
