from __future__ import annotations

import os

from .schedule import ROOT


async def html_to_pdf(html: str) -> bytes:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        msg = "Playwright is not installed. Run: python -m pip install -r requirements.txt"
        raise RuntimeError(msg) from exc

    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".ms-playwright"))
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 794, "height": 1123})
        await page.set_content(html, wait_until="networkidle")
        pdf = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
            prefer_css_page_size=True,
        )
        await browser.close()
        return pdf
