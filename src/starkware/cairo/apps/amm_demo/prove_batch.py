import dataclasses
import json
import tempfile
from typing import Any, Dict, List, Tuple

from starkware.cairo.bootloader.generate_fact import get_program_output
from starkware.cairo.sharp.sharp_client import Program, SharpClient


@dataclasses.dataclass
class Balance:
    """
    Represents the balance of each of the two tokens.
    """
    a: int
    b: int


@dataclasses.dataclass
class Account:
    pub_key: int
    balance: Balance


@dataclasses.dataclass
class SwapTransaction:
    account_id: int
    token_a_amount: int


class BatchProver:
    def __init__(
            self, program: Program, balance: Balance, accounts: Dict[int, Account],
            sharp_client: SharpClient):
        """
        Initializes the prover client.
        Parameters:
            program: the compiled AMM program.
            token_a_balance, token_b_balance: AMM pool balances.
            sharp_client: client of the shared proving service.
        """
        self.program = program
        self.balance = balance
        self.accounts = accounts
        self.sharp_client = sharp_client

    def prove_batch(self, transactions: List[SwapTransaction]) -> Tuple[str, str, List[int]]:
        """
        Submits a SHARP job to prove the state transition implied by the provided transactions.
        Returns the job key in the SHARP service, the fact to be registered, and the program output.
        """
        program_input = self.get_program_input(transactions)
        job_key, fact, program_output = self.submit_job(program_input)
        self.update_state(transactions)

        # Sanity check.
        assert program_output[2] == self.balance.a
        assert program_output[3] == self.balance.b

        return job_key, fact, program_output

    def get_program_input(self, transactions: List[SwapTransaction]):
        """
        Constructs the Cairo program input from the provided transactions and the system state.
        """
        program_input: Dict[str, Any] = {
            'token_a_balance': self.balance.a,
            'token_b_balance': self.balance.b,
            'accounts': {},
            'transactions': []
        }

        for index, account in self.accounts.items():
            program_input['accounts'][str(index)] = {
                'public_key': hex(account.pub_key),
                'token_a_balance': account.balance.a,
                'token_b_balance': account.balance.b,
            }

        for tx in transactions:
            program_input['transactions'].append(
                {'account_id': tx.account_id, 'token_a_amount': tx.token_a_amount})

        return program_input

    def submit_job(self, program_input) -> Tuple[str, str, List[int]]:
        """
        Submits a SHARP job to prove the state transition implied by the provided transactions.
        Returns the job id in the SHARP service, the fact to be registered, and the program output.
        """
        with tempfile.NamedTemporaryFile(mode='w') as program_input_file:
            json.dump(
                program_input, program_input_file, indent=4, sort_keys=True)
            program_input_file.flush()
            cairo_pie = self.sharp_client.run_program(
                program=self.program, program_input_path=program_input_file.name)
            job_key = self.sharp_client.submit_cairo_pie(cairo_pie=cairo_pie)

            fact = self.sharp_client.get_fact(cairo_pie)
            output = get_program_output(cairo_pie)

        return job_key, fact, output

    def update_state(self, transactions: List[SwapTransaction]):
        for tx in transactions:
            a = tx.token_a_amount
            b = (self.balance.b * a) // (self.balance.a + a)
            self.balance.a += a
            self.balance.b -= b
            self.accounts[tx.account_id].balance.a -= a
            self.accounts[tx.account_id].balance.b += b
