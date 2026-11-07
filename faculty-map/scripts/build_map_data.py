#!/usr/bin/env python3
"""Build map-data.js and map-data-extended.js, the data files the interactive map loads.

map-data.js is what the page opens with: the QCB faculty. Combines data/faculty.json
(who they are), data/edges.json (collaborations), data/features/faculty-features.npz
(research terms, topics), data/papers/papers.json (recent papers, citations, papers by
year), data/labs.json (lab sizes and PhD students, from scripts/build_labs.py) and
data/lab-methods.json (methods, from scripts/build_methods.py).

map-data-extended.js is loaded when someone expands into related fields. It adds the
other people in scripts/combined.py after the QCB faculty, so a person's number means
the same in both files. Their lab sizes are the website counts in data/lab-sizes.json.

Each file holds "worlds", one for each way of arranging its people:

    qcb/field        data/layout.json                 data/cluster-names.json
    qcb/technique    data/layout-methods.json         data/cluster-names-methods.json
    all/field        data/layout-extended.json        data/cluster-names-extended.json
    all/technique    data/layout-extended-methods.json   data/cluster-names-extended-methods.json

Layouts come from the notebooks, and their 3D twins from scripts/build_layouts_3d.py.
Cluster names and colors are written by hand. Each
entry names one member as its "anchor", so names stay with the right group if the
cluster numbers change. Hues are assigned so that clusters sitting next to each other
on the map are the easiest to tell apart, and "hollow" gives a cluster past the eighth
a second look in a shared hue rather than another color. If you change the number of
clusters in a notebook, this script tells you which clusters need a name.

    python3 scripts/build_map_data.py

Needs numpy, plus the paper records from scripts/fetch_papers.py.
"""

import datetime as dt
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combined  # noqa: E402
import stamp_page  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "map-data.js")
OUT_EXTENDED = os.path.join(ROOT, "map-data-extended.js")

N_TERMS = 40     # per person, searchable; the page shows the first few
N_TOPICS = 5
N_PAPERS = 5
N_SIMILAR = 5
N_EXAMPLES = 8   # shared papers listed per collaboration
N_STUDENT_PAPERS = 6
N_GROUP_METHODS = 5   # listed for a technique cluster
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
        return src or None
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


def method_entry(row, index):
    """What the panel shows for one method at one lab. Levels match scripts/build_methods.py."""
    x = row["example"]
    return {"m": index[row["method"]], "l": row["level"], "s": row["share"], "n": row["papers"], "of": row["of"],
            "w": row["website"], "f": row["firsthand"],
            "x": x and {"t": x["title"], "y": x["year"], "v": x["venue"], "u": paper_link(x["doi"], x["id"])}}


def name_clusters(layout, names):
    """Cluster number -> entry in the names file, checked against the layout."""
    entries = load_json(names)
    cluster_of = {f["id"]: f["cluster"] for f in layout["faculty"]}
    named = {}
    for entry in entries:
        c = cluster_of.get(entry["anchor"])
        if c is None:
            sys.exit(f"{names}: {entry['anchor']} isn't on the map")
        if c in named:
            sys.exit(f"{names}: {entry['anchor']} and {named[c]['anchor']} are in the same cluster")
        named[c] = entry
    missing = sorted(set(cluster_of.values()) - set(named))
    if missing:
        groups = [", ".join(f["label"] for f in layout["faculty"] if f["cluster"] == c) for c in missing]
        sys.exit(f"Add these clusters to data/{names}:\n  " + "\n  ".join(groups))
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


def tree_of(layout, index):
    """The layout's tree, with its leaves renumbered to match the page's people."""
    tree, merges, n = layout["tree"], layout["tree"]["merges"], len(layout["faculty"])
    leaves = [index[f["id"]] for f in layout["faculty"]]
    node = lambda a: leaves[a] if a < n else a   # noqa: E731
    k = tree["k"]
    return {
        "merges": [[node(m["left"]), node(m["right"]), m["height"]] for m in merges],
        "order": [index[pid] for pid in tree["leaf_order"]],
        "k": k,
        "cut": round((merges[n - k - 1]["height"] + merges[n - k]["height"]) / 2, 4),
    }


