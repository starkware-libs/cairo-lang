from typing import List, Tuple


def generate_encoding_felts_test_param() -> Tuple[List[int], List[int]]:
    """
    Generates a list of felt values and their expected encoded u32 limb representation.

    Returns:
        Tuple[List[int], List[int]]: A tuple containing:
            - values: The list of original felt integers
            - expected_out: The corresponding list of encoded u32 integers
    """
    import random

    random.seed(0)
    values: List[int] = [
        random.randrange(2**63) if random.random() < 0.8 else random.randrange(2**250)
        for _ in range(998)
    ] + [2**63, 2**63 - 1]

    expected_out: List[int] = []
    for val in values:
        limbs: List[int] = []
        val_len = 2 if val < 2**63 else 8
        if val_len == 8:
            val += 2**255
        for _ in range(val_len):
            val, res = divmod(val, 2**32)
            limbs.append(res)
        expected_out.extend(limbs[::-1])

    return values, expected_out
