#!/usr/bin/env python3
"""Describe each lab by the quantitative and computational work a student could do there.

SPECTER2 and OpenAlex topics say what a lab studies, which groups labs by domain. This
says how a lab works, using the hand-written methods in data/method-taxonomy.json:

- demonstrated: the lab does this work, by its papers or its own website, matched on a
  method's `analysis` terms.
- potential: the lab generates data this work could use, matched on its `data` terms. A
  microscopy lab has computer vision potential even if it never publishes on computer
  vision.
- firsthand: what people who worked in a lab report, in data/lab-method-notes.json.
  Papers can't show this, so it counts as much as a lab's strongest method.

    {"julia-schwartzman": {"methods": ["computer-vision"], "note": "why"}}

Each lab-method pair gets one level, so a method a lab has demonstrated is never also
listed as potential. Website text comes from scripts/scrape_lab_research.py.

Papers carry the same weights as scripts/build_features.py (recency, authorship and
consortium size). A method counts for less when many labs share it, so a lab's vector
stresses what sets it apart.

Writes data/features/methods-features.npz (same people as extended-features.npz),
data/features/methods-report.md, which shows the papers behind each label, and
data/lab-methods.json, the same evidence for the page.

    python3 scripts/build_methods.py
    python3 scripts/build_methods.py --no-notes   # papers only, for testing the taxonomy
"""

import argparse
import collections
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_features  # noqa: E402
import combined  # noqa: E402

import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY = os.path.join(ROOT, "data", "method-taxonomy.json")
NOTES = os.path.join(ROOT, "data", "lab-method-notes.json")
RESEARCH = os.path.join(ROOT, "data", "raw", "lab-research.json")
FEATURES = os.path.join(ROOT, "data", "features", "methods-features.npz")
REPORT = os.path.join(ROOT, "data", "features", "methods-report.md")
EVIDENCE = os.path.join(ROOT, "data", "lab-methods.json")

POTENTIAL_WEIGHT = 0.5  # how much "could use this data" counts against "does this work"
MIN_PAPERS = 3  # papers needed before a method is listed for a lab
MIN_SHARE = 0.04  # share of a lab's weighted papers needed before a method is listed
WEBSITE_SHARE = 0.10  # what a lab's own website saying so counts for in its vector
WEBSITE_STATEMENTS = 2  # sentences needed to count as demonstrated; fewer is potential
# Sentences that aren't a lab describing its work: citations, course lists and bios.
NOT_A_STATEMENT = re.compile(r"\b(19|20)\d\d\b|et al|\bpp\.|\bdoi\b|Ph\.?D\.? (student|candidate)|postdoc|"
                             r"undergraduate|graduate student|interested in|\b[A-Z]{3,4} \d{3}|\bjoined\b|"
                             r"\b(He|She) (is|was|has|received)\b", re.I)

NONE, POTENTIAL, FIRSTHAND, DEMONSTRATED = 0, 1, 2, 3
LEVELS = {POTENTIAL: "potential", FIRSTHAND: "firsthand", DEMONSTRATED: "demonstrated"}


def compile_terms(terms):
    return re.compile("|".join(f"(?:{t})" for t in terms), re.I) if terms else None


def match_papers(papers, methods):
    """-> (analysis, data), each a papers × methods array of 0 and 1."""
    analysis = np.zeros((len(papers), len(methods)))
    data = np.zeros((len(papers), len(methods)))
    patterns = [(compile_terms(m["analysis"]), compile_terms(m["data"])) for m in methods]
    for j, w in enumerate(papers):
        text = build_features.paper_text(w)
        for k, (a, d) in enumerate(patterns):
            if a and a.search(text):
                analysis[j, k] = 1
            elif d and d.search(text):
                data[j, k] = 1
    return analysis, data


def match_websites(faculty, methods):
    """-> (analysis, data), each a labs × methods array of how many sentences say so."""
    analysis = np.zeros((len(faculty), len(methods)))
    data = np.zeros((len(faculty), len(methods)))
    if not os.path.exists(RESEARCH):
        print("! no data/raw/lab-research.json, so using papers only", file=sys.stderr)
        return analysis, data
    with open(RESEARCH, encoding="utf-8") as f:
        pages = json.load(f)
    patterns = [(compile_terms(m["analysis"]), compile_terms(m["data"])) for m in methods]
    for i, person in enumerate(faculty):
        seen = set()  # the same sentence often repeats across a lab's pages
        for page in pages.get(person["id"], []):
            for sentence in re.split(r"(?<=[.!?])\s+", page["text"]):
                if sentence in seen or NOT_A_STATEMENT.search(sentence):
                    continue
                seen.add(sentence)
                for k, (a, d) in enumerate(patterns):
                    if a and a.search(sentence):
                        analysis[i, k] += 1
                    elif d and d.search(sentence):
                        data[i, k] += 1
    return analysis, data


