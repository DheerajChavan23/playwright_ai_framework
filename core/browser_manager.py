"""DOM Reconnaissance and Accessibility Inspection Manager."""

import asyncio
from typing import Any, Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page

INTERACTIVE_ROLES = {
    "button",
    "link",
    "textbox",
    "combobox",
    "checkbox",
    "menuitem",
    "heading",
}

# Fallback script for Playwright versions where page.accessibility is deprecated/removed
DOM_EXTRACT_SCRIPT = """
() => {
    const targetRoles = new Set(['button', 'link', 'textbox', 'combobox', 'checkbox', 'menuitem', 'heading']);
    const results = [];

    function resolveRole(el) {
        const explicit = el.getAttribute('role');
        if (explicit) return explicit.toLowerCase();
        const tag = el.tagName.toLowerCase();
        if (tag === 'button') return 'button';
        if (tag === 'a' && el.hasAttribute('href')) return 'link';
        if (tag === 'input') {
            const t = (el.getAttribute('type') || 'text').toLowerCase();
            if (['button', 'submit', 'reset'].includes(t)) return 'button';
            if (t === 'checkbox') return 'checkbox';
            return 'textbox';
        }
        if (tag === 'textarea') return 'textbox';
        if (tag === 'select') return 'combobox';
        if (/^h[1-6]$/.test(tag)) return 'heading';
        return null;
    }

    function resolveName(el) {
        return (
            el.getAttribute('aria-label') ||
            el.getAttribute('placeholder') ||
            el.getAttribute('title') ||
            el.getAttribute('name') ||
            el.innerText ||
            el.value ||
            ''
        ).trim();
    }

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let curr = walker.currentNode;
    while (curr) {
        const role = resolveRole(curr);
        if (role && targetRoles.has(role)) {
            const name = resolveName(curr);
            const value = (curr.value || curr.getAttribute('value') || '').trim();
            results.push({ role, name, value });
        }
        curr = walker.nextNode();
    }
    return results;
}
"""


class BrowserManager:
    """Manages headless browser reconnaissance and DOM accessibility tree extraction."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    def _prune_tree(self, node: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Recursively prune accessibility node retaining only interactive elements."""
        if not node:
            return []

        retained: List[Dict[str, str]] = []
        role = (node.get("role") or "").lower()

        if role in INTERACTIVE_ROLES:
            retained.append({
                "role": role,
                "name": (node.get("name") or "").strip(),
                "value": str(node.get("value") or "").strip(),
            })

        for child in node.get("children", []):
            retained.extend(self._prune_tree(child))

        return retained

    async def inspect_page(self, url: str) -> Dict[str, Any]:
        """Launch headless Playwright Chromium, navigate to url, and extract pruned accessibility map.

        Args:
            url: Target web application URL.

        Returns:
            Structured dictionary representing the interactive accessibility map.
        """
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=self.headless)
            page: Page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded")

                # Attempt standard accessibility snapshot if available on page
                snapshot = None
                if hasattr(page, "accessibility"):
                    try:
                        snapshot = await page.accessibility.snapshot()
                    except Exception:
                        snapshot = None

                if snapshot:
                    interactive_elements = self._prune_tree(snapshot)
                else:
                    # Robust fallback using DOM tree walking matching interactive accessibility roles
                    interactive_elements = await page.evaluate(DOM_EXTRACT_SCRIPT)

                title = await page.title()

                return {
                    "url": url,
                    "title": title,
                    "interactive_elements": interactive_elements,
                }
            finally:
                await browser.close()
