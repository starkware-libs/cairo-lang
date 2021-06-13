import asyncio
import dataclasses
import logging
import os
import ssl
from http import HTTPStatus
from typing import Any, Dict, Optional, Sequence, Union
from urllib.parse import urljoin

import aiohttp

from services.external_api.has_uri_prefix import HasUriPrefix

logger = logging.getLogger(__name__)


class BadRequest(Exception):
    """
    Base class to exceptions raised by BaseClient and its derived classes.
    """

    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def __repr__(self) -> str:
        return f'HTTP error ocurred. Status: {self.status_code}. Text: {self.text}'

    def __str__(self) -> str:
        """
        Overrides base's str method, which returns an empty string (so it falls back to repr).
        """
        return self.__repr__()


@dataclasses.dataclass(frozen=True)
class RetryConfig:
    """
    A configuration defining the retry protocol for failed HTTP requests.
    """

    # Set n_retries == -1 for unlimited retries (for any error type).
    n_retries: int = 30
    retry_codes: Sequence[HTTPStatus] = (
        HTTPStatus.BAD_GATEWAY, HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.GATEWAY_TIMEOUT)


class BaseClient(HasUriPrefix):
    """
    A base class for HTTP clients.
    """

    def __init__(
            self, url: str, certificates_path: Optional[str] = None,
            retry_config: Optional[RetryConfig] = None):
        self.url = url
        self.ssl_context: Optional[ssl.SSLContext] = None

        self.retry_config = RetryConfig() if retry_config is None else retry_config
        assert self.retry_config.n_retries > 0 or self.retry_config.n_retries == -1, \
            'RetryConfig n_retries parameter value must be either a positive int or equals to -1.'

        if certificates_path is not None:
            self.ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
            self.ssl_context.check_hostname = True

            self.ssl_context.load_cert_chain(
                certfile=os.path.join(certificates_path, 'user.crt'),
                keyfile=os.path.join(certificates_path, 'user.key'))

            self.ssl_context.load_verify_locations(os.path.join(certificates_path, 'server.crt'))

    async def _send_request(
            self, send_method: str, uri: str,
            data: Optional[Union[str, Dict[str, Any]]] = None) -> str:
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
                                method=send_method, url=url, data=data) as response:
                            text = await response.text()
                            if response.status != HTTPStatus.OK:
                                raise BadRequest(status_code=response.status, text=text)

                            return text
            except aiohttp.ClientError:
                if limited_retries and n_retries_left == 0:
                    raise

                logger.error('ClientConnectorError, retrying...', exc_info=True)
            except BadRequest as exception:
                if limited_retries and (
                        n_retries_left == 0 or
                        exception.status_code not in self.retry_config.retry_codes):
                    raise

                logger.error(f'BadRequest with code {exception.status_code}, retrying...')

            await asyncio.sleep(1)

    async def is_alive(self) -> str:
        return await self._send_request(send_method='GET', uri='/is_alive')
