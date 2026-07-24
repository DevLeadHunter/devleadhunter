"""
Export a generated site's source as a standalone, runnable project.

A generated site has **no per-client codebase**: it is a shared template (a Nuxt
layer, one GitHub repo per template) rendered with the client's ``content_json``
(a flat ``SiteContent``). To do bespoke work by hand after a sale, we rebuild a
self-contained fork of the template with the client's content baked in.

The template repo is already a standalone Nuxt app (its ``.playground`` renders
the root component with a mock ``SiteContent`` from ``content.ts``). So the export
= download the template at its live tag, replace ``content.ts`` with the client's
real content, and zip it. ``npm install && npm run dev`` runs it as-is.

Scope (MVP): ZIP download only, and a pure code-recovery fork — the live site keeps
running on demo-host; this bundle is a working copy. Image URLs stay remote.
"""

from __future__ import annotations

import io
import json
import logging
import tarfile
import zipfile
from typing import Any

import httpx

from models.demo_site import DemoSite
from services.templates.template_repos import get_template_repo, tarball_url

logger = logging.getLogger(__name__)

# content.ts lives at the template repo root; the playground imports `mockSiteContent`
# from it. We overwrite the whole file (some templates have helper code above the export).
_CONTENT_FILE = "content.ts"


def _render_content_ts(content: dict[str, Any]) -> str:
    """Render a ``content.ts`` module exporting the client's ``SiteContent``.

    We emit ``{...} as SiteContent`` (not a typed literal) so any extra keys carried
    in ``content_json`` (e.g. a legacy ``theme``) don't trip excess-property checks.
    """
    body = json.dumps(content, ensure_ascii=False, indent=2)
    return (
        "import type { SiteContent } from './app/types/SiteContent'\n\n"
        "/**\n"
        " * Real client content for this site, injected by the DevLeadHunter export.\n"
        " * This is your working copy — edit it freely for bespoke changes.\n"
        " */\n"
        f"export const mockSiteContent = {body} as SiteContent\n"
    )


def _render_export_readme(demo_site: DemoSite, repo: str, tag: str) -> str:
    """Short README explaining what this bundle is and how to run it."""
    return (
        f"# {demo_site.business_name} — code du site\n\n"
        f"Export du site généré par DevLeadHunter — template `{demo_site.template_id}` "
        f"(`{tag}`, repo `{repo}`).\n\n"
        "C'est une application Nuxt autonome : le contenu réel du client est dans "
        "`content.ts`, tout le design vit dans `app/`.\n\n"
        "## Lancer en local\n\n"
        "```bash\nnpm install\nnpm run dev\n```\n\n"
        "Ouvrez ensuite l'URL affichée. `npm run generate` produit un site statique "
        "déployable partout.\n\n"
        "## Où éditer\n\n"
        "- **Contenu** (textes, photos, services, avis…) : `content.ts`.\n"
        "- **Design & sections** : `app/components/` (le composant racine + `sections/`).\n\n"
        "> Fork de récupération : le site live du client tourne toujours sur DevLeadHunter. "
        "Ce dossier est une copie de travail pour du sur-mesure — à toi de le redéployer.\n"
    )


class SiteExportService:
    """Builds a downloadable, runnable source bundle for a generated demo site."""

    async def build_export(self, demo_site: DemoSite) -> tuple[bytes, str]:
        """
        Build a standalone zip of the site's source with the client content baked in.

        Args:
            demo_site: The generated site to export (must have ``content_json``).

        Returns:
            ``(zip_bytes, filename)``.
        @raises ValueError - Unknown template or missing content (client-facing 400).
        @raises httpx.HTTPError - GitHub tarball download failed (surfaced as 502).
        """
        content: dict[str, Any] | None = demo_site.content_json if isinstance(demo_site.content_json, dict) else None
        if not content:
            raise ValueError("Ce site n'a pas encore de contenu généré — rien à exporter.")

        repo_tag: tuple[str, str] | None = get_template_repo(demo_site.template_id)
        if not repo_tag:
            raise ValueError(f"Template inconnue pour l'export : {demo_site.template_id}")
        repo, tag = repo_tag

        if "businessName" not in content:
            # All live templates render a flat SiteContent; warn but still export best-effort.
            logger.warning("Export: content_json for slug=%s is not a flat SiteContent", demo_site.slug)

        tar_bytes: bytes = await self._download_tarball(repo, tag)
        content_ts: str = _render_content_ts(content)
        readme: str = _render_export_readme(demo_site, repo, tag)
        root: str = f"{demo_site.slug}-site"

        zip_bytes: bytes = self._repackage(
            tar_bytes,
            new_root=root,
            overrides={
                _CONTENT_FILE: content_ts.encode("utf-8"),
                "EXPORT.md": readme.encode("utf-8"),
            },
        )
        return zip_bytes, f"{root}.zip"

    async def _download_tarball(self, repo: str, tag: str) -> bytes:
        """Download the GitHub source tarball for a template at a tag (follows redirects)."""
        url: str = tarball_url(repo, tag)
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _repackage(self, tar_bytes: bytes, *, new_root: str, overrides: dict[str, bytes]) -> bytes:
        """
        Convert a GitHub ``.tar.gz`` into a clean ``.zip`` under a new root folder.

        Files in ``overrides`` (path relative to the repo root) replace the archive's
        version; any override not present in the archive is appended.
        """
        applied: set[str] = set()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    # GitHub wraps everything under a single top dir (e.g. repo-1.2.0/…).
                    parts = member.name.split("/", 1)
                    if len(parts) != 2 or not parts[1]:
                        continue
                    rel_path: str = parts[1]
                    if rel_path in overrides:
                        data = overrides[rel_path]
                        applied.add(rel_path)
                    else:
                        extracted = tar.extractfile(member)
                        if extracted is None:
                            continue
                        data = extracted.read()
                    zf.writestr(f"{new_root}/{rel_path}", data)

                # Append any override that wasn't already in the archive (e.g. EXPORT.md).
                for rel_path, data in overrides.items():
                    if rel_path not in applied:
                        zf.writestr(f"{new_root}/{rel_path}", data)

        return buffer.getvalue()


site_export_service = SiteExportService()
