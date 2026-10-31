"""The clock a prospect reads: his French overseas department's, else his country's.

Every send slot of a prospect is counted in this zone: his first email, his follow-ups, a re-send, a
re-plan after a network cut, a bounce fallback. A Martinique prospect, French in every other respect,
thus receives his emails between 8 a.m. and 6 p.m. in Fort-de-France, as a Québec prospect receives
his at 8 a.m. in Montréal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.country_profiles import CountryProfiles
from services.french_overseas import FrenchOverseas

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB


def prospect_timezone(prospect: ProspectDB | None) -> str:
    """
    The IANA zone a prospect reads the clock in.

    An unknown or closed country reads as France, like everywhere else in the product.

    Args:
        prospect: The prospect, or ``None`` on a row whose prospect is gone.

    Returns:
        An IANA zone name such as ``America/Martinique`` or ``Europe/Paris``.
    """
    department = FrenchOverseas.of_prospect(prospect)
    if department is not None:
        return department.timezone
    return CountryProfiles.get(prospect.country if prospect is not None else None).timezone
