import inspect
import json
import os


def load_nearby_contract(name) -> dict:
    """
    Loads a contract json from the directory of the caller module.
    """
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    filename = module.__file__  # type: ignore
    with open(os.path.join(os.path.dirname(filename), f"{name}.json")) as fp:
        return json.load(fp)
