#!/usr/bin/env python3
"""Refresh public GitHub projects and recent public-event activity."""
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER = "saket5ingh"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-updater"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)

def main():
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner&sort=pushed")
    events = api(f"/users/{USER}/events/public?per_page=100")
    if not isinstance(repos, list) or not isinstance(events, list):
        raise RuntimeError("Invalid API result; refusing to overwrite profile")
    projects = [r for r in repos if not r.get("fork") and not r.get("archived") and r["name"] not in (USER, "test")]
    projects.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    lines = [
        f'- **[{r["name"]}](https://github.com/{USER}/{r["name"]})** · '
        f'{html.escape(r.get("language") or "Project")} · updated {(r.get("pushed_at") or "")[:10]}'
        for r in projects[:5]
    ]
    readme = ROOT / "README.md"
    content = readme.read_text(encoding="utf-8")
    pattern = r"(?<=<!-- AUTO-PROJECTS:START -->)\n.*?\n(?=<!-- AUTO-PROJECTS:END -->)"
    updated, count = re.subn(pattern, "\n" + ("\n".join(lines) or "_No public projects available._") + "\n", content, flags=re.S)
    if count != 1:
        raise RuntimeError("README project markers missing or duplicated")
    if updated != content:
        readme.write_text(updated, encoding="utf-8")
    today = dt.datetime.now(dt.timezone.utc).date()
    days = [today - dt.timedelta(days=n) for n in range(13, -1, -1)]
    counts = collections.Counter()
    for event in events:
        if event.get("type") in ("PushEvent", "PullRequestEvent", "IssuesEvent", "CreateEvent"):
            try:
                counts[dt.date.fromisoformat(event["created_at"][:10])] += 1
            except (KeyError, ValueError, TypeError):
                pass
    peak = max([1] + [counts[d] for d in days])
    bars = []
    for i, day in enumerate(days):
        height = round(65 * counts[day] / peak) if counts[day] else 3
        x = 50 + i * 67
        bars.append(f'<rect x="{x}" y="{174-height}" width="35" height="{height}" rx="5" fill="{"#31d5e6" if counts[day] else "#253650"}"/>')
        bars.append(f'<text x="{x+17}" y="195" text-anchor="middle" font-family="monospace" font-size="10" fill="#94a3b8">{day:%d}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 230" role="img" aria-label="Recent public GitHub activity">
<rect width="1100" height="230" rx="18" fill="#0e172a"/><rect x="1" y="1" width="1098" height="228" rx="17" fill="none" stroke="#26344f"/>
<text x="45" y="42" font-family="Arial" font-size="22" font-weight="700" fill="#e8f0ff">Public activity · last 14 days</text>
<text x="45" y="68" font-family="Arial" font-size="13" fill="#94a3b8">{sum(counts[d] for d in days)} sampled events · updated {today:%d %b %Y} UTC</text>
<path d="M42 176 H1050" stroke="#334155"/>{''.join(bars)}
<text x="1050" y="213" text-anchor="end" font-family="Arial" font-size="11" fill="#8395b3">Public events API · not total contributions</text></svg>'''
    (ROOT / "assets" / "activity.svg").write_text(svg, encoding="utf-8")
    print("Refreshed public profile.")

if __name__ == "__main__":
    main()
