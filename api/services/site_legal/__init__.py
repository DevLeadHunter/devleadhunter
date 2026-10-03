"""
Legal notice and privacy policy of the generated sites, computed when a site is served.

The block is built from what the database knows for sure (the site, its prospect, the trusted
registry match, the sale, the demo's publisher) and from the country profile, then sent next to
the site content: it is never stored in ``content_json``, so a Storyblok publication can update
a contact line but never erase a legal mention.

Public surface:
  - ``site_legal_notice_service`` : the block of one served site.
"""

from services.site_legal.notice_service import site_legal_notice_service

__all__ = ["site_legal_notice_service"]
