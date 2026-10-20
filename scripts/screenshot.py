"""Screenshot an Argus page and report what a reviewer would notice: load time, page errors and
horizontal overflow. Needs Playwright's Chromium (`uvx --from playwright playwright install chromium`).

    uvx --from playwright python scripts/screenshot.py /markets shots/markets.png
    uvx --from playwright python scripts/screenshot.py /t/MSFT shots/msft-phone.png --width 390 --dark --full
"""

import argparse
import json
import time

from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser()
p.add_argument("path", help="Page path, e.g. / or /markets or /t/MSFT")
p.add_argument("out", help="PNG file to write")
p.add_argument("--base", default="http://127.0.0.1:8787")
p.add_argument("--width", type=int, default=1400)
p.add_argument("--height", type=int, default=1000)
p.add_argument("--dark", action="store_true")
p.add_argument("--full", action="store_true", help="Whole page, not just the viewport")
p.add_argument("--wait", default="main", help="CSS selector that means the page has rendered")
p.add_argument("--settle", type=float, default=2.0, help="Seconds to wait after it renders (data loading)")
args = p.parse_args()

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": args.width, "height": args.height},
                            color_scheme="dark" if args.dark else "light")
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    t0 = time.perf_counter()
    page.goto(args.base + args.path)  # not "networkidle": the live price stream never goes idle
    page.wait_for_selector(args.wait, timeout=90_000)
    rendered = time.perf_counter() - t0
    page.wait_for_timeout(args.settle * 1000)
    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    page.screenshot(path=args.out, full_page=args.full)
    browser.close()

print(json.dumps({"page": args.path, "file": args.out, "rendered_s": round(rendered, 2),
                  "horizontal_overflow": overflow, "errors": errors}))
