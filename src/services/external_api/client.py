import asyncio
import dataclasses
import logging
import os
import ssl
from abc import abstractmethod
from http import HTTPStatus
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Union
from urllib.parse import urljoin

import aiohttp

from services.external_api.has_uri_prefix import HasUriPrefix
from starkware.python.object_utils import generic_object_repr
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass

logger = logging.getLogger(__name__)
JsonObject = Dict[str, Any]
FlexibleJsonObject = Union[str, List[Any], JsonObject]


class JrpcOk(NamedTuple):
    """
    Result object of a successful JRPC query.
    """

    result: Any
    response_id: Any


class JrpcError(NamedTuple):
    """
    Error object of a failed JRPC query.
    """

    code: int
    message: str
    data: Any
    response_id: Any


TJrpcResult = Union[JrpcOk, JrpcError]


def to_jrpc_result_single(response: JsonObject) -> TJrpcResult:
    """
    Parses a single dictionary into a JRPC result.
    """
    return (
        JrpcOk(result=response["result"], response_id=response["id"])
        if "result" in response
        else JrpcError(
            code=response["error"]["code"],
            message=response["error"]["message"],
            data=response["error"].get("data"),
            response_id=response["id"],
        )
    )


def to_jrpc_result(
    response: Union[JsonObject, List[JsonObject]]
) -> Union[TJrpcResult, List[TJrpcResult]]:
    """
    Parses the JSON response of a JRPC request into result(s). If a list of dicts is provided, each
    element in the list is treated as a different result and is parsed separately.
    """
    if isinstance(response, list):
        return [to_jrpc_result_single(response=resp) for resp in response]
    return to_jrpc_result_single(response=response)


class BadRequest(Exception):
    """
    Base class to exceptions raised by ClientBase and its derived classes.
    """

    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def __repr__(self) -> str:
        return f"HTTP error ocurred. Status: {self.status_code}. Text: {self.text}"

    def __str__(self) -> str:
        """
        Overrides base's str method, which returns an empty string (so it falls back to repr).
        """
        return self.__repr__()


@dataclasses.dataclass(frozen=True)
class RetryConfig(ValidatedDataclass):
    """
    A configuration defining the retry protocol for failed HTTP requests.
    """

    # Set n_retries == -1 for unlimited retries (for any error type).
    n_retries: int = 30
    retry_codes: Sequence[HTTPStatus] = (
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    )


