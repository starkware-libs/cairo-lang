import dataclasses
import json
from typing import ClassVar, List, Type

import marshmallow
import marshmallow_dataclass

GPS_FACT_TOPOLOGY = 'gps_fact_topology'


@dataclasses.dataclass(frozen=True)
class FactTopology:
    tree_structure: List[int]
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
