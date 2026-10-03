"""The provider that hosts every generated site, demo or delivered: demo-host is deployed on Vercel.

The address and phone number are those Vercel publishes itself: the address in its privacy policy
(vercel.com/legal/privacy-policy) and the phone number of its designated agent
(vercel.com/legal/dmca-policy). Vercel is certified under the EU-U.S. and Swiss-U.S. Data Privacy
Frameworks, the ground of the transfer to the United States stated in the privacy policy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostingProvider:
    """The identity of a hosting provider, as a legal notice names it (its address on its postal lines)."""

    name: str
    address: str
    phone: str
    phone_e164: str
    website_url: str
    country_name: str


SITE_HOSTING_PROVIDER: HostingProvider = HostingProvider(
    name="Vercel Inc.",
    address="440 N Barranca Avenue #4133\nCovina, CA 91723\nÉtats-Unis",
    phone="+1 559 288 7060",
    phone_e164="+15592887060",
    website_url="https://vercel.com",
    country_name="États-Unis",
)
