import inspect
import json
from pathlib import Path


def load_nearby_contract(name: str, no_throw=False) -> dict:
    """
    Loads a contract json from the directory of the caller module.
    """
    # Read __file__ off the caller's frame directly; inspect.stack() resolves source info for
    # every frame on the stack (O(stack depth * len(sys.modules))), which dominates service
    # startup time when called at module level during deep import chains.
    frame = inspect.currentframe()
    assert frame is not None and frame.f_back is not None
    filename = frame.f_back.f_globals.get("__file__")
    assert filename is not None
    try:
        path = Path(filename).parent / f"{name}.json"
        return json.load(path.open())
    except Exception as ex:
        if no_throw:
            return {}
        else:
            raise ex
