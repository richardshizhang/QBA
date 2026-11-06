#!/usr/bin/env python3
"""Work out each lab's size and its PhD students' papers, for the map.

Lab size comes from the best source available for each person:

1. data/lab-sizes.json: everyone the lab's own website lists, PI and undergraduates
   included, from scripts/scrape_lab_sizes.py. A lab is never smaller than the people
   the QCB rosters place in it, plus the PI.
2. Otherwise an estimate from publications: USC co-authors on the person's senior-author
   papers since RECENT, who appear on at least two of them or as first author on one.
   People with several senior-author papers of their own are left out as collaborators
   rather than lab members. Anyone the QCB rosters place in the lab is added, and the PI.

The QCB rosters alone can't be used, as they only list QCB's own students and postdocs:
13 of 48 labs. The estimate counts anyone active in the window, so it runs high for labs
with a lot of turnover, and low for new labs with few papers. data/lab-report.md compares
it with the website counts.

Students' papers come from scripts/fetch_student_papers.py. Conference abstracts, data
deposits and repeat records are removed here.

    python3 scripts/build_labs.py

Writes data/labs.json and data/lab-report.md. No API calls. Only the standard library
is used.
"""

import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_student_papers import same_person  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

RECENT = 2023
MAX_AUTHORS = 40        # beyond this a paper says little about who's in the lab
OWN_LAB = 3             # senior-author papers that make someone a collaborator
LISTED_TYPES = {"article", "review", "book-chapter", "letter", "conference-paper", "preprint"}
NOT_A_PAPER = re.compile(r"^(abstract\b|additional file|code and derived|data from|supplement|figure |table |bps\d{4}|\d{2,5} )", re.I)
# Website counts that need a word of warning on the page.
CAVEATS = {
    "paul-thompson": "This is the whole Imaging Genetics Center, which includes other faculty.",
    "aiichiro-nakano": "This is CACS, a center shared by four faculty.",
    "charleston-chiang": "Probably high, as the page still lists undergraduates from 2019 to 2021.",
}


def load(*path):
    with open(os.path.join(DATA, *path), encoding="utf-8") as f:
        return json.load(f)


def estimate(pid, ids, all_faculty, works, coauthors, senior_papers):
    """Co-authors counted as lab members: {author ID: name}."""
    papers, first, names = collections.Counter(), collections.Counter(), {}
    for wid, authors in coauthors.items():
        w = works.get(wid)
        if not w or w["duplicate_of"] or (w["year"] or 0) < RECENT or len(authors) > MAX_AUTHORS:
            continue
        if not (w["faculty"].get(pid) or {}).get("keep"):
            continue
        me = next((a for a in authors if a[0] in ids), None)
        if not me or not (me[2] == "last" or me[4]):
            continue
        for a in authors:
            if a[0] and a[3] and a[0] not in all_faculty:
                papers[a[0]] += 1
                first[a[0]] += a[2] == "first"
                names[a[0]] = a[1]
    return {k: names[k] for k in papers if (papers[k] >= 2 or first[k]) and senior_papers[k] < OWN_LAB}


def full_record(record, works):
    """Stored student paper -> title, year, venue, link, or None if it isn't listed."""
    if record.get("from_faculty_paper"):
        w = works.get(record["id"])
        if not w:
            return None
        record = {**record, "title": w["title"], "year": w["year"], "venue": w["venue"], "doi": w["doi"], "type": w["type"]}
    if record.get("type") not in LISTED_TYPES or NOT_A_PAPER.match(record["title"] or ""):
        return None
    return record


def paper_list(records, works):
    """Newest first, one record per title, journal versions ahead of preprints."""
    full = [r for r in (full_record(x, works) for x in records) if r]
    full.sort(key=lambda r: (r["type"] == "preprint", -(r["year"] or 0)))
    seen, out = set(), []
    for r in full:
        key = re.sub(r"[^a-z0-9]", "", r["title"].lower())[:80]
        if key not in seen:
            seen.add(key)
            out.append(r)
    out.sort(key=lambda r: -(r["year"] or 0))
    return out


