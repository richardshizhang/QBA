#!/usr/bin/env python3
"""Build map-data.js, the one data file the interactive map loads.

Combines data/layout.json (positions, clusters, tree), data/faculty.json (who they
are), data/edges.json (collaborations), data/features/faculty-features.npz (research
terms, topics, similarity), data/papers/papers.json (recent papers, citations, papers
by year) and data/labs.json (lab sizes and PhD students, from scripts/build_labs.py).

Cluster names and colors come from data/cluster-names.json, which is written by hand.
Each entry names one member as its "anchor", so names stay with the right group if
the cluster numbers change. Hues are assigned so that clusters sitting next to each
other on the map are the easiest to tell apart, and "hollow" gives the ninth cluster
a second look in a shared hue rather than a ninth color. If you change the number of
clusters in the notebook, this script tells you which clusters need a name.

    python3 scripts/build_map_data.py

Needs numpy, plus the paper records from scripts/fetch_papers.py.
"""

import datetime as dt
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "map-data.js")

N_TERMS = 40     # per person, searchable; the page shows the first few
N_TOPICS = 5
N_PAPERS = 5
N_SIMILAR = 5
N_EXAMPLES = 8   # shared papers listed per collaboration
N_STUDENT_PAPERS = 6
PHOTO_SIZE = (240, 300)   # twice the size it's shown at, for sharp screens
# Conference abstracts and preprints are fine as evidence but poor reading suggestions.
LISTED_TYPES = {"article", "review", "book-chapter", "letter", "conference-paper", "preprint"}


def load_json(*path):
    with open(os.path.join(DATA, *path), encoding="utf-8") as f:
        return json.load(f)


def distinct_terms(terms, limit):
    """Drop terms whose words all appear in a term already kept ("genome" after
    "genome assembly"), so a short list says more."""
    kept, seen = [], set()
    for term in terms:
        words = set(term.split())
        if words <= seen:
            continue
        kept.append(str(term))
        seen |= words
        if len(kept) == limit:
            break
    return kept


def paper_link(doi, work_id):
    return f"https://doi.org/{doi}" if doi else f"https://openalex.org/{work_id}"


def recent_papers(pid, works):
    """Most recent papers where the person is first or last author, topped up with
    their other recent papers if they have few."""
    theirs = [w for w in works
              if w["faculty"].get(pid, {}).get("keep") and not w["duplicate_of"]
              and w["year"] and w["type"] in LISTED_TYPES]
    theirs.sort(key=lambda w: (w["faculty"][pid].get("position") not in ("first", "last"),
                               -w["year"], -w["cited_by"]))
    return [{"t": w["title"], "y": w["year"], "v": w["venue"], "u": paper_link(w["doi"], w["id"])}
            for w in theirs[:N_PAPERS]]


def photo_url(src):
    """Many scraped links are blurred loading placeholders, but Wix serves any size of
    the same file. Photos stay on the department's site, so they follow its updates."""
    m = re.search(r"/media/([^/]+?\.(?:jpe?g|png|webp|avif))", src or "", re.I)
    if not m:
        return None
    w, h = PHOTO_SIZE
    return f"https://static.wixstatic.com/media/{m.group(1)}/v1/fill/w_{w},h_{h},al_c,q_85/{m.group(1)}"


def career(pid, works, through):
    """h-index, citations and papers per year, from the same papers as the rest of the
    map. A preprint and its journal version count once, with the higher citation count."""
    cited, year = {}, {}
    for w in works:
        if (w["faculty"].get(pid) or {}).get("keep"):
            key = w["duplicate_of"] or w["id"]
            cited[key] = max(cited.get(key, 0), w["cited_by"] or 0)
            if w["year"]:
                year[key] = min(year.get(key, w["year"]), w["year"])
    ranked = sorted(cited.values(), reverse=True)
    first = min(year.values())
    counts = [0] * (through - first + 1)
    for y in year.values():
        if y <= through:
            counts[y - first] += 1
    return {"h": sum(c >= i + 1 for i, c in enumerate(ranked)), "cites": sum(ranked), "years": [first, counts]}


def student_entry(student):
    return {"name": student["name"], "n": len(student["papers"]),
            "p": [{"t": x["title"], "y": x["year"], "v": x["venue"], "u": paper_link(x["doi"], x["id"]),
                   "first": x["position"] == "first"} for x in student["papers"][:N_STUDENT_PAPERS]]}


def name_clusters(layout, ids):
    """Cluster number -> entry in cluster-names.json, checked against the layout."""
    entries = load_json("cluster-names.json")
    cluster_of = {f["id"]: f["cluster"] for f in layout["faculty"]}
    named = {}
    for entry in entries:
        c = cluster_of.get(entry["anchor"])
        if c is None:
            sys.exit(f"cluster-names.json: {entry['anchor']} isn't on the map")
        if c in named:
            sys.exit(f"cluster-names.json: {entry['anchor']} and {named[c]['anchor']} are in the same cluster")
        named[c] = entry
    missing = sorted(set(cluster_of.values()) - set(named))
    if missing:
        groups = [", ".join(f["label"] for f in layout["faculty"] if f["cluster"] == c) for c in missing]
        sys.exit("Add these clusters to data/cluster-names.json:\n  " + "\n  ".join(groups))
    return named


