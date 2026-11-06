#!/usr/bin/env python3
"""Turn each faculty member's papers into feature vectors for the similarity map.

Reads the kept papers in data/papers/papers.json and builds three representations
of every core, joint and emeritus faculty member:

- tfidf:   words and two-word phrases from titles, abstracts and keywords. Each paper
           becomes a term-frequency vector, a person's vector is the weighted mean of
           their papers', and terms are weighted by how few *faculty* use them (IDF over
           the 48 people, not over papers, so Thompson's 2,500 papers don't set the
           vocabulary's weights).
- topics:  OpenAlex's topic labels (about 4,500 topics; each paper has up to 3, with
           scores), as a weighted distribution per person. Also coarser distributions
           over subfields and fields, from each paper's primary topic.
- specter: SPECTER2 embeddings (allenai/specter2 with its proximity adapter), a model
           trained so that papers citing each other land close together. Each paper's
           title and abstract becomes a 768-number vector; a person's vector is the
           weighted mean of their papers'.

Paper weights: papers from the last ten years count most (weight halves every
HALF_LIFE years), papers where the person is first or last author count fully and
middle-author papers half, and consortium papers (more than 50 authors) half again.
The notebook can redo this weighting if you want to experiment with it.

Writes data/features/faculty-features.npz (small, committed; what the notebook loads)
and data/features/features-report.md (top terms, topics and nearest neighbours for
checking by eye). Paper embeddings are cached in data/papers/specter2.npz.

Embeddings need the `adapters` library, installed in this project's virtual
environment so it can't disturb other Python work:

    python3 -m venv --system-site-packages .venv
    .venv/bin/python -m pip install adapters
    .venv/bin/python scripts/build_features.py

Without `adapters` (and no cache), the script builds tfidf and topics and skips
specter. The model download is about 440 MB, cached in ~/.cache/huggingface.

With --extended, this covers everyone in scripts/combined.py and writes
data/features/extended-features.npz and extended-features-report.md. New embeddings go
to data/papers/specter2-extended.npz; the QCB cache is read but never changed.
"""

import argparse
import collections
import datetime as dt
import json
import math
import os
import re
import sys

# torch has to load its OpenMP runtime before scikit-learn loads its own, or the
# embedding step segfaults on macOS. So import it first whenever it's installed.
try:
    import torch
except ImportError:
    torch = None

import numpy as np  # noqa: E402
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACULTY = os.path.join(ROOT, "data", "faculty.json")
PAPERS = os.path.join(ROOT, "data", "papers", "papers.json")
EMBED_CACHE = os.path.join(ROOT, "data", "papers", "specter2.npz")
OUT_DIR = os.path.join(ROOT, "data", "features")
FEATURES = os.path.join(OUT_DIR, "faculty-features.npz")
REPORT = os.path.join(OUT_DIR, "features-report.md")
QCB_EMBED_CACHE = EMBED_CACHE
EXTENDED_EMBED_CACHE = os.path.join(ROOT, "data", "papers", "specter2-extended.npz")
EXTENDED_FEATURES = os.path.join(OUT_DIR, "extended-features.npz")
EXTENDED_REPORT = os.path.join(OUT_DIR, "extended-features-report.md")

GROUPS = ("core", "joint", "emeritus")
HALF_LIFE = 10  # years
MIDDLE_AUTHOR = 0.5
CONSORTIUM = 0.5  # extra factor for papers with more than 50 authors

MODEL = "allenai/specter2_base"
# The main branch only has pickled weights, which recent transformers refuses to load
# with torch < 2.6; the Hub's safetensors conversion lives on this pull request.
MODEL_REVISION = "refs/pr/10"
ADAPTER = "allenai/specter2"

