"""Run a prospect search from the operator's own machine — the entry point Claude Code runs.

The search itself runs on the API (Bright Data, the public registries, the judge). The one
thing the server cannot do is open Facebook: this CLI plays the part of the desktop app and
reads the waiting Facebook pages with the Chrome of this machine, then hands them over.

Usage:
    python prospect_search_cli.py --trades paysagiste "électricien" --country CH --count 5 --channel email_and_sms
    python prospect_search_cli.py --trades garage --cities Annecy Chambéry --count 3
    python prospect_search_cli.py --follow 12
    python prospect_search_cli.py --resume 12

Output: the search's journal on stderr as it advances; on stdout one JSON line per
candidate worth reading (kept, set aside, to confirm), then a summary line.

Environment:
    DLH_API_BASE / DLH_API_TOKEN — see :mod:`core.operator_api`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from typing import Any

import httpx

from core.operator_api import OperatorApi
from core.win32_asyncio import ensure_proactor_event_loop
from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper

_HTTP_TIMEOUT: float = 60.0
_POLL_SECONDS: float = 4.0
_FINISHED_STATUSES: frozenset[str] = frozenset({"completed", "cancelled", "failed"})
_REPORTED_STATUSES: tuple[str, ...] = ("kept", "set_aside", "to_confirm")
_CHANNELS: tuple[str, ...] = ("email", "sms", "email_and_sms")


class ProspectSearchCli:
    """Starts or follows one search, reading its Facebook pages locally."""

    def __init__(self, api: OperatorApi, *, reads_facebook_pages: bool) -> None:
        """
        Args:
            api: Authenticated access to the API.
            reads_facebook_pages: Whether this machine's Chrome reads the waiting pages.
        """
        self._api = api
        self._reads_facebook_pages = reads_facebook_pages
        self._printed_journal_lines: set[tuple[str, str]] = set()
        self._read_candidate_ids: set[int] = set()

    async def create(self, args: argparse.Namespace) -> int:
        """
        Create a search from the command-line objective.

        Args:
            args: Parsed flags.

        Returns:
            The id of the search, already started by the API.
        """
        response = await self._api.post(
            "/prospect-searches",
            json={
                "trades": args.trades,
                "country": args.country.upper(),
                "cities": args.cities or [],
                "count_per_trade": args.count,
                "channel": args.channel,
                "only_without_website": not args.with_website,
                "minimum_rating": args.minimum_rating,
            },
        )
        if response.status_code == 422:
            raise SystemExit(f"Search refused: {response.json().get('detail')}")
        response.raise_for_status()
        return int(response.json()["id"])

    async def resume(self, search_id: int) -> None:
        """Ask the API to carry on a search that stopped short of its objective."""
        response = await self._api.post(f"/prospect-searches/{search_id}/resume")
        if response.status_code == 404:
            raise SystemExit(f"Search #{search_id} not found.")
        response.raise_for_status()

    async def follow(self, search_id: int) -> dict[str, Any]:
        """
        Follow a search to its end, reading the Facebook pages it waits for.

        Args:
            search_id: The search to follow.

        Returns:
            The search's final detail (totals, journal, candidates).
        """
        while True:
            detail = await self._detail(search_id)
            self._print_new_journal_lines(detail)
            status = str(detail.get("status"))
            if status in _FINISHED_STATUSES:
                return detail
            read_count = await self._read_waiting_pages(search_id) if self._reads_facebook_pages else 0
            if status == "waiting_browser" and read_count == 0:
                # Nothing left this machine can read: the search stays as it is for the desktop app.
                return detail
            await asyncio.sleep(_POLL_SECONDS)

    async def _detail(self, search_id: int) -> dict[str, Any]:
        """The search with its journal and candidates."""
        response = await self._api.get(f"/prospect-searches/{search_id}")
        if response.status_code == 404:
            raise SystemExit(f"Search #{search_id} not found.")
        response.raise_for_status()
        return dict(response.json())

    async def _read_waiting_pages(self, search_id: int) -> int:
        """
        Read each waiting Facebook page once and hand it over.

        A page this machine's browser could not read is not handed over: its candidate stays waiting.

        Returns:
            How many pages were handed over during this pass.
        """
        response = await self._api.get(f"/prospect-searches/{search_id}/browser-tasks")
        response.raise_for_status()
        handed_over = 0
        for task in response.json():
            candidate_id = int(task["candidate_id"])
            if candidate_id in self._read_candidate_ids:
                continue
            self._read_candidate_ids.add(candidate_id)
            print(f"  reading the Facebook page of {task['name']}…", file=sys.stderr, flush=True)
            page = await facebook_enrichment_scraper.read_contact(
                business_name=str(task["name"]),
                facebook_url=str(task["facebook_url"]),
                country=str(task["country"]),
            )
            if page is None:
                print(
                    f"  the browser could not read the Facebook page of {task['name']}: left waiting.",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            posted = await self._api.post(
                f"/prospect-searches/{search_id}/candidates/{candidate_id}/facebook-contact",
                json={
                    "is_readable": page.place_title is not None,
                    "emails": list(page.emails),
                    "phone": page.phone,
                    "website": page.website,
                },
            )
            posted.raise_for_status()
            handed_over += 1
        return handed_over

    def _print_new_journal_lines(self, detail: dict[str, Any]) -> None:
        """Print the journal lines not shown yet, at this machine's local time (the journal is a sliding window)."""
        for line in detail.get("journal") or []:
            written_at, message = str(line["at"]), str(line["message"])
            if (written_at, message) in self._printed_journal_lines:
                continue
            self._printed_journal_lines.add((written_at, message))
            print(f"{self.local_clock_time(written_at)} {message}", file=sys.stderr, flush=True)

    @staticmethod
    def local_clock_time(naive_utc_timestamp: str) -> str:
        """
        Clock time of this machine for a timestamp the API gives as naive UTC.

        Args:
            naive_utc_timestamp: ISO timestamp without timezone (« 2026-10-04T12:34:56 »).

        Returns:
            The time of day, hours to seconds, in the machine's timezone.
        """
        written_at = datetime.fromisoformat(naive_utc_timestamp).replace(tzinfo=UTC)
        return written_at.astimezone().strftime("%H:%M:%S")

    @staticmethod
    def report(detail: dict[str, Any]) -> None:
        """Print one JSON line per candidate worth reading, then the summary of the search."""
        for candidate in detail.get("candidates") or []:
            if candidate.get("status") not in _REPORTED_STATUSES:
                continue
            row = {
                "status": candidate["status"],
                "trade": candidate["trade"],
                "name": candidate["name"],
                "city": candidate.get("city"),
                "phone": candidate.get("phone"),
                "phone_is_mobile": candidate.get("phone_is_mobile"),
                "email": candidate.get("email"),
                "email_proof_level": candidate.get("email_proof_level"),
                "facebook_url": candidate.get("facebook_url"),
                "google_rating": candidate.get("google_rating"),
                "google_reviews_count": candidate.get("google_reviews_count"),
                "owner_name": candidate.get("owner_name"),
                "prospect_id": candidate.get("prospect_id"),
                "detail": candidate.get("reject_detail"),
            }
            print(json.dumps(row, ensure_ascii=False), flush=True)
        summary = {
            "summary": {
                "search_id": detail.get("id"),
                "status": detail.get("status"),
                "request_count": detail.get("request_count"),
                "judge_call_count": detail.get("judge_call_count"),
                "trades": [
                    {
                        key: counts.get(key)
                        for key in (
                            "trade",
                            "wanted",
                            "kept",
                            "set_aside",
                            "to_confirm",
                            "waiting_browser",
                            "rejected",
                            "unverified",
                            "towns",
                            "stop_reason",
                        )
                    }
                    for counts in detail.get("trade_counts") or []
                ],
            }
        }
        print(json.dumps(summary, ensure_ascii=False), flush=True)


