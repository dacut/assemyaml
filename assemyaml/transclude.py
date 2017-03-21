from six.moves import range
from .assemble import get_assemblies
from .constructor import LocatableNull
from .error import TranscludeError
from .loader import LocatableLoader
from .types import AssemblyPoint, TranscludePoint


NoneType = type(None)


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
            asy_value = assemblies.get(trans_name)
            # Merge the assembly value with the transcluded value.
            if isinstance(asy_value, (NoneType, LocatableNull)):
                value = trans_value
            if isinstance(asy_value, list):
                if isinstance(trans_value, list):
                    value = trans_value + asy_value
                elif isinstance(trans_value, (NoneType, LocatableNull)):
                    value = asy_value
                else:
                    raise TranscludeError(
                        "Mismatched assembly types for %s: list at" %
                        trans_name,
                        getattr(asy_value, "start_mark", None),
                        "%s at" % trans_value.py_type.__name__,
                        getattr(trans_value, "start_mark", None))
            elif isinstance(asy_value, dict):
                if isinstance(trans_value, dict):
                    value = asy_value.copy()
                    for key in trans_value:
                        if key in asy_value:
                            raise TranscludeError(
                                ("Duplicate key %r for assembly %s: first "
                                 "occurence at") % (key, trans_name),
                                getattr(asy_value, "start_mark", None),
                                "second occurrence at",
                                getattr(trans_value, "start_mark", None))
                        asy_value[key] = trans_value[key]
                elif trans_value is None:
                    value = asy_value
                else:
                    raise TranscludeError(
                        "Mismatched assembly types for %s: dict at" %
                        trans_name,
                        getattr(asy_value, "start_mark", None),
                        "%s at" % trans_value.py_type.__name__,
                        getattr(trans_value, "start_mark", None))
            elif asy_value is None:
                value = trans_value
            elif trans_value is not None:
                raise TranscludeError(
                    "Cannot set value for transclude %s: %s at" % (
                        trans_name, asy_value.py_type.__name__),
                    getattr(asy_value, "start_mark", None),
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
            getattr(node, "start_mark", None),
            getattr(node, "end_mark", None))

    # Rule 2: Transclude name must be a scalar.
    if isinstance(transclude_key.name, (list, dict, tuple)):
        raise TranscludeError(
            None, None, "Transclude name must be a scalar",
            getattr(transclude_key.name, "start_mark", None),
            getattr(transclude_key.name, "end_mark", None))

    return (transclude_key.name, node[transclude_key])
