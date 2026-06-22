"""Capture dashboard screenshots for the demo video using Playwright."""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3000"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)

NAV_LABELS = {
    "dashboard": "Overview",
    "spc": "SPC Monitor",
    "grr": "GR&R Studies",
    "alerts": "Alert Inbox",
    "review": "Review Queue",
    "chat": "AI Copilot",
    "integrations": "Connections",
    "audit": "Audit Trail",
}


async def main():
    scenes = json.loads((Path(__file__).parent / "scenes.json").read_text())
    screenshot_scenes = [s for s in scenes if s["type"] == "screenshot"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
        )
        page = await ctx.new_page()

        print("Loading dashboard...")
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Dismiss welcome guide if present
        dismiss = page.locator('button:has-text("Got it")')
        if await dismiss.count() > 0:
            await dismiss.first.click()
            print("Dismissed welcome guide.")
            await asyncio.sleep(1)

        for scene in screenshot_scenes:
            page_id = scene["page"]
            label = NAV_LABELS.get(page_id, page_id)
            out_path = OUT / f"{scene['id']}.png"

            print(f"  Navigating to {label}...")

            # Handle audit page separately (different route)
            if page_id == "audit":
                await page.goto(f"{BASE_URL}/audit")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else:
                btn = page.locator(f'button:has-text("{label}")').first
                try:
                    await btn.click(timeout=5000)
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"    Sidebar click failed for {label}: {e}")
                    continue

            await page.screenshot(path=str(out_path), full_page=False)
            fsize = out_path.stat().st_size / 1024
            print(f"    Captured: {out_path.name} ({fsize:.0f} KB)")

        await browser.close()
    print(f"\nDone — {len(screenshot_scenes)} screenshots in {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
