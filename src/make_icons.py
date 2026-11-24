#!/usr/bin/env python3
"""Render assets/logo.svg to assets/logo-120.png and favicon.ico (headless Chromium + Pillow)."""
import asyncio, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
svg = (ROOT / "assets/logo.svg").read_text()

async def render(size):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
        await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("width=\"64\" height=\"64\"", f"width=\"{size}\" height=\"{size}\"")}</body></html>')
        png = await pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
        await b.close()
        return Image.open(io.BytesIO(png)).convert("RGBA")

async def main():
    big = await render(480)
    big.resize((120, 120), Image.LANCZOS).save(ROOT / "assets/logo-120.png", optimize=True)
    big.resize((256, 256), Image.LANCZOS).save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("ok")

asyncio.run(main())