# Words that say nothing about research content: abstract headings and publisher text.
EXTRA_STOP = {
    "abstract", "background", "objective", "objectives", "methods", "method", "results", "result",
    "conclusion", "conclusions", "introduction", "purpose", "study", "studies", "paper", "article",
    "review", "using", "used", "use", "uses", "based", "show", "shows", "shown", "showed", "demonstrate",
    "demonstrated", "present", "presented", "propose", "proposed", "report", "reported", "find", "found",
    "findings", "approach", "approaches", "new", "novel", "investigate", "investigated", "including",
    "suggest", "suggests", "provide", "provides", "potential", "important", "significant",
    "significantly", "associated", "associations", "association", "high", "higher", "low", "lower",
    "increase", "increased", "different", "differences", "compared", "related", "role", "effect",
    "effects", "analysis", "analyses", "data", "work", "however", "also", "may", "well", "one", "two",
    "elsevier", "copyright", "rights", "reserved", "published", "publisher", "wiley", "springer",
    "society", "license", "licensee", "ltd", "inc", "author", "authors", "press", "journal", "url",
    "http", "https", "www", "doi", "org", "jats", "figure", "figures", "fig", "table", "tables",
    "supplementary", "supplemental",
}
STOP_WORDS = sorted(ENGLISH_STOP_WORDS | EXTRA_STOP)


# ---------------------------------------------------------------- inputs

def load(extended=False):
    if extended:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import combined
        faculty, works = combined.people(), combined.works()
    else:
        with open(FACULTY, encoding="utf-8") as f:
            faculty = [p for p in json.load(f)["faculty"] if p["group"] in GROUPS]
        with open(PAPERS, encoding="utf-8") as f:
            works = json.load(f)["works"]
    papers = [w for w in works.values()
              if not w["duplicate_of"] and any(i["keep"] for i in w["faculty"].values())]
    papers.sort(key=lambda w: w["id"])
    return faculty, papers


def paper_text(w):
    parts = [w["title"], w["abstract"] or "", " ".join(w["keywords"])]
    return re.sub(r"<[^>]+>", " ", " ".join(parts))


def weight_matrix(faculty, papers, half_life):
    """W[i, j] = weight of paper j in faculty member i's profile (0 if not theirs)."""
    index = {p["id"]: i for i, p in enumerate(faculty)}
    now = max((w["year"] or 0) for w in papers)
    W = np.zeros((len(faculty), len(papers)), dtype=np.float64)
    for j, w in enumerate(papers):
        age = max(now - (w["year"] or now), 0)
        recency = 0.5 ** (age / half_life)
        size = CONSORTIUM if w["n_authors"] > 50 else 1.0
        for pid, info in w["faculty"].items():
            if info["keep"] and pid in index:
                role = 1.0 if info.get("position") in ("first", "last") else MIDDLE_AUTHOR
                W[index[pid], j] = recency * role * size
    return W, now


def normalize_rows(X):
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.where(norms == 0, 1, norms)


# ---------------------------------------------------------------- representations

