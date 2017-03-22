from __future__ import absolute_import, print_function
from logging import getLogger

log = getLogger("assemyaml.types")


class Locatable(object):
    def _set_marks(self, node):
        self.start_mark = node.start_mark
        self.end_mark = node.end_mark

    def copy(self):
        result = super(Locatable, self).copy()
        result = type(self)(result)
        result.start_mark = self.start_mark
        result.end_mark = self.end_mark
        return result

    @classmethod
    def represent(cls, dumper, data):
        return dumper.represent_data(data.py_type(data))


class LocatableNull(Locatable):
    py_type = type(None)

    def __init__(self, value):
        super(LocatableNull, self).__init__()
        return

    def __bool__(self):
        return False
    __nonzero__ = __bool__

    def __eq__(self, other):
        return other is None or isinstance(other, LocatableNull)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(None)

    def __repr__(self):
        return "None"

    @classmethod
    def represent(cls, dumper, data):
        return dumper.represent_data(None)


class LocatableProxy(Locatable):
    def __init__(self, value, start_mark=None, end_mark=None):
        super(LocatableProxy, self).__init__()
        self._proxy_value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        return

    def __bool__(self):
        return bool(self._proxy_value)
    __nonzero__ = __bool__

    def __eq__(self, other):
        if isinstance(other, LocatableProxy):
            return self._proxy_value == other._proxy_value
        else:
            return self._proxy_value == other

    def __ne__(self, other):
        if isinstance(other, LocatableProxy):
            return self._proxy_value != other._proxy_value
        else:
            return self._proxy_value != other

    def __lt__(self, other):
        if isinstance(other, LocatableProxy):
            return self._proxy_value < other._proxy_value
        else:
            return self._proxy_value < other

    def __le__(self, other):
        if isinstance(other, LocatableProxy):
            return self._proxy_value <= other._proxy_value
        else:
            return self._proxy_value <= other

    def __ge__(self, other):
        if isinstance(other, LocatableProxy):
            return self._proxy_value >= other._proxy_value
        else:
            return self._proxy_value >= other

    def __gt__(self, other):
        if isinstance(other, LocatableProxy):
            return self._proxy_value > other._proxy_value
        else:
            return self._proxy_value > other

    def __hash__(self):
        return hash(self._proxy_value)

    def __repr__(self):
        return repr(self._proxy_value)

    def __getattr__(self, name):
        return getattr(self._proxy_value, name)

    def __setattr__(self, name, value):
        if name in ("_proxy_value", "start_mark", "end_mark"):
            self.__dict__[name] = value
        else:
            setattr(self._proxy_value, name, value)

        return

    def __delattr__(self, name):
        return delattr(self._proxy_value, name)

    @classmethod
    def represent(cls, dumper, data):
        return dumper.represent_data(data._proxy_value)

    def to_json(self):
        return self._proxy_value


LocatableBool = type("LocatableBool", (LocatableProxy,), {"py_type": bool})
LocatableDict = type("LocatableDict", (Locatable, dict), {"py_type": dict})
LocatableList = type("LocatableList", (Locatable, list), {"py_type": list})
LocatableSet = type("LocatableSet", (Locatable, set), {"py_type": set})


class TAPoint(Locatable):
    namespace = u"tag:assemyaml.nz,2017:"

    def __init__(self, name):
        super(TAPoint, self).__init__()
        assert not isinstance(name, TAPoint)
        self.name = name
        return

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def construct(cls, loader, node):
        return cls(loader.construct_scalar(node))

    @classmethod
    def represent(cls, dumper, data):  # pragma: nocover
        dumper.represent_str("ERROR: Attempted to stream out %s" %
                             cls.__name__)


class TranscludePoint(TAPoint):
    global_tag = TAPoint.namespace + u"Transclude"
    local_tag = u"!Transclude"

    def __repr__(self):
        return "!Transclude %s" % self.name


class AssemblyPoint(TAPoint):
    global_tag = TAPoint.namespace + u"Assembly"
    local_tag = u"!Assembly"

    def __repr__(self):
        return "!Assembly [%s]" % self.name


class UnknownLocalTag(Locatable):
    def __init__(self, tag, value, start_mark=None, end_mark=None):
        super(UnknownLocalTag, self).__init__()
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        return

    @classmethod
    def yaml_constructor(cls, loader, node):
        return cls(node.tag, node.value, node.start_mark, node.end_mark)

    def __repr__(self):
        return "%s %r" % (self.tag, self.value)

    @classmethod
    def represent(cls, dumper, data):
        if isinstance(data.value, (list, set, tuple)):
            log.debug("UnknownLocalTag.represent sequence: %s %s",
                      data.tag, data.value)
            return dumper.represent_sequence(data.tag, data.value)
        elif isinstance(data.value, dict):
            log.debug("UnknownLocalTag.represent mapping: %s %s",
                      data.tag, data.value)
            return dumper.represent_mapping(data.tag, data.value)
        else:
            log.debug("UnknownLocalTag.represent scalar: %s %s",
                      data.tag, data.value)
            return dumper.represent_scalar(data.tag, data.value)

    def __eq__(self, other):
        if not isinstance(other, UnknownLocalTag):
            return False

        return self.tag == other.tag and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)
