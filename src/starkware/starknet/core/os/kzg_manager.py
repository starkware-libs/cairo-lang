from typing import Callable, List, Optional, Tuple

# Input: polynomial in coefficients representation.
# Output: KZG commitment on the polynomial, split into two Uint192.
CoefficientsToKzgCommitmentCallback = Callable[[List[int]], Tuple[int, int]]


class KzgManager:
    def __init__(
        self,
        polynomial_coefficients_to_kzg_commitment_callback: CoefficientsToKzgCommitmentCallback,
    ):
        # Stores the state diff computed by the OS, in case that KZG commitment is used (since
        # it won't be part of the OS output).
        self._da_segment: Optional[List[int]] = None

        # Callback that computes the KZG commitment of a polynomial in coefficient representation.
        self.polynomial_coefficients_to_kzg_commitment_callback = (
            polynomial_coefficients_to_kzg_commitment_callback
        )

    @property
    def da_segment(self) -> List[int]:
        assert self._da_segment is not None, "DA segment is not initialized."
        return self._da_segment

    def store_da_segment(self, da_segment: List[int]):
        """
        Stores the data-availabilty segment, to be used for computing the KZG commitment
        and published on L1 using a blob transaction.
        """
        assert self._da_segment is None, "DA segment is already initialized."
        self._da_segment = da_segment