class ClientBase(HasUriPrefix):
    """
    A base class for HTTP clients.
    """

    def __init__(
        self,
        url: str,
        certificates_path: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.url = url
        self.ssl_context: Optional[ssl.SSLContext] = None

        self.retry_config = RetryConfig() if retry_config is None else retry_config
        assert (
            self.retry_config.n_retries > 0 or self.retry_config.n_retries == -1
        ), "RetryConfig n_retries parameter value must be either a positive int or equals to -1."

        if certificates_path is not None:
            self.ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
            self.ssl_context.check_hostname = True

            self.ssl_context.load_cert_chain(
                certfile=os.path.join(certificates_path, "user.crt"),
                keyfile=os.path.join(certificates_path, "user.key"),
            )

            # Enforce usage of server certificate authentication.
            self.ssl_context.load_verify_locations(os.path.join(certificates_path, "server.crt"))

    def __repr__(self) -> str:
        return generic_object_repr(obj=self)

    @abstractmethod
    async def _parse_response(
        self,
        request_url: str,
        request_data: Optional[FlexibleJsonObject],
        response: aiohttp.ClientResponse,
    ) -> str:
        """
        Parses the request response and returns a string.
        """

    @abstractmethod
    def _prepare_data(
        self, data: Optional[FlexibleJsonObject]
    ) -> Optional[Union[FlexibleJsonObject, aiohttp.payload.JsonPayload]]:
        """
        Performs conversions of data before sending the request.
        """

    async def _send_request(
        self, send_method: str, uri: str, data: Optional[FlexibleJsonObject] = None
    ) -> str:
        """
        Sends an HTTP request to the target URI.
        Retries upon failure according to the retry configuration:
        1.  In case of unlimited retries (n_retries == -1): always retries upon failure.
        2.  In case of limited retries (n_retries > 0):
            a. Retries n_retries times for specified error types.
            b. Raises an exception immediately for other error types.
        """
        url = urljoin(base=self.url, url=self.format_uri(uri))

        limited_retries = self.retry_config.n_retries > 0
        # n_retries > 0 means limited retries; n_retries == -1 means unlimited retries.
        n_retries_left = self.retry_config.n_retries

        while True:
            n_retries_left -= 1

            try:
                async with aiohttp.TCPConnector(ssl=self.ssl_context) as connector:
                    async with aiohttp.ClientSession(connector=connector) as session:
                        async with session.request(
                            method=send_method, url=url, data=self._prepare_data(data=data)
                        ) as response:
                            return await self._parse_response(
                                request_url=url,
                                request_data=data,
                                response=response,
                            )
            except aiohttp.ClientError as exception:
                error_message = f"Got {type(exception).__name__} while trying to access {url}."

                if limited_retries and n_retries_left == 0:
                    logger.error(error_message, exc_info=True)
                    raise

                logger.debug(f"{error_message}, retrying...")
            except BadRequest as exception:
                error_message = f"Got {type(exception).__name__} while trying to access {url}."

                if limited_retries and (
                    n_retries_left == 0
                    or exception.status_code not in self.retry_config.retry_codes
                ):
                    full_error_message = (
                        f"{error_message} "
                        f"Status code: {exception.status_code}; text: {exception.text}."
                    )
                    logger.error(full_error_message, exc_info=True)
                    raise

                logger.debug(f"{error_message}, retrying...")

            await asyncio.sleep(1)

    async def is_alive(self) -> str:
        return await self._send_request(send_method="GET", uri="/is_alive")


class BaseRestClient(ClientBase):
    async def _parse_response(
        self,
        request_url: str,
        request_data: Optional[FlexibleJsonObject],
        response: aiohttp.ClientResponse,
    ) -> str:
        text = await response.text()
        if response.status != HTTPStatus.OK:
            raise BadRequest(status_code=response.status, text=text)

        return text

    def _prepare_data(
        self, data: Optional[FlexibleJsonObject]
    ) -> Optional[Union[FlexibleJsonObject, aiohttp.payload.JsonPayload]]:
        return data


class BaseJRPCClient(ClientBase):
    async def _parse_response(
        self,
        request_url: str,
        request_data: Optional[FlexibleJsonObject],
        response: aiohttp.ClientResponse,
    ) -> str:
        """
        Parses and returns the result (or results) JSON string of the JRPC query.
        If the single response is an error, or if multiple responses are given and at least one of
        them is an error response, raises a BadRequest exception.
        """
        response_json = await response.json()
        if response_json is None:
            raise BadRequest(
                status_code=response.status,
                text=(
                    f"Response JSON is empty for {response}. Request: {request_url}, "
                    f"json={request_data}."
                ),
            )
        parsed = to_jrpc_result(response=response_json)
        if isinstance(parsed, list):
            result = []
            for single_result in parsed:
                if isinstance(single_result, JrpcError):
                    raise BadRequest(status_code=response.status, text=single_result.message)
                assert isinstance(single_result, JrpcOk)
                result += [single_result.result]
        else:
            if isinstance(parsed, JrpcError):
                raise BadRequest(status_code=response.status, text=parsed.message)
            assert isinstance(parsed, JrpcOk)
            result = parsed.result
        return str(result)

    def _prepare_data(
        self, data: Optional[FlexibleJsonObject]
    ) -> Optional[Union[FlexibleJsonObject, aiohttp.payload.JsonPayload]]:
        if data is None:
            return None
        return aiohttp.payload.JsonPayload(data)
