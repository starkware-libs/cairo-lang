from enum import Enum, auto


class StorageConflictStatus(Enum):
    NO_OBJECT = auto()
    SAME_OBJECT = auto()
    DIFFERENT_CLASS = auto()
    DIFFERENT_OBJECT = auto()


class StorageConflictError(Exception):
    """
    Raised when a storage operation fails due to an existing object
    at the target key or identifier, causing a conflict.
    """

    def __init__(self, obj_name: str, existing_obj, expected_obj):
        message = (
            f"Inconsistent attempt to write {obj_name} object. "
            f"Found {existing_obj}, but expected {expected_obj}"
        )
        super().__init__(message)
