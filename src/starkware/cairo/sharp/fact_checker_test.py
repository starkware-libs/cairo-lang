from starkware.cairo.sharp.fact_checker import FactChecker


def test_init():
    """
    Initializes the FactChecker.
    This test is a basic sanity check.
    """
    FactChecker(fact_registry_address='', node_rpc_url='')
