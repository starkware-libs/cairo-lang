import base64
import gzip
import json

from services.external_api.client import JsonObject
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import wrap_with_stark_exception


def compress_program(program_json: JsonObject) -> str:
    full_program = json.dumps(program_json)
    compressed_program = gzip.compress(data=full_program.encode("ascii"))
    compressed_program = base64.b64encode(compressed_program)

    return compressed_program.decode("ascii")


def compress_program_post_dump(data: JsonObject, program_attr_name: str) -> JsonObject:
    contract_attr_name = (
        "contract_definition" if "contract_definition" in data else "contract_class"
    )

    data[contract_attr_name][program_attr_name] = compress_program(
        program_json=data[contract_attr_name][program_attr_name]
    )

    return data


def decompress_program(compressed_program: str) -> JsonObject:
    with wrap_with_stark_exception(
        code=StarknetErrorCode.INVALID_PROGRAM,
        message="Invalid compressed program.",
        exception_types=[Exception],
    ):
        compressed_program_bytes = base64.b64decode(compressed_program.encode("ascii"))
        decompressed_program = gzip.decompress(data=compressed_program_bytes)
        return json.loads(decompressed_program.decode("ascii"))


def decompress_program_pre_load(data: JsonObject, program_attr_name: str) -> JsonObject:
    contract_attr_name = (
        "contract_definition" if "contract_definition" in data else "contract_class"
    )

    data[contract_attr_name][program_attr_name] = decompress_program(
        data[contract_attr_name][program_attr_name]
    )

    return data


def rename_contract_address_to_sender_address_pre_load(data: JsonObject) -> JsonObject:
    if "contract_address" in data:
        assert "sender_address" not in data
        data["sender_address"] = data.pop("contract_address")
    return data
