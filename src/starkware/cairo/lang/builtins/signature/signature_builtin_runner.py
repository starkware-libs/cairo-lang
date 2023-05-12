from typing import Any, Dict

from starkware.cairo.lang.builtins.signature.instance_def import (
    CELLS_PER_SIGNATURE,
    INPUT_CELLS_PER_SIGNATURE,
)
from starkware.cairo.lang.vm.builtin_runner import BuiltinVerifier, SimpleBuiltinRunner
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.python.math_utils import safe_div


class SignatureBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, name: str, included: bool, ratio, process_signature, verify_signature):
        """
        'process_signature' is a function that takes signatures as saved in 'signatures' and
        returns a dict representing the signature in the format expected by the component used by
        the runner.
        It may also assert that the signature is valid.
        """
        super().__init__(
            name=name,
            included=included,
            ratio=ratio,
            cells_per_instance=CELLS_PER_SIGNATURE,
            n_input_cells=INPUT_CELLS_PER_SIGNATURE,
        )
        self.process_signature = process_signature
        self.verify_signature = verify_signature

        # A dict of address -> signature.
        self.signatures: Dict = {}

    def add_validation_rules(self, runner):
        def rule(memory, addr):
            # A signature builtin instance consists of a pair of public key and message.
            if addr.offset % CELLS_PER_SIGNATURE == 0 and addr + 1 in memory:
                pubkey_addr = addr
                msg_addr = addr + 1
            elif addr.offset % CELLS_PER_SIGNATURE == 1 and addr - 1 in memory:
                pubkey_addr = addr - 1
                msg_addr = addr
            else:
                return set()

            pubkey = memory[pubkey_addr]
            msg = memory[msg_addr]
            assert isinstance(pubkey, int), (
                f"ECDSA builtin: Expected public key at address {pubkey_addr} to be an integer. "
                f"Got: {pubkey}."
            )
            assert isinstance(msg, int), (
                f"ECDSA builtin: Expected message hash at address {msg_addr} to be an integer. "
                f"Got: {msg}."
            )
            assert pubkey_addr in self.signatures, (
                f"Signature hint is missing for ECDSA builtin at address {pubkey_addr}. "
                "Add it using 'ecdsa_builtin.add_signature'."
            )

            signature = self.signatures[pubkey_addr]
            assert self.verify_signature(pubkey, msg, signature), (
                f"Signature {signature}, is invalid, with respect to the public key {pubkey}, "
                f"and the message hash {msg}."
            )
            return {pubkey_addr, msg_addr}

        runner.vm.add_validation_rule(self.base.segment_index, rule)

    def air_private_input(self, runner) -> Dict[str, Any]:
        res: Dict[int, Any] = {}
        for addr, signature in self.signatures.items():
            addr_offset = addr - self.base
            idx = safe_div(addr_offset, CELLS_PER_SIGNATURE)
            pubkey = runner.vm_memory[addr]
            msg = runner.vm_memory[addr + 1]
            res[idx] = {
                "index": idx,
                "pubkey": hex(pubkey),
                "msg": hex(msg),
                "signature_input": self.process_signature(pubkey, msg, signature),
            }

        return {self.name: sorted(res.values(), key=lambda item: item["index"])}

    def add_signature(self, addr, signature):
        """
        This function should be used in Cairo hints.
        """
        assert isinstance(
            addr, RelocatableValue
        ), f"Expected memory address to be relocatable value. Found: {addr}."
        assert (
            addr.segment_index == self.base.segment_index
        ), f"Signature hint must point to the signature builtin segment, not {addr}."
        assert (
            addr.offset % CELLS_PER_SIGNATURE == 0
        ), f"Signature hint must point to the public key cell, not {addr}."
        self.signatures[addr] = signature

    def get_additional_data(self):
        return [
            [list(RelocatableValue.to_tuple(addr)), signature]
            for addr, signature in sorted(self.signatures.items())
        ]

    def extend_additional_data(self, data, relocate_callback, data_is_trusted=True):
        for addr, signature in data:
            relocated_addr = relocate_callback(RelocatableValue.from_tuple(addr))
            assert relocated_addr.segment_index == self.base.segment_index, (
                f"Error while loading {self.name} builtin additional data: "
                "Signature hint must point to the signature builtin segment. "
                f"Found: {addr} (after relocation: {relocated_addr})."
            )
            self.signatures[relocated_addr] = signature


class SignatureBuiltinVerifier(BuiltinVerifier):
    def __init__(self, included: bool, ratio):
        self.included = included
        self.ratio = ratio

    def expected_stack(self, public_input):
        if not self.included:
            return [], []

        addresses = public_input.memory_segments["signature"]
        max_size = safe_div(public_input.n_steps, self.ratio) * CELLS_PER_SIGNATURE
        assert (
            0
            <= addresses.begin_addr
            <= addresses.stop_ptr
            <= addresses.begin_addr + max_size
            < 2**64
        )
        return [addresses.begin_addr], [addresses.stop_ptr]
