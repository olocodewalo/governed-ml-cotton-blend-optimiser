"""Capture the HITL app screenshots used in the write-up / posts.

    python -m streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
    python docs/shots.py

Writes docs/screenshots/*.png. Needs `pip install playwright && playwright install chromium`.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "screenshots"
URL = "http://localhost:8501"


def _run_button(page):
    return page.get_by_text("Run optimiser", exact=True)


def _review_shots(page) -> None:
    _run_button(page).click()
    page.wait_for_selector("text=Recommended blend", timeout=120_000)
    page.wait_for_timeout(1500)
    page.screenshot(path=OUT / "01_review_screen.png")

    page.get_by_text("Predicted quality", exact=False).first.scroll_into_view_if_needed()
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "02_quality_and_rationale.png")


def _stale_price_shot(page) -> None:
    """Planning date pushed months past the price sheet -> the guard refuses.

    Streamlit's date picker is awkward to drive from a script; the guard itself is
    covered by tests/test_pipeline.py::test_optimisers_refuse_stale_prices, so a
    failure here costs only a screenshot.
    """
    page.reload(wait_until="networkidle")
    date_input = page.locator('[data-testid="stDateInput"] input').first
    date_input.click(force=True)
    page.keyboard.press("Control+a")
    page.keyboard.type("2025/03/01")
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    page.wait_for_timeout(800)
    _run_button(page).click()
    page.wait_for_selector("text=Refusing to optimise", timeout=30_000)
    page.wait_for_timeout(500)
    page.screenshot(path=OUT / "03_stale_price_refused.png",
                    clip={"x": 0, "y": 0, "width": 1500, "height": 420})


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
            page.goto(URL, wait_until="networkidle")
            _review_shots(page)
            try:
                _stale_price_shot(page)
            except Exception as e:
                print(f"[skip] stale-price screenshot: {type(e).__name__}")
        finally:
            browser.close()
    print(f"wrote {len(list(OUT.glob('*.png')))} screenshots -> {OUT}")


if __name__ == "__main__":
    main()
