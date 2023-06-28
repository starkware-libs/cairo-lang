from enum import Enum


class HttpStatusCode(Enum):
    """
    See HTTP status codes in Wikipedia: https://en.wikipedia.org/wiki/List_of_HTTP_status_codes.
    """

    # Success.
    OK = 200

    # Client Errors.
    BAD_REQUEST = 400

    # Server Errors.
    INTERNAL_SERVER_ERROR = 500
