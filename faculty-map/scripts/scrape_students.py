#!/usr/bin/env python3
"""Scrape the QCB PhD student and postdoc rosters into data/raw/students.json.

Reads https://www.qcb-dornsife.usc.edu/phdstudents and /postdocs (Wix pages; plain
curl works). Each card gives a name, a role, and either a lab ("Finley Lab") or a
year ("1st Year Student") for students who haven't joined one. Labs are matched to
faculty by last name. Only names, roles and labs are kept: no emails, offices or
photos. The file is gitignored: postdocs only feed lab counts, and students reach the
page through data/labs.json.

    python3 scripts/scrape_students.py              # fetch the pages, then parse
    python3 scripts/scrape_students.py --offline    # reparse data/raw/*.html

Only the standard library is used.
"""

import argparse
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrape_faculty import NAME_CASE, Blocks, parse_name  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.qcb-dornsife.usc.edu/"
PAGES = {"phd": ("phdstudents", 3), "postdoc": ("postdocs", 4)}   # page, card heading level
OUT = os.path.join(ROOT, "data", "raw", "students.json")

NAME_CASE.update({"Mcdermott": "McDermott"})
FOOTER = "DEPARTMENT OF QUANTITATIVE AND COMPUTATIONAL BIOLOGY"


def page_html(slug, offline):
    path = os.path.join(ROOT, "data", "raw", slug + ".html")
    if not offline:
        req = urllib.request.Request(BASE + slug, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
    with open(path, encoding="utf-8") as f:
        return f.read()


def cards(body, level):
    """Each person's heading and the lines of text under it."""
    parser = Blocks()
    parser.feed(body)
    start = next(i for i, e in enumerate(parser.events) if e[0] == "h" and e[1] == 1)
    found, current = [], None
    for event in parser.events[start:]:
        if event[0] == "h" and event[1] == level:
            current = {"heading": event[2], "lines": []}
            found.append(current)
        elif event[0] == "p" and current:
            if event[1] == FOOTER:
                break
            current["lines"].append(event[1])
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="reparse the saved pages")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "data", "faculty.json"), encoding="utf-8") as f:
        faculty = json.load(f)["faculty"]
    by_last = {}
    for person in faculty:
        by_last.setdefault(person["last"].lower(), []).append(person["id"])

    people, problems = [], []
    for kind, (slug, level) in PAGES.items():
        for card in cards(page_html(slug, args.offline), level):
            name = parse_name(card["heading"])
            labs = [lab for line in card["lines"] for m in [re.fullmatch(r"(.+?) Labs?", line)] if m
                    for lab in m.group(1).split(" and ")]
            year = next((int(m.group(1)) for line in card["lines"]
                         for m in [re.fullmatch(r"(\d)\w\w Year Student", line)] if m), None)
            advisors = []
            for lab in labs:
                match = by_last.get(lab.lower(), [])
                if len(match) == 1:
                    advisors.append(match[0])
                else:
                    problems.append(f"{name['name']}: {lab} Lab matches {match or 'no one on the faculty list'}")
            people.append({"id": name["id"], "name": name["name"], "first": name["first"], "last": name["last"],
                           "nickname": name["nickname"], "kind": kind,
                           "role": card["lines"][0] if card["lines"] else None,
                           "labs": advisors, "year": year})
            if not labs and year is None:
                problems.append(f"{name['name']}: no lab or year in {card['lines']}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": [BASE + slug for slug, _ in PAGES.values()], "people": people}, f,
                  ensure_ascii=False, indent=1)
    for kind in PAGES:
        group = [p for p in people if p["kind"] == kind]
        print(f"{kind}: {len(group)} people, {sum(bool(p['labs']) for p in group)} in a lab")
    for line in problems:
        print("  !", line)


if __name__ == "__main__":
    main()
