#!/usr/bin/env python3
"""Build graph-data.js for the QBIO course dependency graph.

Reads the hand-maintained program requirements (data/requirements.json, transcribed
from the USC catalogue) and pulls titles, descriptions, prerequisites, corequisites
and offering history from the USC Schedule of Classes API (classes.usc.edu).

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
import sys
import time
import urllib.request

API = "https://classes.usc.edu/api"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def course_record(code, latest, offered):
    if code not in latest:
        return {"src": None, "off": sorted(offered.get(code, []))}
    term, c = latest[code]
    units = c.get("courseUnits") or []
    units = [int(u) if float(u).is_integer() else u for u in units]
    rec = {
        "t": c.get("name"),
        "u": (f"{units[0]}-{units[-1]}" if len(units) > 1 else str(units[0])) if units else None,
        "d": (c.get("description") or "").strip() or None,
        "pre": groups(c.get("prerequisiteCourseCodes")),
        "co": groups(c.get("corequisiteCourseCodes")),
        "rec": c.get("recommendedPrep"),
        "restr": restrictions(c),
        "dup": c.get("duplicateCredit"),
        "src": term,
        "off": sorted(offered.get(code, [])),
    }
    return {k: v for k, v in rec.items() if v not in (None, [], "")} | {"src": term}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=os.path.join(ROOT, ".cache"), help="directory for raw API responses")
    ap.add_argument("--terms", type=int, default=11, help="how many recent terms (incl. summers) to scan")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(ROOT, "graph-data.js"))
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

    # Prerequisites that live outside the major (e.g. CSCI 102, LING 385) get their own
    # nodes when a group can only be met by outside courses, so fetch their departments too.
    outside = set()
    for code in program_courses:
        if code in latest:
            for g in groups(latest[code][1].get("prerequisiteCourseCodes")):
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
        courses[code] = course_record(code, latest, offered)
        for key in ("pre", "co"):
            for g in courses[code].get(key, []):
                referenced |= {c for bundle in g["o"] for c in bundle}
    # Titles for courses that only appear as alternatives inside a requisite group.
    titles = {code: latest[code][1].get("name") for code in sorted(referenced - set(courses)) if code in latest}

    missing = sorted(c for c in program_courses if courses[c]["src"] is None)
    if missing:
        print(f"Not found in the scanned terms (no prerequisite data): {', '.join(missing)}")

    data = {
        "generated": dt.date.today().isoformat(),
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
