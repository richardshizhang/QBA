#!/usr/bin/env python3
"""Download every faculty member's papers from OpenAlex as trimmed records.

Reads data/faculty.json and the hand-checked data/openalex-authors.json, pages
through all works of each person's OpenAlex profiles (or looks up their DOIs when
OpenAlex never linked them to a profile), and keeps only what later steps need:

    title, year, type, venue, citations, plain-text abstract, primary topic,
    keywords, number of authors, and for each faculty member on the paper their
    author position and institutions on it.

Raw API responses are never written to disk; full author lists exist only in memory
while a person's papers are being processed. Output goes to data/papers/papers.json
(gitignored, about 26 MB) plus data/paper-report.md, a summary of what was kept and
dropped for checking by eye.

Papers are dropped for a faculty member when they are:

- not research: peer reviews, errata, supplementary files, datasets, reference
  entries, "Data from ..." deposits, dissertations they didn't write;
- not in English (mostly machine-translated duplicates), or retracted;
- off-profile: not linked through co-authors to any paper they published with a USC
  affiliation, and either part of a separate co-author cluster whose topics barely
  overlap their USC-linked papers, or a lone paper in a subfield those papers rarely
  touch. This is what removes namesakes' papers from merged OpenAlex profiles (see
  the notes in data/openalex-authors.json). It also drops genuine work far from
  someone's main research, such as early papers in another field, which is fine for
  a research-similarity map.

Papers with a USC affiliation are always kept, so a namesake *at USC* gets through;
the report lists kept papers with unusual topics so those can be dropped by hand.

Exact duplicates (a preprint and its journal version, a conference paper reprinted
as a chapter) are grouped by title, and one record stands for the group.

Corrections go in data/paper-overrides.json (optional, hand-edited):

    {"liang-chen": {"keep": ["W123"], "drop": ["W456"], "note": "why"}}

    python3 scripts/fetch_papers.py                       # fetch anyone not yet fetched
    python3 scripts/fetch_papers.py --refresh remo-rohs   # refetch some people
    python3 scripts/fetch_papers.py --refilter            # no API calls; reapply filters
    python3 scripts/fetch_papers.py --extended            # the extended roster instead

With --extended, this reads data/roster-extended.json and
data/openalex-authors-extended.json and writes data/papers/papers-extended.json and
data/paper-report-extended.md, with corrections in data/paper-overrides-extended.json.
The QCB files behind the live map don't change. Anyone not yet verified is skipped.

Papers on a person's "dois" list were picked by hand, so they anchor the filter the
same way USC-affiliated papers do, even for someone who also has OpenAlex profiles.

A full run costs about 120 OpenAlex credits (one per page of 200 papers).
Only the standard library is used.
"""

import argparse
import collections
import datetime as dt
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openalex  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACULTY = os.path.join(ROOT, "data", "faculty.json")
MAPPING = os.path.join(ROOT, "data", "openalex-authors.json")
OVERRIDES = os.path.join(ROOT, "data", "paper-overrides.json")
OUT_DIR = os.path.join(ROOT, "data", "papers")
PAPERS = os.path.join(OUT_DIR, "papers.json")
REPORT = os.path.join(ROOT, "data", "paper-report.md")
EXTENDED_FACULTY = os.path.join(ROOT, "data", "roster-extended.json")
EXTENDED_MAPPING = os.path.join(ROOT, "data", "openalex-authors-extended.json")
EXTENDED_OVERRIDES = os.path.join(ROOT, "data", "paper-overrides-extended.json")
EXTENDED_PAPERS = os.path.join(OUT_DIR, "papers-extended.json")
EXTENDED_REPORT = os.path.join(ROOT, "data", "paper-report-extended.md")

GROUPS = ("core", "joint", "emeritus")
USC = "https://openalex.org/I1174212"
WORK_FIELDS = ("id,doi,title,publication_year,type,language,is_retracted,primary_location,"
               "authorships,primary_topic,topics,keywords,abstract_inverted_index,cited_by_count")

