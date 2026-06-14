"""Run each registered scraper and print up to 3 prospects (smoke test)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrappers.google_scraper import GoogleScraper
from scrappers.mock_scraper import MockScraper
from scrappers.osm_scraper import OSMScraper
from scrappers.pagesjaunes_scraper import PagesJaunesScraper

CATEGORY = "plombier"
CITY = "Iffendic"
MAX_RESULTS = 3
ONLY_WITHOUT_WEBSITE = True


async def run_one(name: str, scraper, category: str, city: str) -> None:
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    try:
        results = await scraper.scrape(
            category,
            city,
            max_results=MAX_RESULTS,
            only_without_website=ONLY_WITHOUT_WEBSITE,
        )
        print(f"OK — {len(results)} prospect(s)")
        for i, p in enumerate(results[:MAX_RESULTS], 1):
            print(
                f"  {i}. {p.name} | {p.phone or '-'} | {p.city} | "
                f"web={bool(p.website)} | src={p.source}"
            )
        if len(results) < MAX_RESULTS:
            print(f"  (only {len(results)} returned — may be filter: no website)")
    except Exception as exc:
        print(f"FAIL — {exc!r}")
        raise


async def main() -> None:
    scrapers = [
        ("mock", MockScraper()),
        ("pagesjaunes", PagesJaunesScraper()),
        ("google", GoogleScraper()),
        ("osm", OSMScraper()),
    ]
    failures: list[str] = []
    for name, scraper in scrapers:
        try:
            await run_one(name, scraper, CATEGORY, CITY)
        except Exception:
            failures.append(name)
    print(f"\n{'=' * 60}")
    if failures:
        print("FAILED:", ", ".join(failures))
        sys.exit(1)
    print("All scrapers completed without exception")


if __name__ == "__main__":
    asyncio.run(main())
