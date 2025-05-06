import asyncio
import dataclasses
from dataclasses import field
from typing import Any, Dict, Tuple

import marshmallow_dataclass

from starkware.starknet.core.os.deprecated_os_syscall_handler import DeprecatedOsSysCallHandler
from starkware.starknet.core.os.execution_helper import OsExecutionHelper
from starkware.starknet.core.os.kzg_manager import KzgManager
from starkware.starknet.core.os.os_input import OsBlockInput, StarknetOsInput
from starkware.starknet.core.os.os_logger import OptionalSegmentManager
from starkware.starknet.core.os.os_syscall_handler import OsSyscallHandler
from starkware.starknet.definitions.general_config import StarknetOsConfig
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)
from starkware.storage.storage import FactFetchingContext


@dataclasses.dataclass(frozen=True)
class OsGlobalHints(ValidatedDataclass):
    loop: asyncio.AbstractEventLoop
    segments_manager: OptionalSegmentManager
    kzg_manager: KzgManager
    ffc: FactFetchingContext


@marshmallow_dataclass.dataclass(frozen=True)
class OsHintsConfig(ValidatedMarshmallowDataclass):
    dynamic_read_fallback: bool
    debug_mode: bool
    full_output: int
    use_kzg_da: bool
    starknet_os_config: StarknetOsConfig = field(default_factory=StarknetOsConfig)


@dataclasses.dataclass(frozen=True)
class OsHints(ValidatedDataclass):
    os_input: StarknetOsInput
    os_hints_config: OsHintsConfig
    global_hints: OsGlobalHints

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_input": self.os_input.dump(),
            "global_hints": self.global_hints,
            "os_hints_config": self.os_hints_config.dump(),
        }


def get_execution_helper_and_syscall_handlers(
    block_input: OsBlockInput, global_hints: OsGlobalHints, os_hints_config: OsHintsConfig
) -> Tuple[OsExecutionHelper, OsSyscallHandler, DeprecatedOsSysCallHandler]:
    execution_helper = OsExecutionHelper.create(
        block_input=block_input,
        loop=global_hints.loop,
        segments=global_hints.segments_manager,
        kzg_manager=global_hints.kzg_manager,
        ffc=global_hints.ffc,
        debug_mode=os_hints_config.debug_mode,
        dynamic_read_fallback=os_hints_config.dynamic_read_fallback,
    )
    deprecated_syscall_handler = DeprecatedOsSysCallHandler(
        execution_helper=execution_helper, block_info=block_input.block_info
    )
    syscall_handler = OsSyscallHandler(
        execution_helper=execution_helper, block_info=block_input.block_info
    )

    return execution_helper, syscall_handler, deprecated_syscall_handler