def build_tfidf(papers, W):
    vec = CountVectorizer(stop_words=STOP_WORDS, ngram_range=(1, 2), min_df=5, max_df=0.3,
                          token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b", max_features=40000)
    counts = vec.fit_transform(paper_text(w) for w in papers).astype(np.float64)
    counts.data = np.log1p(counts.data)  # sublinear term frequency
    lengths = np.asarray(counts.sum(axis=1)).ravel()
    lengths[lengths == 0] = 1
    tf_papers = counts.multiply(1 / lengths[:, None]).tocsr()
    totals = W.sum(axis=1, keepdims=True)
    tf = np.asarray((W / np.where(totals == 0, 1, totals)) @ tf_papers)
    df = (tf > 0).sum(axis=0)
    idf = np.log((1 + len(tf)) / (1 + df)) + 1
    X = normalize_rows(tf * idf)
    # Terms used by only one person can't make two people similar; drop them so the
    # committed matrix stays small. Dot products between rows are unchanged.
    shared = df >= 2
    return X[:, shared].astype(np.float32), vec.get_feature_names_out()[shared].astype(str)


def build_topics(papers, W):
    topic_names, sub_names, field_names = {}, set(), set()
    for w in papers:
        for tid, name, _ in w["topics"]:
            topic_names[tid] = name
        if w["topic"]:
            sub_names.add(w["topic"]["subfield"])
            field_names.add(w["topic"]["field"])
    topic_ids = sorted(topic_names)
    subs, fields = sorted(sub_names), sorted(field_names)
    ti = {t: k for k, t in enumerate(topic_ids)}
    si = {s: k for k, s in enumerate(subs)}
    fi = {f: k for k, f in enumerate(fields)}
    P_topic = np.zeros((len(papers), len(topic_ids)))
    P_sub = np.zeros((len(papers), len(subs)))
    P_field = np.zeros((len(papers), len(fields)))
    for j, w in enumerate(papers):
        for tid, _, score in w["topics"]:
            P_topic[j, ti[tid]] += score
        if w["topic"]:
            P_sub[j, si[w["topic"]["subfield"]]] = 1
            P_field[j, fi[w["topic"]["field"]]] = 1

    def distribution(P):
        X = W @ P
        sums = X.sum(axis=1, keepdims=True)
        return (X / np.where(sums == 0, 1, sums)).astype(np.float32)

    return {
        "topics": distribution(P_topic),
        "topic_ids": np.array(topic_ids),
        "topic_names": np.array([topic_names[t] for t in topic_ids]),
        "subfields": distribution(P_sub),
        "subfield_names": np.array(subs),
        "fields": distribution(P_field),
        "field_names": np.array(fields),
    }


def embed_papers(papers, batch_size=32):
    """SPECTER2 vectors for every paper, reusing cached ones. None if unavailable."""
    cached = {}
    for path in dict.fromkeys((QCB_EMBED_CACHE, EMBED_CACHE)):
        if os.path.exists(path):
            z = np.load(path)
            cached.update(zip(z["ids"].tolist(), z["vectors"]))
    todo = [w for w in papers if w["id"] not in cached]
    if todo:
        try:
            from adapters import AutoAdapterModel
            from transformers import AutoTokenizer
            if torch is None:
                raise ImportError("torch")
        except ImportError:
            print("! `adapters` isn't installed, so skipping SPECTER2 embeddings "
                  "(see the top of this script).", file=sys.stderr)
            return None
        print(f"embedding {len(todo)} papers with SPECTER2 ...")
        tok = AutoTokenizer.from_pretrained(MODEL)
        model = AutoAdapterModel.from_pretrained(MODEL, revision=MODEL_REVISION)
        model.load_adapter(ADAPTER, source="hf", load_as="proximity", set_active=True)
        device = "mps" if torch.backends.mps.is_available() else (
            "cuda" if torch.cuda.is_available() else "cpu")
        model.to(device).eval()
        # Shortest first keeps padding (wasted work) per batch small.
        todo.sort(key=lambda w: len(w["title"]) + len(w["abstract"] or ""))
        for start in range(0, len(todo), batch_size):
            batch = todo[start:start + batch_size]
            texts = [w["title"] + tok.sep_token + (w["abstract"] or "") for w in batch]
            inputs = tok(texts, padding=True, truncation=True, max_length=512,
                         return_tensors="pt", return_token_type_ids=False).to(device)
            with torch.no_grad():
                out = model(**inputs).last_hidden_state[:, 0, :].float().cpu().numpy()
            for w, v in zip(batch, out):
                cached[w["id"]] = v.astype(np.float16)
            done = start + len(batch)
            if done % 1024 < batch_size or done == len(todo):
                print(f"  {done}/{len(todo)}")
                save_embeddings(cached)
        save_embeddings(cached)
    return np.stack([np.asarray(cached[w["id"]], dtype=np.float32) for w in papers])


def save_embeddings(cached):
    ids = sorted(cached)
    np.savez_compressed(EMBED_CACHE, ids=np.array(ids),
                        vectors=np.stack([np.asarray(cached[i], dtype=np.float16) for i in ids]))


def build_specter(E, W):
    totals = W.sum(axis=1, keepdims=True)
    X = (W / np.where(totals == 0, 1, totals)) @ normalize_rows(E)
    return normalize_rows(X).astype(np.float32)


# ---------------------------------------------------------------- report

def cosine_matrix(X, center=False):
    X = np.asarray(X, dtype=np.float64)
    if center:
        X = X - X.mean(axis=0)
    X = normalize_rows(X)
    return X @ X.T


def spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def write_report(faculty, feats, n_papers, now, half_life):
    names = [p["name"] for p in faculty]
    reps = {"TF-IDF": cosine_matrix(feats["tfidf"]),
            "Topics": cosine_matrix(feats["topics"])}
    if "specter" in feats:
        reps["SPECTER2"] = cosine_matrix(feats["specter"], center=True)
    iu = np.triu_indices(len(faculty), 1)

    lines = [
        "# Feature report",
        "",
        "Generated by `scripts/build_features.py`. Each faculty member's papers are weighted",
        f"by recency (weight halves every {half_life} years before {now}), authorship (first or",
        "last author 1, middle author 0.5) and size (more than 50 authors ×0.5).",
        "",
        "## How much the representations agree",
        "",
        "Spearman correlation between the pairwise similarities of all faculty pairs",
        "(1 = same ranking of who is similar to whom).",
        "",
        "| | " + " | ".join(reps) + " |",
        "|---" * (len(reps) + 1) + "|",
    ]
    for a in reps:
        row = [f"{spearman(reps[a][iu], reps[b][iu]):.2f}" for b in reps]
        lines.append(f"| {a} | " + " | ".join(row) + " |")
    lines += ["", "SPECTER2 similarities are computed after centring (subtracting the mean",
              "faculty vector); raw SPECTER2 vectors all point roughly the same way.", ""]

    vocab = feats["tfidf_vocab"]
    for i, p in enumerate(faculty):
        lines += ["---", "", f"## {names[i]}", "",
                  f"{p['group'].title()} · {p['home_department']} · {n_papers[i]} papers", ""]
        top_terms = np.argsort(-feats["tfidf"][i])[:12]
        lines.append("**Top terms:** " + ", ".join(vocab[k] for k in top_terms))
        lines.append("")
        top_topics = np.argsort(-feats["topics"][i])[:5]
        lines.append("**Top topics:** " + ", ".join(
            f"{feats['topic_names'][k]} ({feats['topics'][i][k]:.0%})" for k in top_topics))
        lines.append("")
        for rep, S in reps.items():
            nn = [k for k in np.argsort(-S[i]) if k != i][:4]
            lines.append(f"- **Nearest by {rep}:** " + ", ".join(f"{names[k]} ({S[i, k]:.2f})" for k in nn))
        lines.append("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--half-life", type=float, default=HALF_LIFE, help="recency half-life in years")
    ap.add_argument("--no-embed", action="store_true", help="skip SPECTER2 embeddings")
    ap.add_argument("--extended", action="store_true", help="QCB and the extended roster together")
    args = ap.parse_args()

    global EMBED_CACHE, FEATURES, REPORT
    if args.extended:
        EMBED_CACHE, FEATURES, REPORT = EXTENDED_EMBED_CACHE, EXTENDED_FEATURES, EXTENDED_REPORT
    faculty, papers = load(args.extended)
    W, now = weight_matrix(faculty, papers, args.half_life)
    n_papers = (W > 0).sum(axis=1)
    print(f"{len(papers)} papers, {len(faculty)} faculty")

    feats = {}
    feats["tfidf"], feats["tfidf_vocab"] = build_tfidf(papers, W)
    print(f"tfidf: {feats['tfidf'].shape[1]} shared terms")
    feats.update(build_topics(papers, W))
    print(f"topics: {len(feats['topic_ids'])} topics, {len(feats['subfield_names'])} subfields")
    E = None if args.no_embed else embed_papers(papers)
    if E is not None:
        feats["specter"] = build_specter(E, W)
        print(f"specter: {feats['specter'].shape[1]} dimensions")

    os.makedirs(OUT_DIR, exist_ok=True)
    np.savez_compressed(
        FEATURES,
        faculty_ids=np.array([p["id"] for p in faculty]),
        n_papers=n_papers,
        abstract_share=np.array([
            float((W[i] > 0)[[w["abstract"] is not None for w in papers]].sum() / max(n_papers[i], 1))
            for i in range(len(faculty))]),
        half_life=args.half_life,
        reference_year=now,
        **feats,
    )
    write_report(faculty, feats, n_papers, now, args.half_life)
    size = os.path.getsize(FEATURES) / 1e6
    print(f"wrote {os.path.relpath(FEATURES, ROOT)} ({size:.1f} MB) and {os.path.relpath(REPORT, ROOT)}")


if __name__ == "__main__":
    main()
