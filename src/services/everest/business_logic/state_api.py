from abc import ABC


class StateProxy(ABC):
    """
    A proxy to the state, exposing the sufficient functionality to run a transaction.
    """
