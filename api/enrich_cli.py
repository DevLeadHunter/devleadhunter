"""Enrich prospects from the operator's own machine — the entry point Claude Code runs.

Google and Facebook block datacenter IPs, so the browser-driven scraping must leave from a
residential connection. This CLI does exactly what the desktop app does, without its window: it
scrapes each prospect with the same pipeline as the sidecar (``enrichment_scraper.enrich``), then
POSTs the result to the remote API for persistence. Selecting prospects and persisting the result
go through the API (authenticated with the operator's token); only the scraping runs locally.

Usage:
    python enrich_cli.py --prospect 123 [456 ...]
    python enrich_cli.py --name "Hell's Cantina"
    python enrich_cli.py --missing-photos [--limit 10]
    python enrich_cli.py --all [--limit 10]
    python enrich_cli.py --prospect 123 --dry-run

Environment:
    DLH_API_BASE   API base URL (default: https://api.devleadhunter.dibodev.fr).
    DLH_API_TOKEN  Bearer JWT of the operator's account. Optional: when unset, the CLI logs in
                   with ADMIN_EMAIL / ADMIN_PASSWORD from the .env and mints a fresh token itself,
                   so no token ever has to be pasted by hand.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict

import httpx

from core.config import settings
from core.win32_asyncio import ensure_proactor_event_loop
from scrappers.enrichment_scraper import EnrichmentData, enrichment_scraper

_DEFAULT_API_BASE = "https://api.devleadhunter.dibodev.fr"
_API_PREFIX = "/api/v1"
_HTTP_TIMEOUT = 60.0

# Resolved once per run by ``_ensure_authenticated`` and read by ``_auth_headers``.
_access_token: str | None = None


def _api_base() -> str:
    """Return the API base URL, from ``DLH_API_BASE`` or the production default."""
    return (os.environ.get("DLH_API_BASE") or _DEFAULT_API_BASE).rstrip("/")


async def _ensure_authenticated(client: httpx.AsyncClient) -> None:
    """Resolve the operator's Bearer token once, before any authenticated call.

    Prefers ``DLH_API_TOKEN`` when set (handy to force a specific token or another
    account while debugging); otherwise logs in with the operator credentials already
    present in the ``.env`` (``ADMIN_EMAIL`` / ``ADMIN_PASSWORD``) and mints a fresh
    token, so the run never needs a hand-pasted token.
    """
    global _access_token

    env_token = (os.environ.get("DLH_API_TOKEN") or "").strip()
    if env_token:
        _access_token = env_token
        return

    email = (settings.admin_email or "").strip()
    password = settings.admin_password or ""
    if not email or not password:
        raise SystemExit("No DLH_API_TOKEN and no ADMIN_EMAIL / ADMIN_PASSWORD in the .env — cannot authenticate.")

    response = await client.post(
        f"{_api_base()}{_API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    if response.status_code == 401:
        raise SystemExit(f"Login rejected for {email} — check ADMIN_PASSWORD in the .env.")
    response.raise_for_status()

    token = str(response.json().get("access_token") or "").strip()
    if not token:
        raise SystemExit("Login succeeded but the API returned no access_token.")
    _access_token = token


def _auth_headers() -> dict[str, str]:
    """Return the Bearer auth header resolved by ``_ensure_authenticated``."""
    if not _access_token:
        raise SystemExit("Not authenticated — _ensure_authenticated must run before any API call.")
    return {"Authorization": f"Bearer {_access_token}"}


async def _list_prospects(client: httpx.AsyncClient) -> list[dict[str, object]]:
    """Return every prospect the operator owns."""
    response = await client.get(f"{_api_base()}{_API_PREFIX}/prospects", headers=_auth_headers())
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


async def _enrichment_photos(client: httpx.AsyncClient, prospect_id: int) -> list[str] | None:
    """Return a prospect's enrichment photos, or ``None`` when it has no enrichment record yet."""
    response = await client.get(
        f"{_api_base()}{_API_PREFIX}/prospects/{prospect_id}/enrichment", headers=_auth_headers()
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    photos = response.json().get("photos")
    return photos if isinstance(photos, list) else []


def _name_matches(prospect: dict[str, object], needle: str) -> bool:
    """True when the prospect's name contains ``needle`` (case-insensitive)."""
    return needle.strip().lower() in str(prospect.get("name") or "").lower()


async def _select_targets(client: httpx.AsyncClient, args: argparse.Namespace) -> list[dict[str, object]]:
    """Resolve the CLI selection flags into the list of prospects to enrich."""
    if args.prospect:
        wanted = set(args.prospect)
        targets = [p for p in await _list_prospects(client) if int(p.get("id", 0)) in wanted]
        for missing in wanted - {int(p["id"]) for p in targets}:
            print(json.dumps({"prospect_id": missing, "status": "not_found"}), flush=True)
        return targets

    if args.name:
        matches = [p for p in await _list_prospects(client) if _name_matches(p, args.name)]
        if len(matches) > 1:
            listed = ", ".join(f"#{p['id']} {p.get('name')}" for p in matches)
            raise SystemExit(f"« {args.name} » matches several prospects: {listed}. Use --prospect <id>.")
        return matches

    prospects = await _list_prospects(client)
    if args.missing_photos:
        prospects = [p for p in prospects if not await _enrichment_photos(client, int(p["id"]))]
    if args.limit is not None:
        prospects = prospects[: args.limit]
    return prospects


async def _scrape(prospect: dict[str, object]) -> EnrichmentData:
    """Scrape a prospect's full enrichment locally (residential IP), like the sidecar."""
    return await enrichment_scraper.enrich(
        business_name=str(prospect.get("name") or ""),
        city=str(prospect["city"]) if prospect.get("city") else None,
        google_maps_url=str(prospect["google_maps_url"]) if prospect.get("google_maps_url") else None,
        facebook_url=str(prospect["facebook_url"]) if prospect.get("facebook_url") else None,
    )


def _is_meaningful(data: EnrichmentData) -> bool:
    """True when the scrape found something — so a blocked/empty run never overwrites good data.

    An email counts on its own (a Facebook page may yield only a contact email); this mirrors the
    server-side ``EnrichmentService._facebook_scrape_is_empty`` guard, which already counts emails.
    """
    return bool(
        data.photos or data.reviews or data.opening_hours or data.description or data.rating is not None or data.emails
    )


async def _persist(client: httpx.AsyncClient, prospect_id: int, data: EnrichmentData) -> str:
    """Post the scraped data to the API for persistence; return the resulting enrichment status."""
    response = await client.post(
        f"{_api_base()}{_API_PREFIX}/prospects/{prospect_id}/enrichment/run",
        headers=_auth_headers(),
        json=asdict(data),
    )
    response.raise_for_status()
    return str(response.json().get("status") or "unknown")


async def _enrich_one(client: httpx.AsyncClient, prospect: dict[str, object]) -> dict[str, object]:
    """Scrape then persist a single prospect, returning a result row for the report."""
    prospect_id = int(prospect["id"])
    name = str(prospect.get("name") or "")
    try:
        data = await _scrape(prospect)
    except Exception as exc:
        return {"prospect_id": prospect_id, "name": name, "status": "scrape_failed", "error": str(exc)}

    if not _is_meaningful(data):
        return {"prospect_id": prospect_id, "name": name, "status": "empty", "photos": 0}

    try:
        persisted_status = await _persist(client, prospect_id, data)
    except Exception as exc:
        return {"prospect_id": prospect_id, "name": name, "status": "persist_failed", "error": str(exc)}

    return {"prospect_id": prospect_id, "name": name, "status": persisted_status, "photos": len(data.photos)}


async def _cleanup() -> None:
    """Close any throwaway Chrome the run left open (mirrors the sidecar's hygiene)."""
    try:
        from scrappers.email_scraper import email_scraper

        if email_scraper.browser:
            await email_scraper.close()
    except Exception:
        pass
    try:
        from scrappers.google_scraper import close_maps_suggestion_session

        await close_maps_suggestion_session()
    except Exception:
        pass


def _preflight() -> None:
    """Warn when the local env cannot actually scrape (nodriver missing), and provision Chrome."""
    try:
        from scrappers.nodriver_browser import NODRIVER_AVAILABLE

        if not NODRIVER_AVAILABLE:
            print(
                "nodriver is not installed in this Python env — Google/Facebook scraping will be "
                "skipped. Install the api requirements first.",
                file=sys.stderr,
                flush=True,
            )
    except Exception:
        pass
    try:
        from scrappers.chrome_provisioning import ensure_chrome

        ensure_chrome()
    except Exception as exc:
        print(f"Chrome provisioning skipped ({exc}); relying on system Chrome.", file=sys.stderr, flush=True)


async def _run(args: argparse.Namespace) -> int:
    """Select, scrape and persist; stream one JSON line per prospect plus a final summary."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        await _ensure_authenticated(client)
        targets = await _select_targets(client, args)

        if not targets:
            print(json.dumps({"summary": {"total": 0, "message": "no matching prospect"}}), flush=True)
            return 0

        if args.dry_run:
            for prospect in targets:
                row = {"prospect_id": int(prospect["id"]), "name": prospect.get("name"), "status": "dry_run"}
                print(json.dumps(row, ensure_ascii=False), flush=True)
            print(json.dumps({"summary": {"total": len(targets), "dry_run": True}}), flush=True)
            return 0

        _preflight()
        results: list[dict[str, object]] = []
        try:
            for index, prospect in enumerate(targets, start=1):
                print(
                    f"[{index}/{len(targets)}] enriching {prospect.get('name')} (#{prospect.get('id')})…",
                    file=sys.stderr,
                    flush=True,
                )
                result = await _enrich_one(client, prospect)
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
        finally:
            await _cleanup()

        completed = sum(1 for row in results if row.get("status") == "completed")
        summary = {"summary": {"total": len(results), "completed": completed, "failed": len(results) - completed}}
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the CLI selection flags (exactly one selector is required)."""
    parser = argparse.ArgumentParser(prog="enrich_cli", description="Enrich prospects locally (residential IP).")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--prospect", type=int, nargs="+", metavar="ID", help="Enrich these prospect ids.")
    selection.add_argument("--name", type=str, help="Enrich the single prospect whose name contains this text.")
    selection.add_argument("--missing-photos", action="store_true", help="Enrich every prospect with no photos.")
    selection.add_argument("--all", action="store_true", dest="all_prospects", help="Enrich every prospect.")
    parser.add_argument("--limit", type=int, default=None, help="Cap the count (with --missing-photos / --all).")
    parser.add_argument("--dry-run", action="store_true", help="List the targets without scraping.")
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: set the Windows event-loop policy, then run the async pipeline."""
    args = _parse_args(sys.argv[1:])
    ensure_proactor_event_loop()
    try:
        exit_code = asyncio.run(_run(args))
    except httpx.HTTPStatusError as exc:
        raise SystemExit(f"API error {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except httpx.RequestError as exc:
        raise SystemExit(f"Cannot reach the API ({exc}).") from exc
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
