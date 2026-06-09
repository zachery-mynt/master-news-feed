#!/usr/bin/env python3
"""
merge_feeds.py — Merge multiple Google Alerts RSS/Atom feeds into one master feed.

Usage:
    1. Paste your Google Alerts feed URLs into the FEEDS list below.
    2. Run:  python3 merge_feeds.py
    3. Output: master_feed.xml  (a single combined Atom feed)

No external dependencies — uses only the Python standard library, so it runs
anywhere python3 is installed.
"""

import os
import sys
import html
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# ----------------------------------------------------------------------------
# FEED SOURCES
# Either paste URLs into FEEDS below, or drop them (one per line) into the file
# named in FEEDS_FILE. If FEEDS is empty, the script reads FEEDS_FILE.
# ----------------------------------------------------------------------------
FEEDS = [
    # "https://www.google.com/alerts/feeds/1234567890/1111111111",
]
FEEDS_FILE = "feed_urls.txt"

OUTPUT_FILE = "master_feed.xml"
FEED_TITLE = "Mynt — Master News Feed"
FEED_LINK = "https://myntagency.com"
MAX_WORKERS = 20  # concurrent feed fetches
# ----------------------------------------------------------------------------

ATOM = "{http://www.w3.org/2005/Atom}"


def load_feeds():
    """Return the list of feed URLs from FEEDS or FEEDS_FILE."""
    if FEEDS:
        return list(FEEDS)
    if os.path.exists(FEEDS_FILE):
        with open(FEEDS_FILE, encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    return []


def fetch(url):
    """Download a feed; return raw bytes or None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MyntFeedMerger)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as e:
        print(f"  ! Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def parse_time(text):
    """Parse an ISO-8601 timestamp from a feed; fall back to epoch on failure."""
    if not text:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    text = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def feed_source(root):
    """Get the watched term from a Google Alerts feed title: 'Google Alert - "Aesop"' -> 'Aesop'."""
    title = (root.findtext(f"{ATOM}title") or "").strip()
    if " - " in title:
        title = title.split(" - ", 1)[1]
    return title.strip().strip('"')


def parse_entries(raw):
    """Extract entries from a Google Alerts Atom feed, tagged with their source term."""
    entries = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  ! Parse error: {e}", file=sys.stderr)
        return entries

    source = feed_source(root)
    for entry in root.findall(f"{ATOM}entry"):
        title_el = entry.find(f"{ATOM}title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else "(no title)"

        link = ""
        for link_el in entry.findall(f"{ATOM}link"):
            if link_el.get("rel", "alternate") == "alternate":
                link = link_el.get("href", "")
                break

        published = entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated") or ""
        content_el = entry.find(f"{ATOM}content")
        content = "".join(content_el.itertext()).strip() if content_el is not None else ""
        entry_id = entry.findtext(f"{ATOM}id") or link

        entries.append({
            "title": title,
            "link": link,
            "published": published,
            "content": content,
            "id": entry_id,
            "source": source,
            "_sort": parse_time(published),
        })
    return entries


def build_master(entries):
    """Emit a single combined Atom feed as a string."""
    now = datetime.now(timezone.utc).isoformat()
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{html.escape(FEED_TITLE)}</title>",
        f'  <link href="{html.escape(FEED_LINK)}"/>',
        f"  <updated>{now}</updated>",
        f"  <id>{html.escape(FEED_LINK)}/master</id>",
    ]
    for e in entries:
        parts.append("  <entry>")
        parts.append(f"    <title>{html.escape(e['title'])}</title>")
        parts.append(f'    <link href="{html.escape(e["link"])}"/>')
        parts.append(f"    <id>{html.escape(e['id'])}</id>")
        if e["published"]:
            parts.append(f"    <published>{html.escape(e['published'])}</published>")
            parts.append(f"    <updated>{html.escape(e['published'])}</updated>")
        if e.get("source"):
            parts.append(f'    <category term="{html.escape(e["source"])}"/>')
        parts.append(f'    <content type="html">{html.escape(e["content"])}</content>')
        parts.append("  </entry>")
    parts.append("</feed>")
    return "\n".join(parts)


def fetch_and_parse(url):
    raw = fetch(url)
    return parse_entries(raw) if raw else []


def main():
    feeds = load_feeds()
    if not feeds:
        print("No feeds configured. Add URLs to the FEEDS list or to feed_urls.txt.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching {len(feeds)} feeds with {MAX_WORKERS} workers...")
    all_entries = []
    seen = set()  # dedupe by link
    ok = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for entries in pool.map(fetch_and_parse, feeds):
            if entries:
                ok += 1
            for e in entries:
                key = e["link"] or e["id"]
                if key in seen:
                    continue
                seen.add(key)
                all_entries.append(e)

    all_entries.sort(key=lambda e: e["_sort"], reverse=True)

    xml_out = build_master(all_entries)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml_out)

    print(f"\nDone. {ok}/{len(feeds)} feeds returned data.")
    print(f"{len(all_entries)} unique items written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
