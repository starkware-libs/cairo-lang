def read_file_from_dict(dct):
    """
    Given a dictionary from a package name (a.b.c) to a file content returns a function that can be
    passed to collect_imports.
    """
    return lambda x: (dct[x], x)
