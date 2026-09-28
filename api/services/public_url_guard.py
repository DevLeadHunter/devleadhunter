"""
The fetches of an address typed by someone (a prospect's website, its logo) reach the public internet only.

A website field can hold anything: ``http://localhost:8005/admin``, ``http://169.254.169.254/`` (the metadata
service of a cloud machine), or a domain whose DNS answers a private address. Every host is resolved and each of its
addresses checked before any connection; the connection then goes to the checked address itself, so a DNS answer that
changes in between (rebinding) changes nothing. Redirects pass through the same check, hop after hop, because the
guard is the HTTP client's transport.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Iterable
from typing import ClassVar

import httpx

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

logger = logging.getLogger(__name__)

_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


class NonPublicAddressError(httpx.ConnectError):
    """A fetch refused before connecting: its host is, or resolves to, an address outside the public internet."""


class PublicUrlGuard:
    """Tells a public internet address from a private, local, reserved or cloud-metadata one."""

    # Written out rather than read from ``ipaddress`` flags alone: their coverage changed across Python patch releases.
    BLOCKED_NETWORKS: ClassVar[tuple[IpNetwork, ...]] = tuple(
        ipaddress.ip_network(network)
        for network in (
            "0.0.0.0/8",  # « this network »
            "10.0.0.0/8",  # private
            "100.64.0.0/10",  # carrier-grade NAT
            "127.0.0.0/8",  # loopback
            "169.254.0.0/16",  # link-local, the cloud metadata service (169.254.169.254) included
            "172.16.0.0/12",  # private
            "192.0.0.0/24",  # protocol assignments
            "192.0.2.0/24",  # documentation
            "192.88.99.0/24",  # 6to4 relays
            "192.168.0.0/16",  # private
            "198.18.0.0/15",  # benchmarking
            "198.51.100.0/24",  # documentation
            "203.0.113.0/24",  # documentation
            "224.0.0.0/4",  # multicast
            "240.0.0.0/4",  # reserved, broadcast included
            "::/128",  # unspecified
            "::1/128",  # loopback
            "64:ff9b:1::/48",  # local NAT64
            "100::/64",  # discard
            "2001::/23",  # protocol assignments, Teredo included
            "2001:db8::/32",  # documentation
            "fc00::/7",  # unique local, the cloud metadata service (fd00:ec2::254) included
            "fe80::/10",  # link-local
            "fec0::/10",  # site-local
            "ff00::/8",  # multicast
        )
    )

    @classmethod
    def is_public_address(cls, address: IpAddress) -> bool:
        """
        Whether an address belongs to the public internet.

        An IPv6 address carrying an IPv4 one (``::ffff:127.0.0.1``, 6to4, NAT64) is judged by the address it carries.

        Args:
            address: The address to judge.

        Returns:
            ``False`` for a private, loopback, link-local, multicast, reserved or unspecified address.
        """
        embedded = cls._embedded_ipv4(address)
        if embedded is not None:
            return cls.is_public_address(embedded)
        if any(address in network for network in cls.BLOCKED_NETWORKS if network.version == address.version):
            return False
        return not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )

    @classmethod
    def public_addresses(cls, host: str, resolved: Iterable[str]) -> list[str]:
        """
        The addresses a host resolved to, once every one of them is checked.

        Args:
            host: The host, for the refusal message.
            resolved: The addresses its resolution gave.

        Returns:
            The addresses, IPv4 first, without duplicates.

        Raises:
            NonPublicAddressError: When the host resolved to nothing, or to any address outside the public internet
                (a host answering a public and a private address is refused as a whole).
        """
        addresses: list[IpAddress] = []
        for resolved_address in resolved:
            address = ipaddress.ip_address(resolved_address.split("%", 1)[0])
            if not cls.is_public_address(address):
                logger.warning("Fetch refused: %s resolves to the non-public address %s", host, address)
                raise NonPublicAddressError(f"Adresse non publique refusée : {host} ({address})")
            if address not in addresses:
                addresses.append(address)
        if not addresses:
            raise NonPublicAddressError(f"Adresse introuvable : {host}")
        return [str(address) for address in sorted(addresses, key=lambda address: address.version)]

    @classmethod
    def resolve(cls, host: str, port: int) -> list[str]:
        """
        The addresses of a host: itself when it is an address, else what the DNS answers.

        Args:
            host: A hostname (ASCII, IDNA already applied) or an address.
            port: The port about to be used.

        Returns:
            The addresses, unchecked.

        Raises:
            httpx.ConnectError: When the name cannot be resolved.
        """
        try:
            return [str(ipaddress.ip_address(host))]
        except ValueError:
            pass
        try:
            answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError) as exc:
            raise httpx.ConnectError(f"Nom de domaine introuvable : {host}") from exc
        return [str(answer[4][0]) for answer in answers]

    @classmethod
    def pinned_requests(cls, request: httpx.Request, addresses: list[str]) -> list[httpx.Request]:
        """
        The request aimed at each checked address in turn, still named after its host (``Host``, TLS name).

        Args:
            request: The request as the client built it.
            addresses: The checked addresses of its host.

        Returns:
            One request per address, in the order to try them.
        """
        host = request.url.raw_host.decode("ascii")
        extensions = dict(request.extensions)
        if request.url.scheme == "https":
            extensions["sni_hostname"] = host
        return [
            httpx.Request(
                request.method,
                request.url.copy_with(host=address),
                headers=request.headers,
                stream=request.stream,
                extensions=extensions,
            )
            for address in addresses
        ]

    @staticmethod
    def target(request: httpx.Request) -> tuple[str, int]:
        """The host (ASCII) and the port a request goes to."""
        port = request.url.port or _DEFAULT_PORTS.get(request.url.scheme, 443)
        return request.url.raw_host.decode("ascii"), port

    @staticmethod
    def _embedded_ipv4(address: IpAddress) -> ipaddress.IPv4Address | None:
        """The IPv4 address an IPv6 one carries (mapped, 6to4, NAT64 well-known prefix), or None."""
        if not isinstance(address, ipaddress.IPv6Address):
            return None
        if address.ipv4_mapped is not None:
            return address.ipv4_mapped
        if address.sixtofour is not None:
            return address.sixtofour
        if address in ipaddress.ip_network("64:ff9b::/96"):
            return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
        return None


class PublicOnlyAsyncTransport(httpx.AsyncBaseTransport):
    """An async HTTP transport that only connects to the public internet (see the module docstring)."""

    def __init__(self, inner: httpx.AsyncBaseTransport | None = None) -> None:
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """
        Resolve and check the request's host, then send it to the first checked address that answers.

        Args:
            request: The request to send.

        Returns:
            The response.

        Raises:
            NonPublicAddressError: When the host is, or resolves to, an address outside the public internet.
            httpx.ConnectError: When no checked address accepts the connection.
        """
        host, port = PublicUrlGuard.target(request)
        resolved = await asyncio.to_thread(PublicUrlGuard.resolve, host, port)
        pinned = PublicUrlGuard.pinned_requests(request, PublicUrlGuard.public_addresses(host, resolved))
        for pinned_request in pinned[:-1]:
            try:
                return await self._inner.handle_async_request(pinned_request)
            except httpx.ConnectError:
                continue
        return await self._inner.handle_async_request(pinned[-1])

    async def aclose(self) -> None:
        """Close the connections of the inner transport."""
        await self._inner.aclose()


class PublicOnlyTransport(httpx.BaseTransport):
    """The synchronous twin of :class:`PublicOnlyAsyncTransport`."""

    def __init__(self, inner: httpx.BaseTransport | None = None) -> None:
        self._inner = inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """
        Resolve and check the request's host, then send it to the first checked address that answers.

        Args:
            request: The request to send.

        Returns:
            The response.

        Raises:
            NonPublicAddressError: When the host is, or resolves to, an address outside the public internet.
            httpx.ConnectError: When no checked address accepts the connection.
        """
        host, port = PublicUrlGuard.target(request)
        resolved = PublicUrlGuard.resolve(host, port)
        pinned = PublicUrlGuard.pinned_requests(request, PublicUrlGuard.public_addresses(host, resolved))
        for pinned_request in pinned[:-1]:
            try:
                return self._inner.handle_request(pinned_request)
            except httpx.ConnectError:
                continue
        return self._inner.handle_request(pinned[-1])

    def close(self) -> None:
        """Close the connections of the inner transport."""
        self._inner.close()
