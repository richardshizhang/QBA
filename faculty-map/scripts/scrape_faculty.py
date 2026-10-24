#!/usr/bin/env python3
"""Scrape the QCB faculty roster into data/faculty.json.

Reads https://www.qcb-dornsife.usc.edu/faculty (a Wix page; plain curl works) and
records each person's group (core / emeritus / joint / adjunct), title, departments,
rank, contact details, lab website, profile page and headshot.

    python3 scripts/scrape_faculty.py              # fetch the page, then parse
    python3 scripts/scrape_faculty.py --offline    # reparse data/raw/faculty.html

Only the standard library is used.
"""

import argparse
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
from html.parser import HTMLParser

URL = "https://www.qcb-dornsife.usc.edu/faculty"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "faculty.html")
OUT = os.path.join(ROOT, "data", "faculty.json")

SECTIONS = {
    "PRIMARY FACULTY": "core",
    "EMERITI FACULTY": "emeritus",
    "JOINT FACULTY": "joint",
    "ADJUNCT FACULTY": "adjunct",
}

# Department names as they appear after "Professor of" in titles. Longest match wins,
# so "Quantitative and Computational Biology" is never split at its "and".
DEPARTMENTS = [
    "Quantitative and Computational Biology",
    "Aerospace and Mechanical Engineering",
    "Biochemistry",
    "Biological Sciences",
    "Biomedical Engineering",
    "Cancer Biology",
    "Chemical Engineering and Materials Science",
    "Chemistry",
    "Computer Science",
    "Earth Sciences",
    "Electrical and Computer Engineering",
    "Gerontology",
    "Industrial and Systems Engineering",
    "Mathematics",
    "Medicine",
    "Microbiology, Immunology & Molecular Genetics",
    "Molecular Microbiology and Immunology",
    "Neurology",
    "Ophthalmology",
    "Pediatrics",
    "Pharmacology and Pharmaceutical Sciences",
    "Physics and Astronomy",
    "Physiology and Biophysics",
    "Population and Public Health Sciences",
    "Psychiatry and Behavioral Sciences",
    "Radiology",
    "Stem Cell Biology and Regenerative Medicine",
]
# Spelling variants on the page -> canonical name above.
DEPARTMENT_ALIASES = {
    "Chemical Engineering and Materials Sciences": "Chemical Engineering and Materials Science",
    "Clinical Medicine": "Medicine",
    "Ophtalmology": "Ophthalmology",
}
QCB = "Quantitative and Computational Biology"

# str.title() gets these wrong.
NAME_CASE = {"Maclean": "MacLean", "Mcmahon": "McMahon"}

PHONE = re.compile(r"^\(?\d{3}\)?\s*[\d\s\-‑]*(?:BRAIN)?$|^\(\d{3}\)\s*44-BRAIN$")


