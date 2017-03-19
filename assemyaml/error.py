from yaml import MarkedYAMLError


class TranscludeError(MarkedYAMLError):
    pass


class AssemblyError(MarkedYAMLError):
    pass