def _preflight() -> None:
    """Warn when this machine cannot read Facebook pages (nodriver missing), and provision Chrome."""
    try:
        from scrappers.nodriver_browser import NODRIVER_AVAILABLE

        if not NODRIVER_AVAILABLE:
            print(
                "nodriver is not installed in this Python env — Facebook pages will stay unread.",
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
    """Create, resume or follow the search, then print its report."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        api = OperatorApi(client)
        await api.authenticate()
        cli = ProspectSearchCli(api, reads_facebook_pages=not args.no_browser)

        if args.follow is not None:
            search_id = args.follow
        elif args.resume is not None:
            search_id = args.resume
            await cli.resume(search_id)
        else:
            search_id = await cli.create(args)
        print(f"Search #{search_id} on {api.base_url}", file=sys.stderr, flush=True)

        if not args.no_browser:
            _preflight()
        try:
            detail = await cli.follow(search_id)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print(
                f"Stopped following. The search carries on: --follow {search_id} to come back to it.",
                file=sys.stderr,
                flush=True,
            )
            return 130
        cli.report(detail)
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the objective of a new search, or the id of a search to follow or resume."""
    parser = argparse.ArgumentParser(
        prog="prospect_search_cli", description="Run a prospect search, reading Facebook pages on this machine."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--trades", type=str, nargs="+", metavar="TRADE", help="Trades to search (new search).")
    target.add_argument("--follow", type=int, metavar="ID", help="Follow an existing search.")
    target.add_argument("--resume", type=int, metavar="ID", help="Carry on a stopped search, then follow it.")
    parser.add_argument("--country", type=str, default="FR", help="ISO country of the search (default FR).")
    parser.add_argument("--cities", type=str, nargs="*", metavar="CITY", help="Towns to search (default: chosen).")
    parser.add_argument("--count", type=int, default=5, help="Prospects wanted for each trade (default 5).")
    parser.add_argument("--channel", choices=_CHANNELS, default="email", help="Contact the prospects must allow.")
    parser.add_argument("--with-website", action="store_true", help="Also keep businesses with a working website.")
    parser.add_argument("--minimum-rating", type=float, default=None, help="Google rating floor (e.g. 4.0).")
    parser.add_argument("--no-browser", action="store_true", help="Do not read Facebook pages on this machine.")
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
