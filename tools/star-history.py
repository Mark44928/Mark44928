#!/usr/bin/env python3
"""Generate a static star-history SVG for the Mark44928 profile.

GitHub restricted the public stargazer API in mid-2026, so the hosted
star-history badge is unreliable. This script reads every non-fork repo's
stargazers with the authenticated `gh` CLI (which can see your own repos),
then renders a self-contained cumulative chart for all repos with stars.

Run:  python3 tools/star-history.py
Out:  assets/star-history.svg
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

OWNER = "Mark44928"
OUT = Path(__file__).resolve().parent.parent / "assets" / "star-history.svg"
PALETTE = [
    "#7BD88F", "#63C9A8", "#4FB3A0", "#3E9A8C", "#2F7F74",
    "#A7E8C4", "#8AD9B0", "#6FC79B", "#55B58A", "#256E66",
]


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def repos() -> list[str]:
    raw = gh("repo", "list", OWNER, "--limit", "100",
             "--json", "name,isFork", "--jq",
             '.[] | select(.isFork|not) | .name')
    return [line for line in raw.splitlines() if line]


def star_dates(repo: str) -> list[dt.date]:
    dates: list[dt.date] = []
    page = 1
    while True:
        raw = gh("api", f"repos/{OWNER}/{repo}/stargazers?per_page=100&page={page}",
                 "-H", "Accept: application/vnd.github.star+json")
        batch = json.loads(raw)
        if not batch:
            return dates
        for item in batch:
            stamped = item.get("starred_at")
            if stamped:
                dates.append(dt.date.fromisoformat(stamped[:10]))
        if len(batch) < 100:
            return dates
        page += 1


def render(series: list[tuple[str, list[dt.date]]]) -> str:
    series = [(name, sorted(days)) for name, days in series if days]
    series.sort(key=lambda item: (-len(item[1]), item[0].lower()))
    first = min(days[0] for _, days in series)
    last = max(dt.date.today(), max(days[-1] for _, days in series))
    span = max(1, (last - first).days)
    top = max(len(days) for _, days in series)
    top = max(2, top)
    W, H = 840, 380
    L, R, T, B = 54, 190, 54, 44
    plot_w, plot_h = W - L - R, H - T - B

    def x(day: dt.date) -> float:
        return L + (day - first).days / span * plot_w

    def y(count: float) -> float:
        return T + plot_h - (count / top) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">',
        '<title id="t">Mark44928 — star history</title>',
        '<rect width="100%" height="100%" rx="18" fill="#0C1F17"/>',
        f'<text x="{L}" y="30" font-family="system-ui,sans-serif" font-size="19" '
        f'font-weight="800" fill="#C9E4CE">Star history · all non-fork repos</text>',
        f'<text x="{L}" y="47" font-family="system-ui,sans-serif" font-size="11" '
        f'fill="#78997F">generated from the GitHub API · {len(series)} repos '
        f'with stars · latest star {last.isoformat()}</text>',
    ]

    for tick in range(top + 1):
        gy = y(tick)
        parts.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{W - R}" y2="{gy:.1f}" '
                     f'stroke="#1D3A2F" stroke-width="1"/>')
        parts.append(f'<text x="{L - 10}" y="{gy + 4:.1f}" text-anchor="end" '
                     f'font-family="ui-monospace,monospace" font-size="10" '
                     f'fill="#78997F">{tick}</text>')

    steps = max(4, min(6, span // 45 + 1))
    for i in range(steps + 1):
        day = first + dt.timedelta(days=round(span * i / steps))
        px = x(day)
        parts.append(f'<line x1="{px:.1f}" y1="{T}" x2="{px:.1f}" y2="{T + plot_h}" '
                     f'stroke="#1D3A2F" stroke-width="1"/>')
        parts.append(f'<text x="{px:.1f}" y="{T + plot_h + 22}" text-anchor="middle" '
                     f'font-family="ui-monospace,monospace" font-size="10" '
                     f'fill="#78997F">{day.strftime("%b %Y")}</text>')

    legend_y = T + 6
    for index, (name, days) in enumerate(series):
        color = PALETTE[index % len(PALETTE)]
        points = [(x(first), y(0))]
        for i, day in enumerate(days):
            points.append((x(day), y(i + 1)))
        points.append((x(last), y(len(days))))
        poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        parts.append(f'<polyline points="{poly}" fill="none" stroke="{color}" '
                     f'stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{x(days[-1]):.1f}" cy="{y(len(days)):.1f}" r="3" '
                     f'fill="{color}"/>')
        label = name if len(name) <= 22 else name[:21] + "…"
        ly = legend_y + index * 20
        parts.append(f'<line x1="{W - R + 16}" y1="{ly - 4}" x2="{W - R + 42}" '
                     f'y2="{ly - 4}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{W - R + 50}" y="{ly}" font-family="system-ui,sans-serif" '
                     f'font-size="11.5" fill="#C9E4CE">{label} '
                     f'<tspan fill="#78997F">({len(days)})</tspan></text>')

    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main() -> int:
    collected: list[tuple[str, list[dt.date]]] = []
    for name in repos():
        days = star_dates(name)
        print(f"  {name}: {len(days)} star(s)")
        collected.append((name, days))
    if not any(days for _, days in collected):
        print("no stars found", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(collected), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
