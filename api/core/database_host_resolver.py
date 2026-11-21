"""Fallback to the database host's last known address when the server cannot resolve its name."""

import ipaddress
import logging
import socket
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)

DEFAULT_MYSQL_PORT: int = 3306


class DatabaseHostResolver:
    """Remembers where the database host was last found, and sends new connections there when its name stops resolving."""

    def __init__(self) -> None:
        self._last_known_addresses: dict[str, str] = {}
        self._hosts_on_fallback: set[str] = set()

    def fall_back_to_last_known_address(
        self, dialect: Any, connection_record: Any, connect_args: list[Any], connect_params: dict[str, Any]
    ) -> None:
        """
        SQLAlchemy ``do_connect`` hook: point a new connection at the host's last known address when its name does not resolve.

        Args:
            connect_params: The driver's connection arguments, edited in place.
        """
        host: object = connect_params.get("host")
        if not isinstance(host, str) or not host or self._is_ip_address(host):
            return None
        port: int = int(connect_params.get("port") or DEFAULT_MYSQL_PORT)
        try:
            *_, socket_address = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)[0]
        except socket.gaierror as error:
            last_known_address: str | None = self._last_known_addresses.get(host)
            if last_known_address is None:
                return None
            if host not in self._hosts_on_fallback:
                self._hosts_on_fallback.add(host)
                logger.warning(
                    "Database host %s does not resolve (%s): connecting to its last known address %s",
                    host,
                    error,
                    last_known_address,
                )
            connect_params["host"] = last_known_address
            return None
        address: str = str(socket_address[0])
        self._last_known_addresses[host] = address
        if host in self._hosts_on_fallback:
            self._hosts_on_fallback.discard(host)
            logger.warning("Database host %s resolves again (%s)", host, address)
        return None

    @staticmethod
    def _is_ip_address(host: str) -> bool:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return False
        return True


database_host_resolver = DatabaseHostResolver()
