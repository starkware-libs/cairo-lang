import asyncio
import functools
import logging
from typing import List, Tuple, cast

import marshmallow_dataclass

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.security import SecurityError
from starkware.cairo.lang.vm.utils import ResourcesError
from starkware.cairo.lang.vm.vm_exceptions import HintException, VmException, VmExceptionBase
from starkware.starknet.business_logic.execution.execute_entry_point_base import (
    ExecuteEntryPointBase,
)
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    TransactionExecutionContext,
)
from starkware.starknet.business_logic.state.state import CarriedState
from starkware.starknet.business_logic.utils import get_return_values
from starkware.starknet.core.os import os_utils, syscall_utils
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_definition import (
    ContractDefinition,
    ContractEntryPoint,
)
from starkware.starknet.storage.starknet_storage import BusinessLogicStarknetStorage
from starkware.starkware_utils.error_handling import (
    StarkException,
    stark_assert,
    wrap_with_stark_exception,
)
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

logger = logging.getLogger(__name__)


@marshmallow_dataclass.dataclass(frozen=True)
class ExecuteEntryPoint(ValidatedMarshmallowDataclass, ExecuteEntryPointBase):
    """
    Represents a Cairo entry point execution of a StarkNet contract.
    """

    async def execute(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        tx_execution_context: TransactionExecutionContext,
    ) -> CallInfo:
        """
        Executes the selected entry point with the given calldata in the specified contract.
        The information collected from this run (number of steps required, modifications to the
        contract storage, etc.) is saved on the carried state argument.
        Returns a CallInfo object that represents the execution.
        """
        # Pass the running loop before entering to it. It will be used to run asynchronous
        # tasks, such as fetching data from storage.
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        sync_execute = functools.partial(
            self.sync_execute,
            state=state,
            general_config=general_config,
            loop=loop,
            tx_execution_context=tx_execution_context,
        )

        return await loop.run_in_executor(
            executor=None,  # Runs on the default executor.
            func=sync_execute,
        )

    def sync_execute(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> CallInfo:
        """
        Synchronous version of execute_entry_point with a given TransactionExecutionContext object;
        needed since this function also runs inside Cairo hints (when processing internal contract
        calls).
        Should be called from whithin the given loop.
        """
        previous_cairo_usage = state.cairo_usage

        runner, syscall_handler = self._run(
            state=state,
            general_config=general_config,
            loop=loop,
            tx_execution_context=tx_execution_context,
        )

        # Apply modifications to the contract storage.
        state.update_contract_storage(
            contract_address=self.contract_address,
            modifications=syscall_handler.starknet_storage.get_modifications(),
        )

        # Update resources usage (for bouncer).
        state.cairo_usage += runner.get_execution_resources()

        # Build and return call info.
        return self._build_call_info(
            previous_cairo_usage=previous_cairo_usage,
            syscall_handler=syscall_handler,
            retdata=get_return_values(runner=runner),
        )

    def _run(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> Tuple[CairoFunctionRunner, syscall_utils.BusinessLogicSysCallHandler]:
        """
        Runs the selected entry point with the given calldata in the code of the contract deployed
        at self.code_address.
        The execution is done in the context (e.g., storage) of the contract at
        self.contract_address.
        Returns the corresponding CairoFunctionRunner and BusinessLogicSysCallHandler in order to
        retrieve the execution information.
        """
        # Extract pre-fetched contract code from carried state.
        code_contract_state = state.contract_states[self.code_address].state
        code_contract_state.assert_initialized(contract_address=self.code_address)

        # Prepare input for Cairo function runner.
        contract_definition = state.contract_definitions[code_contract_state.contract_hash]
        contract_definition.validate()
        entry_point = self._get_selected_entry_point(contract_definition=contract_definition)

        # Run the specified contract entry point with given calldata.
        with wrap_with_stark_exception(code=StarknetErrorCode.SECURITY_ERROR):
            runner = CairoFunctionRunner(program=contract_definition.program, layout="all")
        os_context = os_utils.prepare_os_context(runner=runner)

        # Extract pre-fetched contract state from carried state.
        pre_run_contract_carried_state = state.contract_states[self.contract_address]
        contract_state = pre_run_contract_carried_state.state
        contract_state.assert_initialized(contract_address=self.contract_address)

        starknet_storage = BusinessLogicStarknetStorage(
            commitment_tree=contract_state.storage_commitment_tree,
            ffc=state.ffc,
            # Note that pending_modifications might be modified during the run as a result of an
            # internal call.
            pending_modifications=pre_run_contract_carried_state.storage_updates.copy(),
            loop=loop,
        )

        initial_syscall_ptr = cast(RelocatableValue, os_context[starknet_abi.SYSCALL_PTR_OFFSET])
        syscall_handler = syscall_utils.BusinessLogicSysCallHandler(
            execute_entry_point_cls=ExecuteEntryPoint,
            tx_execution_context=tx_execution_context,
            state=state,
            caller_address=self.caller_address,
            contract_address=self.contract_address,
            starknet_storage=starknet_storage,
            general_config=general_config,
            initial_syscall_ptr=initial_syscall_ptr,
        )

        # Positional arguments are passed to *args in the 'run_from_entrypoint' function.
        entry_points_args = [
            self.entry_point_selector,
            os_context,
            len(self.calldata),
            self.calldata,
        ]

        try:
            runner.run_from_entrypoint(
                entry_point.offset,
                *entry_points_args,
                hint_locals={
                    "__storage": starknet_storage,
                    "syscall_handler": syscall_handler,
                },
                static_locals={
                    "__find_element_max_size": 2 ** 20,
                    "__squash_dict_max_size": 2 ** 20,
                    "__keccak_max_size": 2 ** 20,
                    "__usort_max_size": 2 ** 20,
                },
                run_resources=tx_execution_context.run_resources,
                verify_secure=True,
            )
        except VmException as exception:
            code = StarknetErrorCode.TRANSACTION_FAILED
            if isinstance(exception.inner_exc, HintException):
                hint_exception = exception.inner_exc

                if isinstance(hint_exception.inner_exc, syscall_utils.HandlerException):
                    stark_exception = hint_exception.inner_exc.stark_exception
                    code = stark_exception.code
                    called_contract_address = hint_exception.inner_exc.called_contract_address
                    message_prefix = (
                        f"Error in the called contract ({hex(called_contract_address)}):\n"
                    )
                    # Override python's traceback and keep the Cairo one of the inner exception.
                    exception.notes = [message_prefix + str(stark_exception.message)]

            if isinstance(exception.inner_exc, ResourcesError):
                code = StarknetErrorCode.OUT_OF_RESOURCES

            raise StarkException(code=code, message=str(exception))
        except VmExceptionBase as exception:
            raise StarkException(code=StarknetErrorCode.TRANSACTION_FAILED, message=str(exception))
        except SecurityError as exception:
            raise StarkException(code=StarknetErrorCode.SECURITY_ERROR, message=str(exception))
        except Exception:
            logger.error("Got an unexpected exception.", exc_info=True)
            raise StarkException(
                code=StarknetErrorCode.UNEXPECTED_FAILURE,
                message="Got an unexpected exception during the execution of the transaction.",
            )

        # Complete handler validations.
        os_utils.validate_and_process_os_context(
            runner=runner,
            syscall_handler=syscall_handler,
            initial_os_context=os_context,
        )

        # When execution starts the stack holds entry_points_args + [ret_fp, ret_pc].
        args_ptr = runner.initial_fp - (len(entry_points_args) + 2)

        # The arguments are touched by the OS and should not be counted as holes, mark them
        # as accessed.
        assert isinstance(args_ptr, RelocatableValue)  # Downcast.
        runner.mark_as_accessed(address=args_ptr, size=len(entry_points_args))

        return runner, syscall_handler

    def _get_selected_entry_point(
        self, contract_definition: ContractDefinition
    ) -> ContractEntryPoint:
        """
        Returns the entry point with selector corresponding with self.entry_point_selector.
        """
        entry_points = contract_definition.entry_points_by_type[self.entry_point_type]
        filtered_entry_points = list(
            filter(
                lambda ep: ep.selector == self.entry_point_selector,
                entry_points,
            )
        )

        if len(filtered_entry_points) == 0 and len(entry_points) > 0:
            first_entry_point = entry_points[0]
            if first_entry_point.selector == starknet_abi.DEFAULT_ENTRY_POINT_SELECTOR:
                return first_entry_point

        selector_formatter = fields.EntryPointSelectorField.format
        address_formatter = fields.L2AddressField.format
        # Non-unique entry points are not possible in a ContractDefinition object, thus
        # len(filtered_entry_points) <= 1.
        stark_assert(
            len(filtered_entry_points) == 1,
            code=StarknetErrorCode.ENTRY_POINT_NOT_FOUND_IN_CONTRACT,
            message=(
                f"Entry point {selector_formatter(self.entry_point_selector)} not found in contract"
                f" with address {address_formatter(self.contract_address)}."
            ),
        )

        (entry_point,) = filtered_entry_points
        return entry_point

    def _build_call_info(
        self,
        previous_cairo_usage: ExecutionResources,
        syscall_handler: syscall_utils.BusinessLogicSysCallHandler,
        retdata: List[int],
    ) -> CallInfo:
        return CallInfo(
            caller_address=self.caller_address,
            contract_address=self.contract_address,
            code_address=self.code_address,
            entry_point_selector=self.entry_point_selector,
            entry_point_type=self.entry_point_type,
            calldata=self.calldata,
            retdata=retdata,
            execution_resources=syscall_handler.state.cairo_usage - previous_cairo_usage,
            events=syscall_handler.events,
            l2_to_l1_messages=syscall_handler.l2_to_l1_messages,
            storage_read_values=syscall_handler.starknet_storage.read_values,
            accessed_storage_keys=syscall_handler.starknet_storage.accessed_addresses,
            internal_calls=syscall_handler.internal_calls,
        )
