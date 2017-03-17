from .constructor import Locatable

class TAPoint(Locatable):
    namespace = "tag:assemyaml.nz,2017:"

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
    def represent(cls, dumper, data):
        dumper.represent_str("ERROR: Attempted to stream out %s" % cls.__name__)

class TranscludePoint(TAPoint):
    global_tag = TAPoint.namespace + "Transclude"
    local_tag = "!Transclude"

    def __repr__(self):
        return "!Transclude %s" % self.name

class AssemblyPoint(TAPoint):
    global_tag = TAPoint.namespace + "Assembly"
    local_tag = "!Assembly"

    def __repr__(self):
        return "!Assembly [%s]" % self.name
