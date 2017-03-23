from __future__ import absolute_import, print_function
from logging import getLogger
from six.moves import range
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

log = getLogger("assemyaml.types")

# Assemyaml-specific tags
ASSEMYAML_NS = u"tag:assemyaml.nz,2017:"
GLOBAL_ASSEMBLY_TAG = ASSEMYAML_NS + u"Assembly"
GLOBAL_TRANSCLUDE_TAG = ASSEMYAML_NS + u"Transclude"
LOCAL_ASSEMBLY_TAG = u"!Assembly"
LOCAL_TRANSCLUDE_TAG = u"!Transclude"

# YAML native types
YAML_NS = u"tag:yaml.org,2002:"
YAML_BINARY_TAG = YAML_NS + u"binary"
YAML_BOOL_TAG = YAML_NS + u"bool"
YAML_FLOAT_TAG = YAML_NS + u"float"
YAML_INT_TAG = YAML_NS + u"int"
YAML_NULL_TAG = YAML_NS + u"null"
YAML_MAP_TAG = YAML_NS + u"map"
YAML_OMAP_TAG = YAML_NS + u"omap"
YAML_PAIRS_TAG = YAML_NS + u"pairs"
YAML_SEQ_TAG = YAML_NS + u"seq"
YAML_SET_TAG = YAML_NS + u"set"
YAML_STR_TAG = YAML_NS + u"str"
YAML_TIMESTAMP_TAG = YAML_NS + u"timestamp"

# Because Python3 removed this from types <sigh>
NoneType = type(None)

# tag-to-function mapping for comparing nodes
comparison_functions = {}


def comparison_function(*tags):
    def add_function(f):
        for tag in tags:
            comparison_functions[tag] = f
        return f

    return add_function


def nodes_equal(a, b):
    """
    nodes_equal(a, b) -> bool

    Indicates whether two nodes are equal (examining both tags and values).
    """
    global comparison_functions

    if a.tag != b.tag:
        return False

    try:
        return comparison_functions[a.tag](a, b)
    except KeyError:
        log.info("No comparison function found for %s", a.tag)
        if type(a) is not type(b):
            return False

        if isinstance(a, ScalarNode):
            return scalar_compare(a, b)
        elif isinstance(a, SequenceNode):
            return seq_compare(a, b)
        elif isinstance(a, MappingNode):
            return map_compare(a, b)

        return False


@comparison_function(YAML_BINARY_TAG, YAML_BOOL_TAG, YAML_FLOAT_TAG,
                     YAML_INT_TAG, YAML_STR_TAG, YAML_TIMESTAMP_TAG)
def scalar_compare(a, b):
    return a.value == b.value


@comparison_function(YAML_NULL_TAG)
def null_compare(a, b):
    return True


@comparison_function(YAML_OMAP_TAG, YAML_PAIRS_TAG, YAML_SEQ_TAG)
def seq_compare(a, b):
    if len(a.value) != len(b.value):
        return False

    for a_el, b_el in zip(a.value, b.value):
        return nodes_equal(a_el, b_el)


@comparison_function(YAML_SET_TAG)
def set_compare(a, b):
    # We need to do an unordered comparison. Since we can't put this into a
    # Python datastructure, the comparison is O(n^2).
    if len(a.value) != len(b.value):
        return False

    a_values = [key for key, _ in a.value]
    b_values = [key for key, _ in b.value]

    for a_el in a_values:
        # Look for this value anywhere in the b_values
        for i in range(len(b_values)):
            b_el = b_values[i]
            if nodes_equal(a_el, b_el):
                # Found a match. Mark it as seen from b_values by deleting it.
                del b_values[i]
                break
        else:
            # Not found. We're done.
            return False

    assert len(b_values) == 0
    return True


@comparison_function(YAML_MAP_TAG)
def map_compare(a, b):
    # This is similar to set_compare, except the values are 2-tuples in the
    # form (key, value).
    if len(a.value) != len(b.value):
        return False

    b_values = list(b.value)

    for a_key, a_value in a.value:
        # Look for this key anywhere in the b_values
        for i in range(len(b_values)):
            b_key, b_value = b_values[i]

            if nodes_equal(a_key, b_key):
                if not nodes_equal(a_value, b_value):
                    return False

                # Found a match. Mark it as seen from b_values by deleting it.
                del b_values[i]
                break
        else:
            # Not found. We're done.
            return False

    assert len(b_values) == 0
    return True


def mapping_find(mapping, node):
    for i, kv in enumerate(mapping.value):
        if nodes_equal(kv[0], node):
            return (i, kv[0], kv[1])

    return None
