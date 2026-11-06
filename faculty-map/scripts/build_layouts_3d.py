#!/usr/bin/env python3
"""Work out the map's 3D view: data/layouts-3d.json.

Every flat layout the notebooks export gets a 3D twin, from the same method, settings
and features with a third component. Choosing a layout stays the notebooks' job: this
script reads each file's "representation" and "settings", so changing them there and
rerunning here keeps the two views in step.

Each twin is turned to line up with its flat map (orthogonal Procrustes), so the 3D view
starts out looking like the map it came from, then scaled to fit inside a unit sphere.

    python3 scripts/build_layouts_3d.py

It also reports trustworthiness for both, the check the notebooks use: how far each
person's closest neighbors on the map are their real closest neighbors.
"""

import json
import os
import warnings

import numpy as np
from sklearn.manifold import MDS, TSNE, trustworthiness

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "layouts-3d.json")

LAYOUTS = {
    "layout.json": "faculty-features.npz",
    "layout-methods.json": "faculty-features.npz",
    "layout-extended.json": "extended-features.npz",
    "layout-extended-methods.json": "extended-features.npz",
}
NEIGHBORS = 5   # the notebooks' trustworthiness setting
TSNE_RATE = 25
TSNE_RUNS = 5


def unit_rows(X):
    X = np.asarray(X, dtype=float)
    n = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.where(n == 0, 1, n)


def distances(layout, features):
    """Cosine distances between the people in a layout, as in the notebooks."""
    ids = [p["id"] for p in layout["faculty"]]
    if layout["representation"] == "methods":
        M = np.load(os.path.join(DATA, "features", "methods-features.npz"))
        rows = [list(M["faculty_ids"]).index(pid) for pid in ids]
        X = unit_rows(M["methods"][rows])
    else:
        F = np.load(os.path.join(DATA, "features", features))
        rows = [list(F["faculty_ids"]).index(pid) for pid in ids]
        spec = F[layout["representation"]][rows]
        X = unit_rows(spec - spec.mean(axis=0))
    D = np.clip(1 - X @ X.T, 0, None)
    np.fill_diagonal(D, 0)
    return D


def embed(key, settings, D):
    if key == "tsne":
        # scikit-learn's defaults stall at a poor map in 3D with this few people, so this
        # runs slower and steadier, keeping the best of a few by t-SNE's own measure.
        # Each run needs its own copy: the exact method squares the distances in place.
        runs = [TSNE(n_components=3, perplexity=settings["perplexity"], metric="precomputed", init="random",
                     method="exact", learning_rate=TSNE_RATE, max_iter=3000, random_state=seed) for seed in range(TSNE_RUNS)]
        maps = [run.fit_transform(D.copy()) for run in runs]
        return maps[int(np.argmin([run.kl_divergence_ for run in runs]))]
    if key == "mds":
        return MDS(n_components=3, dissimilarity="precomputed", metric=True, n_init=8, random_state=0,
                   normalized_stress="auto").fit_transform(D)
    import umap   # slow to import, and only some layouts need it
    return umap.UMAP(n_components=3, n_neighbors=settings["n_neighbors"], min_dist=settings["min_dist"],
                     metric="precomputed", random_state=0).fit_transform(D)


def line_up(Z, flat):
    """Turn Z so that looking along its third axis shows the flat map as nearly as possible."""
    A = Z - Z.mean(axis=0)
    B = np.c_[flat - flat.mean(axis=0), np.zeros(len(flat))]
    U, _, Vt = np.linalg.svd(A.T @ B)
    A = A @ (U @ Vt)
    return A / np.linalg.norm(A, axis=1).max()


def main():
    warnings.filterwarnings("ignore", module="umap")   # notes about precomputed distances and seeds
    out = {}
    for name, features in LAYOUTS.items():
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            layout = json.load(f)
        D = distances(layout, features)
        out[name] = {}
        for key, spec in layout["layouts"].items():
            flat = np.array([p[key] for p in layout["faculty"]])
            Z = line_up(embed(key, spec["settings"], D), flat)
            trust = [trustworthiness(D, z, n_neighbors=NEIGHBORS, metric="precomputed") for z in (flat, Z)]
            out[name][key] = {
                "trust": {"flat": round(float(trust[0]), 3), "solid": round(float(trust[1]), 3)},
                "people": {p["id"]: [round(float(v), 4) for v in z] for p, z in zip(layout["faculty"], Z)},
            }
            print(f"{name} {spec['name']}: trustworthiness {trust[0]:.3f} flat, {trust[1]:.3f} in 3D")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({os.path.getsize(OUT) / 1000:.0f} KB)")


if __name__ == "__main__":
    main()
