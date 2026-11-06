#!/usr/bin/env python3
"""Count the members of each lab, for sizing lab icons on the map.

For everyone in data/roster-extended.json outside the secondary tier, this looks for a
people page on their lab website and counts who it lists as current members, with the
PI included. Anyone listed under an alumni or former-members heading is left out.

A lab with no readable people page gets "members": null, never a guess, and "status"
says why. Page wording varies a lot, so treat a count as a draft until it is checked:
entries in data/lab-size-overrides.json were checked by hand and replace the automatic
count on every run.

Writes data/lab-sizes.json (counts only, since this repo is public and lab pages name
students) and data/lab-size-report.md. The names behind each count go to the gitignored
data/raw/lab-members.json for checking.

    python3 scripts/scrape_lab_sizes.py             # fetch what isn't cached, then count
    python3 scripts/scrape_lab_sizes.py --offline   # use cached pages only

Only the standard library is used.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(ROOT, "data", "roster-extended.json")
OVERRIDES = os.path.join(ROOT, "data", "lab-size-overrides.json")
OUT = os.path.join(ROOT, "data", "lab-sizes.json")
REPORT = os.path.join(ROOT, "data", "lab-size-report.md")
NAMES = os.path.join(ROOT, "data", "raw", "lab-members.json")

DEFINITION = ("Everyone a lab's own website lists as a current member, PI included, on the "
              "date shown. Labs differ in whether they list undergraduates and how often "
              "they update, so compare sizes loosely.")

# Link wording that points to a people page, best first.
TEAM_LINKS = [
    (r"current (lab )?members|current team", 6),
    (r"lab members|lab-members|our team|meet the team|the team|our-team|our people|lab personnel", 5),
    (r"\bpeople\b", 4),
    (r"\bteam\b", 4),
    (r"\bmembers\b", 3),
    (r"\bpersonnel\b|\bgroup\b", 2),
]
SKIP_LINK = re.compile(r"alumni|former|gallery|photos?\b|join|facebook|twitter|linkedin|instagram|"
                       r"\.pdf|/news|/feed|mailto:|tel:", re.I)
NOT_LAB_SITES = re.compile(r"scholar\.google|pubmed|ncbi\.nlm|linkedin\.com|researchgate|orcid\.org|"
                           r"/profile/|faculty-search|/cf/faculty-and-staff/|/directory/", re.I)
# Lab sites that moved, or that a listing links wrongly. Found by hand.
WEBSITE_FIXES = {
    "dion-dickman": "https://dornsife.usc.edu/dickmanlab/",
    "jed-fuhrman": "https://dornsife.usc.edu/fuhrmanlab/",
    "carolyn-phillips": "https://dornsife.usc.edu/phillips/",
    "peter-kuhn": "https://dornsife.usc.edu/kuhn/",
    "xianrui-cheng": "https://xianruichenglab.weebly.com/",
    "assal-habibi": "https://dornsife.usc.edu/brainandmusic/",
    "lisa-aziz-zadeh": "https://dornsife.usc.edu/cenec/",
    "morteza-dehghani": "https://calm-lab.org/",
    "justin-haldar": "https://mr.usc.edu/",
}
# Sites shared by many labs, where a lab's pages all sit under one folder.
SHARED_HOSTS = ("dornsife.usc.edu", "gero.usc.edu", "keck.usc.edu", "sites.usc.edu", "sites.google.com")

PAST_HEADING = re.compile(r"^\W*(?:lab |group |our )?(?:alumni|alumnae|former|past|previous|graduated)"
                          r"(?: lab| group)?(?: (?:and )?(?:members?|postdocs?|post-docs?|students?|"
                          r"trainees?|researchers?|scholars?|undergraduates?|graduate students|"
                          r"interns|visitors))*\W*$", re.I)
PAST_START = re.compile(r"\balumn(?:i|ae)\b|^\W*(?:lab |group |our )?(?:former|past|previous|graduated)\b", re.I)
CAPTION = re.compile(r"\s+(?:profile picture|portrait|headshot|photo|picture|face)\s*$", re.I)
DEGREE = r"(?:Ph\.?\s?D\.?|M\.?\s?D\.?|M\.?\s?S\.?c?\.?|B\.?\s?S\.?c?\.?|B\.?\s?A\.?|M\.?P\.?H\.?|Pharm\.?\s?D\.?)"
NAME = re.compile(r"^(?:Dr\.?\s+|Prof\.?\s+)?"
                  r"([^\W\d_][\w'’.\-]*(?:\s+\(?[^\W\d_][\w'’.\-]*\)?){1,3})"
                  rf"(?:,?\s*{DEGREE})*\.?$")
NOT_NAME_WORDS = set("""
    lab labs laboratory research researcher researchers university college professor professors
    assistant associate postdoc postdocs postdoctoral graduate undergraduate undergraduates student
    students staff member members people team current contact home news publications publication
    join principal investigator investigators scholar scholars fellow fellows manager technician
    usc southern california department school center institute science sciences biology engineering
    alumni former past previous our the of and for in at with about us welcome open positions
    medicine director coordinator program project scientist scientists phd candidate candidates
    visiting summer high interns intern specialist affiliates collaborators more read view click
    bio biography email website photo gallery menu search skip content page site los angeles
    computer data molecular cell cellular neuroscience master masters doctoral technicians
    resident physician major minor philosophy office main who we are docs post history education
    professional services cv full structure-based ligand discovery microbial collective behavior
    group pic overview teaching awards software tools resources lab's
