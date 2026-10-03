"""The opt-out mention smsmode appends to a marketing SMS, and the room it takes in the body.

We never write the mention ourselves: ``body.stop = true`` on the send makes smsmode add it
after our text, in the shape the destination country expects — « STOP » plus the account's
five-digit short code to a French number, an unsubscribe link (``no-sms.eu/…``) to a foreign
one. The mention is billed with the body, so the segment count must reserve its characters.
"""

from __future__ import annotations

from typing import ClassVar

from enums.sms_opt_out_mode import SmsOptOutMode
from services.country_profiles import CountryProfiles
from services.sms.phone_normalizer import PhoneNumberPlans


class SmsOptOutMention:
    """How many characters smsmode's opt-out mention adds after our text, per unsubscribe mechanism.

    The reserves cover the documented mentions with their separator: « STOP 36034 » in France (14 kept,
    as the former « STOP au 36180 »), a ``no-sms.eu/xxxxx`` link abroad.
    """

    # TODO: recalibrate from the body text smsmode acknowledges on the first French and Swiss sends.
    RESERVED_CHARACTERS_BY_MODE: ClassVar[dict[SmsOptOutMode, int]] = {
        SmsOptOutMode.SHORT_CODE: 14,
        SmsOptOutMode.LINK: 25,
    }

    @classmethod
    def mode_for_country(cls, country: str | None) -> SmsOptOutMode:
        """The unsubscribe mechanism of a destination country, the link for a country we have no profile of.

        Args:
            country: ISO 3166-1 alpha-2 code of the destination, ``None`` when the number's country is unknown.

        Returns:
            The mode smsmode applies to that destination.
        """
        profile = CountryProfiles.declared(country) if country else None
        return profile.sms_opt_out if profile is not None else SmsOptOutMode.LINK

    @classmethod
    def reserved_characters_for_country(cls, country: str | None) -> int:
        """Characters to reserve in the body for the mention appended to a number of *country*.

        Args:
            country: ISO code of the destination country, ``None`` when unknown.

        Returns:
            The reserved character count.
        """
        return cls.RESERVED_CHARACTERS_BY_MODE[cls.mode_for_country(country)]

    @classmethod
    def reserved_characters_for_number(cls, to_e164: str) -> int:
        """Characters to reserve in the body for the mention appended to the number *to_e164*.

        Args:
            to_e164: The recipient number in E.164, whose dial code names the destination country.

        Returns:
            The reserved character count.
        """
        return cls.reserved_characters_for_country(PhoneNumberPlans.country_of_e164(to_e164))
