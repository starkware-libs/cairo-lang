from starkware.cairo.stark_verifier.air.stark_test_utils import PROOF_FILE, run_test


def test_stark():
    run_test(proof_file=PROOF_FILE, layout="starknet_with_keccak")
