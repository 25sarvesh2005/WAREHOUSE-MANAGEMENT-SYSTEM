"""HTTPX transport that connects only to previously validated public IPs."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend
from httpcore._backends.base import AsyncNetworkBackend, AsyncNetworkStream

from common.webhook_url import PublicHttpsDestination


class _PinnedNetworkBackend(AsyncNetworkBackend):
    """Resolve the validated origin hostname to a fixed public IP for TCP."""

    def __init__(self, destination: PublicHttpsDestination) -> None:
        self._hostname = destination.hostname.lower().rstrip(".")
        self._port = destination.port
        self._addresses = destination.addresses
        self._backend = AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> AsyncNetworkStream:
        normalized_host = host.lower().rstrip(".").strip("[]")
        if normalized_host != self._hostname or port != self._port:
            raise OSError("Webhook transport refused a connection outside its validated origin")

        address = self._addresses[0]
        # The DNS result was validated before this transport was created, and
        # this backend prevents httpcore from resolving the hostname again.
        if not ipaddress.ip_address(address).is_global:
            raise OSError("Webhook transport refused a non-public destination")
        return await self._backend.connect_tcp(
            address,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(self, *args: object, **kwargs: object) -> AsyncNetworkStream:
        raise OSError("Unix domain sockets are not valid webhook destinations")

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


class PinnedWebhookTransport(httpx.AsyncHTTPTransport):
    """HTTPX transport with DNS pinning and standard TLS hostname verification."""

    def __init__(self, destination: PublicHttpsDestination) -> None:
        # Initialize HTTPX's response/request adaptation, then provide a
        # connection pool whose TCP backend pins the resolved origin address.
        super().__init__(verify=True, trust_env=False, retries=0)
        self._pool = httpcore.AsyncConnectionPool(
            network_backend=_PinnedNetworkBackend(destination),
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=5.0,
            retries=0,
        )
