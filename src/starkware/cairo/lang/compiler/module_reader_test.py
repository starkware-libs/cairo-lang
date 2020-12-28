import pytest

from starkware.cairo.lang.compiler.module_reader import ModuleNotFoundException, ModuleReader


def test_file_path_extractor():
    isfile = lambda _: True
    reader = ModuleReader(paths=['/usr/include'], cairo_suffix='.f~o')
    assert reader.module_to_file_path('foo.bar', isfile) == '/usr/include/foo/bar.f~o'

    reader = ModuleReader(paths=['rel//path'], cairo_suffix='.txt')
    assert reader.module_to_file_path('hello.world', isfile) == 'rel//path/hello/world.txt'


def test_search_file():
    reader = ModuleReader(paths=['a', 'b', 'c'], cairo_suffix='.c')
    assert reader.module_to_file_path('f', isfile=lambda x: x in ['b/f.c', 'c/f.c']) == 'b/f.c'

    with pytest.raises(ModuleNotFoundException, match="""\
Could not find module 'x.y.z'. Searched in the following paths:
a/x/y/z.c
b/x/y/z.c
c/x/y/z.c"""):
        reader.module_to_file_path('x.y.z', isfile=lambda _: False)
