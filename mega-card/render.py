#!/usr/bin/env python3
"""Render a FUT-style skill card and a 24-spoke radar from a MEGA Assessment report."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
PROFILE_DIR = Path.home() / ".cache" / "mega-card" / "chrome-profile"
WINDOW = "1600,1240"

TRAIT_ROW = re.compile(
    r"^\|\s*(T\d{2})\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$",
    re.M,
)
# The indicator table reuses trait ids; its second column is a kebab-case indicator slug.
INDICATOR_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def parse_traits(text):
    traits = {}
    for m in TRAIT_ROW.finditer(text):
        tid, name = m.group(1), m.group(2)
        if INDICATOR_SLUG.match(name) or tid in traits:
            continue
        traits[tid] = [int(m.group(3)), int(m.group(4)), int(m.group(5))]
    missing = [f"T{i:02d}" for i in range(1, 25) if f"T{i:02d}" not in traits]
    if missing:
        sys.exit(f"Report has no trait rows for: {', '.join(missing)}")
    return traits


def plural(n, one, few, many):
    if n == 1:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def parse_meta(text):
    def num(pattern):
        m = re.search(pattern, text)
        return int(m.group(1)) if m else None

    date = re.search(r"\*\*Data skanu:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    episodes = num(r"Epizody zadaniowe\s*\|\s*\**(\d+)")
    sessions = num(r"Przeskanowane\s*\|\s*(\d+)")
    days = num(r"\((\d+)\s*dni\)")

    parts = []
    if episodes is not None:
        parts.append(f"{episodes} {plural(episodes, 'epizod', 'epizody', 'epizodów')}")
    if sessions is not None:
        parts.append(f"{sessions} {plural(sessions, 'sesja', 'sesje', 'sesji')}")
    if days is not None:
        parts.append(f"{days} {'dzień' if days == 1 else 'dni'}")
    return (date.group(1) if date else None), " · ".join(parts)


def find_chrome():
    for candidate in CHROME_CANDIDATES:
        path = candidate if candidate.startswith("/") and Path(candidate).exists() else shutil.which(candidate)
        if path:
            return path
    return None


def render_png(html_path, png_path, chrome):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    png_path.unlink(missing_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={PROFILE_DIR}",
        "--force-device-scale-factor=2",
        f"--window-size={WINDOW}",
        "--virtual-time-budget=5000",
        f"--screenshot={png_path}",
        html_path.as_uri(),
    ]
    # Headless Chrome can keep running after it writes the screenshot, so wait for a stable file, not for exit.
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 60
    last_size = -1
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        if png_path.exists():
            size = png_path.stat().st_size
            if size > 0 and size == last_size:
                break
            last_size = size
        time.sleep(0.5)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if not png_path.exists():
        sys.exit("Chrome produced no screenshot. In Claude Code run this script outside the sandbox.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="mega-assessment-*.md")
    parser.add_argument("--name", default="KRYCH", help="name printed on the card")
    parser.add_argument("--out-dir", type=Path, help="default: the report's directory")
    parser.add_argument("--no-png", action="store_true", help="write HTML only")
    args = parser.parse_args()

    text = args.report.read_text(encoding="utf-8")
    traits = parse_traits(text)
    date, foot = parse_meta(text)

    out_dir = (args.out_dir or args.report.parent).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"mega-pajeczyna-{date}" if date else f"{args.report.stem}-pajeczyna"
    html_path = out_dir / f"{stem}.html"
    png_path = out_dir / f"{stem}.png"

    data = {"name": args.name.upper(), "date": date, "foot": foot, "traits": traits}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", f"const DATA = {payload};")
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML: {html_path}")

    if args.no_png:
        return
    chrome = find_chrome()
    if not chrome:
        sys.exit("Chrome/Chromium not found, PNG skipped. HTML is ready.")
    render_png(html_path, png_path, chrome)
    print(f"PNG:  {png_path}")


if __name__ == "__main__":
    main()
