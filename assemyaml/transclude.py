from logging import getLogger
from six.moves import range
from .assemble import get_assemblies
from .constructor import LocatableNull
from .error import TranscludeError
from .loader import LocatableLoader
from .types import AssemblyPoint, TranscludePoint


NoneType = type(None)
log = getLogger("assemyaml.transclude")


def transclude_template(stream, assemblies, local_tags=True):
    loader = LocatableLoader(stream)

    try:
        loader.add_constructor(
            TranscludePoint.global_tag, TranscludePoint.construct)
        loader.add_constructor(
            AssemblyPoint.global_tag, AssemblyPoint.construct)
        if local_tags:
            loader.add_constructor(
                TranscludePoint.local_tag, TranscludePoint.construct)
            loader.add_constructor(
                AssemblyPoint.local_tag, AssemblyPoint.construct)

        documents = []

        while loader.check_data():
            # Record any assemblies in the document itself, but don't apply
            # these to other documents.
            doc = loader.get_data()
            doc_assemblies = assemblies.copy()
            get_assemblies([doc], doc_assemblies)
            transclude([doc], doc_assemblies)
            documents.append(doc)

        return documents
    finally:
        loader.dispose()


def transclude(node, assemblies):
    """
    transclude(node, assemblies)

    Find all transclusion points in the given node and replace or merge their
    contents with values from the assemblies.
    """
    if isinstance(node, list):
        keys = range(len(node))
    elif isinstance(node, dict):
        keys = list(node.keys())
    else:
        # Scalar type -- no need to evaluate
        return

    for key in keys:
        value = node[key]
        trans_name, trans_value = get_transclude(value)
        if trans_name is not None:
            existing_value = assemblies.get(trans_name)
            log.debug("trans_name=%s trans_value=%s existing_value=%s",
                      trans_name, trans_value, existing_value)

            # Merge the assembly value with the transcluded value.
            if isinstance(trans_value, (NoneType, LocatableNull)):
                value = existing_value
            elif isinstance(existing_value, list):
                if not isinstance(trans_value, list):
                    raise TranscludeError(
                        "Mismatched assembly types for %s: list at" %
                        trans_name,
                        getattr(existing_value, "start_mark", None),
                        "%s at" % trans_value.py_type.__name__,
                        getattr(trans_value, "start_mark", None))

                value = trans_value + existing_value
            elif isinstance(existing_value, dict):
                if not isinstance(trans_value, dict):
                    raise TranscludeError(
                        "Mismatched assembly types for %s: dict at" %
                        trans_name,
                        getattr(existing_value, "start_mark", None),
                        "%s at" % trans_value.py_type.__name__,
                        getattr(trans_value, "start_mark", None))

                value = existing_value.copy()
                for dkey in trans_value:
                    if dkey in existing_value:
                        raise TranscludeError(
                            ("Duplicate key %r for assembly %s: first "
                             "occurrence at") % (dkey, trans_name),
                            getattr(existing_value, "start_mark", None),
                            "second occurrence at",
                            getattr(trans_value, "start_mark", None))
                    value[dkey] = trans_value[dkey]
            elif isinstance(existing_value, set):
                if not isinstance(trans_value, set):
                    raise TranscludeError(
                        "Mismatched assembly types for %s: set at" %
                        trans_name,
                        getattr(existing_value, "start_mark", None),
                        "%s at" % trans_value.py_type.__name__,
                        getattr(trans_value, "start_mark", None))

                value = existing_value.union(trans_value)
            elif isinstance(existing_value, (NoneType, LocatableNull)):
                value = trans_value
            else:
                raise TranscludeError(
                    "Cannot set value for assembly %s: %s at" % (
                        trans_name, existing_value.py_type.__name__),
                    getattr(existing_value, "start_mark", None),
                    "%s at" % trans_value.py_type.__name__,
                    getattr(trans_value, "start_mark", None))

            # Move the assembly value up in the hierarchy
            node[key] = value

        # Recurse on the value
        transclude(value, assemblies)
    return


def get_transclude(node):
    """
    get_transclude(node) -> (name, value) | (None, None)

    If node represents an transclude point, decompose it into the name and
    value of the node.
    """
    if not isinstance(node, dict):
        return (None, None)

    transclude_key = None
    for key in node:
        if isinstance(key, TranscludePoint):
            transclude_key = key
            break

    if transclude_key is None:
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
    if len(node) != 1:
        raise TranscludeError(
            None, None, "Transclude must be a single-entry mapping",
            getattr(node, "start_mark", None))

    # Rule 2: Transclude name must be a scalar.
    if isinstance(transclude_key.name, (list, dict, tuple)):  # pragma: nocover
        raise TranscludeError(
            None, None, "Transclude name must be a scalar",
            getattr(transclude_key.name, "start_mark", None))

    return (transclude_key.name, node[transclude_key])