# Research output types. Dissertations count only when the person is first author:
# OpenAlex often lists advisors as authors of their students' theses.
RESEARCH_TYPES = {"article", "review", "preprint", "letter", "book", "book-chapter",
                  "conference-paper", "conference-abstract", "report", "dissertation"}
# Best representative of a group of duplicates comes first.
TYPE_RANK = ["article", "review", "letter", "conference-paper", "book-chapter", "book", "report",
             "preprint", "conference-abstract", "dissertation"]
NOT_RESEARCH_TITLE = re.compile(
    r"^(reviewer #|author response|decision letter|supplementa|additional file|data from |"
    r"(supplementary |supplemental )?(figure|fig\.|table) s?\d|publisher correction|author correction|"
    r"correction( to)?\b|corrigendum|erratum|retraction|retracted|expression of concern)",
    re.I)
# Placeholder records: the whole title is one of these.
JUNK_TITLE = re.compile(
    r"^(oup accepted manuscript|accepted manuscript|author manuscript|contributors|front matter|"
    r"back matter|index|table of contents|editorial board|title page|untitled|10\.\d{4,}/\S+)$", re.I)
# Conference abstracts carry poster numbers: "Abstract 3825: ...", "BM-15 * ...".
TITLE_PREFIX = re.compile(r"^(abstract\s+[a-z]*[-\d]+[a-z]*\s*:\s*|[a-z]{1,6}-?\d+[a-z]?\s*\*\s*)", re.I)

# Papers with more authors than this don't link a person's co-author network: one
# 1,000-author consortium paper would otherwise join everything to everything.
NETWORK_MAX_AUTHORS = 50
# Off-profile = outside the USC-linked co-author network and in a subfield making up
# less than this share of that network's papers, within a field below FIELD_SHARE.
SUBFIELD_SHARE = 0.03
FIELD_SHARE = 0.15
# A separate co-author cluster (2+ papers) is off-profile when the cosine similarity of
# its OpenAlex topics to the USC-linked papers' topics is below this. Namesake clusters
# score about 0; people's own pre-USC clusters mostly 0.15-0.75.
CLUSTER_SIMILARITY = 0.15
# When fewer than this many papers (or a fifth of someone's papers) are USC-linked,
# their largest co-author cluster counts as core too.
MIN_CORE = 5


# ---------------------------------------------------------------- trimming

def clean_title(title):
    title = html.unescape(re.sub(r"<[^>]+>", "", title or ""))
    return " ".join(title.split())


def norm_title(title):
    """Title key for spotting duplicates: no poster numbers, case or punctuation."""
    return re.sub(r"[^a-z0-9]+", "", TITLE_PREFIX.sub("", title).lower())


def abstract_text(inverted):
    if not inverted:
        return None
    words = {}
    for word, positions in inverted.items():
        for p in positions:
            words[p] = word
    text = " ".join(words[p] for p in sorted(words))
    return " ".join(text.split()) or None


def trim_topic(t):
    if not t:
        return None
    return {"id": openalex.short(t["id"]), "name": t["display_name"],
            "subfield": t["subfield"]["display_name"], "field": t["field"]["display_name"],
            "domain": t["domain"]["display_name"]}


def trim_work(w):
    """Everything later steps need from a work record, minus the author list."""
    source = (w.get("primary_location") or {}).get("source") or {}
    n_authors = len(w.get("authorships") or [])
    return {
        "id": openalex.short(w["id"]),
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": clean_title(w.get("title")),
        "year": w.get("publication_year"),
        "type": w.get("type"),
        "language": w.get("language"),
        "retracted": bool(w.get("is_retracted")),
        "venue": source.get("display_name"),
        "cited_by": w.get("cited_by_count", 0),
        # List responses cap author lists at 100, so 100 means "100 or more".
        "n_authors": n_authors,
        "authors_truncated": n_authors >= 100,
        "abstract": abstract_text(w.get("abstract_inverted_index")),
        "topic": trim_topic(w.get("primary_topic")),
        "topics": [[openalex.short(t["id"]), t["display_name"], round(t.get("score", 0), 3)]
                   for t in (w.get("topics") or [])],
        "keywords": [k["display_name"] for k in (w.get("keywords") or [])],
        "faculty": {},
    }


