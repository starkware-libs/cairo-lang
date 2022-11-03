import base64
import gzip
import json

from services.external_api.client import JsonObject
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import wrap_with_stark_exception


def compress_program(program_json: JsonObject):
    full_program = json.dumps(program_json)
    compressed_program = gzip.compress(data=full_program.encode("ascii"))
    compressed_program = base64.b64encode(compressed_program)

    return compressed_program.decode("ascii")


def compress_program_post_dump(data: JsonObject, many: bool, **kwargs) -> JsonObject:
    contract_attr_name = (
        "contract_definition" if "contract_definition" in data else "contract_class"
    )
    data[contract_attr_name]["program"] = compress_program(
        program_json=data[contract_attr_name]["program"]
    )

    return data


def decompress_program(data: JsonObject, many: bool, **kwargs) -> JsonObject:
    contract_attr_name = (
        "contract_definition" if "contract_definition" in data else "contract_class"
    )

    compressed_program: str = data[contract_attr_name]["program"]

    with wrap_with_stark_exception(
        code=StarknetErrorCode.INVALID_PROGRAM,
        message="Invalid compressed program.",
        exception_types=[Exception],
    ):
        compressed_program_bytes = base64.b64decode(compressed_program.encode("ascii"))
        decompressed_program = gzip.decompress(data=compressed_program_bytes)
        data[contract_attr_name]["program"] = json.loads(decompressed_program.decode("ascii"))

    return data
