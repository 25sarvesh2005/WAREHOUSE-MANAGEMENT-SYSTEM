"""URL validation for server-side webhook requests."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PublicHttpsDestination:
    """Validated host data used to pin a webhook connection to public IPs."""

    hostname: str
    port: int
    addresses: tuple[str, ...]


async def ensure_public_https_url(url: str) -> PublicHttpsDestination:
    """Reject unsafe destinations and return their validated public addresses."""
    parsed = urlsplit(url)
    hostname = parsed.hostname
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("Webhook destinations must be absolute HTTPS URLs without credentials")

    try:
        port = parsed.port or 443
    except ValueError as error:
        raise ValueError("Webhook destination URL has an invalid port") from error
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        if hostname.lower() == "localhost" or hostname.lower().endswith(
            (".localhost", ".local", ".internal")
        ):
            raise ValueError("Webhook destination must resolve to a public address") from None
        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo,
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except OSError as error:
            raise ValueError("Webhook destination hostname could not be resolved") from error
        addresses = {record[4][0] for record in records}
    else:
        addresses = {str(literal_ip)}

    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Webhook destination must resolve only to public addresses")
    return PublicHttpsDestination(hostname=hostname, port=port, addresses=tuple(sorted(addresses)))
