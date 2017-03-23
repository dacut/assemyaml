from __future__ import absolute_import, print_function
from assemyaml.types import (
    nodes_equal, YAML_MAP_TAG, YAML_NS, YAML_NULL_TAG, YAML_SEQ_TAG,
    YAML_SET_TAG, YAML_STR_TAG,
)
from unittest import TestCase
from yaml.nodes import Node, MappingNode, ScalarNode, SequenceNode


def ystr(x):
    return ScalarNode(YAML_STR_TAG, x)


class TestTypes(TestCase):
    def test_unequal_tags(self):
        n1 = ScalarNode(YAML_STR_TAG, "foo")
        n2 = ScalarNode(YAML_NS + "bar", "foo")

        self.assertFalse(nodes_equal(n1, n2))

    def test_unknown_tag_comparison(self):
        n1 = ScalarNode(YAML_NS + "xyz", "foo")
        n2 = ScalarNode(YAML_NS + "xyz", "foo")
        n3 = ScalarNode(YAML_NS + "xyz", "bar")
        self.assertTrue(nodes_equal(n1, n2))
        self.assertFalse(nodes_equal(n1, n3))

        n1 = SequenceNode(YAML_NS + "xyz", [ystr("foo")])
        n2 = SequenceNode(YAML_NS + "xyz", [ystr("foo")])
        n3 = SequenceNode(YAML_NS + "xyz", [ystr("bar")])
        self.assertTrue(nodes_equal(n1, n2))
        self.assertFalse(nodes_equal(n1, n3))

        n1 = MappingNode(YAML_NS + "xyz", [(ystr("foo"), ystr("bar"))])
        n2 = MappingNode(YAML_NS + "xyz", [(ystr("foo"), ystr("bar"))])
        n3 = MappingNode(YAML_NS + "xyz", [(ystr("foo"), ystr("baz"))])
        self.assertTrue(nodes_equal(n1, n2))
        self.assertFalse(nodes_equal(n1, n3))

    def test_unknown_tag_wrong_type_comparison(self):
        n1 = ScalarNode(YAML_NS + "xyz", "foo")
        n2 = SequenceNode(YAML_NS + "xyz", [ystr("foo")])
        self.assertFalse(nodes_equal(n1, n2))

        n1 = Node(YAML_NS + "xyz", "foo", None, None)
        n2 = Node(YAML_NS + "xyz", "foo", None, None)
        self.assertFalse(nodes_equal(n1, n2))

    def test_seq_comparison(self):
        n1 = SequenceNode(YAML_SEQ_TAG, [])
        n2 = SequenceNode(YAML_SEQ_TAG, [ystr("foo")])
        n3 = SequenceNode(YAML_SEQ_TAG, [ystr("foo"), ystr("bar")])
        n4 = SequenceNode(YAML_SEQ_TAG, [ystr("foo"), ystr("bar")])
        n5 = SequenceNode(YAML_SEQ_TAG, [ystr("bar"), ystr("foo")])
        self.assertFalse(nodes_equal(n1, n2))
        self.assertFalse(nodes_equal(n1, n3))
        self.assertFalse(nodes_equal(n2, n3))
        self.assertTrue(nodes_equal(n3, n4))
        self.assertTrue(nodes_equal(n4, n3))
        self.assertFalse(nodes_equal(n3, n5))

    def test_set_comparison(self):
        null = ScalarNode(YAML_NULL_TAG, "")
        n1 = MappingNode(YAML_SET_TAG, [(ystr("a"), null), (ystr("b"), null)])
        n2 = MappingNode(YAML_SET_TAG, [(ystr("b"), null), (ystr("a"), null)])
        n3 = MappingNode(YAML_SET_TAG, [(ystr("b"), null), (ystr("a"), null),
                                        (ystr("c"), null)])
        n4 = MappingNode(YAML_SET_TAG, [(ystr("b"), null), (ystr("a"), null),
                                        (ystr("d"), null)])
        self.assertTrue(nodes_equal(n1, n2))
        self.assertFalse(nodes_equal(n1, n3))
        self.assertFalse(nodes_equal(n3, n1))
        self.assertFalse(nodes_equal(n3, n4))
        self.assertFalse(nodes_equal(n4, n3))

    def test_map_misordered_comparison(self):
        n1 = MappingNode(YAML_MAP_TAG, [(ystr("a"), ystr("foo")),
                                        (ystr("b"), ystr("bar"))])
        n2 = MappingNode(YAML_MAP_TAG, [(ystr("b"), ystr("bar")),
                                        (ystr("a"), ystr("foo"))])
        n3 = MappingNode(YAML_MAP_TAG, [(ystr("a"), ystr("bar")),
                                        (ystr("b"), ystr("foo")),
                                        (ystr("c"), ystr("baz"))])
        n4 = MappingNode(YAML_MAP_TAG, [(ystr("a"), ystr("bar")),
                                        (ystr("b"), ystr("foo")),
                                        (ystr("c"), ystr("xxx"))])
        n5 = MappingNode(YAML_MAP_TAG, [(ystr("a"), ystr("bar")),
                                        (ystr("b"), ystr("foo")),
                                        (ystr("d"), ystr("xxx"))])
        self.assertTrue(nodes_equal(n1, n2))
        self.assertTrue(nodes_equal(n2, n1))
        self.assertFalse(nodes_equal(n1, n3))
        self.assertFalse(nodes_equal(n3, n4))
        self.assertFalse(nodes_equal(n4, n5))
