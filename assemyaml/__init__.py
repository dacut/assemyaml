#!/usr/bin/env python
from __future__ import absolute_import, print_function
from .assemble import record_assemblies
from getopt import getopt, GetoptError
from os.path import basename
import sys
from sys import argv, exit as sys_exit
from .transclude import transclude_template
from yaml import dump_all
from yaml.error import YAMLError

# NOTE: We print to sys.stderr and do NOT do a "from sys import stderr" and
# print to the imported stderr so we can do unit testing on error messages.


def run(template_fd, resource_fds, output_fd, local_tags):
    assemblies = {}
    for fd in resource_fds:
        try:
            record_assemblies(fd, assemblies, local_tags)
        except YAMLError as e:
            print("Error while processing resource document %s:" %
                  getattr(fd, "filename", "<input>"), file=sys.stderr)
            print(str(e), file=sys.stderr)
            return 1

    try:
        docs = transclude_template(template_fd, assemblies, local_tags)
    except YAMLError as e:
        print("Error while processing template document %s:" %
              getattr(template_fd, "filename", "<input>"), file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    dump_all(docs, output_fd)

    return 0


def main(args=None):
    template_filename = None
    local_tags = True
    output = sys.stdout

    if args is None:  # pragma: nocover
        args = argv[1:]

    try:
        opts, filenames = getopt(
            args, "hlo:t:", ["help", "no-local-tag", "output=", "template="])
    except GetoptError as e:
        print(str(e), file=sys.stderr)
        usage()
        return 2

    for opt, val in opts:
        if opt in ("-h", "--help",):
            usage(sys.stdout)
            return 0
        elif opt in ("-l", "--no-local-tag",):
            local_tags = False
        elif opt in ("-o", "--output",):
            try:
                output = open(val, "w")
            except IOError as e:
                print("Unable to open %s for writing: %s" % (val, e),
                      file=sys.stderr)
                return 1
        elif opt in ("-t", "--template",):
            template_filename = val

    if template_filename is None:
        if len(filenames) == 0:
            print("Missing template filename", file=sys.stderr)
            usage()
            return 2
        template_filename = filenames[0]
        filenames = filenames[1:]

    try:
        template_fd = open(template_filename, "r")
    except IOError as e:
        print("Unable to open %s for reading: %s" % (template_filename, e),
              file=sys.stderr)
        return 1

    resource_fds = []
    for filename in filenames:
        try:
            resource_fds.append(open(filename, "r"))
        except IOError as e:
            print("Unable to open %s for reading: %s" % (filename, e),
                  file=sys.stderr)
            return 1

    result = run(template_fd, resource_fds, output, local_tags)

    template_fd.close()
    for fd in resource_fds:
        fd.close()

    if output is not sys.stdout:
        output.flush()
        output.close()

    return result


def usage(fd=None):
    if fd is None:  # Can't use default args for unit testing.
        fd = sys.stderr

    fd.write("""
Usage: %(argv0)s [options] template-document resource-documents...
       %(argv0)s [options] --template template-document resource-documents...

Transclude parts of YAML documents to produce a final document.

Syntax examples:
    Template document:
        Hello:
          !Transclude World:
            - First Line

    Resource documents:
        !Assembly World:
          - Second Line

        !Assembly World:
          - Third Line

    Resulting output:
        Hello:
          - First Line
          - Second Line
          - Third Line

See https://assemyaml.nz for details on document syntax.

Options:
    --help
        Show this usage information.

    --no-local-tag | -l
        Ignore !Transclude and !Assembly local tags and use global tags only.

    --output <filename> | -o <filename>
        Write output to filename instead of stdout.
""" % {"argv0": basename(argv[0])})
    fd.flush()
    return


if __name__ == "__main__":  # pragma: nocover
    sys_exit(main(argv[1:]))
