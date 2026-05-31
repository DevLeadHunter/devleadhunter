"""Probe Google Maps place extraction."""
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
    if hrefs:
        href = hrefs[0]
        await NodriverDom.evaluate(
            tab,
            f"""
            (() => {{
                const links = document.querySelectorAll("motion.div[role='feed'] a[href*='/maps/place/'], div[role='feed'] a[href*='/maps/place/']");
                for (const el of links) {{
                    if (el.getAttribute('href') === {repr(href)}) {{
                        el.removeAttribute('target');
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }})()
            """,
            by_value=True,
        )
        for wait in [1, 2, 3]:
            await asyncio.sleep(1)
            h1 = await NodriverDom.inner_text(tab, "h1")
            h1panel = await NodriverDom.inner_text(tab, "div[role='main'] h1")
            print(f"after {wait}s h1={h1!r} panel={h1panel!r}")
    await s.close()


if __name__ == "__main__":
    asyncio.run(run_nodriver_task(main, timeout=120))
