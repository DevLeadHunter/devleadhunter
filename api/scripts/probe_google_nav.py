"""Test Google direct place URL navigation."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrappers.google_scraper import GoogleScraper
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task


async def main() -> None:
    s = GoogleScraper()
    tab = await s._nodriver.get_tab()
    url = "https://www.google.com/maps/search/plombier+%C3%A0+Rennes"
    await NodriverDom.navigate(tab, url, sleep_s=2)
    await s._prepare_maps_tab(tab)
    hrefs = await NodriverDom.evaluate_list(
        tab,
        """
        (() => Array.from(document.querySelectorAll("motion.div[role='feed'] a[href*='/maps/place/'], div[role='feed'] a[href*='/maps/place/']"))
            .map(a => a.getAttribute('href'))
            .filter(Boolean)
            .slice(0, 3))()
        """,
    )
    print("hrefs", hrefs)
    for href in hrefs[:3]:
        place_url = GoogleScraper._normalize_maps_href(str(href))
        await NodriverDom.navigate(tab, place_url, sleep_s=1.5)
        await s._prepare_maps_tab(tab)
        details = await s._extract_current_place(tab, default_category="plombier", item_timeout_s=5.0)
        print("details", details)
    await s.close()


if __name__ == "__main__":
    asyncio.run(run_nodriver_task(main, timeout=180))
