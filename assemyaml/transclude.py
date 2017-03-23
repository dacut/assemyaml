from logging import getLogger
from .assemble import assemble, merge_nodes
from .error import TranscludeError
from .types import GLOBAL_TRANSCLUDE_TAG, LOCAL_TRANSCLUDE_TAG, YAML_SEQ_TAG
from yaml import compose_all
from yaml.nodes import (
    Node, CollectionNode, MappingNode, ScalarNode, SequenceNode,
)

log = getLogger("assemyaml.transclude")


def transclude_template(stream, assemblies, local_tags=True):
    documents = []

    for doc in compose_all(stream):
        # Wrap the document in a sequence node so we can apply get_assemblies()
        # and transclude() to an assembly or transclude at the top level.
        wrapper = SequenceNode(YAML_SEQ_TAG, [doc])

        # Record any assemblies in the document itself, but don't apply
        # these to other documents.
        doc_assemblies = assemblies.copy()

        log.debug("Before transclude: wrapper=%s", wrapper)

        wrapper = assemble(wrapper, doc_assemblies, local_tags)
        wrapper = transclude(wrapper, doc_assemblies, local_tags)

        log.debug("After transclude:  wrapper=%s", wrapper)

        documents.append(wrapper.value[0])

    return documents


def transclude(node, assemblies, local_tags):
    """
    transclude(node, assemblies, local_tags) -> node

    Find all transclusion points in the given node and replace or merge their
    contents with values from the assemblies.
    """
    assert isinstance(node, Node)
    if isinstance(node, ScalarNode):
        # Scalar type -- no need to evaluate
        return node

    log.debug("transclude(%s)", node)

    name, value = get_transclude(node, local_tags)
    if name is not None:
        log.debug("transclude starting on node=%s", node)
        assembly_value = assemblies.get(name)

        if assembly_value is not None:
            # Add existing assembly values into the transcluded value.
            value = merge_nodes(value, assembly_value)

        node = value
        assert isinstance(node, Node)
        if isinstance(node, ScalarNode):
            return node

    # Recurse on the node's value
    old_values = node.value
    node.value = []

    for value in old_values:
        if isinstance(value, tuple):
            value = tuple([transclude(el, assemblies, local_tags)
                          for el in value])
        else:
            assert isinstance(value, Node)
            value = transclude(value, assemblies, local_tags)

        node.value.append(value)

    return node


def get_transclude(node, local_tags):
    """
    get_transclude(node) -> (name, value) | (None, None)

    If node represents an transclude point, decompose it into the name and
    value of the node.
    """
    # This node is a transclude if it's a mapping node and has a key tagged
    # with one of our transclude tags.
    if not isinstance(node, MappingNode):
        return (None, None)

    transclude_key = None
    transclude_value = None
    for key_node, value_node in node.value:
        log.debug("get_transclude: considering key_node=%s", key_node)
        if (key_node.tag == GLOBAL_TRANSCLUDE_TAG or  # noqa: E129
            local_tags and key_node.tag == LOCAL_TRANSCLUDE_TAG):
            transclude_key = key_node
            transclude_value = value_node
            break
    else:
        # No transclude key found.
        return (None, None)

    # Make sure the transclude conforms to rules
    # Rule 1: Transclude must be a single-entry mapping. This is ok:
    # X:
    #   !Transclude Foo: ...
    #
    # This is not ok:
    # X:
    #   !Transclude Foo: ...
    #   !Transclude Bar: ...
    #   p: q
    if len(node.value) != 1:
        raise TranscludeError(
            None, None, "Transclude must be a single-entry mapping",
            node.start_mark)

    # Rule 2: Transclude name must be a scalar.
    if isinstance(transclude_key, CollectionNode):
        raise TranscludeError(
            None, None, "Transclude name must be a scalar",
            transclude_key.start_mark)

    return (transclude_key.value, transclude_value)
