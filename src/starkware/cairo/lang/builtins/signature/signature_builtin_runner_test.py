import dataclasses
from types import SimpleNamespace
from typing import Optional

import pytest

from starkware.cairo.lang.builtins.builtin_runner_test_utils import compile_and_run
from starkware.cairo.lang.vm.vm import VmException
from starkware.python.test_utils import maybe_raises


@dataclasses.dataclass
class SignatureCodeSections:
    """
    Code sections relevant for using the signature builtin.
    See code snippet structure below.
    """
    hint: str
    write_pubkey: str
    write_msg: str


@dataclasses.dataclass
class SignatureExample:
    code_sections: SignatureCodeSections
    # Error message received by running the example code, in case there is any.
    error_msg: Optional[str]


# Constants used for creating a code snippet using the signature builtin.
# See signature_builtin_runner_test.py.
SIG_PTR = 'ecdsa_ptr'
formats = SimpleNamespace(
    hint_code_format='%{{ ecdsa_builtin.add_signature({addr}, {signature}) %}}',
    pubkey_code_format=f'assert [{SIG_PTR} + SignatureBuiltin.pub_key] = {{pubkey}}',
    msg_code_format=f'assert [{SIG_PTR} + SignatureBuiltin.message] = {{msg}}',
)

# The address is used inside a hint.
VALID_ADDR = f'ids.{SIG_PTR}'
VALID_SIG = (
    3086480810278599376317923499561306189851900463386393948998357832163236918254,
    598673427589502599949712887611119751108407514580626464031881322743364689811)
constants = SimpleNamespace(
    valid_addr=VALID_ADDR,
    invalid_addr=VALID_ADDR + ' + 1',
    valid_sig=VALID_SIG,
    invalid_sig=(VALID_SIG[0] + 1, VALID_SIG[1]),
    valid_pubkey=1735102664668487605176656616876767369909409133946409161569774794110049207117,
    valid_msg=2718,
    invalid_pubkey_or_msg=SIG_PTR,
)


class SignatureTest:
    """
    Aggregates test cases for the signature builtin runner.
    A valid test case is added at initialization and further test cases are added based on the
    valid case.
    """

    def __init__(self):
        self.test_cases = {'valid': SignatureExample(
            error_msg=None,
            code_sections=SignatureCodeSections(
                hint=formats.hint_code_format.format(
                    addr=constants.valid_addr, signature=constants.valid_sig),
                write_pubkey=formats.pubkey_code_format.format(
                    pubkey=constants.valid_pubkey),
                write_msg=formats.msg_code_format.format(msg=constants.valid_msg),
            )
        )}

    def add_test_case(self, name: str, error_msg: Optional[str], **code_section_changes):
        """
        Adds a new test case with the given error message, based on the valid case and the given
        changes to it.
        """
        self.test_cases[name] = SignatureExample(
            code_sections=dataclasses.replace(
                self.test_cases['valid'].code_sections, **code_section_changes),
            error_msg=error_msg,
        )

    def get_test_cases(self):
        return self.test_cases


# Signature code snippet structure.
CODE = """
%builtins ecdsa
from starkware.cairo.common.cairo_builtins import SignatureBuiltin

func main(ecdsa_ptr) -> (ecdsa_ptr):
    {hint}
    {write_pubkey}
    {write_msg}
    return(ecdsa_ptr=ecdsa_ptr + SignatureBuiltin.SIZE)
end
"""

test = SignatureTest()
test.add_test_case(
    name='invalid_signature_address',
    error_msg='Signature hint must point to the public key cell, not 2:1.',
    hint=formats.hint_code_format.format(
        addr=constants.invalid_addr, signature=constants.valid_sig),
)

test.add_test_case(
    name='invalid_signature',
    error_msg=(
        r'Signature .* is invalid, with respect to the public key '
        '1735102664668487605176656616876767369909409133946409161569774794110049207117, '
        'and the message hash 2718.'),
    hint=formats.hint_code_format.format(
        addr=constants.valid_addr, signature=constants.invalid_sig),
)

test.add_test_case(
    name='invalid_public_key',
    error_msg='ECDSA builtin: Expected public key at address 2:0 to be an integer. Got: 2:0.',
    write_pubkey=formats.pubkey_code_format.format(pubkey=constants.invalid_pubkey_or_msg),
)

test.add_test_case(
    name='invalid_message',
    error_msg='ECDSA builtin: Expected message hash at address 2:1 to be an integer. Got: 2:0.',
    write_msg=formats.msg_code_format.format(msg=constants.invalid_pubkey_or_msg),
)

test.add_test_case(
    name='missing_hint',
    error_msg=(
        'Signature hint is missing for ECDSA builtin at address 2:0. '
        "Add it using 'ecdsa_builtin.add_signature'."),
    hint='',
)

# Missing public key or message would not cause a runtime error, but would fail the prover.
test.add_test_case(name='missing_public_key', error_msg=None, write_pubkey='')
test.add_test_case(name='missing_message', error_msg=None, write_msg='')

test_cases = test.get_test_cases()


@pytest.mark.parametrize('case', test_cases.values(), ids=test_cases.keys())
def test_validation_rules(case):
    code = CODE.format(**dataclasses.asdict(case.code_sections))
    with maybe_raises(
            expected_exception=VmException, error_message=case.error_msg,
            escape_error_message=False):
        compile_and_run(code)
