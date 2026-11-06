#!/usr/bin/env python3
"""Scrape the other departments QBIO students do research in.

Reads the faculty listings of Molecular and Cellular Biosciences, Marine and
Environmental Biology, Neurobiology, Biomedical Engineering, Biostatistics and the Brain
and Creativity Institute, fills in contact details and lab links from profile pages
where the site allows it, adds the hand-picked labs in EXTRA_PEOPLE, and merges everyone
with the QCB roster. Pages in SAVED_PAGES come from ../other_department_faculty/, saved
by hand from a browser, and are never fetched.

QCB comes first. Anyone on data/faculty.json keeps that record and group, and their
"affiliations" list starts with QCB, so joint faculty read as joint before their other
department. data/faculty.json itself is not changed, so the live map stays as it is.

Writes data/roster-extended.json and the review page data/roster-report.md.

    python3 scripts/scrape_departments.py             # fetch what isn't cached, then merge
    python3 scripts/scrape_departments.py --offline   # use cached pages only

Each person has a "tier": qcb (on the QCB roster), named (in EXTRA_PEOPLE), department
(a research appointment in one of the five departments) or secondary (teaching,
emeritus, adjunct, and joint or affiliate listings). Only the standard library is used.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfetch  # noqa: E402
from scrape_faculty import DEPARTMENTS, QCB, slugify  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(ROOT, "data", "faculty.json")
OUT = os.path.join(ROOT, "data", "roster-extended.json")
REPORT = os.path.join(ROOT, "data", "roster-report.md")

MCB = "Molecular and Cellular Biosciences"
MEB = "Marine and Environmental Biology"
NEURO = "Neurobiology"
BME = "Biomedical Engineering"
BIOSTAT = "Biostatistics and Health Data Science"
GERO = "Gerontology"
BCI = "Brain and Creativity Institute"

MCB_URL = "https://dornsife.usc.edu/mcb/mcb-faculty/"
MEB_URL = "https://dornsife.usc.edu/meb/tenured-tenure-track-faculty/"
NEURO_URL = "https://dornsife.usc.edu/neurobiology/people-2/"
BME_URL = "https://bme.usc.edu/directory/faculty/"
BIOSTAT_URL = "https://keck.usc.edu/biostatistics/faculty/"
BIOSTAT_AFFILIATED_URL = "https://keck.usc.edu/biostatistics/faculty/affiliated-faculty/"
BCI_URL = "https://dornsife.usc.edu/bci/people-2/"

# Dornsife's robots.txt has "Disallow: /*/page/", which covers MCB pages 2-4, so the
# listing is read from browser copies instead. Each URL maps to its saved file.
SAVED = os.path.join(os.path.dirname(ROOT), "other_department_faculty")
MCB_SAVED = "MCB Faculty - Molecular and Cellular Biosciences"
SAVED_PAGES = {
    MCB_URL: f"{MCB_SAVED}.html",
    f"{MCB_URL}page/2/": f"{MCB_SAVED} 2.html",
    f"{MCB_URL}page/3/": f"{MCB_SAVED} 3.html",
    f"{MCB_URL}page/4/": f"{MCB_SAVED} 4.html",
    BCI_URL: "People - Brain and Creativity Institute.html",
}
BCI_FACULTY = ("BCI Directors", "Faculty")  # its other sections are trainees and staff

# The form's "By Affiliation Type" values. The page opens filtered to tenure-track.
BME_TYPES = {7: "tenure-track", 5: "research", 6: "teaching", 3: "joint", 1: "adjunct", 2: "emeritus"}
BME_PRIMARY = ("tenure-track", "research")

TITLE_DEPARTMENTS = DEPARTMENTS + [
    MCB, MEB, NEURO, "Human and Evolutionary Biology", "Psychology", "Pathology", "Neuroscience",
    "Biochemistry and Molecular Medicine", "Surgery", "Urology", "Otolaryngology",
    "Biokinesiology", "Occupational Science", "Neurological Surgery",
]

# Names that differ between listings, checked by hand: listing form -> one id.
ALIASES = {
    "donald-arnold": "don-arnold",
    "matt-michael": "matthew-michael",
}

# Labs asked for by name that no listing above covers fully. Listing data wins where it
# exists; these fields fill the gaps. "note" records anything to check before mapping.
EXTRA_PEOPLE = [
    {"name": "Berenice Benayoun", "unit": GERO,
     "title": "Associate Professor of Gerontology and Biological Sciences",
     "profile": "https://gero.usc.edu/faculty/berenice-benayoun-phd/",
     "website": "https://gero.usc.edu/labs/benayounlab/"},
    {"name": "Paula Cannon", "unit": "Molecular Microbiology and Immunology",
     "title": "Distinguished Professor, Molecular Microbiology and Immunology, Stem Cell Biology and Regenerative Medicine, Biomedical Engineering; Associate Director, Cross School Programs for the MESH Academy; Special Advisor to the Provost",
     "profile": "https://stemcell.keck.usc.edu/people/paula-cannon-phd/"},
    {"name": "Rong Lu", "unit": "Stem Cell Biology and Regenerative Medicine",
     "title": "Professor, Stem Cell Biology and Regenerative Medicine, Biomedical Engineering, Medicine, Gerontology; Leukemia & Lymphoma Society Scholar",
     "profile": "https://stemcell.keck.usc.edu/people/rong-lu-phd/",
     "website": "https://ronglulab.usc.edu/"},
    {"name": "Francesca Mariani", "unit": "Stem Cell Biology and Regenerative Medicine",
     "title": "Associate Professor, Stem Cell Biology and Regenerative Medicine",
     "profile": "https://stemcell.keck.usc.edu/people/francesca-mariani-phd/",
     "website": "https://marianilab.usc.edu/"},
    {"name": "Andrei Irimia", "unit": GERO,
     "website": "https://gero.usc.edu/labs/irimialab/"},
    {"name": "Peter Kuhn", "unit": "Biological Sciences",
     "profile": "https://dornsife.usc.edu/profile/peter-kuhn/"},
]

DEGREES = re.compile(r",?\s*\b(?:Ph\.?\s?D|M\.?\s?D|M\.?P\.?H|Sc\.?D|Ed\.?D|Dr\.?P\.?H)\b\.?", re.I)
QCB_TEXT = re.compile(r"Quantitative (?:and|&) Computational Biology")


def strip(fragment):
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment or "", flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\xa0", " ")
    return " ".join(text.split())


def split_name(raw):
    """'Lewinger, Juan Pablo, PhD' or 'Yaoheng (Mack) Yang' -> name parts."""
    raw = DEGREES.sub("", strip(raw)).strip(" ,")
    if "," in raw:
        last, given = raw.split(",", 1)
        raw = f"{given.strip()} {last.strip()}"
    nickname = None
    m = re.search(r"\(([^)]+)\)", raw)
    if m:
        nickname = m.group(1)
        raw = " ".join((raw[:m.start()] + raw[m.end():]).split())
    parts = raw.split()
    display = " ".join(parts)
    if nickname:
        display = display.replace(parts[0], f"{parts[0]} ({nickname})", 1)
    return {"name": display, "first": parts[0], "last": parts[-1],
            "middle": " ".join(parts[1:-1]) or None, "nickname": nickname}


def track_of(title, section):
    """Kind of appointment, from the title or else the listing's section."""
    text = title or section or ""
    if re.search(r"emerit", text, re.I):
        return "emeritus"
    if re.search(r"adjunct|\bdual\b", text, re.I):
        return "adjunct"
    if re.search(r"\(Teaching\)|Lecturer|Instructor|Practice|Clinical|teaching", text):
        return "teaching"
    if re.search(r"\(Research\)|Research (?:Assistant |Associate )?Professor|Professor of Research|^research$", text):
        return "research"
    if re.search(r"Professor|tenure-track", text):
        return "tenure-track"
    return "unknown"


