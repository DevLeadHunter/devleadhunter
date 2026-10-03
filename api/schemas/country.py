"""Country facts exposed to the dashboard, read from the country profiles."""

from __future__ import annotations

from pydantic import BaseModel

from services.country_profiles import CountryProfile


class CountryProfileResponse(BaseModel):
    """What the dashboard needs to know about a country without duplicating it: the sale drawer
    labels the fiscal identifier, validates the postal code and knows the currency from here."""

    code: str
    label: str
    currency: str
    dial_code: str
    postal_code_pattern: str
    postal_code_example: str
    tax_id_label: str
    tax_id_example: str
    tax_id_required: bool
    sms_prospecting_open: bool

    @classmethod
    def from_profile(cls, profile: CountryProfile) -> CountryProfileResponse:
        """Project a country profile into its public shape.

        Args:
            profile: An enabled country profile.

        Returns:
            The response payload of that country.
        """
        return cls(
            code=profile.code,
            label=profile.label,
            currency=profile.currency,
            dial_code=profile.dial_code,
            postal_code_pattern=profile.postal_code_pattern,
            postal_code_example=profile.postal_code_example,
            tax_id_label=profile.tax_id_label,
            tax_id_example=profile.tax_id_example,
            tax_id_required=profile.tax_id_required,
            sms_prospecting_open=profile.sms_prospecting_open,
        )