def build_world(layout_file, names, ids, X, apart, stats, labels=None):
    """One way of arranging `ids`, who are always the page's first len(ids) people.

    X is one row of features per person. apart(members) says what sets a cluster apart.
    """
    layout = load_json(layout_file)
    solid = load_json("layouts-3d.json")[layout_file]
    by_id = {f["id"]: f for f in layout["faculty"]}
    if set(by_id) != set(ids):
        sys.exit(f"{layout_file} has different people from the map")
    people = [by_id[pid] for pid in ids]
    index = {pid: i for i, pid in enumerate(ids)}
    named = name_clusters(layout, names)
    views = list(layout["layouts"])

    if layout["representation"] == "specter":
        X = X - X.mean(axis=0)
    X = X / np.linalg.norm(X, axis=1, keepdims=True)
    sim = X @ X.T
    similarity = np.round(sim, 3).tolist()   # lets a thrown dot be compared with everyone
    np.fill_diagonal(sim, -np.inf)

    clusters = []
    for c in sorted(named):
        members = np.array([f["cluster"] == c for f in people])
        clusters.append({
            "name": named[c]["name"], "color": named[c]["color"], "hollow": bool(named[c].get("hollow")),
            "size": int(members.sum()),
            "terms": apart(members),
            "anchor": {v: [round(float(t), 4) for t in label_anchor(np.array([f[v] for f in people])[members])]
                       for v in views},
        })
    return {
        "n": len(ids),
        "views": [[v, layout["layouts"][v]["name"]] for v in views],
        "xy": {v: [f[v] for f in people] for v in views},
        "xyz": {v: [solid[v]["people"][pid] for pid in ids] for v in views},
        "cluster": [f["cluster"] for f in people],
        "labels": labels or [f["label"] for f in people],
        "similar": [[int(k) for k in np.argsort(-sim[i])[:N_SIMILAR]] for i in range(len(ids))],
        "similarity": similarity,
        "clusters": clusters,
        "tree": tree_of(layout, index),
        **stats,
    }


def out_edge(e, index):
    return {
        "a": index[e["source"]], "b": index[e["target"]], "s": e["strength"], "n": e["papers"],
        "size": [e["by_size"][k] for k in ("2-10", "11-50", "51+")], "usc": e["at_usc"],
        "y0": e["first_year"], "y1": e["last_year"],
        "ex": [{"t": x["title"], "y": x["year"], "a": x["authors"], "v": x["venue"],
                "u": f"https://openalex.org/{x['id']}"} for x in e["examples"][:N_EXAMPLES]],
    }


