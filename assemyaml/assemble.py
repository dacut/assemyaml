from logging import getLogger
from six.moves import range
from .constructor import LocatableNull
from .error import AssemblyError
from .loader import LocatableLoader
from .types import AssemblyPoint, TranscludePoint


NoneType = type(None)
log = getLogger("assemyaml.assemble")


def record_assemblies(stream, assemblies, local_tags=True):
    loader = LocatableLoader(stream)

    try:
        loader.add_constructor(
            TranscludePoint.global_tag, TranscludePoint.construct)
        loader.add_constructor(
            AssemblyPoint.global_tag, AssemblyPoint.construct)
        if local_tags:
            loader.add_constructor(TranscludePoint.local_tag,
                                   TranscludePoint.construct)
            loader.add_constructor(AssemblyPoint.local_tag,
                                   AssemblyPoint.construct)

        while loader.check_data():
            doc = loader.get_data()
            get_assemblies([doc], assemblies)
    finally:
        loader.dispose()


def get_assemblies(node, assemblies):
    """
    get_assemblies(node, assemblies)

    Find all assemblies in the given node, record their values into the dict
    assemblies, and remove their nodes from the hierarchy.
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
        log.debug("get_assemblies: node=%s, node[%s]=%s", node, key, value)
        asy_name, asy_value = get_assembly(value)
        if not isinstance(asy_value, (NoneType, LocatableNull)):
            existing_value = assemblies.get(asy_name)
            if isinstance(existing_value, (NoneType, LocatableNull)):
                assemblies[asy_name] = asy_value
            elif isinstance(existing_value, list):
                if not isinstance(asy_value, list):
                    raise AssemblyError(
                        "Mismatched assembly types for %s: list at" % asy_name,
                        getattr(existing_value, "start_mark", None),
                        "%s at" % asy_value.py_type.__name__,
                        getattr(asy_value, "start_mark", None))
                existing_value.extend(asy_value)
            elif isinstance(existing_value, dict):
                if not isinstance(asy_value, dict):
                    raise AssemblyError(
                        "Mismatched assembly types for %s: dict at" % asy_name,
                        getattr(existing_value, "start_mark", None),
                        "%s at" % asy_value.py_type.__name__,
                        getattr(asy_value, "start_mark", None))

                for dkey in asy_value:
                    if dkey in existing_value:
                        raise AssemblyError(
                            ("Duplicate key %r for assembly %s: first "
                             "occurrence at") % (dkey, asy_name),
                            getattr(existing_value, "start_mark", None),
                            "second occurrence at",
                            getattr(asy_value, "start_mark", None))

                    existing_value[dkey] = asy_value[dkey]
            elif isinstance(existing_value, set):
                if not isinstance(asy_value, set):
                    raise AssemblyError(
                        "Mismatched assembly types for %s: set at" % asy_name,
                        getattr(existing_value, "start_mark", None),
                        "%s at" % asy_value.py_type.__name__,
                        getattr(asy_value, "start_mark", None))

                existing_value.update(asy_value)
            elif existing_value is not None:
                raise AssemblyError(
                    "Cannot set value for assembly %s: %s at" % (
                        asy_name, existing_value.py_type.__name__),
                    getattr(existing_value, "start_mark", None),
                    "%s at" % asy_value.py_type.__name__,
                    getattr(asy_value, "start_mark", None))

            # Move the assembly value up in the hierarchy
            node[key] = value = asy_value

        # Recurse on the value
        get_assemblies(value, assemblies)
    return


def get_assembly(node):
    """
    get_assembly(node) -> (name, value) | (None, None)

    If node represents an assembly, decompose it into the name and value of
    the node.
    """
    if not isinstance(node, dict):
        return (None, None)

    assembly_key = None
    for key in node:
        if isinstance(key, AssemblyPoint):
            assembly_key = key
            break

    if assembly_key is None:
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
    if len(node) != 1:
        raise AssemblyError(
            None, None, "Assembly must be a single-entry mapping",
            getattr(node, "start_mark", None))

    # Rule 2: Assembly name must be a scalar.
    # Note: PyYAML is currently not capable of producing these
    if isinstance(assembly_key.name, (list, dict, tuple)):  # pragma: nocover
        raise AssemblyError(
            None, None, "Assembly name must be a scalar",
            getattr(assembly_key.name, "start_mark", None))

    return (assembly_key.name, node[assembly_key])
