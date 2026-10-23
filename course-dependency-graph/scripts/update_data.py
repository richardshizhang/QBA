#!/usr/bin/env python3
"""Build graph-data.js for the QBIO course dependency graph.

Reads the hand-maintained program requirements (data/requirements.json, transcribed
from the USC catalogue) and pulls titles, descriptions, prerequisites, corequisites
and offering history from the USC Schedule of Classes API (classes.usc.edu).

If data/catalogue-courses.json exists (exported with scripts/catalogue_export.js), its
catalogue prerequisites, corequisites, descriptions and "Terms Offered" take precedence:
the Schedule of Classes leaves out some prerequisites the catalogue lists.

    python3 scripts/update_data.py                # fetch (cached) + build
    python3 scripts/update_data.py --terms 8      # shorter offering-history window
    python3 scripts/update_data.py --cache DIR    # reuse raw API responses from DIR

Only the standard library is used.
"""

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

import catalogue

API = "https://classes.usc.edu/api"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE_EXPORT = os.path.join(ROOT, "data", "catalogue-courses.json")
SEASONS = {1: "Spring", 2: "Summer", 3: "Fall"}


def get_json(url, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.load(resp)
        except Exception as exc:  # timeouts on big departments are common; back off and retry
            if attempt == retries - 1:
                raise RuntimeError(f"{url}: {exc}") from exc
            time.sleep(3 * (attempt + 1))


def norm(code):
    """'CHEM 105b' -> 'CHEM 105B' (catalogue sequence letters are case-insensitive)."""
    return " ".join(code.split()).upper()


def prev_terms(latest, n):
    """Term codes are YYYYT with T = 1 spring, 2 summer, 3 fall."""
    year, t = divmod(latest, 10)
    out = []
    while len(out) < n:
        out.append(year * 10 + t)
        t -= 1
        if t == 0:
            year, t = year - 1, 3
    return out


def fetch_listing(cache, term, school, prefix):
    path = os.path.join(cache, f"{term}_{prefix}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except ValueError:
            pass  # partial file from an interrupted run
    url = f"{API}/Courses/CoursesByTermSchoolProgram?termCode={term}&school={school}&program={prefix}"
    data = get_json(url)
    with open(path, "w") as f:
        json.dump(data, f)
    return data


def fetch_all(cache, pairs, school_of, workers):
    """pairs: iterable of (term, prefix). Returns {(term, prefix): listing}."""
    jobs = {}
    results = {}
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for term, prefix in pairs:
            if prefix not in school_of:
                print(f"  ! no school found for prefix {prefix}, skipping", file=sys.stderr)
                continue
            jobs[pool.submit(fetch_listing, cache, term, school_of[prefix], prefix)] = (term, prefix)
        for i, job in enumerate(futures.as_completed(jobs), 1):
            key = jobs[job]
            try:
                results[key] = job.result()
            except RuntimeError as exc:
                print(f"  ! {exc}", file=sys.stderr)
            if i % 10 == 0 or i == len(jobs):
                print(f"  fetched {i}/{len(jobs)} listings")
    return results


def groups(raw):
    """API requisite groups -> [{"n": count, "o": [[code, ...], ...]}]; groups are ANDed,
    a group needs n of its options, and each option is a bundle of courses (its 'ands')."""
    out = []
    for g in raw or []:
        opts = []
        for o in g.get("courseOptions") or []:
            bundle = [norm(o["courseSpace"])] + [norm(a["courseSpace"]) for a in o.get("ands") or []]
            opts.append(bundle)
        if opts:
            out.append({"n": g.get("requiredCourses") or 1, "o": opts})
    return out


def restrictions(course):
    parts = []
    for key, label in (("courseRestrictions", "Class level"), ("majorRestrictions", "Major"), ("schoolRestrictions", "School")):
        items = course.get(key) or []
        incl = [r["groupDescription"] or r["groupCode"] for r in items if r.get("restrictionCode") == "I"]
        excl = [r["groupDescription"] or r["groupCode"] for r in items if r.get("restrictionCode") != "I"]
        if incl:
            parts.append(f"{label}: open only to {', '.join(incl)}")
        if excl:
            parts.append(f"{label}: not open to {', '.join(excl)}")
    return "; ".join(parts) or None


def index_listings(listings):
    """Latest record per course code, plus the terms in which it had a live section."""
    latest, offered = {}, {}
    for (term, _prefix), listing in listings.items():
        for c in (listing or {}).get("courses") or []:
            code = norm(c["fullCourseName"])
            if any(not s.get("isCancelled") for s in c.get("sections") or []):
                offered.setdefault(code, set()).add(term)
            if code not in latest or latest[code][0] < term:
                latest[code] = (term, c)
    return latest, offered


def catalogue_requisites(cat, key):
    """(groups, text, parsed) from a parsed catalogue course; 'co' also folds in
    'Concurrent Enrollment'. groups is None when there is text the parser couldn't turn
    into any course groups."""
    keys = ("co", "conc") if key == "co" else (key,)
    texts = [cat[k] for k in keys if cat.get(k)]
    if not texts:
        return [], None, True
    found = [g for k in keys if cat.get(k) for g in cat.get(k + "_groups", [])]
    complete = all(cat.get(k + "_complete", True) for k in keys if cat.get(k))
    return (found or None), "; ".join(texts), complete


def effective_prereqs(code, latest, cat):
    """Catalogue first (an entry without a Prerequisite line means none), else schedule."""
    if code in cat:
        found, _text, _complete = catalogue_requisites(cat[code], "pre")
        if found is not None:
            return found
    return groups(latest[code][1].get("prerequisiteCourseCodes")) if code in latest else []


def course_record(code, latest, offered, cat=None):
    rec = {"src": None, "off": sorted(offered.get(code, []))}
    if code in latest:
        term, c = latest[code]
        units = c.get("courseUnits") or []
        units = [int(u) if float(u).is_integer() else u for u in units]
        rec |= {
            "t": c.get("name"),
            "u": (f"{units[0]}-{units[-1]}" if len(units) > 1 else str(units[0])) if units else None,
            "d": (c.get("description") or "").strip() or None,
            "pre": groups(c.get("prerequisiteCourseCodes")),
            "co": groups(c.get("corequisiteCourseCodes")),
            "rec": c.get("recommendedPrep"),
            "restr": restrictions(c),
            "dup": c.get("duplicateCredit"),
            "src": term,
        }
    if cat:
        rec["cat"] = True
        rec["t"] = rec.get("t") or cat.get("title")
        rec["u"] = rec.get("u") or cat.get("units")
        rec["d"] = cat.get("desc") or rec.get("d")
        rec["cterms"] = cat.get("terms")
        rec["curl"] = cat.get("url")
        rec["rec"] = cat.get("rec") or rec.get("rec")
        rec["restr"] = cat.get("restr") or rec.get("restr")
        if not rec.get("dup") and cat.get("dup"):
            rec["dup"] = re.sub(r"^Duplicates Credit\s*(?:In|in|with)?\s*", "", cat["dup"])
        for key in ("pre", "co"):
            found, text, complete = catalogue_requisites(cat, key)
            if found is not None:
                rec[key] = found
                rec[key + "Src"] = "catalogue"
            else:
                rec[key + "Src"] = "schedule"  # kept the schedule's version
            if text:
                rec[key + "Text"] = text
                if not complete or found is None:
                    rec[key + "Partial"] = True
    keep = {k: v for k, v in rec.items() if v not in (None, [], "")}
    keep["src"] = rec["src"]
    return keep


def describe(gs):
    return " AND ".join("(" + " or ".join("+".join(b) for b in g["o"]) + ")" for g in gs) or "none"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=os.path.join(ROOT, ".cache"), help="directory for raw API responses")
    ap.add_argument("--terms", type=int, default=11, help="how many recent terms (incl. summers) to scan")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(ROOT, "graph-data.js"))
    ap.add_argument("--catalogue", default=CATALOGUE_EXPORT, help="catalogue export from scripts/catalogue_export.js")
    args = ap.parse_args()
    os.makedirs(args.cache, exist_ok=True)

    with open(os.path.join(ROOT, "data", "requirements.json")) as f:
        req = json.load(f)
    program_courses = set(req["courses"])
    placement = set(req["placement"]["courses"])

    active = get_json(f"{API}/Terms/Active")
    newest = max(t["termCode"] for t in active)
    terms = prev_terms(newest, args.terms)
    print(f"Terms: {', '.join(map(str, terms))}")

    school_of = {}
    for school in get_json(f"{API}/Schools/TermCode?termCode={newest}"):
        for prog in school.get("programs") or []:
            school_of.setdefault(prog["prefix"], school["prefix"])

    prefixes = sorted({c.split()[0] for c in program_courses})
    print(f"Pass 1: {len(prefixes)} departments x {len(terms)} terms")
    listings = fetch_all(args.cache, [(t, p) for t in terms for p in prefixes], school_of, args.workers)
    latest, offered = index_listings(listings)

    cat_meta, cat = {}, {}
    if os.path.exists(args.catalogue):
        cat_meta, cat = catalogue.load(args.catalogue)
        print(f"Catalogue export: {len(cat)} courses from {cat_meta.get('catalogue', '?')} ({cat_meta.get('exported', '?')[:10]})")
    else:
        print("No data/catalogue-courses.json; using Schedule of Classes prerequisites only.")

    # Prerequisites that live outside the major (e.g. CSCI 102, LING 385) get their own
    # nodes when a group can only be met by outside courses, so fetch their departments too.
    outside = set()
    for code in program_courses:
        for g in effective_prereqs(code, latest, cat):
            flat = {c for bundle in g["o"] for c in bundle}
            if not flat & (program_courses | placement):
                outside |= flat
    extra = sorted({c.split()[0] for c in outside} - set(prefixes))
    if extra:
        print(f"Pass 2: outside departments {', '.join(extra)} x {min(4, len(terms))} terms")
        more = fetch_all(args.cache, [(t, p) for t in terms[:4] for p in extra], school_of, args.workers)
        listings.update(more)
        latest, offered = index_listings(listings)

    courses = {}
    referenced = set()
    for code in sorted(program_courses | outside):
        courses[code] = course_record(code, latest, offered, cat.get(code))
        for key in ("pre", "co"):
            for g in courses[code].get(key, []):
                referenced |= {c for bundle in g["o"] for c in bundle}
    # Titles for courses that only appear as alternatives inside a requisite group.
    titles = {code: latest[code][1].get("name") for code in sorted(referenced - set(courses)) if code in latest}

    missing = sorted(c for c in program_courses if courses[c]["src"] is None and not courses[c].get("cat"))
    if missing:
        print(f"No prerequisite data from either source: {', '.join(missing)}")
    if cat:
        not_in_export = sorted(c for c in program_courses if c not in cat)
        if not_in_export:
            print(f"Not in the catalogue export (schedule data used): {', '.join(not_in_export)}")
        canon = lambda gs: sorted(sorted(sorted(b) for b in g["o"]) for g in gs)
        for code in sorted(program_courses):
            soc = groups(latest[code][1].get("prerequisiteCourseCodes")) if code in latest else []
            mine = courses[code].get("pre", [])
            if canon(soc) != canon(mine):
                print(f"  prereq change {code}: schedule {describe(soc)} -> catalogue {describe(mine)}")
            if courses[code].get("prePartial"):
                print(f"  partly parsed {code}: {courses[code].get('preText')!r}")

    data = {
        "generated": dt.date.today().isoformat(),
        "catalogueExport": {"catalogue": cat_meta.get("catalogue"), "exported": cat_meta.get("exported")} if cat else None,
        "terms": terms,
        "seasons": SEASONS,
        "requirements": req,
        "courses": courses,
        "outside": sorted(outside),
        "titles": titles,
    }
    with open(args.out, "w") as f:
        f.write("// Generated by scripts/update_data.py -- do not edit by hand.\n")
        f.write("window.QBIO_DATA = ")
        json.dump(data, f, indent=1, sort_keys=False)
        f.write(";\n")
    print(f"Wrote {os.path.relpath(args.out, ROOT)} ({len(courses)} courses)")


if __name__ == "__main__":
    main()