def main():
    faculty = {p["id"]: p for p in load("faculty.json")["faculty"] if p["group"] != "adjunct"}
    roster = load("raw", "students.json")["people"]
    profiles = load("openalex-authors.json")
    works = load("papers", "papers.json")["works"]
    coauthors = load("papers", "coauthors.json")["works"]
    found = load("papers", "student-works.json")
    pages = load("lab-sizes.json")["labs"]

    ids = {pid: set(profiles[pid].get("openalex") or []) for pid in faculty}
    all_faculty = set().union(*ids.values())
    senior_papers = collections.Counter(a[0] for authors in coauthors.values() for a in authors if a[2] == "last")

    labs, rows = {}, []
    for pid in faculty:
        members = [p for p in roster if pid in p["labs"]]
        coauthored = estimate(pid, ids[pid], all_faculty, works, coauthors, senior_papers)
        known = {a for p in members for a in found.get(p["id"], {}).get("profiles", [])}
        extra = [name for k, name in coauthored.items()
                 if k not in known and not any(same_person(p, name) for p in members)]
        guess = len(members) + len(extra) + 1 if members or extra else 0
        page = pages[pid]
        count = page["members"]
        labs[pid] = {"size": guess if count is None else max(count, len(members) + 1),
                     "source": "website" if count is not None else "estimate" if guess else None,
                     "url": None if count is None else page["people_page"] or page["website"],
                     "note": CAVEATS.get(pid), "count": count, "estimate": guess,
                     "phd": sum(p["kind"] == "phd" for p in members), "postdoc": sum(p["kind"] == "postdoc" for p in members)}
        rows.append((pid, labs[pid]))

    students = []
    for p in roster:
        if p["kind"] != "phd" or not p["labs"]:
            continue
        papers = paper_list(found.get(p["id"], {}).get("works", []), works)
        students.append({"id": p["id"], "name": p["name"], "labs": p["labs"],
                         "papers": [{"title": r["title"], "year": r["year"], "venue": r["venue"], "doi": r["doi"],
                                     "id": r["id"], "position": r["position"]} for r in papers]})

    out = {"recent": RECENT, "labs": labs, "students": students,
           "no_lab_yet": sum(p["kind"] == "phd" and not p["labs"] for p in roster)}
    with open(os.path.join(DATA, "labs.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    both = [(pid, v) for pid, v in rows if v["source"] == "website"]
    lines = ["# Lab sizes and student papers", "",
             "Generated by `scripts/build_labs.py`. Sizes include the PI. Website counts also include any "
             "undergraduates the lab lists; estimates don't.", "",
             f"## Website counts compared with the estimate ({len(both)} labs)", "",
             "| Lab | Website | Size used | Estimate | QCB PhD | QCB postdocs |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    lines += [f"| {faculty[pid]['name']} | {v['count']} | {v['size']} | {v['estimate']} | {v['phd']} | {v['postdoc']} |"
              for pid, v in sorted(both, key=lambda r: -r[1]["size"])]
    rest = sorted(((pid, v) for pid, v in rows if v["source"] != "website"), key=lambda r: -r[1]["size"])
    lines += ["", f"## Estimate only ({len(rest)} labs)", "", "| Lab | Estimate | QCB PhD | QCB postdocs |", "| --- | ---: | ---: | ---: |"]
    lines += [f"| {faculty[pid]['name']} | {v['size']} | {v['phd']} | {v['postdoc']} |" for pid, v in rest]
    with_papers = [s for s in students if s["papers"]]
    lines += ["", f"## PhD students ({len(students)} in a lab, {len(with_papers)} with papers found; "
              f"{out['no_lab_yet']} haven't joined a lab)", ""]
    for s in students:
        lines.append(f"- **{s['name']}** ({', '.join(faculty[x]['last'] for x in s['labs'])}): {len(s['papers'])}")
        lines += [f"  - {r['year']} {r['title']}" for r in s["papers"]]
    with open(os.path.join(DATA, "lab-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"{len(with_papers)} of {len(students)} PhD students in labs have papers; "
          f"sizes: {sum(v['source'] == 'website' for v in labs.values())} from lab websites, "
          f"{sum(v['source'] == 'estimate' for v in labs.values())} estimated, "
          f"{sum(not v['source'] for v in labs.values())} unknown")


if __name__ == "__main__":
    main()
