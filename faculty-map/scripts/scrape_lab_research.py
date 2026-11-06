#!/usr/bin/env python3
"""Collect what labs say about their own work, for scripts/build_methods.py.

For everyone on the combined map, this reads the research statement on their faculty
profile, their lab's home page, and up to MAX_PAGES research pages linked from it. All
fetching goes through scripts/webfetch.py, so robots.txt and crawl delays are respected
and a block is never worked around.

The page text goes to the gitignored data/raw/lab-research.json, because this repo is
public and the text isn't ours to republish. data/lab-research.json keeps only what was
read and from where.

    python3 scripts/scrape_lab_research.py             # fetch what isn't cached
    python3 scripts/scrape_lab_research.py --offline   # use cached pages only

Only the standard library is used.
"""

import argparse
import collections
import datetime
import html
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combined  # noqa: E402
import webfetch  # noqa: E402
from scrape_lab_sizes import NOT_LAB_SITES, same_site, site_root, strip_furniture, text_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB_SIZES = os.path.join(ROOT, "data", "lab-sizes.json")
RAW = os.path.join(ROOT, "data", "raw", "lab-research.json")
OUT = os.path.join(ROOT, "data", "lab-research.json")

MAX_PAGES = 3  # research pages per lab, besides its home page
MAX_CHARS = 20000  # per page, so a long page can't swamp a lab's profile
MIN_CHARS = 200  # shorter than this is a navigation stub

RESEARCH_LINK = re.compile(r"research|projects?\b|our (work|science)|what we do|focus|interests|about|overview|themes?\b", re.I)
SKIP_LINK = re.compile(r"publication|people|team|members|alumni|news|gallery|contact|join|photos?\b|facebook|twitter|"
                       r"linkedin|instagram|\.pdf|/feed|mailto:|tel:|resources|teaching|courses", re.I)
# Linked as someone's website, but they describe a database or a whole institute.
NOT_ONE_LAB = re.compile(r"rcsb\.org|dornsife\.usc\.edu/bci|uscnorriscancer\.usc\.edu", re.I)
# Where a profile's research statement ends.
STATEMENT_END = re.compile(r"\b(Research Specialties|Research Keywords|Honors|Awards|Publications|Selected Publications|"
                           r"Academic Appointment|Education|Biography|Contact|Service|Courses)\b")


def page_text(body):
    return text_of(strip_furniture(body))[:MAX_CHARS]


def research_links(home_url, body):
    root = site_root(home_url)
    found = {}
    for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.S | re.I):
        target = urllib.parse.urldefrag(urllib.parse.urljoin(home_url, html.unescape(href).strip()))[0]
        label = text_of(label)
        where = f"{label} {urllib.parse.urlsplit(target).path}"
        if (same_site(target, root) and target.rstrip("/") != home_url.rstrip("/")
                and RESEARCH_LINK.search(where) and not SKIP_LINK.search(where)):
            # "Research" itself beats a page that only mentions it in a longer path.
            found.setdefault(target, 0 if re.search(r"\bresearch\b", label, re.I) else 1)
    return sorted(found, key=found.get)[:MAX_PAGES]


def profile_statement(body):
    text = text_of(strip_furniture(body))
    m = re.search(r"(Summary Statement of Research Interests|Research Summary|Description of Research)", text)
    if not m:
        return None
    statement = text[m.end():]
    end = STATEMENT_END.search(statement, 40)
    return (statement[:end.start()] if end else statement)[:MAX_CHARS].strip()


def read_lab(person, site):
    """-> (pages, problem). Each page is {url, kind, text}."""
    pages, problem = [], None

    profile = person.get("profile") or ""
    if "dornsife.usc.edu/profile/" in profile or "bme.usc.edu/directory" in profile:
        try:
            page = webfetch.get(profile)
            statement = profile_statement(page.body) if page.ok else None
            if statement and len(statement) >= MIN_CHARS:
                pages.append({"url": profile, "kind": "profile", "text": statement})
        except (webfetch.Disallowed, webfetch.Blocked, webfetch.NotCached, OSError, ValueError):
            pass

    if not site or NOT_LAB_SITES.search(site) or NOT_ONE_LAB.search(site):
        return pages, None if pages else "no lab website"
    try:
        home = webfetch.get(site)
    except webfetch.RobotsUnreadable:
        return pages, "could not connect from this machine"
    except webfetch.Disallowed:
        return pages, "robots.txt asks crawlers to stay out"
    except webfetch.Blocked:
        return pages, "site refused automated requests"
    except webfetch.NotCached:
        return pages, "not fetched yet"
    except (OSError, ValueError) as e:
        return pages, f"could not load website ({type(e).__name__})"
    if not home.ok or "shibboleth" in home.url or home.url.rstrip("/") == "https://dornsife.usc.edu":
        return pages, "website is gone or needs a login"

    text = page_text(home.body)
    if len(text) >= MIN_CHARS:
        pages.append({"url": home.url, "kind": "home", "text": text})
    for link in research_links(home.url, home.body):
        try:
            page = webfetch.get(link)
        except (webfetch.Disallowed, webfetch.Blocked, webfetch.NotCached, OSError, ValueError) as e:
            problem = problem or type(e).__name__
            continue
        text = page_text(page.body) if page.ok else ""
        if len(text) >= MIN_CHARS:
            pages.append({"url": page.url, "kind": "research", "text": text})
    return pages, problem


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="use cached pages only")
    args = ap.parse_args()
    webfetch.offline = args.offline

    with open(LAB_SIZES, encoding="utf-8") as f:
        sites = {pid: lab["website"] for pid, lab in json.load(f)["labs"].items()}
    people = combined.people()
    raw, summary = {}, {}
    for i, person in enumerate(people, 1):
        pages, problem = read_lab(person, sites.get(person["id"]) or person.get("website"))
        raw[person["id"]] = pages
        summary[person["id"]] = {
            "name": person["name"],
            "pages": [{"url": p["url"], "kind": p["kind"], "words": len(p["text"].split())} for p in pages],
            "problem": problem,
        }
        print(f"[{i}/{len(people)}] {person['name']}: {len(pages)} pages {problem or ''}", flush=True)

    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    with open(RAW, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"fetched": datetime.date.today().isoformat(), "labs": summary}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    kinds = collections.Counter(p["kind"] for pages in raw.values() for p in pages)
    print(f"wrote {sum(bool(p) for p in raw.values())} of {len(people)} labs with text: {dict(kinds)}")


if __name__ == "__main__":
    main()
