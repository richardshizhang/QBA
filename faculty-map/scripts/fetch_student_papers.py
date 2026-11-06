#!/usr/bin/env python3
"""Find the papers of QCB PhD students and postdocs who are in a lab.

Names alone can't be trusted here: the roster has a Wei Liu and a Yue Huang. So a
person's OpenAlex profile is only accepted when it's found on a paper by their own
advisor (from data/papers/coauthors.json), or when it has been checked by hand and
listed in data/student-overrides.json:

    {"yangyang-liu": {"openalex": ["A123"], "drop": ["W456"], "note": "why"}}

Each accepted profile's USC papers are then downloaded, keeping only papers where that
person listed USC or a QCB faculty member is a co-author. Merged profiles and earlier
work elsewhere are therefore left out. Results are trimmed records in
data/papers/student-works.json (gitignored); raw responses are never written to disk.

    python3 scripts/fetch_student_papers.py            # fetch accepted profiles
    python3 scripts/fetch_student_papers.py --search   # also print candidate profiles
                                                       # for people with none, to review

A run costs about 60 OpenAlex credits, and --search adds 10 per person searched.
Only the standard library is used.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openalex  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "papers", "student-works.json")
USC = "https://openalex.org/I1174212"
USC_ID = "I1174212"
FIELDS = "id,doi,title,publication_year,type,language,primary_location,authorships"
SKIP_TYPES = {"dataset", "peer-review", "erratum", "paratext", "supplementary-materials", "reference-entry", "dissertation"}


def load(*path):
    with open(os.path.join(DATA, *path), encoding="utf-8") as f:
        return json.load(f)


def tokens(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z]+", text)


def same_person(person, author):
    """Last names match and the author's first name is one of the person's given
    names or nickname. Middle names and initials on the paper are ignored."""
    words = tokens(author or "")
    if len(words) < 2:
        return False
    last = tokens(person["last"])[-1]
    given = [w for w in tokens(person["name"]) if w != last]
    plain = "".join(w for w in tokens(person["name"].split("(")[0]) if w != last)   # Seung Jae = Seungjae
    for first, family in ((words[:-1], words[-1]), (words[1:], words[0])):           # Liu Wei = Wei Liu
        if family == last and (first[0] in given or "".join(first) == plain):
            return True
    return False


def seed_profiles(person, faculty_ids, coauthors, all_faculty):
    """Profiles found on the person's advisors' papers, and the papers themselves.
    OpenAlex hasn't assigned every author a profile, so some papers come with none."""
    found, papers = {}, {}
    for advisor in person["labs"]:
        for wid, authors in coauthors.items():
            if any(a[0] in faculty_ids[advisor] for a in authors):
                for a in authors:
                    if a[0] not in all_faculty and same_person(person, a[1]):
                        papers[wid] = a[2]
                        if a[0]:
                            found[a[0]] = a[1]
    return found, papers


def usc_works(author_id):
    cursor = "*"
    while cursor:
        data = openalex.get_json("/works", {
            "filter": f"authorships.author.id:{author_id},authorships.institutions.lineage:{USC_ID}",
            "per-page": 200, "select": FIELDS, "cursor": cursor})
        yield from data["results"]
        cursor = data["meta"].get("next_cursor")


def trim(work, author_id, faculty_by_author):
    """The paper as stored, or None if it doesn't qualify."""
    if work.get("type") in SKIP_TYPES or work.get("language") not in (None, "en") or not work.get("title"):
        return None
    mine = next((a for a in work["authorships"] if openalex.short(a["author"].get("id")) == author_id), None)
    if mine is None:
        return None
    usc = any(USC in (i.get("lineage") or [i.get("id")]) for i in mine.get("institutions") or [])
    colleagues = sorted({faculty_by_author[k] for k in (openalex.short(a["author"].get("id")) for a in work["authorships"])
                         if k in faculty_by_author})
    if not usc and not colleagues:
        return None
    source = ((work.get("primary_location") or {}).get("source") or {}).get("display_name")
    return {"id": openalex.short(work["id"]), "doi": (work.get("doi") or "").replace("https://doi.org/", "") or None,
            "title": re.sub(r"<[^>]+>", "", work["title"]).strip(), "year": work.get("publication_year"), "venue": source,
            "type": work.get("type"), "position": mine.get("author_position"), "n_authors": len(work["authorships"]),
            "usc": usc, "faculty": colleagues}


def search(person):
    for name in dict.fromkeys(filter(None, [person["name"].split("(")[0].strip(),
                                            f"{person['nickname']} {person['last']}" if person["nickname"] else None])):
        data = openalex.get_json("/authors", {"search": name, "filter": f"affiliations.institution.id:{USC_ID}", "per-page": 6,
                                              "select": "id,display_name,works_count,orcid,topics"})
        for a in data["results"]:
            if same_person(person, a["display_name"]):
                topics = "; ".join(t["display_name"] for t in (a.get("topics") or [])[:3])
                print(f"    {openalex.short(a['id'])}  {a['display_name']}  {a['works_count']} works  {topics}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--search", action="store_true", help="print candidate profiles for people with none")
    args = ap.parse_args()

    roster = [p for p in load("raw", "students.json")["people"] if p["labs"]]
    profiles = load("openalex-authors.json")
    faculty_ids = {pid: set(entry.get("openalex") or []) for pid, entry in profiles.items()}
    faculty_by_author = {a: pid for pid, ids in faculty_ids.items() for a in ids}
    coauthors = load("papers", "coauthors.json")["works"]
    path = os.path.join(DATA, "student-overrides.json")
    overrides = load("student-overrides.json") if os.path.exists(path) else {}

    out = {}
    for person in roster:
        fix = overrides.get(person["id"], {})
        seeds, seed_papers = seed_profiles(person, faculty_ids, coauthors, faculty_by_author)
        accepted = list(dict.fromkeys(list(seeds) + fix.get("openalex", [])))
        accepted = [a for a in accepted if a not in fix.get("reject", [])]
        papers = {}
        for author_id in accepted:
            for work in usc_works(author_id):
                record = trim(work, author_id, faculty_by_author)
                if record and record["id"] not in fix.get("drop", []):
                    papers[record["id"]] = record
            # Papers with QCB faculty that list no USC address for this person.
            for wid, authors in coauthors.items():
                if wid not in papers and any(a[0] == author_id for a in authors) and wid not in fix.get("drop", []):
                    papers.setdefault(wid, {"id": wid, "from_faculty_paper": True,
                                            "position": next(a[2] for a in authors if a[0] == author_id)})
        for wid, position in seed_papers.items():
            if wid not in fix.get("drop", []):
                papers.setdefault(wid, {"id": wid, "from_faculty_paper": True, "position": position})
        out[person["id"]] = {"profiles": accepted, "seeded": sorted(seeds), "works": list(papers.values())}
        if args.search and not accepted and person["kind"] == "phd":
            print(person["name"], "-", ", ".join(person["labs"]))
            search(person)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    have = sum(bool(v["works"]) for v in out.values())
    print(f"{have} of {len(out)} lab members have papers; credits left {openalex.credits_left}")


if __name__ == "__main__":
    main()