""".split())


def text_of(fragment):
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")
    return " ".join(text.split())


def site_root(url):
    """Scheme, host and, on a shared host, the folder the lab's pages live in."""
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if parts.netloc.lower().removeprefix("www.") in SHARED_HOSTS:
        folders = [x for x in parts.path.split("/") if x]
        keep = 2 if folders[:1] in (["labs"], ["view"], ["site"]) else 1
        root += "/" + "/".join(folders[:keep])
    return root


def same_site(target, root):
    bare = lambda url: re.sub(r"^https?://(?:www\.)?", "", url).rstrip("/")  # noqa: E731
    return bare(target).startswith(bare(root))


def find_people_page(home_url, body):
    """The best people link on a lab's home page -> (url, on-page anchor), or (None, None)."""
    root = site_root(home_url)
    best, anchor, best_score = None, None, 0
    for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.S | re.I):
        target, fragment = urllib.parse.urldefrag(urllib.parse.urljoin(home_url, html.unescape(href).strip()))
        label = text_of(label)
        if not same_site(target, root) or SKIP_LINK.search(f"{target} {label}"):
            continue
        for pattern, score in TEAM_LINKS:
            where = f"{label} {urllib.parse.urlsplit(target).path} {fragment}"
            if re.search(pattern, where, re.I) and score > best_score:
                best, anchor, best_score = target, fragment or None, score
    return best, anchor


def page_updated(body):
    m = re.search(r'article:modified_time"\s+content="(\d{4}-\d{2}-\d{2})', body)
    return m.group(1) if m else None


def strip_furniture(body):
    return re.sub(r"<(script|style|noscript|nav|header|footer)\b.*?</\1>", " ", body, flags=re.S | re.I)


def past_headings(body):
    """Where each alumni heading starts. Real headings only need to contain the word;
    some pages use plain text or a <span> instead, which must be the whole label."""
    found = []
    for m in re.finditer(r"<(h[1-6]|strong|b)\b[^>]*>(.*?)</\1>", body, re.S | re.I):
        if PAST_START.search(text_of(m.group(2))):
            found.append(m.start())
    for m in re.finditer(r"<(?:p|span|div|li|td|summary|button)\b[^>]*>\s*([^<]{4,40}?)\s*<", body, re.I):
        if PAST_HEADING.match(html.unescape(m.group(1))):
            found.append(m.start())
    return sorted(found)


def looks_like_name(text):
    text = CAPTION.sub("", text)
    text = re.split(r"\s+[–—|-]\s+|,\s+(?!" + DEGREE + r")", text)[0].strip(" :,")
    m = NAME.match(text)
    if not m or len(text) > 45 or re.search(r"\d|_", text):
        return None
    words = [w.strip("().").lower() for w in m.group(1).split()]
    if any(w in NOT_NAME_WORDS for w in words) or (text.islower() and len(words) > 2):
        return None
    return m.group(1)


