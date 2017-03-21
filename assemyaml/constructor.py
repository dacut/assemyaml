#!/usr/bin/env python
from yaml.constructor import Constructor, ConstructorError
from yaml.nodes import MappingNode, SequenceNode
from yaml.representer import Representer


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


Representer.add_representer(LocatableNull, LocatableNull.represent)


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


LocatableBool = type("LocatableBool", (LocatableProxy,),
                     {"py_type": bool})
Representer.add_representer(LocatableBool, LocatableProxy.represent)

LocatableDict = type("LocatableDict", (Locatable, dict), {"py_type": dict})
Representer.add_representer(LocatableDict, Locatable.represent)

LocatableList = type("LocatableList", (Locatable, list), {"py_type": list})
Representer.add_representer(LocatableList, Locatable.represent)

LocatableSet = type("LocatableSet", (Locatable, set), {"py_type": set})
Representer.add_representer(LocatableSet, Locatable.represent)


class LocatableConstructor(Constructor):
    locatable_classes = {
        type(None): LocatableNull,
        bool: LocatableBool,
        dict: LocatableDict,
        list: LocatableList,
        set: LocatableSet,
    }

    @classmethod
    def wrap_object(cls, obj, node):
        if isinstance(obj, Locatable):
            return obj

        obj_type = type(obj)
        loc_type = cls.locatable_classes.get(obj_type)

        if loc_type is None:
            # Construct a new Locatable class
            loc_type = type("Locatable%s" % obj_type.__name__.title(),
                            (LocatableProxy,), {"py_type": obj_type})
            cls.locatable_classes[obj_type] = loc_type
            Representer.add_representer(loc_type, LocatableProxy.represent)

        result = loc_type(obj)
        result._set_marks(node)

        return result

    def construct_object(self, node, deep=False):
        obj = self.wrap_object(
            Constructor.construct_object(self, node, deep), node)
        return obj

    def construct_yaml_null(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_null(self, node), node)

    def construct_yaml_bool(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_bool(self, node), node)

    def construct_yaml_int(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_int(self, node), node)

    def construct_yaml_float(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_float(self, node), node)

    def construct_yaml_binary(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_binary(self, node), node)

    def construct_yaml_timestamp(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_timestamp(self, node), node)

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = LocatableList()
        omap._set_marks(node)
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                "while constructing an ordered map", node.start_mark,
                "expected a sequence, but found %s" % node.id,
                node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError(
                    "while constructing an ordered map", node.start_mark,
                    "expected a mapping of length 1, but "
                    "found %s" % subnode.id,
                    subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError(
                    "while constructing an ordered map", node.start_mark,
                    "expected a single mapping item, but "
                    "found %d items" % len(subnode.value),
                    subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = LocatableList()
        pairs._set_marks(node)
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                "while constructing pairs", node.start_mark,
                "expected a sequence, but found %s" % node.id,
                node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError(
                    "while constructing pairs", node.start_mark,
                    "expected a mapping of length 1, but "
                    "found %s" % subnode.id, subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError(
                    "while constructing pairs", node.start_mark,
                    "expected a single mapping item, but "
                    "found %d items" % len(subnode.value),
                    subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = LocatableSet()
        data._set_marks(node)
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        return self.wrap_object(
            Constructor.construct_yaml_str(self, node), node)

    def construct_yaml_seq(self, node):
        data = LocatableList()
        data._set_marks(node)
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = LocatableDict()
        data._set_marks(node)
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = self.wrap_object(cls.__new__(cls), node)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)


LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:null',
    LocatableConstructor.construct_yaml_null)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:bool',
    LocatableConstructor.construct_yaml_bool)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:int',
    LocatableConstructor.construct_yaml_int)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:float',
    LocatableConstructor.construct_yaml_float)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:binary',
    LocatableConstructor.construct_yaml_binary)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:timestamp',
    LocatableConstructor.construct_yaml_timestamp)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:omap',
    LocatableConstructor.construct_yaml_omap)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:pairs',
    LocatableConstructor.construct_yaml_pairs)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:set',
    LocatableConstructor.construct_yaml_set)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:str',
    LocatableConstructor.construct_yaml_str)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:seq',
    LocatableConstructor.construct_yaml_seq)

LocatableConstructor.add_constructor(
    'tag:yaml.org,2002:map',
    LocatableConstructor.construct_yaml_map)

LocatableConstructor.add_constructor(
    None,
    LocatableConstructor.construct_undefined)
