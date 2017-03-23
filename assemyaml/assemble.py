from logging import getLogger
from .error import AssemblyError
from .types import (
    GLOBAL_ASSEMBLY_TAG, LOCAL_ASSEMBLY_TAG, mapping_find, YAML_MAP_TAG,
    YAML_NULL_TAG, YAML_NS, YAML_SEQ_TAG,
)
from yaml import compose_all
from yaml.loader import SafeLoader
from yaml.nodes import (
    Node, CollectionNode, MappingNode, ScalarNode, SequenceNode,
)


log = getLogger("assemyaml.assemble")


def record_assemblies(stream, assemblies, local_tags=True):
    for doc in compose_all(stream, Loader=SafeLoader):
        # Wrap the document in a sequence node so we can apply get_assemblies()
        # to an assembly at the top level.
        wrapper = SequenceNode(YAML_SEQ_TAG, [doc])
        assemble(wrapper, assemblies, local_tags)

    return


def assemble(node, assemblies, local_tags):
    """
    assemble(node, assemblies, local_tags) -> node

    First, recurse on the values in this node.

    Then, if the current node is an assembly, record its value and return the
    value as the node.
    """
    assert isinstance(node, Node)
    if isinstance(node, ScalarNode):
        # Scalar type -- no need to evaluate
        return node

    old_values = node.value
    node.value = []
    for value in old_values:
        if isinstance(value, tuple):
            value = tuple(
                [assemble(el, assemblies, local_tags) for el in value])
        else:
            value = assemble(value, assemblies, local_tags)

        node.value.append(value)

    # Is this node an assembly?
    name, value = get_assembly(node, local_tags)
    if name is not None:
        # Yes. Take a look at the existing value.
        existing_value = assemblies.get(name)

        if existing_value is None:
            node = assemblies[name] = value
        else:
            node = assemblies[name] = merge_nodes(existing_value, value)

    return node


def simplify_tag(tag):
    if tag.startswith(YAML_NS):
        return "!!" + tag[len(YAML_NS):]
    else:
        return tag


def merge_nodes(a, b):
    """
    merge_nodes(a, b) -> node

    Merge the values of the two nodes together to produce a new node.
    """

    if a.tag == YAML_NULL_TAG:
        node = b
    elif b.tag == YAML_NULL_TAG:
        node = a
    elif isinstance(a, ScalarNode):
        raise AssemblyError(
            "Cannot merge %s value at" % simplify_tag(b.tag), b.start_mark,
            "into %s value at" % simplify_tag(a.tag), a.start_mark)
    elif isinstance(a, SequenceNode):
        if not isinstance(b, SequenceNode) or b.tag != a.tag:
            raise AssemblyError(
                "Cannot merge %s value at" % simplify_tag(b.tag), b.start_mark,
                "into %s value at" % simplify_tag(a.tag), a.start_mark)

        node = SequenceNode(a.tag, a.value + b.value)
    elif isinstance(a, MappingNode):
        if not isinstance(b, MappingNode) or b.tag != a.tag:
            raise AssemblyError(
                "Cannot merge %s value at" % simplify_tag(b.tag), b.start_mark,
                "into %s value at" % simplify_tag(a.tag), a.start_mark)

        # If the existing value is a regular map (not an omap), we need to
        # look for duplicate keys and raise an exception if one
        # is found. Since YAML allows for complex keys (sequences, etc.),
        # PyYAML stores mappings as an unordered list of (key, value) tuples.
        if a.tag == YAML_MAP_TAG:
            for bkey, _ in b.value:
                pos = mapping_find(a, bkey)
                if pos is not None:
                    akey = pos[1]
                    raise AssemblyError(
                        "Cannot merge duplicate mapping key '%s' at" %
                        bkey.value, bkey.start_mark,
                        "into existing mapping at", akey.start_mark)

        # Extend the existing mapping
        node = MappingNode(a.tag, a.value + b.value)
    else:
        raise RuntimeError("Unable to handle node of type %s" %
                           type(a).__name__)

    return node


def get_assembly(node, local_tags):
    """
    get_assembly(node, local_tags) -> (name, value) | (None, None)

    If node represents an assembly, decompose it into the name and value of
    the node.
    """
    # This node is an assembly if it's a mapping node and has a key tagged
    # with one of our assembly tags.
    if not isinstance(node, MappingNode):
        return (None, None)

    assembly_key = None
    assembly_value = None
    for key_node, value_node in node.value:
        if (key_node.tag == GLOBAL_ASSEMBLY_TAG or  # noqa: E129
            local_tags and key_node.tag == LOCAL_ASSEMBLY_TAG):
            assembly_key = key_node
            assembly_value = value_node
            break
    else:
        # No assembly key found.
        return (None, None)

    # Make sure the assembly conforms to rules
    # Rule 1: Assembly must be a single-entry mapping. This is ok:
    # X:
    #   !Assembly Foo: ...
    #
    # This is not ok:
    # X:
    #   !Assembly Foo: ...
    #   !Assembly Bar: ...
    #   p: q
    if len(node.value) != 1:
        raise AssemblyError(
            None, None, "Assembly must be a single-entry mapping",
            node.start_mark)

    # Rule 2: Assembly name must be a scalar.
    if isinstance(assembly_key, CollectionNode):
        raise AssemblyError(
            None, None, "Assembly name must be a scalar",
            assembly_key.start_mark)

    return (assembly_key.value, assembly_value)
