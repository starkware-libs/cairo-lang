def are_parameters_supported(proof_parameters: dict):
    """
    The stark verifier implemented in Cairo expects a specific set of hash functions and a
    specific field to be used by the prover. Check if proof_parameters match these requirements.
    """
    if proof_parameters["channel_hash"] != "poseidon3":
        return False

    if proof_parameters["commitment_hash"] != "blake256_masked248_lsb":
        return False

    if proof_parameters["field"] != "PrimeField0":
        return False

    if proof_parameters["pow_hash"] != "blake256":
        return False

    if proof_parameters["statement"]["page_hash"] != "pedersen":
        return False

    if proof_parameters["verifier_friendly_commitment_hash"] != "poseidon3":
        return False

    return True
