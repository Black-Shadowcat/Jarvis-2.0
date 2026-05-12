"""
Jarvis V2 — Browser Tools
Web search via DuckDuckGo, page visits via Playwright, URL opening.
"""

import re
import webbrowser
import subprocess
from urllib.parse import unquote, parse_qs, urlparse
import httpx
from playwright.async_api import async_playwright

_pw = None
_browser = None
_context = None


async def _get_browser():
    """Return a live browser context, reinitialising if closed or crashed."""
    global _pw, _browser, _context

    # Check if existing browser is still alive
    if _browser is not None:
        try:
            if not _browser.is_connected():
                raise RuntimeError("disconnected")
        except Exception:
            _browser = None
            _context = None
            if _pw:
                try:
                    await _pw.stop()
                except Exception:
                    pass
                _pw = None

    if _browser is None:
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
        _context = await _browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            no_viewport=True,
        )

    return _context


async def search_and_read(query: str) -> dict:
    """Search DuckDuckGo, click first result, return page content."""
    try:
        ctx = await _get_browser()
    except Exception as e:
        return {"error": f"Browser konnte nicht gestartet werden: {e}"}

    page = None
    try:
        page = await ctx.new_page()
        await page.goto(f"https://duckduckgo.com/?q={query}", timeout=15000)
        await page.wait_for_timeout(2000)

        first_link = page.locator('[data-testid="result-title-a"]').first
        if await first_link.count() > 0:
            await first_link.click()
            await page.wait_for_timeout(3000)
            title = await page.title()
            url = page.url
            text = await page.evaluate("""
                () => {
                    const selectors = ['main', 'article', '[role="main"]', '.content', '#content', 'body'];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.trim().length > 100)
                            return el.innerText.trim();
                    }
                    return document.body?.innerText?.trim() || '';
                }
            """)
            return {"title": title, "url": url, "content": text[:3000]}
        else:
            return {"title": "Keine Ergebnisse", "url": f"https://duckduckgo.com/?q={query}", "content": "Keine Ergebnisse gefunden."}
    except Exception as e:
        return {"error": f"Suche fehlgeschlagen: {e}"}
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def visit(url: str, max_chars: int = 5000) -> dict:
    """Visit a URL and extract main text content."""
    try:
        ctx = await _get_browser()
    except Exception as e:
        return {"error": f"Browser konnte nicht gestartet werden: {e}"}

    page = None
    try:
        page = await ctx.new_page()
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        text = await page.evaluate("""
            () => {
                const selectors = ['main', 'article', '[role="main"]', '.content', '#content', 'body'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 100)
                        return el.innerText.trim();
                }
                return document.body?.innerText?.trim() || '';
            }
        """)
        title = await page.title()
        return {"title": title, "url": url, "content": text[:max_chars]}
    except Exception as e:
        return {"error": str(e), "url": url}
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def fetch_news() -> str:
    """Fetch current world news from worldmonitor.app."""
    try:
        ctx = await _get_browser()
    except Exception as e:
        return f"Browser konnte nicht gestartet werden: {e}"

    page = None
    try:
        page = await ctx.new_page()
        await page.goto("https://www.worldmonitor.app/", timeout=20000)
        await page.wait_for_timeout(6000)
        text = await page.evaluate("() => document.body.innerText")
        return f"World Monitor Nachrichten:\n{text[:4000]}"
    except Exception as e:
        return f"News konnten nicht geladen werden: {e}"
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def open_url(url: str):
    """Open URL in the default browser (non-blocking)."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, webbrowser.open, url)
    return {"success": True, "url": url}


async def close():
    global _pw, _browser, _context
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
    if _pw:
        try:
            await _pw.stop()
        except Exception:
            pass
    _browser = None
    _context = None
    _pw = None
