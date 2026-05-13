"""
Jarvis V3 — Browser Tools
Web search via DuckDuckGo HTML (httpx), page visits via Playwright, URL opening.
"""

import re
import webbrowser
from urllib.parse import quote_plus, urlparse, parse_qs, unquote as url_unquote
import httpx
from playwright.async_api import async_playwright

_pw = None
_browser = None
_context = None

_DDG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.7,en;q=0.6",
}


async def _get_browser():
    """Return a live browser context, reinitialising if closed or crashed."""
    global _pw, _browser, _context

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
            user_agent=_DDG_HEADERS["User-Agent"],
            no_viewport=True,
        )

    return _context


async def _ddg_links(query: str) -> list[str]:
    """Fetch top result URLs from DuckDuckGo HTML endpoint via httpx."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(
                f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&kl=de-de",
                headers=_DDG_HEADERS,
            )
            html = r.text
    except Exception:
        return []

    links = []
    # DDG HTML result links: class="result__a" href="..."
    # href is either a direct URL or a DDG redirect (/l/?uddg=encoded_url)
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"', html):
        raw = m.group(1)
        if "uddg=" in raw:
            parsed = urlparse(raw if raw.startswith("http") else "https:" + raw)
            uddg = parse_qs(parsed.query).get("uddg", [""])[0]
            url = url_unquote(uddg)
        else:
            url = raw
        if url.startswith("http") and "duckduckgo.com" not in url and url not in links:
            links.append(url)
        if len(links) >= 5:
            break

    return links


async def _ddg_instant(query: str) -> dict | None:
    """Try DuckDuckGo Instant Answer API — returns dict or None if no useful answer."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1",
                headers={"User-Agent": _DDG_HEADERS["User-Agent"]},
            )
            data = r.json()
        abstract = data.get("AbstractText", "").strip()
        if abstract and len(abstract) > 80:
            return {
                "title": data.get("Heading", query),
                "url": data.get("AbstractURL", ""),
                "content": abstract,
            }
    except Exception:
        pass
    return None


def _extract_text(html_text: str) -> str:
    """Clean up extracted page text — collapse whitespace, strip boilerplate."""
    lines = [l.strip() for l in html_text.splitlines()]
    lines = [l for l in lines if l and len(l) > 2]
    return "\n".join(lines)


async def search_and_read(query: str) -> dict:
    """
    Search DuckDuckGo for query, visit the best result page, return content.

    Strategy:
      1. DDG Instant Answer (fast path for factual queries)
      2. DDG HTML via httpx → extract result links
      3. Visit first 3 links via Playwright until one returns usable content
    """
    # Fast path: instant answer
    instant = await _ddg_instant(query)
    if instant:
        return instant

    # Get search result links
    links = await _ddg_links(query)
    if not links:
        return {
            "title": "Keine Ergebnisse",
            "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
            "content": "Es wurden keine Suchergebnisse gefunden.",
        }

    # Visit up to 3 results, return first with usable content
    for url in links[:3]:
        result = await visit(url, max_chars=4000)
        if "error" not in result and len(result.get("content", "")) > 150:
            return result

    return {
        "title": "Keine verwertbaren Inhalte",
        "url": links[0],
        "content": "Die gefundenen Seiten konnten leider nicht ausgelesen werden.",
    }


async def visit(url: str, max_chars: int = 5000) -> dict:
    """Visit a URL and extract main text content via Playwright."""
    try:
        ctx = await _get_browser()
    except Exception as e:
        return {"error": f"Browser konnte nicht gestartet werden: {e}"}

    page = None
    try:
        page = await ctx.new_page()
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        raw = await page.evaluate("""
            () => {
                // Remove noise elements
                ['script','style','nav','footer','header','aside',
                 '[role="banner"]','[role="navigation"]'].forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                const selectors = ['main','article','[role="main"]',
                                   '.content','#content','#main','.main',
                                   '.article','#article','body'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 150)
                        return el.innerText.trim();
                }
                return document.body?.innerText?.trim() || '';
            }
        """)
        title = await page.title()
        content = _extract_text(raw)
        return {"title": title, "url": url, "content": content[:max_chars]}
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
