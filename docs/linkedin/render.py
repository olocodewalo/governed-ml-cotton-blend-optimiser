"""Render the carousel (1080x1350 per slide) and the article cover (1920x1080).

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

        for name, sel, w, h, out in (
                ("cover.html", ".cover", 1920, 1080, "article_cover.png"),
                ("social.html", ".social", 1280, 640, "social_preview.png")):
            page2 = b.new_page()
            page2.set_viewport_size({"width": w, "height": h})
            page2.goto(HERE.joinpath(name).as_uri(), wait_until="networkidle")
            page2.locator(sel).screenshot(path=OUT / out)
        b.close()
    print(f"wrote {len(list(OUT.glob('slide_*.png')))} slides + article_cover.png + social_preview.png -> {OUT}")


if __name__ == "__main__":
    main()
