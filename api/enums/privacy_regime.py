"""The data protection law a generated site's privacy notice follows.

The European Union countries apply the GDPR, Switzerland its revised Federal Act on Data
Protection (nLPD) and Québec its private-sector act as amended by Law 25. The regime is a
fact of the country, read from its profile when the legal page of a site is built: it
decides how the visitor's rights and the person in charge are worded.
"""

from enum import Enum


class PrivacyRegime(str, Enum):
    """The privacy law of a country, as a site's privacy notice cites it."""

    GDPR = "gdpr"
    SWISS_FADP = "swiss_fadp"
    QUEBEC_PRIVATE_SECTOR = "quebec_private_sector"
