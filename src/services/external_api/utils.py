from typing import List


def join_routes(route_list: List[str]) -> str:
    """
    Joins a list of routes where the result will start with '/' and between every two routes there
    will be exactly one '/'. The reason why it is implemented and the builtin urljoin isn't being
    used, is that urljoin ignores preceding strings in the path if a leading slash is encountered.
    """
    assert None not in route_list and "" not in route_list
    return "/" + "/".join(s.strip("/") for s in route_list)