class Blocks(HTMLParser):
    """Flatten the page into (kind, ...) events in document order.

    ("h", level, text) for headings, ("p", text) for paragraphs (one event per <br>
    line), ("a", href, text) for links, ("img", src, alt) for images and
    ("email", address) for the mail buttons some cards use instead of mailto links.
    """

    BLOCK = {"h1", "h2", "h3", "h4", "h5", "h6", "p"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []
        self.block = None  # (tag, [text]) of the open heading/paragraph
        self.link = None  # (href, [text]) of the open <a>
        self.skip = 0  # depth inside <script>/<style>

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.block = (tag, [])
        elif tag == "a":
            self.link = (attrs.get("href") or "", [])
        elif tag == "img":
            self.events.append(("img", attrs.get("src") or "", attrs.get("alt") or ""))
        elif tag == "button" and "@" in (attrs.get("aria-label") or ""):
            self.events.append(("email", attrs["aria-label"].strip()))
        elif tag == "br" and self.block:
            self.block[1].append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK and self.block and self.block[0] == tag:
            for line in "".join(self.block[1]).split("\n"):
                text = clean(line)
                if text:
                    self.events.append(("p", text) if tag == "p" else ("h", int(tag[1]), text))
            self.block = None
        elif tag == "a" and self.link:
            self.events.append(("a", self.link[0].strip(), clean("".join(self.link[1]))))
            self.link = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.block:
            self.block[1].append(data)
        if self.link:
            self.link[1].append(data)


def clean(text):
    text = html.unescape(text).replace("​", "").replace("\xa0", " ")
    return " ".join(text.split())


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    with open(RAW, "w", encoding="utf-8") as f:
        f.write(body)
    return body


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_name(heading):
    """'MICHAEL "DOC" EDGE, PhD' -> name parts. Nicknames come in quotes or parentheses."""
    raw = re.sub(r",\s*Ph\.?D\.?$", "", heading).strip()
    nickname = None
    m = re.search(r'"([^"]+)"|\(([^)]+)\)', raw)
    if m:
        nickname = (m.group(1) or m.group(2)).title()
        raw = (raw[: m.start()] + raw[m.end():]).strip()
    parts = [NAME_CASE.get(p.title(), p.title()) for p in raw.split()]
    first, last = parts[0], parts[-1]
    if len(parts) > 2 and parts[-2] in ("Di",):  # Rosa Di Felice
        last = " ".join(parts[-2:])
    full = " ".join(parts)
    if nickname:
        # Keep the site's form: Michael "Doc" Edge, Chang (April) Shu.
        wrap = f'"{nickname}"' if '"' in heading else f"({nickname})"
        display = full.replace(first, f"{first} {wrap}", 1)
    else:
        display = full
    return {
        "name": display,
        "first": first,
        "last": last,
        "middle": " ".join(parts[1:-1]) if last == parts[-1] and len(parts) > 2 else None,
        "nickname": nickname,
        "id": slugify(full),
    }


def parse_departments(title):
    """Departments listed after each 'Professor ... of' in the title, in order."""
    found = []
    for segment in title.split(";"):
        for m in re.finditer(r"Professor(?: \(Teaching\))?(?: Emeritus)? of ([^;]+)", segment):
            text = m.group(1)
            for alias, canon in DEPARTMENT_ALIASES.items():
                text = text.replace(alias, canon)
            leftover = text
            hits = []
            for dept in sorted(DEPARTMENTS, key=len, reverse=True):
                i = leftover.find(dept)
                if i >= 0:
                    hits.append((text.find(dept), dept))
                    leftover = leftover[:i] + " " * len(dept) + leftover[i + len(dept):]
            if re.sub(r"[\s,]|\band\b", "", leftover):
                print(f"  ! unmatched department text in {title!r}: {leftover.strip()!r}", file=sys.stderr)
            for _, dept in sorted(hits):
                if dept not in found:
                    found.append(dept)
    return found


def parse_rank(title):
    rank = "full"
    if re.search(r"Assistant Professor", title):
        rank = "assistant"
    elif re.search(r"Associate Professor", title):
        rank = "associate"
    return {
        "rank": rank,
        "teaching": "(Teaching)" in title,
        "emeritus": "Emerit" in title,
    }


def parse(body):
    parser = Blocks()
    parser.feed(body)
    people, seen = [], set()
    group, person, photo = None, None, None

    for ev in parser.events:
        kind = ev[0]
        if kind == "h" and ev[1] <= 2:
            group = SECTIONS.get(ev[2].upper(), group)
            person = None
        elif kind == "img":
            photo = ev[1] if ev[2].lower() == "headshot" else photo
        elif kind == "h" and ev[1] == 3 and re.search(r",\s*Ph\.?D", ev[2]):
            info = parse_name(ev[2])
            if info["id"] in seen or group is None:
                person = None  # the page repeats every card further down; keep the first
                continue
            seen.add(info["id"])
            person = {**info, "group": group, "title": None, "institution": None,
                      "departments": [], "email": None, "office": None, "phone": None,
                      "website": None, "profile": None, "photo": photo}
            people.append(person)
            photo = None
        elif person is None:
            continue
        elif kind == "email":
            person["email"] = person["email"] or ev[1]
        elif kind == "a":
            href, text = ev[1], ev[2]
            if href.startswith("mailto:"):
                person["email"] = href[len("mailto:"):].strip()
            elif text == "Website":
                person["website"] = href
            elif text == "Profile":
                person["profile"] = href
        elif kind in ("p", "h"):
            text = ev[-1]
            if person["title"] is None:
                person["title"] = text
            elif PHONE.match(text):
                person["phone"] = text
            elif person["group"] == "adjunct" and person["institution"] is None:
                person["institution"] = text
            elif person["office"] is None and len(text) < 80:
                person["office"] = text

    for p in people:
        title = p["title"] or ""
        p.update(parse_rank(title))
        p["departments"] = parse_departments(title)
        others = [d for d in p["departments"] if d != QCB]
        p["home_department"] = QCB if p["group"] in ("core", "emeritus") or not others else others[0]
        if p["website"] == p["profile"]:
            p["website"] = None
    return people


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="reparse data/raw/faculty.html")
    args = ap.parse_args()

    if args.offline:
        with open(RAW, encoding="utf-8") as f:
            body = f.read()
    else:
        body = fetch()

    people = parse(body)
    counts = {}
    for p in people:
        counts[p["group"]] = counts.get(p["group"], 0) + 1
    out = {"source": URL, "faculty": people}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {len(people)} faculty to {os.path.relpath(OUT, ROOT)}: "
          + ", ".join(f"{n} {g}" for g, n in counts.items()))
    for p in people:
        missing = [k for k in ("title", "email", "profile") if not p[k]]
        if missing:
            print(f"  ! {p['name']}: missing {', '.join(missing)}", file=sys.stderr)


if __name__ == "__main__":
    main()