def assign_levels(W, A, Dm, demonstrated, potential, firsthand, site_analysis, site_data):
    """One level per lab and method. Demonstrated wins, then firsthand, then potential."""
    papers = (W > 0).astype(float)
    shown_analysis = ((papers @ A >= MIN_PAPERS) & (demonstrated >= MIN_SHARE)) | (site_analysis >= WEBSITE_STATEMENTS)
    shown_data = ((papers @ Dm >= MIN_PAPERS) & (potential >= MIN_SHARE)) | (site_data > 0) | (site_analysis > 0)
    levels = np.full(demonstrated.shape, NONE, dtype=np.int8)
    levels[shown_data] = POTENTIAL
    levels[firsthand > 0] = FIRSTHAND
    levels[shown_analysis] = DEMONSTRATED
    return levels


def shares(W, M):
    totals = W.sum(axis=1, keepdims=True)
    return (W / np.where(totals == 0, 1, totals)) @ M


def lab_vectors(demonstrated, potential, firsthand, site_analysis, site_data):
    """Rows are unit vectors, so a dot product is cosine similarity."""
    demonstrated = np.maximum(demonstrated, WEBSITE_SHARE * (site_analysis >= WEBSITE_STATEMENTS))
    potential = np.maximum(potential, WEBSITE_SHARE * ((site_data > 0) | (site_analysis > 0)))
    X = np.sqrt(demonstrated + POTENTIAL_WEIGHT * potential)
    strongest = X.max(axis=1, keepdims=True)
    X = np.maximum(X, firsthand * strongest)
    used = (X > 0.1).sum(axis=0)
    X = X * (np.log((1 + len(X)) / (1 + used)) + 1)
    return build_features.normalize_rows(X)


def best_paper(i, k, W, M, papers):
    """The paper that best shows this method for this lab, or None."""
    hits = np.flatnonzero((W[i] > 0) * M[:, k])
    return papers[max(hits, key=lambda j: W[i, j])] if len(hits) else None


def write_evidence(faculty, methods, papers, W, A, Dm, demonstrated, potential, levels,
                   firsthand, site_analysis, site_data, notes):
    """What the page shows for each lab. Website text stays out, as it isn't ours to republish."""
    labs = {}
    for i, p in enumerate(faculty):
        rows = []
        for k in np.flatnonzero((levels[i] > NONE) | (firsthand[i] > 0)):
            use_data = levels[i, k] == POTENTIAL
            M, share = (Dm, potential) if use_data else (A, demonstrated)
            best = best_paper(i, k, W, M, papers)
            rows.append({
                "method": methods[k]["id"], "level": LEVELS[int(levels[i, k])],
                "share": round(float(share[i, k]), 3), "papers": int(((W[i] > 0) * M[:, k]).sum()),
                "of": int((W[i] > 0).sum()), "website": bool(site_analysis[i, k] + (site_data[i, k] if use_data else 0)),
                "example": best and {"id": best["id"], "title": best["title"], "year": best["year"],
                                     "venue": best["venue"], "doi": best["doi"]},
                "firsthand": notes[p["id"]].get("note") if firsthand[i, k] else None,
            })
        labs[p["id"]] = sorted(rows, key=lambda r: (-list(LEVELS.values()).index(r["level"]), -r["share"]))
    with open(EVIDENCE, "w", encoding="utf-8") as f:
        json.dump({"methods": [{k: m[k] for k in ("id", "family", "name")} for m in methods], "labs": labs},
                  f, indent=1, ensure_ascii=False)
        f.write("\n")


