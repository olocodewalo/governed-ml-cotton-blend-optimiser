"""Record the HITL app as an animated GIF for posts and outreach.

    python -m streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
    python docs/demo_gif.py

Writes docs/screenshots/app_demo.gif. A mill manager grasps the screen in five seconds;
the same point takes three paragraphs in text.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "screenshots"
URL = "http://localhost:8501"
WIDTH, HEIGHT = 1100, 780
FRAME_MS = 1800


def _shot(page, name: str) -> Path:
    path = OUT / f"_frame_{name}.png"
    page.screenshot(path=path)
    return path


def capture() -> list[Path]:
    OUT.mkdir(exist_ok=True)
    frames = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(1200)
            frames.append(_shot(page, "1_scenario"))

            page.get_by_text("Run optimiser", exact=True).click()
            page.wait_for_selector("text=Recommended blend", timeout=120_000)
            page.wait_for_timeout(1500)
            frames.append(_shot(page, "2_result"))
            frames.append(_shot(page, "3_result_hold"))      # linger on the headline

            for name, anchor in (("4_blend", "Recommended blend"),
                                 ("5_quality", "Predicted quality"),
                                 ("6_rationale", "Rationale"),
                                 ("7_decision", "Decision")):
                page.get_by_text(anchor, exact=False).first.scroll_into_view_if_needed()
                page.wait_for_timeout(900)
                frames.append(_shot(page, name))
        finally:
            browser.close()
    return frames


def build_gif(frames: list[Path]) -> Path:
    images = [Image.open(f).convert("RGB") for f in frames]
    # quantise to keep the file small enough to post comfortably
    palettes = [im.quantize(colors=128, method=Image.MEDIANCUT) for im in images]
    dst = OUT / "app_demo.gif"
    palettes[0].save(dst, save_all=True, append_images=palettes[1:],
                     duration=FRAME_MS, loop=0, optimize=True)
    for f in frames:
        f.unlink()
    return dst


def main() -> None:
    dst = build_gif(capture())
    print(f"wrote {dst} ({dst.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