def faculty_authorship(w, profile_ids, last_name, by_name=False):
    """This faculty member's authorship on a work: by profile ID, else by name when
    the work came from their DOI list."""
    for a in w.get("authorships") or []:
        if openalex.short((a.get("author") or {}).get("id")) in profile_ids:
            return a
    if by_name or not profile_ids:
        for a in w.get("authorships") or []:
            name = (a.get("raw_author_name") or (a.get("author") or {}).get("display_name") or "")
            if re.search(rf"\b{re.escape(last_name)}\b", name, re.I):
                return a
    return None


# ---------------------------------------------------------------- fetching

def fetch_all(filt):
    works, cursor = [], "*"
    while cursor:
        data = openalex.get_json("/works", {"filter": filt, "per-page": 200,
                                            "select": WORK_FIELDS, "cursor": cursor})
        works += data.get("results", [])
        cursor = data.get("meta", {}).get("next_cursor") if data.get("results") else None
    return works


def fetch_person(person, entry):
    """Trimmed works for one person, each with this person's authorship details and
    network signals filled in under work["faculty"][person id]."""
    profile_ids = set(entry.get("openalex") or [])
    raw = []
    if profile_ids:
        ids = sorted(profile_ids)
        for i in range(0, len(ids), 50):
            raw += fetch_all("author.id:" + "|".join(ids[i:i + 50]))
    dois = entry.get("dois") or []
    listed = set()
    for i in range(0, len(dois), 50):
        batch = fetch_all("doi:" + "|".join(dois[i:i + 50]))
        listed.update(openalex.short(w["id"]) for w in batch)
        raw += batch

    seen, works, coauthors = set(), [], {}
    for w in raw:
        wid = openalex.short(w["id"])
        if wid in seen:
            continue
        seen.add(wid)
        rec = trim_work(w)
        a = faculty_authorship(w, profile_ids, person["last"], by_name=wid in listed)
        insts = (a or {}).get("institutions") or []
        rec["faculty"][person["id"]] = {
            "position": a["author_position"] if a else None,
            "institutions": [i["display_name"] for i in insts][:3],
            "usc": any(USC in (i.get("lineage") or [i.get("id")]) for i in insts),
            "listed": wid in listed,
        }
        if rec["n_authors"] <= NETWORK_MAX_AUTHORS:
            coauthors[wid] = {openalex.short((x.get("author") or {}).get("id"))
                              for x in w.get("authorships") or []} - profile_ids - {None}
        works.append(rec)
    assign_components(works, coauthors, person["id"], curated=not profile_ids)
    return works


def assign_components(works, coauthors, pid, curated):
    """Number this person's co-author components: two works are in the same component
    when a chain of shared co-authors links them. Works too big to link, or with no
    identified co-authors, get a component of their own. Works from a hand-curated
    DOI list get None."""
    if curated:
        for w in works:
            w["faculty"][pid]["component"] = None
        return
    parent = {wid: wid for wid in coauthors}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first_work = {}
    for wid, authors in coauthors.items():
        for a in authors:
            if a in first_work:
                parent[find(wid)] = find(first_work[a])
            else:
                first_work[a] = wid
    numbers = {}
    for w in works:
        root = find(w["id"]) if w["id"] in coauthors else w["id"]
        w["faculty"][pid]["component"] = numbers.setdefault(root, len(numbers))


# ---------------------------------------------------------------- filtering

def research_problem(w, info):
    """Why a work isn't a research paper of this person, or None."""
    if w["type"] not in RESEARCH_TYPES:
        return f"type: {w['type']}"
    if w["type"] == "dissertation" and info.get("position") != "first":
        return "someone else's dissertation"
    if not w["title"] or NOT_RESEARCH_TITLE.match(w["title"]) or JUNK_TITLE.match(w["title"]):
        return "not research (title)"
    if w["language"] not in (None, "en"):
        return f"language: {w['language']}"
    if w["retracted"]:
        return "retracted"
    return None