def write_report(faculty, methods, papers, W, A, Dm, demonstrated, potential, levels,
                 firsthand, site_analysis, site_data, notes):
    lines = [
        "# Methods report",
        "",
        "Generated by `scripts/build_methods.py`. **Demonstrated** methods appear in the lab's",
        "papers or on its own website. **Potential** methods use data the lab generates.",
        "**Firsthand** methods come from people who worked there. Each method appears at one",
        "level only. Percentages are shares of the lab's weighted papers. Each label lists an",
        "example, so a wrong one can be traced to its terms in `data/method-taxonomy.json`.",
        "",
    ]

    def evidence(i, k, share, M, site):
        n = int(((W[i] > 0) * M[:, k]).sum())
        parts = []
        if n:
            best = best_paper(i, k, W, M, papers)
            parts.append(f"{share[i, k]:.0%}, {n} of {int((W[i] > 0).sum())} papers. "
                         f"For example: {best['title'][:90]} ({best['year']})")
        if site[i, k]:
            parts.append("stated on the lab's website or profile")
        return f"- {methods[k]['name']} ({'; '.join(parts)})"

    for i, p in enumerate(faculty):
        lines += [f"## {p['name']}", ""]
        for level, label, share, M, site in ((DEMONSTRATED, "Demonstrated", demonstrated, A, site_analysis),
                                             (POTENTIAL, "Potential", potential, Dm, site_data + site_analysis)):
            ks = sorted(np.flatnonzero(levels[i] == level), key=lambda k: -share[i, k])
            if ks:
                lines += [f"**{label}:**", ""] + [evidence(i, k, share, M, site) for k in ks] + [""]
        told = [methods[k]["name"] for k in np.flatnonzero(firsthand[i])]
        if told:
            lines += [f"**Firsthand:** {', '.join(told)}. {notes[p['id']].get('note', '')}", ""]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-notes", action="store_true", help="leave out firsthand notes")
    args = ap.parse_args()

    with open(TAXONOMY, encoding="utf-8") as f:
        methods = json.load(f)["methods"]
    notes = {}
    if os.path.exists(NOTES) and not args.no_notes:
        with open(NOTES, encoding="utf-8") as f:
            notes = json.load(f)

    faculty, works = combined.people(), combined.works()
    papers = [w for w in works.values()
              if not w["duplicate_of"] and any(i["keep"] for i in w["faculty"].values())]
    papers.sort(key=lambda w: w["id"])
    W, _ = build_features.weight_matrix(faculty, papers, build_features.HALF_LIFE)

    A, Dm = match_papers(papers, methods)
    demonstrated, potential = shares(W, A), shares(W, Dm)

    index = {m["id"]: k for k, m in enumerate(methods)}
    firsthand = np.zeros_like(demonstrated)
    people = {p["id"]: i for i, p in enumerate(faculty)}
    for pid, note in notes.items():
        for mid in note["methods"]:
            firsthand[people[pid], index[mid]] = 1

    site_analysis, site_data = match_websites(faculty, methods)
    levels = assign_levels(W, A, Dm, demonstrated, potential, firsthand, site_analysis, site_data)

    os.makedirs(os.path.dirname(FEATURES), exist_ok=True)
    np.savez_compressed(
        FEATURES,
        faculty_ids=np.array([p["id"] for p in faculty]),
        method_ids=np.array([m["id"] for m in methods]),
        method_names=np.array([m["name"] for m in methods]),
        method_families=np.array([m["family"] for m in methods]),
        demonstrated=demonstrated.astype(np.float32),
        potential=potential.astype(np.float32),
        firsthand=firsthand.astype(np.float32),
        website_analysis=site_analysis.astype(np.int8),
        website_data=site_data.astype(np.int8),
        levels=levels,
        methods=lab_vectors(demonstrated, potential, firsthand, site_analysis, site_data).astype(np.float32),
    )
    evidence = (faculty, methods, papers, W, A, Dm, demonstrated, potential, levels,
                firsthand, site_analysis, site_data, notes)
    write_report(*evidence)
    write_evidence(*evidence)
    hits = collections.Counter(methods[k]["family"] for k in np.flatnonzero(A.sum(axis=0)))
    print(f"{len(papers)} papers, {len(faculty)} labs, {len(methods)} methods in {len(hits)} families; "
          f"{int((A.sum(axis=1) > 0).sum())} papers match an analysis term")
    print(f"wrote {os.path.relpath(FEATURES, ROOT)}, {os.path.relpath(REPORT, ROOT)} and {os.path.relpath(EVIDENCE, ROOT)}")


if __name__ == "__main__":
    main()
