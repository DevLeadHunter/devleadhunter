"""
Network outlets — garages and shops working under a network's or a brand's sign.

The owner of such an outlet does not decide alone on a website, and the network often gives it a page
on its own site. The network shows in the listing's name (« Garage Exemple - Motrio »), in the name of
the outlet's Facebook page (« AD-Garage-Exemple »), in the website its listing declares (a page of
motrio.fr), or in a page of the network's site naming the outlet.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from services.decision_maker.normalize import fold

# Networks run by a group or under its label, as their outlets write them in their names.
_NETWORK_NAMES: tuple[str, ...] = (
    "norauto",
    "midas",
    "speedy",
    "feu vert",
    "euromaster",
    "carglass",
    "roady",
    "jardiland",
    "gamm vert",
    "ad expert",
    "ad carrosserie",
    "ad garage",
    "garage ad",
    "bosch car service",
    "motrio",
    "eurorepar",
    "euro repar",
    "top garage",
    "top carrosserie",
    "point s",
    "carter cash",
    "vulco",
    "profil plus",
    "first stop",
    "bestdrive",
    "autobacs",
    "autoprimo",
    "precisium",
    "groupauto",
    "rapid pare brise",
    "france pare brise",
    "mondial pare brise",
)
# Sites where a network or a brand gives each outlet its own page (« www.motrio.fr/shop/… »).
_NETWORK_HOSTS: tuple[str, ...] = (
    "ad.fr",
    "motrio.fr",
    "motrio.com",
    "boschcarservice.fr",
    "boschcarservice.com",
    "eurorepar.fr",
    "top-garage.fr",
    "precisium.fr",
    "autoprimo.com",
    "points.fr",
    "norauto.fr",
    "midas.fr",
    "speedy.fr",
    "feuvert.fr",
    "euromaster.fr",
    "vulco.fr",
    "profilplus.fr",
    "carter-cash.com",
    "renault.fr",
    "peugeot.fr",
    "citroen.fr",
    "dacia.fr",
)
# Parts of a Facebook page's address that are no name: its kind of address, its number.
_FACEBOOK_ADDRESS_WORDS: frozenset[str] = frozenset({"pages", "p", "people", "profile.php"})
_NAME_WORD_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")


class NetworkOutlets:
    """Recognises a network's outlet by its name, its Facebook page or the website its listing declares."""

    @staticmethod
    def names_network(name: str) -> bool:
        """
        Whether a name carries, as whole words, the name of a network (« Garage Exemple - Motrio »).

        Args:
            name: A business name, a listing's title or a page's name.

        Returns:
            True when one of the networks is written in it.
        """
        name_words = f" {_NAME_WORD_SEPARATORS_RE.sub(' ', fold(name)).strip()} "
        return any(f" {network} " in name_words for network in _NETWORK_NAMES)

    @staticmethod
    def is_network_page(url: str) -> bool:
        """
        Whether an address is a page of a network's or a brand's own site (« www.motrio.fr/shop/… »).

        Args:
            url: An address, with or without its scheme.

        Returns:
            True when its host is a network's site or one of its subdomains.
        """
        host = (urlparse(url if "//" in url else f"//{url}").hostname or "").lower().removeprefix("www.")
        return any(host == network_host or host.endswith(f".{network_host}") for network_host in _NETWORK_HOSTS)

    @classmethod
    def facebook_page_names_network(cls, facebook_url: str | None) -> bool:
        """
        Whether the name in a Facebook page's address carries a network (« facebook.com/pages/AD-Garage-Exemple/… »).

        Args:
            facebook_url: The business's Facebook page, if known.

        Returns:
            True when the page's name, its number aside, carries a network.
        """
        if not facebook_url:
            return False
        segments = [unquote(segment) for segment in urlparse(facebook_url).path.split("/") if segment]
        page_name = " ".join(
            segment for segment in segments if segment.lower() not in _FACEBOOK_ADDRESS_WORDS and not segment.isdigit()
        )
        return bool(page_name) and cls.names_network(page_name)