def cosine(a, b):
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def unusual_kept(works, pid):
    """Kept papers in a subfield and field rare among the person's kept papers."""
    kept = [w for w in works if w["faculty"][pid]["keep"] and not w["duplicate_of"] and w["topic"]]
    sub = collections.Counter(w["topic"]["subfield"] for w in kept)
    field = collections.Counter(w["topic"]["field"] for w in kept)
    n = max(len(kept), 1)
    return [w for w in kept
            if sub[w["topic"]["subfield"]] / n < SUBFIELD_SHARE and field[w["topic"]["field"]] / n < FIELD_SHARE]


def label_network(pid, ws):
    """'main' = in a co-author component holding a paper the person published with a
    USC affiliation (plus the largest component when those are few); 'other' = in
    another component of 2+ papers; 'alone' = linked to none of their other papers."""
    research = [w for w in ws if w["faculty"][pid]["reason"] is None]
    if any(w["faculty"][pid]["component"] is None for w in ws):
        for w in ws:
            w["faculty"][pid]["network"] = "curated"
        return
    sizes = collections.Counter(w["faculty"][pid]["component"] for w in ws)
    main = {w["faculty"][pid]["component"] for w in research
            if w["faculty"][pid]["usc"] or w["faculty"][pid].get("listed")}
    # Thin USC record (teaching faculty, brand-new hires): also trust the largest cluster.
    in_main = sum(1 for w in research if w["faculty"][pid]["component"] in main)
    if research and in_main < max(MIN_CORE, 0.2 * len(research)):
        main.add(collections.Counter(w["faculty"][pid]["component"] for w in research).most_common(1)[0][0])
    for w in ws:
        info = w["faculty"][pid]
        c = info["component"]
        info["network"] = "main" if c in main else ("alone" if sizes[c] == 1 else "other")


def apply_filters(works, overrides):
    """Set faculty[pid]["keep"] / ["reason"] on every work and mark duplicates."""
    by_person = collections.defaultdict(list)
    for w in works.values():
        for pid, info in w["faculty"].items():
            info["reason"] = research_problem(w, info)
            by_person[pid].append(w)

    for pid, ws in by_person.items():
        label_network(pid, ws)
        # Topic profile of the person's USC-linked network.
        core = [w for w in ws if w["faculty"][pid]["reason"] is None
                and w["faculty"][pid]["network"] in ("main", "curated") and w["topic"]]
        sub = collections.Counter(w["topic"]["subfield"] for w in core)
        field = collections.Counter(w["topic"]["field"] for w in core)
        n = max(len(core), 1)
        core_topics = collections.Counter(w["topic"]["id"] for w in core)
        clusters = collections.defaultdict(list)
        for w in ws:
            info = w["faculty"][pid]
            if info["reason"] is None and info["network"] == "other":
                clusters[info["component"]].append(w)
        for cluster in clusters.values():
            sim = cosine(collections.Counter(w["topic"]["id"] for w in cluster if w["topic"]), core_topics)
            if sim < CLUSTER_SIMILARITY:
                for w in cluster:
                    w["faculty"][pid]["reason"] = f"off-profile cluster (topic similarity {sim:.2f})"
        for w in ws:
            info = w["faculty"][pid]
            if info["reason"] or info["network"] in ("main", "curated"):
                continue
            if w["authors_truncated"] and info["position"] is None:
                continue  # beyond the first 100 authors, so no affiliation to go on
            t = w["topic"]
            if t and sub[t["subfield"]] / n < SUBFIELD_SHARE and field[t["field"]] / n < FIELD_SHARE:
                info["reason"] = f"off-profile ({t['field']} / {t['subfield']})"

    for pid, ov in overrides.items():
        for wid in ov.get("drop", []):
            if wid in works and pid in works[wid]["faculty"]:
                works[wid]["faculty"][pid]["reason"] = "dropped by hand"
        for wid in ov.get("keep", []):
            if wid in works and pid in works[wid]["faculty"]:
                works[wid]["faculty"][pid]["reason"] = None
    for w in works.values():
        for info in w["faculty"].values():
            info["keep"] = info["reason"] is None

    mark_duplicates(works)


