import dataclasses
import json
from typing import Any, ClassVar, Dict, List, Type

import marshmallow
import marshmallow_dataclass

GPS_FACT_TOPOLOGY = "gps_fact_topology"


@dataclasses.dataclass(frozen=True)
class FactTopology:
    tree_structure: List[int]
    # List of page sizes, in words.
    page_sizes: List[int]


@marshmallow_dataclass.dataclass(frozen=True)
class FactTopologiesFile:
    fact_topologies: List[FactTopology]
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


def load_fact_topologies(path) -> List[FactTopology]:
    return FactTopologiesFile.Schema().load(json.load(open(path))).fact_topologies


@dataclasses.dataclass(frozen=True)
class FactInfo:
    program_output: List[int]
    fact_topology: FactTopology
    fact: str


def get_page_sizes_from_page_dict(output_size: int, pages: dict) -> List[int]:
    """
    Returns the sizes of the program output pages, given the pages dictionary that appears
    in the additional attributes of the output builtin.
    """
    # Make sure the pages are adjacent to each other.

    # The first page id is expected to be 1.
    expected_page_id = 1
    # We don't expect anything on its start value.
    expected_page_start = None
    # The size of page 0 is output_size if there are no other pages, or the start of page 1
    # otherwise.
    page0_size = output_size

    pages_list = [
        (int(page_id_str), page_start, page_size)
        for page_id_str, (page_start, page_size) in pages.items()
    ]
    for page_id, page_start, page_size in sorted(pages_list):
        assert page_id == expected_page_id, f"Expected page id {expected_page_id}, found {page_id}."
        if page_id == 1:
            assert (
                isinstance(page_start, int) and 0 < page_start <= output_size
            ), f"Invalid page start {page_start}."
            page0_size = page_start
        else:
            assert (
                page_start == expected_page_start
            ), f"Expected page start {expected_page_start}, found {page_start}."

        assert (
            isinstance(page_size, int) and 0 < page_size <= output_size
        ), f"Invalid page size {page_size}."

        expected_page_start = page_start + page_size
        expected_page_id += 1

    if len(pages) > 0:
        assert expected_page_start == output_size, "Pages must cover the entire program output."

    return [page0_size] + [page_size for _, (_, page_size) in sorted(pages.items())]


def get_fact_topology_from_additional_data(
    output_size: int, output_builtin_additional_data: Dict[str, Any]
) -> FactTopology:
    """
    Returns the fact topology from the additional data of the output builtin.
    """
    pages = output_builtin_additional_data["pages"]
    attributes = output_builtin_additional_data["attributes"]

    # If the GPS_FACT_TOPOLOGY attribute is present, use it. Otherwise, the task is expected to
    # use exactly one page (page 0).
    if GPS_FACT_TOPOLOGY in attributes:
        tree_structure = attributes[GPS_FACT_TOPOLOGY]
        assert (
            isinstance(tree_structure, list)
            and len(tree_structure) % 2 == 0
            and 0 < len(tree_structure) <= 10
            and all(isinstance(x, int) and 0 <= x < 2 ** 30 for x in tree_structure)
        ), f"Invalid tree structure specified in the '{GPS_FACT_TOPOLOGY}' attribute."
    else:
        assert len(pages) == 0, (
            f"Additional pages cannot be used since the '{GPS_FACT_TOPOLOGY}' attribute is not "
            "specified."
        )
        tree_structure = [1, 0]

    return FactTopology(
        tree_structure=tree_structure, page_sizes=get_page_sizes_from_page_dict(output_size, pages)
    )
