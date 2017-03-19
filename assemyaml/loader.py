from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.parser import Parser
from yaml.composer import Composer
from .constructor import LocatableConstructor
from yaml.resolver import Resolver


class LocatableLoader(Reader, Scanner, Parser, Composer, LocatableConstructor,
                      Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        LocatableConstructor.__init__(self)
        Resolver.__init__(self)