def mark_duplicates(works):
    """One representative per title, standing in for everyone on the group."""
    groups = collections.defaultdict(list)
    for w in works.values():
        w["duplicate_of"] = None
        key = norm_title(w["title"])
        if len(key) >= 20 and any(i["keep"] for i in w["faculty"].values()):
            groups[key].append(w)
    for group in groups.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda w: (TYPE_RANK.index(w["type"]) if w["type"] in TYPE_RANK else 99,
                                  w["abstract"] is None, -w["cited_by"], w["id"]))
        best = group[0]
        best["also"] = [w["id"] for w in group[1:]]
        for w in group[1:]:
            w["duplicate_of"] = best["id"]
            for pid, info in w["faculty"].items():
                if info["keep"] and not best["faculty"].get(pid, {}).get("keep"):
                    best["faculty"][pid] = dict(info)


# ---------------------------------------------------------------- report

def write_report(works, faculty, fetched):
    names = {p["id"]: p["name"] for p in faculty}
    stats = {pid: collections.Counter() for pid in fetched}
    dropped = collections.defaultdict(list)
    for w in works.values():
        for pid, info in w["faculty"].items():
            if pid not in stats:
                continue
            s = stats[pid]
            s["fetched"] += 1
            if w["duplicate_of"]:
                s["duplicate"] += 1
            elif info["keep"]:
                s["kept"] += 1
                s["kept_abstract"] += w["abstract"] is not None
            elif info["reason"].startswith("off-profile"):
                s["off-profile"] += 1
                dropped[pid].append(w)
            elif info["reason"] == "dropped by hand":
                s["by hand"] += 1
            else:
                s["not research"] += 1

    lines = [
        "# Paper download report",
        "",
        "Generated by `scripts/fetch_papers.py`. *Kept* papers feed the similarity map and",
        "collaboration edges. *Off-profile* papers aren't linked through co-authors to any",
        "paper the person published at USC, and sit outside the topics of those that are:",
        "mostly namesakes' papers in merged OpenAlex profiles, sometimes the person's own",
        "early work in another field. Fix mistakes in",
        f"`data/{os.path.basename(OVERRIDES)}`, then rerun with `--refilter`.",
        "",
        "| Faculty | Fetched | Kept | With abstract | Duplicates | Not research | Off-profile | By hand |",
        "|---|---|---|---|---|---|---|---|",
    ]
    order = [p for p in faculty if p["id"] in fetched]
    for p in order:
        s = stats[p["id"]]
        lines.append(f"| [{p['name']}](#{p['id']}) | {s['fetched']} | **{s['kept']}** | "
                     f"{s['kept_abstract']} | {s['duplicate']} | {s['not research']} | "
                     f"{s['off-profile'] or ''} | {s['by hand'] or ''} |")
    total = collections.Counter()
    for s in stats.values():
        total.update(s)
    unique_kept = sum(1 for w in works.values()
                      if not w["duplicate_of"] and any(i["keep"] for i in w["faculty"].values()))
    lines += ["", f"{unique_kept} distinct kept papers ({total['kept']} faculty–paper pairs).", ""]

    def paper_line(w, pid):
        info = w["faculty"][pid]
        inst = "; ".join(info["institutions"]) or "no institution listed"
        topic = w["topic"]["subfield"] if w["topic"] else "?"
        title = w["title"] if len(w["title"]) <= 100 else w["title"][:97] + "..."
        return (f"- {w['year']} · [{w['id']}](https://openalex.org/{w['id']}) "
                f"{title.replace('|', '/')} · *{topic}* · {inst}")

    by_person = collections.defaultdict(list)
    for w in works.values():
        for pid in w["faculty"]:
            by_person[pid].append(w)
    for p in order:
        pid = p["id"]
        ws = sorted(dropped.get(pid, []), key=lambda w: (-(w["year"] or 0), w["title"]))
        odd = sorted(unusual_kept(by_person[pid], pid), key=lambda w: (-(w["year"] or 0), w["title"]))
        if not ws and not odd:
            continue
        lines += ["---", "", f'<a id="{pid}"></a>', f"## {names[pid]}", ""]
        if odd:
            lines += [f"**Kept, but unusual topic for them ({len(odd)}):** drop by hand if not theirs.", ""]
            lines += [paper_line(w, pid) for w in odd[:25]]
            if len(odd) > 25:
                lines.append(f"- … and {len(odd) - 25} more")
            lines.append("")
        if ws:
            lines += [f"**Dropped as off-profile ({len(ws)}):**", ""]
            lines += [paper_line(w, pid) for w in ws[:30]]
            if len(ws) > 30:
                lines.append(f"- … and {len(ws) - 30} more")
            lines.append("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh", nargs="*", default=[], help="faculty ids to refetch")
    ap.add_argument("--refilter", action="store_true", help="no API calls; reapply filters")
    ap.add_argument("--only", nargs="*", help="fetch just these faculty ids (for testing)")
    ap.add_argument("--extended", action="store_true", help="use the extended roster and its files")
    args = ap.parse_args()

    global FACULTY, MAPPING, OVERRIDES, PAPERS, REPORT, GROUPS
    if args.extended:
        FACULTY, MAPPING, OVERRIDES = EXTENDED_FACULTY, EXTENDED_MAPPING, EXTENDED_OVERRIDES
        PAPERS, REPORT, GROUPS = EXTENDED_PAPERS, EXTENDED_REPORT, ("named", "department")
    with open(FACULTY, encoding="utf-8") as f:
        roster = json.load(f)["faculty"]
    if args.extended:
        roster = [{**p, "group": p["tier"]} for p in roster]
    faculty = [p for p in roster if p["group"] in GROUPS]
    with open(MAPPING, encoding="utf-8") as f:
        mapping = json.load(f)
    overrides = {}
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES, encoding="utf-8") as f:
            overrides = json.load(f)
    store = {"fetched": {}, "works": {}}
    if os.path.exists(PAPERS):
        with open(PAPERS, encoding="utf-8") as f:
            store = json.load(f)
    works, fetched = store["works"], store["fetched"]

    unverified = [p["name"] for p in faculty if mapping.get(p["id"], {}).get("status") != "verified"]
    if unverified and args.extended:
        print("Skipping, not verified yet: " + ", ".join(unverified))
        faculty = [p for p in faculty if mapping.get(p["id"], {}).get("status") == "verified"]
    elif unverified:
        sys.exit("Check these OpenAlex matches first (scripts/resolve_authors.py): " + ", ".join(unverified))

    for pid in args.refresh:  # forget this person's papers
        fetched.pop(pid, None)
        for wid in [w for w, rec in works.items() if pid in rec["faculty"]]:
            del works[wid]["faculty"][pid]
            if not works[wid]["faculty"]:
                del works[wid]

    todo = [] if args.refilter else [p for p in faculty if p["id"] not in fetched
                                     and (not args.only or p["id"] in args.only)]
    out_of_budget = None
    for i, person in enumerate(todo, 1):
        entry = mapping[person["id"]]
        try:
            got = fetch_person(person, entry)
        except openalex.OutOfBudget as exc:
            out_of_budget = str(exc)
            break
        for rec in got:
            if rec["id"] in works:
                works[rec["id"]]["faculty"].update(rec["faculty"])
            else:
                works[rec["id"]] = rec
        fetched[person["id"]] = {"date": dt.date.today().isoformat(), "works": len(got),
                                 "openalex": entry.get("openalex", []), "dois": len(entry.get("dois") or [])}
        print(f"[{i}/{len(todo)}] {person['name']}: {len(got)} works")
        # Save after each person so an interrupted run loses nothing.
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(PAPERS, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, separators=(",", ":"))

    apply_filters(works, overrides)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(PAPERS, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, separators=(",", ":"))
    write_report(works, faculty, fetched)

    size = os.path.getsize(PAPERS) / 1e6
    print(f"\n{len(fetched)} of {len(faculty)} faculty fetched, {len(works)} works "
          f"({size:.1f} MB) in {os.path.relpath(PAPERS, ROOT)}; report in {os.path.relpath(REPORT, ROOT)}")
    if openalex.credits_left is not None:
        print(f"OpenAlex credits left today: {openalex.credits_left}")
    if out_of_budget:
        sys.exit("OpenAlex budget used up; rerun after midnight UTC to fetch the rest.")


if __name__ == "__main__":
    main()