def extract_names(section):
    """Names from each kind of markup; the kind that finds the most wins."""
    sources = {
        "headings": re.findall(r"<h[2-6]\b[^>]*>(.*?)</h[2-6]>", section, re.S | re.I),
        "bold": re.findall(r"<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>", section, re.S | re.I),
        "image alt": re.findall(r'<img\b[^>]*\balt="([^"]+)"', section, re.I),
        "paragraphs": re.findall(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", section, re.S | re.I),
    }
    best, best_names = None, []
    for method, fragments in sources.items():
        names = {}
        for fragment in fragments:
            name = looks_like_name(text_of(fragment))
            if name:  # "Don Arnold" and "Don B. Arnold" are one person
                words = name.lower().split()
                names.setdefault((words[0], words[-1]), name)
        if len(names) > len(best_names):
            best, best_names = method, list(names.values())
    return best, best_names


def count_lab(person):
    """-> (entry for lab-sizes.json, names for the gitignored review file)."""
    lab = {"name": person["name"], "tier": person["tier"], "website": person.get("website"),
           "people_page": None, "members": None, "method": None, "alumni_excluded": False,
           "page_updated": None, "fetched": None, "status": None, "note": None, "checked": False}
    site = WEBSITE_FIXES.get(person["id"]) or person.get("website")
    lab["website"] = site
    if not site or NOT_LAB_SITES.search(site):
        lab["status"] = "no lab website found" if not site else "website is not a lab site"
        return lab, []
    try:
        home = webfetch.get(site)
        if "shibboleth" in home.url:
            lab["status"] = "site needs a USC login"
            return lab, []
        if home.url.rstrip("/") == "https://dornsife.usc.edu" and site.rstrip("/") != home.url.rstrip("/"):
            lab["status"] = "lab link now goes to the Dornsife home page"
            return lab, []
        if not home.ok:
            lab["status"] = f"website returned HTTP {home.status}"
            return lab, []
        link, anchor = find_people_page(home.url, home.body)
        on_home = not link or link.rstrip("/") == home.url.rstrip("/")
        page = home if on_home else webfetch.get(link)
    except webfetch.RobotsUnreadable:
        lab["status"] = "could not connect from this machine"
        return lab, []
    except webfetch.Disallowed:
        lab["status"] = "robots.txt asks crawlers to stay out"
        return lab, []
    except webfetch.Blocked:
        lab["status"] = "site refused automated requests"
        return lab, []
    except webfetch.NotCached:
        lab["status"] = "not fetched yet"
        return lab, []
    except (OSError, ValueError) as e:
        lab["status"] = f"could not load website ({type(e).__name__})"
        return lab, []

    if not link and not re.search(r"people|team|members", home.url, re.I):
        lab["status"] = "no people page found"
        return lab, []
    if not page.ok:
        lab["status"] = f"people page returned HTTP {page.status}"
        return lab, []

    body = page.body
    target = re.search(rf"""\b(?:id|name)=["']{re.escape(anchor)}["']""", body, re.I) if anchor else None
    body = strip_furniture(body[target.start():] if target else body)
    method, names, cut = None, [], False
    for position in past_headings(body):  # a menu item can match too, so it must leave a list
        method, names = extract_names(body[:position])
        if len(names) >= 2:
            cut = True
            break
    if not cut:
        method, names = extract_names(body)
    lab.update(people_page=page.url, method=method, alumni_excluded=cut,
               page_updated=page_updated(page.body), fetched=webfetch.fetched_on(link or site))
    if len(names) < 2:
        lab["status"] = "people page has no readable list"
        return lab, names
    pi_listed = any(person["last"].lower() in name.lower() for name in names)
    lab["members"] = len(names) + (0 if pi_listed else 1)
    lab["status"] = "counted"
    return lab, names


def write_report(labs):
    counted = [lab for lab in labs.values() if lab["members"] is not None]
    lines = ["# Lab size report", "", DEFINITION, "",
             f"{len(counted)} of {len(labs)} labs have a count; "
             f"{sum(lab['checked'] for lab in labs.values())} were checked by hand.", "",
             "| Status | Labs |", "| --- | --- |"]
    statuses = {}
    for lab in labs.values():
        statuses[lab["status"]] = statuses.get(lab["status"], 0) + 1
    lines += [f"| {status} | {n} |" for status, n in sorted(statuses.items(), key=lambda x: -x[1])]
    lines += ["", "| Lab | Tier | Members | Checked | Page updated | Status | Note | People page |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for lab in sorted(labs.values(), key=lambda x: (x["members"] is None, -(x["members"] or 0), x["name"])):
        members = lab["members"] if lab["members"] is not None else "—"
        link = f"[link]({lab['people_page']})" if lab["people_page"] else ""
        lines.append(f"| {lab['name']} | {lab['tier']} | {members} | {'yes' if lab['checked'] else ''} "
                     f"| {lab['page_updated'] or ''} | {lab['status']} | {lab['note'] or ''} | {link} |")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="use cached pages only")
    args = ap.parse_args()
    webfetch.offline = args.offline

    with open(ROSTER, encoding="utf-8") as f:
        people = [p for p in json.load(f)["faculty"] if p["tier"] != "secondary"]
    overrides = {}
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES, encoding="utf-8") as f:
            overrides = json.load(f)

    for unknown in sorted(set(overrides) - {p["id"] for p in people}):
        print(f"  ! override for unknown person: {unknown}", file=sys.stderr)

    labs, names = {}, {}
    for i, person in enumerate(people, 1):
        lab, found = count_lab(person)
        if person["id"] in overrides:
            lab.update({"checked": True, **overrides[person["id"]]})
        labs[person["id"]] = lab
        names[person["id"]] = found
        print(f"[{i}/{len(people)}] {person['name']}: {lab['members']} ({lab['status']})", flush=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"definition": DEFINITION, "labs": labs}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.makedirs(os.path.dirname(NAMES), exist_ok=True)
    with open(NAMES, "w", encoding="utf-8") as f:
        json.dump(names, f, indent=1, ensure_ascii=False)
    write_report(labs)
    print(f"wrote {len(labs)} labs to {os.path.relpath(OUT, ROOT)}, "
          f"{sum(lab['members'] is not None for lab in labs.values())} with counts")


if __name__ == "__main__":
    main()