def label_anchor(xy):
    """Where to label a cluster: the middle of its densest part, since a cluster can
    be split across the map."""
    if len(xy) <= 2:
        return xy.mean(axis=0)
    d = np.linalg.norm(xy[:, None] - xy[None], axis=-1)
    centre = xy[np.argmin(np.median(d, axis=1))]
    near = xy[np.linalg.norm(xy - centre, axis=1) <= 0.2]
    return near.mean(axis=0)


def main():
    layout = load_json("layout.json")
    roster = {p["id"]: p for p in load_json("faculty.json")["faculty"]}
    edges = load_json("edges.json")["edges"]
    works = list(load_json("papers", "papers.json")["works"].values())
    feats = np.load(os.path.join(DATA, "features", "faculty-features.npz"))
    labs = load_json("labs.json")
    through = dt.date.fromtimestamp(os.path.getmtime(os.path.join(DATA, "papers", "papers.json"))).year

    people = layout["faculty"]
    ids = [p["id"] for p in people]
    index = {pid: i for i, pid in enumerate(ids)}
    rows = [list(feats["faculty_ids"]).index(pid) for pid in ids]
    named = name_clusters(layout, ids)
    views = list(layout["layouts"])

    tfidf = feats["tfidf"][rows]
    vocab = feats["tfidf_vocab"]
    topics, topic_names = feats["topics"][rows], feats["topic_names"]
    n_papers = feats["n_papers"][rows]

    X = feats[layout["representation"]][rows].astype(float)
    X = X - X.mean(axis=0)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    sim = X @ X.T
    similarity = np.round(sim, 3).tolist()   # lets a thrown dot be compared with everyone
    np.fill_diagonal(sim, -np.inf)

    out_people = []
    for i, p in enumerate(people):
        r = roster[p["id"]]
        top_topics = np.argsort(-topics[i])[:N_TOPICS]
        person = {
            "id": p["id"], "name": r["name"], "label": p["label"], "group": r["group"],
            "title": r["title"], "dept": r["home_department"], "website": r["website"],
            "profile": r["profile"], "cluster": p["cluster"], "n": int(n_papers[i]),
            "terms": distinct_terms(vocab[np.argsort(-tfidf[i])[:N_TERMS * 3]], N_TERMS),
            "topics": [[str(topic_names[k]), round(float(topics[i][k]), 3)] for k in top_topics],
            "papers": recent_papers(p["id"], works),
            "similar": [int(k) for k in np.argsort(-sim[i])[:N_SIMILAR]],
            "photo": photo_url(r["photo"]),
            "lab": {k: labs["labs"][p["id"]][k] for k in ("size", "source", "url", "note")},
            "students": [student_entry(s) for s in labs["students"] if p["id"] in s["labs"]],
            **career(p["id"], works, through),
        }
        person.update({v: p[v] for v in views})
        out_people.append(person)

    clusters = []
    for c in sorted(named):
        members = np.array([f["cluster"] == c for f in people])
        lift = tfidf[members].mean(axis=0) - tfidf.mean(axis=0)
        clusters.append({
            "name": named[c]["name"], "color": named[c]["color"], "hollow": bool(named[c].get("hollow")),
            "size": int(members.sum()),
            "terms": distinct_terms(vocab[np.argsort(-lift)[:40]], 8),
            "anchor": {v: [round(float(t), 4) for t in label_anchor(np.array([f[v] for f in people])[members])]
                       for v in views},
        })

    out_edges = []
    for e in edges:
        if e["source"] in index and e["target"] in index:
            out_edges.append({
                "a": index[e["source"]], "b": index[e["target"]], "s": e["strength"], "n": e["papers"],
                "size": [e["by_size"][k] for k in ("2-10", "11-50", "51+")], "usc": e["at_usc"],
                "y0": e["first_year"], "y1": e["last_year"],
                "ex": [{"t": x["title"], "y": x["year"], "a": x["authors"], "v": x["venue"],
                        "u": f"https://openalex.org/{x['id']}"} for x in e["examples"][:N_EXAMPLES]],
            })

    tree = layout["tree"]
    merges = tree["merges"]
    n, k = len(people), tree["k"]
    out = {
        "meta": {
            "faculty": n,
            "papers": sum(1 for w in works if not w["duplicate_of"] and any(
                i["keep"] and pid in index for pid, i in w["faculty"].items())),
            "representation": layout["representation"],
            "layouts": layout["layouts"],
            "through": through,
            "students": len(labs["students"]),
            "noLab": labs["no_lab_yet"],
            "labSources": {k or "none": sum(v["source"] == k for v in labs["labs"].values()) for k in ("website", "estimate", None)},
        },
        "clusters": clusters,
        "people": out_people,
        "edges": out_edges,
        "similarity": similarity,
        "tree": {
            "merges": [[m["left"], m["right"], m["height"]] for m in merges],
            "order": [index[pid] for pid in tree["leaf_order"]],
            "k": k,
            "cut": round((merges[n - k - 1]["height"] + merges[n - k]["height"]) / 2, 4),
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Generated by scripts/build_map_data.py. Don't edit by hand.\n")
        f.write("window.QCB_MAP = ")
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({os.path.getsize(OUT) / 1000:.0f} KB): {n} faculty, "
          f"{len(out_edges)} edges, {len(clusters)} clusters, {out['meta']['papers']} papers")


if __name__ == "__main__":
    main()