def write_js(path, name, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write("// Generated by scripts/build_map_data.py. Don't edit by hand.\n")
        f.write(f"window.{name} = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")


def count_papers(works, ids):
    ids = set(ids)
    return sum(1 for w in works if not w["duplicate_of"] and any(
        i["keep"] and pid in ids for pid, i in w["faculty"].items()))


def person_entry(pid, r, tfidf, vocab, topics, topic_names, n_papers, works, through):
    """Everything about a person that doesn't depend on how the map is arranged."""
    top_topics = np.argsort(-topics)[:N_TOPICS]
    return {
        "id": pid, "name": r["name"], "dept": r["home_department"], "title": r["title"],
        "profile": r["profile"], "email": r.get("email"), "n": int(n_papers),
        "terms": distinct_terms(vocab[np.argsort(-tfidf)[:N_TERMS * 3]], N_TERMS),
        "topics": [[str(topic_names[k]), round(float(topics[k]), 3)] for k in top_topics],
        "papers": recent_papers(pid, works),
        "photo": photo_url(r["photo"]),
        **career(pid, works, through),
    }


def main():
    layout = load_json("layout.json")
    roster = {p["id"]: p for p in load_json("faculty.json")["faculty"]}
    edges = load_json("edges.json")["edges"]
    works = list(load_json("papers", "papers.json")["works"].values())
    feats = np.load(os.path.join(DATA, "features", "faculty-features.npz"))
    labs = load_json("labs.json")
    through = dt.date.fromtimestamp(os.path.getmtime(os.path.join(DATA, "papers", "papers.json"))).year
    evidence = load_json("lab-methods.json")
    method_index = {m["id"]: k for k, m in enumerate(evidence["methods"])}
    method_names = [m["name"] for m in evidence["methods"]]
    M = np.load(os.path.join(DATA, "features", "methods-features.npz"))
    method_rows = {pid: i for i, pid in enumerate(M["faculty_ids"].tolist())}

    def methods_of(pid):
        return [method_entry(row, method_index) for row in evidence["labs"][pid]]

    def technique(ids):
        """Rows of the technique features for ids, and what sets a group of them apart."""
        X = M["methods"][[method_rows[pid] for pid in ids]].astype(float)
        def apart(members):
            lift = X[members].mean(axis=0) - X.mean(axis=0)
            return [method_names[k] for k in np.argsort(-lift)[:N_GROUP_METHODS]]
        return X, apart

    def words_apart(tfidf, vocab):
        """What sets a group apart by research words."""
        def apart(members):
            lift = tfidf[members].mean(axis=0) - tfidf.mean(axis=0)
            return distinct_terms(vocab[np.argsort(-lift)[:40]], 8)
        return apart

    ids = [p["id"] for p in layout["faculty"]]
    index = {pid: i for i, pid in enumerate(ids)}
    qcb_labels = [p["label"] for p in layout["faculty"]]
    rows = [list(feats["faculty_ids"]).index(pid) for pid in ids]
    tfidf, vocab = feats["tfidf"][rows], feats["tfidf_vocab"]
    topics, topic_names = feats["topics"][rows], feats["topic_names"]
    n_papers = feats["n_papers"][rows]

    out_people = []
    for i, pid in enumerate(ids):
        r = roster[pid]
        person = person_entry(pid, r, tfidf[i], vocab, topics[i], topic_names, n_papers[i], works, through)
        person.update({
            "group": r["group"], "website": r["website"],
            "lab": {k: labs["labs"][pid][k] for k in ("size", "source", "url", "note")},
            "students": [student_entry(s) for s in labs["students"] if pid in s["labs"]],
            "methods": methods_of(pid),
        })
        out_people.append(person)

    out_edges = [out_edge(e, index) for e in edges if e["source"] in index and e["target"] in index]
    papers = count_papers(works, ids)
    stats = {"papers": papers, "edges": len(out_edges)}
    out = {
        "meta": {
            "through": through,
            "students": len(labs["students"]),
            "noLab": labs["no_lab_yet"],
            "labSources": {k or "none": sum(v["source"] == k for v in labs["labs"].values()) for k in ("website", "estimate", None)},
        },
        "methods": [{"name": m["name"], "family": m["family"]} for m in evidence["methods"]],
        "people": out_people,
        "edges": out_edges,
        "worlds": {
            "qcb/field": build_world("layout.json", "cluster-names.json", ids, feats[layout["representation"]][rows].astype(float),
                                     words_apart(tfidf, vocab), stats),
            "qcb/technique": build_world("layout-methods.json", "cluster-names-methods.json", ids, *technique(ids), stats, qcb_labels),
        },
    }
    # The expanded map: the same people first, then everyone else, so numbers carry over.
    wide = load_json("layout-extended.json")
    everyone = {p["id"]: p for p in combined.people()}
    sizes = load_json("lab-sizes.json")["labs"]
    all_ids = ids + [p["id"] for p in wide["faculty"] if p["id"] not in index]
    all_index = {pid: i for i, pid in enumerate(all_ids)}
    all_works = list(combined.works().values())
    F = np.load(os.path.join(DATA, "features", "extended-features.npz"))
    rows = [list(F["faculty_ids"]).index(pid) for pid in all_ids]
    tfidf, vocab = F["tfidf"][rows], F["tfidf_vocab"]
    topics, topic_names = F["topics"][rows], F["topic_names"]
    n_papers = F["n_papers"][rows]

    new_people = []
    for i, pid in enumerate(all_ids):
        if pid in index:
            continue
        r, lab = everyone[pid], sizes.get(pid, {})
        person = person_entry(pid, r, tfidf[i], vocab, topics[i], topic_names, n_papers[i], all_works, through)
        counted = lab.get("members")
        person.update({
            "group": "related", "website": lab.get("website") or r.get("website"),
            "lab": {"size": counted or 0, "source": "website" if counted else None,
                    "url": (lab.get("people_page") or lab.get("website")) if counted else None, "note": None},
            "students": [],
            "methods": methods_of(pid),
        })
        new_people.append(person)

    all_edges = load_json("edges-extended.json")["edges"]
    new_edges = [out_edge(e, all_index) for e in all_edges
                 if e["source"] in all_index and e["target"] in all_index
                 and not (e["source"] in index and e["target"] in index)]
    stats = {"papers": count_papers(all_works, all_ids), "edges": len(out_edges) + len(new_edges)}
    wide_labels = {p["id"]: p["label"] for p in wide["faculty"]}
    labels = [wide_labels[pid] for pid in all_ids]
    extended = {
        "people": new_people,
        "edges": new_edges,
        "worlds": {
            "all/field": build_world("layout-extended.json", "cluster-names-extended.json", all_ids, F[wide["representation"]][rows].astype(float),
                                     words_apart(tfidf, vocab), stats, labels),
            "all/technique": build_world("layout-extended-methods.json", "cluster-names-extended-methods.json", all_ids, *technique(all_ids), stats, labels),
        },
    }
    research = load_json("lab-research.json")["labs"]
    out["meta"]["wide"] = {
        "faculty": len(all_ids), "added": len(new_people), "papers": stats["papers"],
        "readLabs": sum(bool(research[pid]["pages"]) for pid in all_ids),
        "counted": sum(p["lab"]["source"] == "website" for p in new_people),
        "unknown": sum(p["lab"]["source"] is None for p in new_people),
    }
    write_js(OUT, "QCB_MAP", out)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({os.path.getsize(OUT) / 1000:.0f} KB): {len(ids)} faculty, "
          f"{len(out_edges)} edges, {papers} papers")
    write_js(OUT_EXTENDED, "QCB_MAP_EXTENDED", extended)
    print(f"wrote {os.path.relpath(OUT_EXTENDED, ROOT)} ({os.path.getsize(OUT_EXTENDED) / 1000:.0f} KB): "
          f"{len(all_ids)} faculty, {stats['edges']} edges, {stats['papers']} papers")
    stamp_page.stamp()


if __name__ == "__main__":
    main()
