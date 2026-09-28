"""DOM Reconnaissance and Accessibility Inspection Manager."""

import asyncio
import re
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
            el.innerText ||
            el.value ||
            el.getAttribute('placeholder') ||
            el.getAttribute('title') ||
            ''
        ).trim().replace(/\\s+/g, ' ');
    }

    function getRelativeCss(el, tag, id, dataTest, cls) {
        if (dataTest) return `${tag}[data-test='${dataTest}']`;
        if (id && !/\\d{5,}/.test(id)) return `${tag}#${id}`;
        if (cls) {
            const firstCls = cls.split(' ').filter(c => c && !c.includes(':'))[0];
            if (firstCls) return `${tag}.${firstCls}`;
        }
        return tag;
    }

    function getRelativeXPath(el, tag, id, dataTest, name) {
        if (dataTest) return `//${tag}[@data-test='${dataTest}']`;
        if (id && !/\\d{5,}/.test(id)) return `//${tag}[@id='${id}']`;
        if (name && name.length > 1 && name.length < 40) return `//${tag}[contains(text(), '${name.replace(/'/g, "")}')]`;
        return `//${tag}`;
    }

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let curr = walker.currentNode;
    while (curr) {
        const role = resolveRole(curr);
        if (role && targetRoles.has(role)) {
            const tag = curr.tagName.toLowerCase();
            const id = curr.id || '';
            const dataTest = curr.getAttribute('data-test') || curr.getAttribute('data-testid') || '';
            const cls = (curr.className && typeof curr.className === 'string') ? curr.className.trim() : '';
            const name = resolveName(curr);
            const value = (curr.value || curr.getAttribute('value') || '').trim();

            const relCss = getRelativeCss(curr, tag, id, dataTest, cls);
            const relXPath = getRelativeXPath(curr, tag, id, dataTest, name);

            // Container context if inside an identifiable card or container
            const parentItem = curr.closest('.inventory_item, .cart_item, [class*="item"], form, [class*="card"]');
            let containerContext = '';
            if (parentItem) {
                const itemTitle = parentItem.querySelector('[class*="title"], [class*="name"], h1, h2, h3, h4, h5, a');
                if (itemTitle && itemTitle.innerText) {
                    containerContext = itemTitle.innerText.trim();
                }
            }

            const item = {
                role,
                name,
                tag,
                relative_css: relCss,
                relative_xpath: relXPath,
            };
            if (id) item.id = id;
            if (dataTest) item.data_test = dataTest;
            if (value) item.value = value;
            if (containerContext) item.container_context = containerContext;

            results.push(item);
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

    async def _extract_snapshot(self, page: Page) -> Dict[str, Any]:
        """Extract interactive elements, DOM attributes, relative CSS/XPath selectors, and page metadata."""
        try:
            interactive_elements = await page.evaluate(DOM_EXTRACT_SCRIPT)
        except Exception:
            snapshot = None
            if hasattr(page, "accessibility"):
                try:
                    snapshot = await page.accessibility.snapshot()
                except Exception:
                    snapshot = None
            interactive_elements = self._prune_tree(snapshot) if snapshot else []

        title = await page.title()
        return {
            "url": page.url,
            "title": title,
            "interactive_elements": interactive_elements,
        }

    def _scenario_implies_auth(self, scenario: Optional[str]) -> bool:
        """Check if user scenario requests authentication/login flow."""
        if not scenario:
            return False
        pattern = r"\b(log\s*in|sign\s*in|signin|login|auth|authenticate|credentials?|standard_user)\b"
        return bool(re.search(pattern, scenario, re.IGNORECASE))

    def _extract_credentials(
        self,
        scenario: Optional[str] = None,
    ) -> tuple[str, str]:
        """Extract or resolve username and password from scenario or demo defaults."""
        username = "standard_user"
        password = "secret_sauce"

        if scenario:
            if "standard_user" in scenario:
                username = "standard_user"
            elif "problem_user" in scenario:
                username = "problem_user"
            elif "performance_glitch_user" in scenario:
                username = "performance_glitch_user"
            else:
                user_match = re.search(
                    r"(?:user(?:name)?|as)\s+['\"]?([a-zA-Z0-9_\-\.\@]+)['\"]?",
                    scenario,
                    re.IGNORECASE,
                )
                if user_match and user_match.group(1).lower() not in (
                    "with", "and", "the", "to", "a", "an", "cart"
                ):
                    username = user_match.group(1).strip()

            pass_match = re.search(
                r"(?:password|pass)\s+['\"]?([a-zA-Z0-9_\-\.\@!]+)['\"]?",
                scenario,
                re.IGNORECASE,
            )
            if pass_match:
                password = pass_match.group(1).strip()
            elif "secret_sauce" in scenario:
                password = "secret_sauce"

        return username, password

    async def _try_fill_and_submit_login(
        self,
        page: Page,
        username: str,
        password: str,
    ) -> bool:
        """Detect and fill login form on page, then submit."""
        # Detect username field
        user_selectors = [
            "input[data-test='username']",
            "input#user-name",
            "input[name='user-name']",
            "input[name='username']",
            "input[placeholder*='user' i]",
            "input[placeholder*='email' i]",
            "input[type='text']",
            "input[type='email']",
        ]
        user_loc = None
        for sel in user_selectors:
            loc = page.locator(sel)
            try:
                if await loc.count() > 0 and await loc.first.is_visible():
                    user_loc = loc.first
                    break
            except Exception:
                continue

        if not user_loc:
            return False

        # Detect password field
        pass_selectors = [
            "input[data-test='password']",
            "input#password",
            "input[name='password']",
            "input[type='password']",
            "input[placeholder*='pass' i]",
        ]
        pass_loc = None
        for sel in pass_selectors:
            loc = page.locator(sel)
            try:
                if await loc.count() > 0 and await loc.first.is_visible():
                    pass_loc = loc.first
                    break
            except Exception:
                continue

        if not pass_loc:
            return False

        # Detect submit button
        submit_selectors = [
            "input[data-test='login-button']",
            "input#login-button",
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Login')",
            "button:has-text('Log In')",
            "button:has-text('Sign In')",
            "button:has-text('Sign in')",
        ]
        submit_loc = None
        for sel in submit_selectors:
            loc = page.locator(sel)
            try:
                if await loc.count() > 0 and await loc.first.is_visible():
                    submit_loc = loc.first
                    break
            except Exception:
                continue

        if not submit_loc:
            return False

        # Fill credentials and click submit
        try:
            await user_loc.fill(username)
            await pass_loc.fill(password)
            await submit_loc.click()

            # Wait for navigation or content update
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            await page.wait_for_timeout(1000)
            return True
        except Exception:
            return False

    async def inspect_page(
        self,
        url: str,
        scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Launch Playwright Chromium, navigate to url, and extract pruned accessibility map.

        Supports multi-step exploration: if scenario implies authentication, performs login exploration
        to snapshot both the landing page (pre-action) and authenticated dashboard (post-action).

        Args:
            url: Target web application URL.
            scenario: Optional user scenario to guide multi-step exploration.

        Returns:
            Structured dictionary representing the interactive accessibility map.
        """
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=self.headless)
            page: Page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded")
                pre_snapshot = await self._extract_snapshot(page)

                if self._scenario_implies_auth(scenario):
                    username, password = self._extract_credentials(scenario)
                    auth_success = await self._try_fill_and_submit_login(page, username, password)

                    if auth_success and page.url != url:
                        post_snapshot = await self._extract_snapshot(page)
                        return {
                            "url": url,
                            "landing_url": url,
                            "authenticated_url": page.url,
                            "title": post_snapshot["title"],
                            "is_authenticated_flow": True,
                            "screens": [
                                {
                                    "screen_name": "Landing / Login Screen",
                                    "url": url,
                                    "title": pre_snapshot["title"],
                                    "interactive_elements": pre_snapshot["interactive_elements"],
                                },
                                {
                                    "screen_name": "Authenticated Dashboard / Post-Login Screen",
                                    "url": page.url,
                                    "title": post_snapshot["title"],
                                    "interactive_elements": post_snapshot["interactive_elements"],
                                },
                            ],
                            "interactive_elements": post_snapshot["interactive_elements"],
                            "pre_action_snapshot": pre_snapshot,
                            "post_action_snapshot": post_snapshot,
                        }

                # Single screen snapshot
                return {
                    "url": url,
                    "title": pre_snapshot["title"],
                    "interactive_elements": pre_snapshot["interactive_elements"],
                    "screens": [
                        {
                            "screen_name": "Landing Screen",
                            "url": url,
                            "title": pre_snapshot["title"],
                            "interactive_elements": pre_snapshot["interactive_elements"],
                        }
                    ],
                }
            finally:
                await browser.close()
