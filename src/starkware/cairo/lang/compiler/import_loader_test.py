import re
from random import sample
from typing import Dict, List

import pytest

from starkware.cairo.lang.compiler.error_handling import LocationError, get_location_marks
from starkware.cairo.lang.compiler.import_loader import (
    DirectDependenciesCollector,
    ImportLoaderError,
    UsingCycleError,
    collect_imports,
)
from starkware.cairo.lang.compiler.parser import ParserError, parse_file
from starkware.cairo.lang.compiler.test_utils import read_file_from_dict


def test_get_imports():
    code = """
from a import b
ap += [fp] + 2, ap++;
from b.c.d.e import f as g

my_label:
call that;
from vim import ide
// from vs.code import ide
func foo() {
    from pytest import cairo_stack_test as ci
}
"""
    ast = parse_file(code)
    collector = DirectDependenciesCollector()
    collector.get_using_pkgs_in_block(ast.code_block)
    assert set([x for x, _ in collector.packages]) == {"a", "b.c.d.e", "vim", "pytest"}


def test_unreachabale_file():
    files = {
        "root.file": """
from fo.o import aa
from bar import bb
""",
        "bar": "[ap] = 2",
    }

    # Failed to parse internal module.
    with pytest.raises(ImportLoaderError) as e:
        collect_imports("root.file", read_file_from_dict(files))
    assert e.value.location is not None
    assert f"""
{get_location_marks(files['root.file'], e.value.location)}
{e.value.message}
""".startswith(
        """
from fo.o import aa
     ^**^
Could not load module 'fo.o'.
Error: """
    )

    # Failed to parse root module.
    with pytest.raises(ImportLoaderError) as e:
        collect_imports("bad.root", read_file_from_dict(files))
    assert e.value.message.startswith("Could not load module 'bad.root'.")


def test_unparsable_import():
    files = {
        "root.file": """
from foo import bar
""",
        "foo": "this is not cairo code",
    }

    with pytest.raises(ParserError):
        collect_imports("root.file", read_file_from_dict(files))


def test_shallow_tree_graph():
    files = {
        "root.file": """
from a import aa
from b import bb
""",
        "a": "[ap] = 1;",
        "b": "[ap] = 2;",
    }

    expected_res = {name: parse_file(code) for name, code in files.items()}
    assert collect_imports("root.file", read_file_from_dict(files)) == expected_res
    assert set(collect_imports("a", read_file_from_dict(files)).keys()) == {"a"}


def test_long_path_grph():
    files = {f"a{i}": f"from a{i+1} import b" for i in range(10)}
    files["a9"] = "[ap] = 0;"

    expected_res = {name: parse_file(code) for name, code in files.items()}
    assert collect_imports("a0", read_file_from_dict(files)) == expected_res


def test_dag():
    files = {
        "root.file": """
from a import aa
from b import bb
""",
        "a": """
from common.first import some1
from common.second import some2
""",
        "b": """
from common.first import some1
from common.second import some2
""",
        "common.first": "[ap] = 1;",
        "common.second": "[ap] = 2;",
    }

    expected_res = {name: parse_file(code) for name, code in files.items()}
    assert collect_imports("root.file", read_file_from_dict(files)) == expected_res


def test_topologycal_order():
    """
    Build dependencies DAG over the vertices 0..99 and a list of files named 'a0'..'a99'
    such that a<i> imports a<j> directly if and only if i -> j in the dependencies DAG.
    The dependencies DAG is constructed by having every node pointing to 3 other nodes
    having higher indices.
    We test collect_imports on 'a0' returns the dictionary ordered correctly,
    by scanning it and ensuring that when we see some file, all it's dependencies
    where seen before.
    """

    N_VERTICES = 100
    N_NEIGHBORS = 3

    # Initialize the dependencies DAG. A list of int lists.
    # j is in the i-th list iff i->j in the dependencies DAG.
    dependencies: List[List[int]] = [[] for _ in range(N_VERTICES)]
    for i in range(N_VERTICES - N_NEIGHBORS):
        dependencies[i] = sample(range(i + 1, N_VERTICES), N_NEIGHBORS)

    # Construct files.
    files: Dict[str, str] = {}
    for i in range(N_VERTICES):
        # Build the i-th file.
        files[f"a{i}"] = "\n".join([f"from a{j} import nothing" for j in dependencies[i]])

    # Collect packages.
    packages = collect_imports("a0", read_file_from_dict(files))

    # Test order.
    seen = [False] * N_VERTICES
    for pkg in packages:
        curr_id = int(pkg[1:])
        for j in dependencies[i]:
            assert seen[j]
        seen[curr_id] = True


def test_circular_dep():
    # Singleton circle.
    with pytest.raises(UsingCycleError) as e:
        collect_imports("a", read_file_from_dict({"a": "from a import b"}))
    assert (
        str(e.value)
        == """\
Found circular imports dependency:
a imports
a"""
    )

    # Big circle.
    with pytest.raises(UsingCycleError) as e:
        collect_imports(
            "a0", read_file_from_dict({f"a{i}": f"from a{(i+1) % 9} import b" for i in range(10)})
        )
    assert (
        str(e.value)
        == """\
Found circular imports dependency:
a0 imports
a1 imports
a2 imports
a3 imports
a4 imports
a5 imports
a6 imports
a7 imports
a8 imports
a0"""
    )


def test_lang_directive():
    files = {
        "a": """
from c import x
""",
        "b": """
%lang other_lang
from c import x
""",
        "c": """
%lang lang
from d_lang import x
from d_no_lang import x
""",
        "d_lang": """
%lang lang
const x = 0;
""",
        "d_no_lang": """
const x = 0;
""",
        "e": """
%lang lang  // First line.
%lang lang  // Second line.
""",
    }

    # Make sure that starting from 'c' does not raise an exception.
    collect_imports("c", read_file_from_dict(files))

    verify_exception(
        files,
        "a",
        """
a:?:?: Importing modules with %lang directive 'lang' must be from a module with the same directive.
from c import x
     ^
""",
    )

    verify_exception(
        files,
        "b",
        """
b:?:?: Importing modules with %lang directive 'lang' must be from a module with the same directive.
from c import x
     ^
""",
    )

    verify_exception(
        files,
        "e",
        """
e:?:?: Found two %lang directives
%lang lang  // Second line.
^********^
""",
    )


def verify_exception(files: Dict[str, str], main_file: str, error: str):
    """
    Verifies that parsing the code results in the given error.
    """
    with pytest.raises(LocationError) as e:
        collect_imports(main_file, read_file_from_dict(files))
    # Remove line and column information from the error using a regular expression.
    assert re.sub(":[0-9]+:[0-9]+: ", ":?:?: ", str(e.value)) == error.strip()
