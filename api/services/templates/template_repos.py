"""
GitHub source repo + live tag for each website template.

Single source of truth (API side) for exporting a generated site's code: it maps
a ``template_id`` to the template's GitHub repo and the tag currently deployed by
``demo-host`` (its ``extends`` list in ``demo-host/nuxt.config.ts``).

⚠️ Keep this in sync with ``demo-host/nuxt.config.ts`` whenever a template tag is
bumped — the export must pin the exact version that renders the live site.
"""
from __future__ import annotations

from typing import Optional

GITHUB_ORG = "DevLeadHunter"

# template_id -> (repo name, live tag). Mirror of demo-host/nuxt.config.ts `extends`.
TEMPLATE_REPOS: dict[str, tuple[str, str]] = {
    "artisan-edito": ("devleadhunter-template-artisan-edito", "v1.2.0"),
    "plumber-signature": ("devleadhunter-template-plumber-signature", "v1.2.0"),
    "plumber-atelier": ("devleadhunter-template-plumber-atelier", "v1.3.0"),
    "plumber-cuivre": ("devleadhunter-template-plumber-cuivre", "v1.2.0"),
    "electrician-lumen": ("devleadhunter-template-electrician-lumen", "v1.2.0"),
    "mechanic-pitlane": ("devleadhunter-template-mechanic-pitlane", "v1.3.0"),
    "dental": ("devleadhunter-template-dental", "v1.1.2"),
    "food": ("devleadhunter-template-food", "v1.0.3"),
    "barber": ("devleadhunter-template-barber", "v1.1.1"),
}


def get_template_repo(template_id: str) -> Optional[tuple[str, str]]:
    """Return ``(repo, tag)`` for a ``template_id``, or ``None`` when unknown."""
    return TEMPLATE_REPOS.get(template_id)


def tarball_url(repo: str, tag: str) -> str:
    """GitHub source tarball URL for a repo at a tag (public repos, no token needed)."""
    return f"https://github.com/{GITHUB_ORG}/{repo}/archive/refs/tags/{tag}.tar.gz"