def title_departments(title):
    found = []
    for dept in sorted(set(TITLE_DEPARTMENTS), key=len, reverse=True):
        i = (title or "").find(dept)
        if i >= 0 and not any(dept in other for _, other in found):
            found.append((i, dept))
    return [dept for _, dept in sorted(found)]


# ---------------------------------------------------------------- listings

def entry(name, unit, section, primary, source, **fields):
    return {**split_name(name), "unit": unit, "section": section, "primary": primary, "source": source,
            "title": None, "email": None, "office": None, "phone": None, "website": None,
            "profile": None, "photo": None, **fields}


def person_cards(body, unit, source):
    """The Dornsife person-listing template (MCB)."""
    people = []
    for card in body.split('class="person-card"')[1:]:
        name = re.search(r'<h3>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        title = re.search(r'class="person-title">(.*?)</span>', card, re.S)
        photo = re.search(r'<img[^>]+src="(https://dornsife\.usc\.edu/wp-content/uploads/[^"]+)"', card)
        if name:
            people.append(entry(name.group(2), unit, "faculty", True, source, profile=name.group(1),
                                title=strip(title.group(1)) if title else None,
                                photo=photo.group(1) if photo else None))
    return people


def stacking_cards(body, unit, source, primary_sections):
    """The stacking-card template (MEB, Neurobiology, Biostatistics affiliates).

    An empty primary_sections means every section counts as a primary listing.
    """
    people = []
    for block in re.split(r'(?=<div\s+class="cc--component-container\s+cc--stacking-cards)', body)[1:]:
        heading = re.search(r'f--section-title">\s*<h2[^>]*>(.*?)</h2>', block, re.S)
        section = strip(heading.group(1)) if heading else "faculty"
        for card in re.split(r'class="card\s*"', block)[1:]:
            name = re.search(r'f--cta-title">\s*<h3[^>]*>(.*?)</h3>', card, re.S)
            if not name or not strip(name.group(1)):
                continue
            bold = re.search(r"<strong>(.*?)</strong>", card, re.S)
            mail = re.search(r'href="mailto:([^"]+)"', card)
            phone = re.search(r"Phone:\s*([^<]+)", card)
            office = re.search(r"Office:\s*([^<]+)", card)
            image = re.search(r'<img[^>]+src="(https://[^"]+)"', card)
            person = entry(name.group(1), unit, section, not primary_sections or section in primary_sections,
                           source, title=strip(bold.group(1)) if bold else None,
                           email=mail.group(1).strip() if mail else None,
                           phone=strip(phone.group(1)) if phone else None,
                           office=strip(office.group(1)) if office else None,
                           photo=image.group(1) if image else None)
            for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', card, re.S):
                href = html.unescape(href).strip()
                if href.startswith("mailto:") or href == "/":
                    continue
                if re.search(r"/profile/|/cf/faculty-and-staff/|/faculty-search/", href):
                    person["profile"] = person["profile"] or href
                else:
                    person["website"] = person["website"] or href
            people.append(person)
    return people


def biostat_core(body):
    people = []
    for card in body.split('class="card"')[1:]:
        name = re.search(r'<h2>\s*<a href="(https://keck\.usc\.edu/faculty-search/[^"]+)"[^>]*>(.*?)</a>', card, re.S)
        photo = re.search(r'<img[^>]+src="(https://[^"]+)"', card)
        if name:
            people.append(entry(name.group(2), BIOSTAT, "core", True, BIOSTAT_URL, profile=name.group(1),
                                photo=photo.group(1) if photo else None))
    return people


def bme_listing(body, kind):
    people = []
    for card in re.split(r"(?=<a href = '/directory/faculty/profile/)", body)[1:]:
        card = card.split("</a>")[0]
        href = re.match(r"<a href = '([^']+)'", card)
        name = re.search(r'class = "resultName">(.*?)</h5>(.*?)</div>', card, re.S)
        photo = re.search(r"""<img src=\s*['"]([^'"]*)['"]""", card)
        photo = photo.group(1) if photo and "noprofile" not in photo.group(1) else None
        people.append(entry(name.group(1), BME, kind, kind in BME_PRIMARY, BME_URL,
                            profile="https://bme.usc.edu" + html.unescape(href.group(1)),
                            title=strip(name.group(2)) or None,
                            photo="https:" + photo if photo and photo.startswith("//") else photo))
    return people


# What marks one person in each template, counted separately from the parsers as a check.
PERSON_CARD = r'class="person-card"'
STACKING_CARD = r'f--cta-title">\s*<h3[^>]*>\s*(?!\s|</h3>|Key Searches)'
BME_CARD = r"<a href = '/directory/faculty/profile/"
BIOSTAT_CARD = r'<h2>\s*<a href="https://keck\.usc\.edu/faculty-search/'
BCI_CARD = r'class="text-container">\s*<h3'


def bci_listing(body):
    """The Institute's people page: an <h2> per group, then a card per person."""
    people = []
    for block in re.split(r'f--section-title">\s*<h2[^>]*>', body)[1:]:
        section = strip(block.split("</h2>")[0])
        for card in re.split(r'class="text-container">', block)[1:]:
            name = re.match(r"\s*<h3[^>]*>(.*?)</h3>", card, re.S)
            if not name:
                continue
            link = re.search(r'href="([^"]+)"', name.group(1))
            lines = [strip(x) for x in re.findall(r"<p>(.*?)</p>", card, re.S)]
            people.append(entry(name.group(1), BCI, section, section in BCI_FACULTY, BCI_URL,
                                title=next((x for x in lines if "Professor" in x), lines[0] if lines else None),
                                profile=link.group(1) if link else None))
    return people


def read_listings():
    """-> (entries, counts, problems). A listing we can't reach is reported, never guessed at."""
    people, counts, problems = [], [], []

    def read(label, url, parse, marker, data=None, keep=lambda person: True):
        if url in SAVED_PAGES and os.path.exists(os.path.join(SAVED, SAVED_PAGES[url])):
            with open(os.path.join(SAVED, SAVED_PAGES[url]), encoding="utf-8", errors="replace") as f:
                body = f.read()
        else:
            try:
                found = webfetch.get(url, data)
            except (webfetch.Disallowed, webfetch.Blocked, webfetch.NotCached) as e:
                problems.append(f"{label}: {type(e).__name__} ({e})")
                counts.append((label, None, 0))
                return
            if not found.ok:
                problems.append(f"{label}: HTTP {found.status}")
                counts.append((label, None, 0))
                return
            body = found.body
        parsed = parse(body)
        expected = len(re.findall(marker, body))
        counts.append((label, expected, len(parsed)))
        if expected != len(parsed):
            problems.append(f"{label}: the page shows {expected} names but {len(parsed)} were parsed")
        people.extend(person for person in parsed if keep(person))

    for n, url in enumerate([MCB_URL] + [f"{MCB_URL}page/{n}/" for n in (2, 3, 4)], 1):
        read(f"MCB page {n}", url, lambda body: person_cards(body, MCB, MCB_URL), PERSON_CARD)
    read("MEB tenured/tenure-track", MEB_URL, lambda body: stacking_cards(body, MEB, MEB_URL, ()), STACKING_CARD)
    read("Neurobiology", NEURO_URL,
         lambda body: stacking_cards(body, NEURO, NEURO_URL, ("Neurobiology Section Faculty",)), STACKING_CARD)
    read("Biostatistics core", BIOSTAT_URL, biostat_core, BIOSTAT_CARD)
    read("Biostatistics affiliated", BIOSTAT_AFFILIATED_URL,
         lambda body: stacking_cards(body, BIOSTAT, BIOSTAT_AFFILIATED_URL, ("none",)), STACKING_CARD)
    read("Brain and Creativity Institute", BCI_URL, bci_listing, BCI_CARD,
         keep=lambda person: person["section"] in BCI_FACULTY)
    for value, kind in BME_TYPES.items():
        data = urllib.parse.urlencode({"faculty_type[]": value}).encode()
        read(f"BME {kind}", BME_URL, lambda body, kind=kind: bme_listing(body, kind), BME_CARD, data)
    return people, counts, problems


# ---------------------------------------------------------------- profile pages

def dornsife_profile(body):
    fields = {}
    h1 = re.search(r"</h1>", body)
    if h1:
        after = strip(body[h1.end():h1.end() + 3000])
        title = re.split(r"\b(?:Pronouns|Email|Office|Links|Center, Institute)\b", after)[0].strip()
        if title and len(title) < 300:
            fields["title"] = title
    mail = re.search(r'<strong>Email</strong>\s*<a href="mailto:([^"]+)"', body)
    office = re.search(r"<strong>Office</strong>\s*([^<]+)", body)
    phone = re.search(r"<strong>Office Phone</strong>\s*([^<]+)", body)
    site = re.search(r'<a href="([^"]+)"[^>]*aria-label="My Website"', body)
    photo = re.search(r'f--image">\s*<img\b[^>]*?src="(https://dornsife\.usc\.edu/wp-content/uploads/[^"]+)"', body)
    fields.update(photo=photo.group(1) if photo else None,
                  email=mail.group(1).strip() if mail else None,
                  office=strip(office.group(1)) if office else None,
                  phone=strip(phone.group(1)) if phone else None,
                  website=html.unescape(site.group(1)).strip() if site else None)
    return fields


def bme_profile(body):
    block = re.search(r'class = "contactInformation">(.*?)<!-- Close contact info', body, re.S)
    if not block:
        return {}
    block = block.group(1)
    appointments = re.search(r"<span>Appointments</span>\s*<ul>(.*?)</ul>", block, re.S)
    contact = re.search(r"<span>Contact Information</span>\s*<ul>(.*?)</ul>", block, re.S)
    mail = re.search(r"[\w.\-]+@[\w.\-]+", strip(contact.group(1))) if contact else None
    research = re.search(r"<a href='([^']+)'[^>]*>Research Website", block)
    personal = re.search(r"<a href='([^']+)'[^>]*>Personal Website", block)
    site = research or personal
    return {"email": mail.group(0) if mail else None,
            "website": html.unescape(site.group(1)).strip() if site else None,
            "appointments": [strip(x) for x in re.findall(r"<li>(.*?)</li>", appointments.group(1), re.S)]
            if appointments else []}


def profile_url(person):
    """The page to read for this person. Neurobiology cards rarely link a profile, so
    those people get the address Dornsife uses for everyone else."""
    url = person.get("profile") or ""
    if "/profile/" in url or "bme.usc.edu" in url:
        return url
    if any(l["unit"] == NEURO for l in person["listed_on"]):
        return f"https://dornsife.usc.edu/profile/{slugify(person['first'] + ' ' + person['last'])}/"
    return None


def enrich(person, problems):
    """Fill gaps from the person's profile page. QCB records keep every value they have."""
    url = profile_url(person)
    if not url or person["tier"] == "secondary":
        return
    parse = dornsife_profile if "dornsife.usc.edu" in url else bme_profile
    try:
        page = webfetch.get(url)
    except (webfetch.Disallowed, webfetch.Blocked) as e:
        problems.append(f"{person['name']}: {type(e).__name__} on {url}")
        return
    except webfetch.NotCached:
        return
    if not page.ok:
        if url == person.get("profile"):
            problems.append(f"{person['name']}: HTTP {page.status} on {url}")
        return
    person["profile"] = person["profile"] if "/profile/" in (person["profile"] or "") else url
    for key, value in parse(page.body).items():
        if key == "appointments":
            person["appointments"] = value
        elif key == "title" and value and person["qcb_status"] is None:
            person["title"] = value  # the profile is newer than the listing's copy
        elif value and not person.get(key):
            person[key] = value


# ---------------------------------------------------------------- merging

def qcb_index(roster):
    """Every way a QCB person could be written -> their record."""
    index = {}
    for person in roster:
        firsts = [person["first"], person.get("nickname"), person.get("middle")]
        for first in filter(None, firsts):
            for part in first.split():
                index.setdefault(slugify(f"{part} {person['last']}"), person)
        index[person["id"]] = person
    return index


def base_record(listing):
    keep = ("name", "first", "last", "middle", "nickname")
    key = slugify(f"{listing['first']} {listing['last']}")
    return {"id": ALIASES.get(key, key), **{k: listing[k] for k in keep}, "group": "department",
            "qcb_status": None, "title": None, "institution": None, "departments": [],
            "email": None, "office": None, "phone": None, "website": None, "profile": None, "photo": None}


def merge(roster, listings):
    """One record per person, with QCB entries taking priority over everything else."""
    index = qcb_index(roster)
    people = {}
    for p in roster:
        people[p["id"]] = {**p, "qcb_status": p["group"], "listed_on": [], "note": None, "named": False}

    def record_for(listing):
        key = slugify(f"{listing['first']} {listing['last']}")
        key = ALIASES.get(key, key)
        if key in index:
            return people[index[key]["id"]]
        if key not in people:
            people[key] = {**base_record(listing), "listed_on": [], "note": None, "named": False}
        return people[key]

    for listing in listings:
        person = record_for(listing)
        person["listed_on"].append({"unit": listing["unit"], "section": listing["section"],
                                    "primary": listing["primary"], "title": listing["title"],
                                    "source": listing["source"]})
        if person["qcb_status"] is None:
            for key in ("title", "email", "office", "phone", "website", "profile", "photo"):
                person[key] = person[key] or listing[key]

    for extra in EXTRA_PEOPLE:
        listing = entry(extra["name"], extra["unit"], "named lab", True, "requested by name")
        person = record_for(listing)
        person["named"] = True
        person["note"] = extra.get("note")
        person["listed_on"].append({"unit": extra["unit"], "section": "named lab", "primary": True,
                                    "title": None, "source": "requested by name"})
        for key in ("website", "profile"):
            person[key] = person.get(key) or extra.get(key)
        if person["qcb_status"] is None:  # newer than any listing, but never over QCB
            person["title"] = extra.get("title") or person["title"]

    for person in people.values():
        person["tier"] = tier_of(person)
    return people


def tier_of(person):
    if person["qcb_status"] in ("core", "joint", "emeritus"):
        return "qcb"
    if person["named"]:
        return "named"
    track = track_of(person["title"], next((l["section"] for l in person["listed_on"]), None))
    primary = any(l["primary"] for l in person["listed_on"])
    return "department" if primary and track in ("tenure-track", "research", "unknown") else "secondary"


def finish(person):
    """Work out the fields that depend on all of a person's listings and titles."""
    sections = [l["section"] for l in person["listed_on"]]
    person["track"] = track_of(person["title"], sections[0] if sections else None)

    evidence = [person["title"] or ""] + [l["title"] or "" for l in person["listed_on"]] + person.get("appointments", [])
    if person["qcb_status"] is None and any(QCB_TEXT.search(text) for text in evidence):
        person["qcb_status"] = "title-only"

    departments = list(person.get("departments") or [])
    for text in [person["title"]] + [l["title"] for l in person["listed_on"]]:
        departments += title_departments(text)
    departments += [l["unit"] for l in person["listed_on"]]
    if person["qcb_status"]:
        departments.insert(0, QCB)
    departments = list(dict.fromkeys(departments))
    person["departments"] = departments

    others = [d for d in departments if d != QCB]
    labels = {"core": "QCB (core)", "joint": "QCB (joint)", "emeritus": "QCB (emeritus)",
              "adjunct": "QCB (adjunct)", "title-only": "QCB (joint, title only)"}
    person["affiliations"] = ([labels[person["qcb_status"]]] if person["qcb_status"] else []) + others
    person.setdefault("home_department", others[0] if others else None)
    return person


# ---------------------------------------------------------------- reports

def near_matches(people):
    """Same surname, first names sharing an initial: possible duplicates to check by eye."""
    found = []
    by_last = {}
    for person in people:
        by_last.setdefault(slugify(person["last"]), []).append(person)
    for group in by_last.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a["first"][0].lower() == b["first"][0].lower():
                    found.append((a["name"], b["name"]))
    return found


def write_report(people, counts, problems):
    order = {"qcb": 0, "named": 1, "department": 2, "secondary": 3}
    lines = ["# Extended roster report", "",
             f"{len(people)} people. QCB entries come from `data/faculty.json` and take priority.", "",
             "| Tier | People |", "| --- | --- |"]
    for tier in order:
        lines.append(f"| {tier} | {sum(p['tier'] == tier for p in people)} |")

    def section(title, rows):
        lines.extend(["", f"## {title}", ""] + (rows or ["None."]))

    section("Listings", ["| Listing | Names on page | Parsed |", "| --- | --- | --- |"]
            + [f"| {label} | {shown if shown is not None else 'not read'} | {parsed} |"
               for label, shown, parsed in counts])

    section("Titles mention QCB, but not on the QCB roster",
            [f"- {p['name']}: {p['title']}" for p in people if p["qcb_status"] == "title-only"])
    section("Notes to check", [f"- {p['name']}: {p['note']}" for p in people if p["note"]])
    section("Possible duplicates (same surname and initial)", [f"- {a} / {b}" for a, b in near_matches(people)])
    section("Missing titles", [f"- {p['name']} ({p['tier']})" for p in people
                               if not p["title"] and p["tier"] != "secondary"])
    section("Pages that could not be read", [f"- {x}" for x in problems])

    lines += ["", "## Everyone", "", "| Name | Tier | Affiliations | Track | Website |", "| --- | --- | --- | --- | --- |"]
    for p in sorted(people, key=lambda p: (order[p["tier"]], p["last"])):
        site = f"[link]({p['website']})" if p["website"] else ""
        lines.append(f"| {p['name']} | {p['tier']} | {', '.join(p['affiliations'])} | {p['track']} | {site} |")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="use cached pages only")
    args = ap.parse_args()
    webfetch.offline = args.offline

    with open(ROSTER, encoding="utf-8") as f:
        roster = json.load(f)["faculty"]
    listings, counts, problems = read_listings()
    people = merge(roster, listings)
    for person in people.values():
        enrich(person, problems)
    people = sorted((finish(p) for p in people.values()), key=lambda p: (p["last"], p["first"]))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"faculty": people}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    write_report(people, counts, problems)

    counts = {}
    for p in people:
        counts[p["tier"]] = counts.get(p["tier"], 0) + 1
    print(f"wrote {len(people)} people to {os.path.relpath(OUT, ROOT)}: "
          + ", ".join(f"{n} {t}" for t, n in counts.items()))
    for problem in problems:
        print(f"  ! {problem}", file=sys.stderr)


if __name__ == "__main__":
    main()
