"""Render docs/linkedin/carousel.html to one PNG per slide (1080x1350, LinkedIn carousel).

    python docs/linkedin/render.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
OUT = HERE / "slides"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("slide_*.png"):
        old.unlink()
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page.goto(HERE.joinpath("carousel.html").as_uri(), wait_until="networkidle")
        slides = page.locator(".slide")
        for i in range(slides.count()):
            slides.nth(i).screenshot(path=OUT / f"slide_{i + 1}.png")
        b.close()
    print(f"wrote {len(list(OUT.glob('slide_*.png')))} slides -> {OUT}")


if __name__ == "__main__":
    main()
