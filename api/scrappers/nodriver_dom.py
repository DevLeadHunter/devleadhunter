"""
DOM helper utilities for nodriver tabs.

Provides Playwright-like selectors on top of nodriver CDP evaluate/select APIs.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NodriverDom:
    """Static helpers for querying and interacting with a nodriver Tab."""

    @staticmethod
    async def evaluate(tab: Any, js: str, *, by_value: bool = True) -> Any:
        """Evaluate JavaScript in the page context."""
        return await tab.evaluate(js, return_by_value=by_value)

    @staticmethod
    def tab_url(tab: Any) -> str:
        """Return the current tab URL."""
        target = getattr(tab, "target", None)
        return (getattr(target, "url", None) or "") if target else ""

    @staticmethod
    async def navigate(tab: Any, url: str, *, sleep_s: float = 0.8) -> None:
        """Navigate the tab to a URL and wait for load."""
        await tab.get(url)
        await tab
        if sleep_s > 0:
            await asyncio.sleep(sleep_s)
        from scrappers.nodriver_browser import activate_tab, resolve_scraper_headless

        if not resolve_scraper_headless():
            await activate_tab(tab)

    @staticmethod
    async def wait_for_selector(tab: Any, selector: str, *, timeout_s: float = 10.0) -> bool:
        """Poll until ``selector`` matches at least one element."""
        deadline = asyncio.get_running_loop().time() + timeout_s
        sel_json = json.dumps(selector)
        while asyncio.get_running_loop().time() < deadline:
            found = await NodriverDom.evaluate(
                tab, f"!!document.querySelector({sel_json})", by_value=True
            )
            if found is True:
                return True
            await asyncio.sleep(0.15)
        return False

    @staticmethod
    async def query_count(tab: Any, selector: str) -> int:
        """Count elements matching ``selector``."""
        sel_json = json.dumps(selector)
        raw = await NodriverDom.evaluate(
            tab, f"document.querySelectorAll({sel_json}).length", by_value=True
        )
        try:
            return int(raw or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    async def inner_text(tab: Any, selector: str, *, index: int = 0) -> Optional[str]:
        """Return trimmed innerText/textContent for the nth matching element."""
        sel_json = json.dumps(selector)
        js = f"""
        (() => {{
            const nodes = document.querySelectorAll({sel_json});
            const el = nodes[{index}];
            if (!el) return null;
            return (el.innerText || el.textContent || '').trim();
        }})()
        """
        raw = await NodriverDom.evaluate(tab, js, by_value=True)
        return raw if isinstance(raw, str) and raw else None

    @staticmethod
    async def inner_html(tab: Any, selector: str, *, index: int = 0) -> Optional[str]:
        """Return innerHTML for the nth matching element."""
        sel_json = json.dumps(selector)
        js = f"""
        (() => {{
            const nodes = document.querySelectorAll({sel_json});
            const el = nodes[{index}];
            return el ? el.innerHTML : null;
        }})()
        """
        raw = await NodriverDom.evaluate(tab, js, by_value=True)
        return raw if isinstance(raw, str) else None

    @staticmethod
    async def all_inner_texts(tab: Any, selector: str) -> list[str]:
        """Return innerText for all elements matching ``selector``."""
        sel_json = json.dumps(selector)
        js = f"""
        (() => {{
            return Array.from(document.querySelectorAll({sel_json}))
                .map(el => (el.innerText || el.textContent || '').trim())
                .filter(Boolean);
        }})()
        """
        raw = await NodriverDom.evaluate(tab, js, by_value=True)
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        return [str(x) for x in NodriverDom._coerce_to_list(raw) if x]

    @staticmethod
    async def get_attribute(
        tab: Any, selector: str, attr: str, *, index: int = 0
    ) -> Optional[str]:
        """Return an attribute value for the nth matching element."""
        sel_json = json.dumps(selector)
        attr_json = json.dumps(attr)
        js = f"""
        (() => {{
            const nodes = document.querySelectorAll({sel_json});
            const el = nodes[{index}];
            if (!el) return null;
            return el.getAttribute({attr_json});
        }})()
        """
        raw = await NodriverDom.evaluate(tab, js, by_value=True)
        return raw if isinstance(raw, str) else None

    @staticmethod
    async def click(tab: Any, selector: str, *, index: int = 0, timeout_s: float = 2.0) -> bool:
        """Click the nth element matching ``selector``."""
        try:
            if index == 0:
                element = await tab.select(selector, timeout=timeout_s)
                if element:
                    await element.click()
                    return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("nodriver select/click failed (%s): %s", selector, exc)

        sel_json = json.dumps(selector)
        js = f"""
        (() => {{
            const nodes = document.querySelectorAll({sel_json});
            const el = nodes[{index}];
            if (!el) return false;
            el.click();
            return true;
        }})()
        """
        raw = await NodriverDom.evaluate(tab, js, by_value=True)
        return raw is True

    @staticmethod
    async def click_first_matching(tab: Any, selectors: list[str]) -> bool:
        """Try each selector until one click succeeds."""
        for selector in selectors:
            if await NodriverDom.click(tab, selector):
                return True
        return False

    @staticmethod
    async def click_by_text(tab: Any, tag: str, text_substring: str) -> bool:
        """Click the first ``tag`` element whose text contains ``text_substring``."""
        tag_json = json.dumps(tag)
        text_json = json.dumps(text_substring.lower())
        js = f"""
        (() => {{
            const needle = {text_json};
            for (const el of document.querySelectorAll({tag_json})) {{
                const t = (el.innerText || el.textContent || el.value || el.getAttribute('aria-label') || '').toLowerCase();
                if (t.includes(needle)) {{ el.click(); return true; }}
            }}
            return false;
        }})()
        """
        raw = await NodriverDom.evaluate(tab, js, by_value=True)
        return raw is True

    @staticmethod
    async def scroll_element(tab: Any, selector: str, delta_y: int) -> None:
        """Scroll an element by ``delta_y`` pixels."""
        sel_json = json.dumps(selector)
        await NodriverDom.evaluate(
            tab,
            f"(() => {{ const el = document.querySelector({sel_json}); if (el) el.scrollBy(0, {delta_y}); }})()",
            by_value=True,
        )

    @staticmethod
    def _coerce_to_list(raw: Any) -> list[Any]:
        """Normalize nodriver evaluate results into a Python list."""
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return []
        deep = getattr(raw, "deep_serialized_value", None)
        if deep is not None:
            items = getattr(deep, "value", None)
            if isinstance(items, list):
                out: list[Any] = []
                for item in items:
                    if isinstance(item, dict) and "value" in item:
                        out.append(item["value"])
                    else:
                        out.append(item)
                return out
        return []

    @staticmethod
    async def evaluate_list(tab: Any, js: str) -> list[Any]:
        """
        Evaluate JS returning an array.

        nodriver often returns ``RemoteObject`` instead of a plain list — we use
        ``JSON.stringify`` and fall back to CDP deep-serialization parsing.
        """
        body = js.strip()
        if body.startswith("(") and body.endswith(")"):
            stringify_js = f"JSON.stringify({body})"
        else:
            stringify_js = f"JSON.stringify(({body}))"
        raw = await NodriverDom.evaluate(tab, stringify_js, by_value=True)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                logger.debug("evaluate_list JSON parse failed")
        return NodriverDom._coerce_to_list(raw)
