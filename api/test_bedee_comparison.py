"""
Comparison test: auto vs brightdata scrapers for Bedee.

Tests:
- 2 plombiers in Bedee
- 2 electriciens in Bedee

Compares results from both sources and reports differences.
"""
from __future__ import annotations

import asyncio
import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("BRIGHTDATA_API_TOKEN", "8daca9ae-dcd4-4aec-b3f1-c8efb6db7098")

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    stream=sys.stdout,
)
# Suppress noisy sub-loggers
logging.getLogger("nodriver").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

from models.prospect import ProspectCreate


def _fmt(p: ProspectCreate) -> str:
    """Format a prospect for display."""
    parts = [f"  NAME    : {p.name}"]
    if p.phone:
        parts.append(f"  PHONE   : {p.phone}")
    if p.email:
        parts.append(f"  EMAIL   : {p.email}")
    if p.address:
        parts.append(f"  ADDRESS : {p.address}")
    if p.city:
        parts.append(f"  CITY    : {p.city}")
    if p.website:
        parts.append(f"  WEBSITE : {p.website}")
    parts.append(f"  CONF    : {p.confidence}/4")
    return "\n".join(parts)


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def run_auto(category: str, city: str, max_results: int) -> list[ProspectCreate]:
    """Run the AutoScraper."""
    from scrappers.auto_scraper import AutoScraper
    scraper = AutoScraper()
    return await scraper.scrape(category, city, max_results, only_without_website=True)


async def run_brightdata(category: str, city: str, max_results: int) -> list[ProspectCreate]:
    """Run the BrightDataScraper."""
    from scrappers.brightdata_scraper import BrightDataScraper
    scraper = BrightDataScraper()
    return await scraper.scrape(category, city, max_results, only_without_website=True)


async def compare(category: str, city: str, max_results: int = 2) -> None:
    """Run and compare both scrapers for one category + city."""
    _section(f"CATEGORY: {category.upper()} | CITY: {city.upper()} | MAX: {max_results}")

    print(f"\n[AUTO] Running...")
    try:
        auto_results = await run_auto(category, city, max_results)
    except Exception as exc:
        print(f"[AUTO] ERROR: {exc}")
        auto_results = []

    print(f"\n[AUTO] Found {len(auto_results)} prospect(s):")
    for i, p in enumerate(auto_results, 1):
        print(f"\n  --- Auto #{i} ---")
        print(_fmt(p))

    print(f"\n[BRIGHTDATA] Running...")
    try:
        bd_results = await run_brightdata(category, city, max_results)
    except Exception as exc:
        print(f"[BRIGHTDATA] ERROR: {exc}")
        bd_results = []

    print(f"\n[BRIGHTDATA] Found {len(bd_results)} prospect(s):")
    for i, p in enumerate(bd_results, 1):
        print(f"\n  --- BrightData #{i} ---")
        print(_fmt(p))

    # Compare
    print(f"\n--- COMPARISON ({category} / {city}) ---")
    auto_names = {p.name.lower().strip() for p in auto_results}
    bd_names = {p.name.lower().strip() for p in bd_results}
    common = auto_names & bd_names
    only_auto = auto_names - bd_names
    only_bd = bd_names - auto_names

    print(f"  Common prospects      : {len(common)}")
    if common:
        print(f"    {common}")
    print(f"  Only in AUTO          : {len(only_auto)}")
    if only_auto:
        print(f"    {only_auto}")
    print(f"  Only in BRIGHTDATA    : {len(only_bd)}")
    if only_bd:
        print(f"    {only_bd}")

    auto_with_email = sum(1 for p in auto_results if p.email)
    bd_with_email = sum(1 for p in bd_results if p.email)
    print(f"  Auto email coverage   : {auto_with_email}/{len(auto_results)}")
    print(f"  BD   email coverage   : {bd_with_email}/{len(bd_results)}")


async def main() -> None:
    print("[TEST] Bedee comparison: auto vs brightdata")
    print("[TEST] Each scraper fetches 2 plombiers + 2 electriciens\n")

    await compare("plombier", "bedee", max_results=2)
    await compare("electricien", "bedee", max_results=2)

    print(f"\n{'=' * 60}")
    print("  TEST COMPLETE")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    from core.win32_asyncio import ensure_proactor_event_loop
    ensure_proactor_event_loop()
    asyncio.run(main())
