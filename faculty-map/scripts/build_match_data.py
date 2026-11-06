#!/usr/bin/env python3
"""Build match-data.js, which lets the page match a student's own words to faculty.

The page is static, so it can't run SPECTER2 on what someone types. Instead this
script precomputes one row of numbers for each of about 8,000 research terms, one number
per faculty member, saying how strongly the term points at them. Two signals are averaged:

- word use: how much that person's papers use the term (the TF-IDF profile);
- meaning: the mean SPECTER2 embedding of all papers using the term, compared with
  each person's embedding. This reaches people who work on a topic in other words.

Each signal is z-scored across faculty for every term. In the browser a student's
words are looked up and their rows averaged, weighted by how rare each word is, which
takes a few milliseconds and sends nothing anywhere.

    python3 scripts/build_match_data.py              # build match-data.js
    python3 scripts/build_match_data.py --evaluate   # also report accuracy
    python3 scripts/build_match_data.py --extended   # everyone on the expanded map, as
                                                     # match-data-extended.js

--evaluate holds out 800 single-author-lead papers, builds the table without them, and
asks how often the real author ranks highly given only the paper's title.
"""

import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_features as bf  # noqa: E402  (loads torch before scikit-learn when present)

import numpy as np  # noqa: E402
from sklearn.feature_extraction.text import CountVectorizer  # noqa: E402

ROOT = bf.ROOT
OUT = os.path.join(ROOT, "match-data.js")
OUT_EXTENDED = os.path.join(ROOT, "match-data-extended.js")
LAYOUT = os.path.join(ROOT, "data", "layout.json")
LAYOUT_EXTENDED = os.path.join(ROOT, "data", "layout-extended.json")

N_TERMS = 8000
PER_PERSON = 80      # each person's top terms always make the cut, however rare
Z_RANGE = 6.0        # table values are stored as int8 covering -6..6
HELD_OUT = 800

# Words that say nothing about a research area, starting with how students describe
# themselves. They're ignored on their own, but phrases such as "large language" stay.
STUDENT_STOP = {
    "want", "wants", "wanted", "like", "likes", "liked", "love", "loved", "enjoy", "enjoyed", "know", "knew",
    "interested", "interest", "interests", "interesting", "passion", "passionate", "curious", "fascinated",
    "experience", "experienced", "experiences", "research", "researcher", "researchers", "lab", "labs",
    "class", "classes", "course", "courses", "coursework", "student", "students", "undergrad", "undergraduate",
    "major", "majors", "minor", "summer", "internship", "internships", "intern", "project", "projects",
    "worked", "working", "works", "did", "doing", "done", "apply", "applying", "applied", "learn", "learned",
    "studying", "studied", "university", "college", "school", "year", "years", "field", "fields", "area", "areas",
    "help", "helped", "good", "better", "best", "really", "lot", "lots", "thing", "things", "way", "ways",
    "future", "career", "professor", "professors", "faculty", "think", "maybe", "something", "someone", "anything",
    # Everyday and academic English that papers use constantly, whatever the topic.
    "does", "doesn", "didn", "don", "people", "person", "make", "makes", "made", "making", "question", "questions",
    "answer", "answers", "real", "world", "change", "changes", "changing", "large", "larger", "small", "multiple",
    "time", "information", "observed", "number", "understanding", "understand", "understood", "complex", "identify",
    "identified", "identifying", "specific", "specifically", "developed", "develop", "developing", "available",
    "common", "framework", "key", "known", "performed", "recent", "recently", "revealed", "reveal", "reveals", "mean",
    "rate", "rates", "set", "sets", "similar", "highly", "level", "levels", "comparison", "compare", "independent",
    "overall", "remain", "remains", "test", "tested", "testing", "underlying", "consistent", "examine", "examined",
    "previous", "previously", "problem", "problems", "range", "support", "addition", "additional", "critical",
    "derived", "greater", "relative", "total", "various", "impact", "included", "include", "obtained", "conditions",
    "existing", "free", "furthermore", "given", "insights", "limited", "general", "measure", "measured", "measures",
    "power", "reduced", "suggesting", "ability", "determine", "determined", "finally", "importance", "loss", "robust",
    "standard", "diverse", "effective", "primary", "techniques", "technique", "assess", "assessed", "assessment",
    "case", "cases", "form", "tool", "tools", "type", "types", "application", "applications", "average", "calculated",
    "correlated", "improve", "improved", "involved", "possible", "predicted", "presence", "processing", "resulting",
    "status", "evaluate", "evaluated", "evaluation", "indicate", "influence", "likely", "point", "relationship",
    "relationships", "accurate", "combined", "essential", "generated", "generate", "need", "particular", "particularly",
    "respectively", "strong", "challenge", "challenges", "challenging", "despite", "direct", "directly", "knowledge",
    "order", "strategy", "strategies", "allows", "central", "characteristics", "contribute", "corresponding", "detect",
    "detected", "efficiency", "efficient", "left", "right", "negative", "positive", "older", "relevant", "active",
    "address", "basis", "defined", "established", "leading", "play", "quality", "required", "second", "value", "values",
    "comprehensive", "conducted", "estimate", "following", "prior", "terms", "unknown", "combination", "components",
    "events", "increasing", "increases", "introduce", "main", "measurements", "providing", "context", "difference",
    "feature", "features", "history", "length", "linked", "useful", "unclear", "widely", "crucial", "highlight",
}
# Shorthand that the term list spells out, or spells differently.
ALIASES = {
    "ai": "artificial intelligence", "ml": "machine learning", "nlp": "language models",
    "llm": "large language", "llms": "large language", "neuro": "neuroscience", "bio": "biology",
    "stats": "statistics", "math": "mathematical", "maths": "mathematical", "modelling": "modeling",
    "tumour": "tumor", "tumours": "tumors", "scrna-seq": "single-cell rna-seq",
    # In these papers "coding" nearly always means coding regions of DNA.
    "coding": "computational", "programming": "computational",
}


def build_table(faculty, papers, W, E, train):
    """Terms, their rarity, and the faculty x terms table, from the papers in `train`."""
    vec = CountVectorizer(stop_words=bf.STOP_WORDS, ngram_range=(1, 2), min_df=5, max_df=0.3,
                          token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b", max_features=40000)
    C = vec.fit_transform(bf.paper_text(papers[j]) for j in train).astype(np.float64)
    vocab = vec.get_feature_names_out().astype(str)
    Wt = W[:, train]
    totals = Wt.sum(axis=1, keepdims=True)
    totals[totals == 0] = 1
    mix = Wt / totals

    # Meaning: each term's mean embedding against each person's.
    F = bf.normalize_rows(mix @ E[train])
    F = bf.normalize_rows(F - F.mean(axis=0))
    T = bf.normalize_rows((C > 0).astype(np.float32).T.tocsr() @ E[train])
    meaning = (T @ F.T).T

    # Word use: the TF-IDF profile, as in build_features.py.
    logged = C.copy()
    logged.data = np.log1p(logged.data)
    lengths = np.asarray(logged.sum(axis=1)).ravel()
    lengths[lengths == 0] = 1
    tf = np.asarray(mix @ logged.multiply(1 / lengths[:, None]).tocsr())
    use = bf.normalize_rows(tf * (np.log((1 + len(tf)) / (1 + (tf > 0).sum(axis=0))) + 1))

    def zscore(M):
        return (M - M.mean(axis=0)) / (M.std(axis=0) + 1e-6)

    H = 0.5 * zscore(meaning) + 0.5 * zscore(use)
    df = np.asarray((C > 0).sum(axis=0)).ravel()
    idf = np.log((1 + len(train)) / (1 + df)) + 1

    keep = np.zeros(len(vocab), bool)
    for row in use:
        keep[np.argsort(-row)[:PER_PERSON]] = True
    for k in np.argsort(-df):
        if keep.sum() >= N_TERMS:
            break
        keep[k] = True
    keep &= ~np.isin(vocab, sorted(STUDENT_STOP))
    return vec, vocab[keep], idf[keep], H[:, keep]


def embeddings(papers):
    lookup = {}
    for path in dict.fromkeys((bf.QCB_EMBED_CACHE, bf.EMBED_CACHE)):
        z = np.load(path)
        lookup.update(zip(z["ids"].tolist(), z["vectors"]))
    E = bf.normalize_rows(np.stack([np.asarray(lookup[w["id"]], dtype=np.float32) for w in papers]))
    return bf.normalize_rows(E - E.mean(axis=0))


def evaluate(faculty, papers, W, E):
    rng = np.random.default_rng(0)
    lead = [j for j, w in enumerate(papers) if (W[:, j] > 0).sum() == 1
            and any(i["keep"] and i.get("position") in ("first", "last") for i in w["faculty"].values())]
    test = set(rng.choice(lead, size=HELD_OUT, replace=False).tolist())
    train = np.array([j for j in range(len(papers)) if j not in test])
    vec, terms, idf, H = build_table(faculty, papers, W, E, train)
    index = {t: k for k, t in enumerate(terms)}
    analyze = vec.build_analyzer()
    ranks = []
    for j in sorted(test):
        hits = sorted({index[t] for t in analyze(papers[j]["title"]) if t in index})
        truth = int(np.argmax(W[:, j] > 0))
        if not hits:
            ranks.append(len(faculty))
            continue
        s = H[:, hits] @ idf[hits]
        ranks.append(int((s > s[truth]).sum()) + 1)
    r = np.array(ranks)
    print(f"held-out titles ({HELD_OUT}): real author ranked 1st {np.mean(r <= 1):.0%}, "
          f"top 3 {np.mean(r <= 3):.0%}, top 5 {np.mean(r <= 5):.0%}; chance top 5 is {5 / len(faculty):.0%}")


def b64(data):
    return base64.b64encode(data).decode("ascii")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evaluate", action="store_true", help="also report held-out accuracy")
    ap.add_argument("--extended", action="store_true", help="everyone on the expanded map")
    args = ap.parse_args()
    if args.extended:
        bf.EMBED_CACHE = bf.EXTENDED_EMBED_CACHE

    faculty, papers = bf.load(args.extended)
    with open(LAYOUT, encoding="utf-8") as f:
        layout = json.load(f)
    order = [p["id"] for p in layout["faculty"]]
    if args.extended:   # the same order as map-data-extended.js: QCB first
        with open(LAYOUT_EXTENDED, encoding="utf-8") as f:
            order += [p["id"] for p in json.load(f)["faculty"] if p["id"] not in order]
    rows = [[p["id"] for p in faculty].index(pid) for pid in order]   # table rows follow the map's order
    W, _ = bf.weight_matrix(faculty, papers, bf.HALF_LIFE)
    E = embeddings(papers)
    if args.evaluate:
        evaluate(faculty, papers, W, E)

    _, terms, idf, H = build_table(faculty, papers, W, E, np.arange(len(papers)))
    H = H[rows]
    table = np.round(np.clip(H / Z_RANGE, -1, 1) * 127).astype(np.int8).T       # terms x faculty
    rarity = np.round(np.clip(idf / idf.max(), 0, 1) * 255).astype(np.uint8)

    out = {
        "n": len(order),
        "range": Z_RANGE,
        "terms": "|".join(terms.tolist()),
        "rarity": b64(rarity.tobytes()),
        "table": b64(table.tobytes()),
        "stop": bf.STOP_WORDS,            # dropped before pairing words, as in the table
        "skip": sorted(STUDENT_STOP),     # ignored as single words, kept inside phrases
        "aliases": ALIASES,
    }
    path = OUT_EXTENDED if args.extended else OUT
    with open(path, "w", encoding="utf-8") as f:
        f.write("// Generated by scripts/build_match_data.py. Don't edit by hand.\n")
        f.write(f"window.{'QCB_MATCH_EXTENDED' if args.extended else 'QCB_MATCH'} = ")
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    single = sum(" " not in t for t in terms)
    print(f"wrote {os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1000:.0f} KB): {len(terms)} terms "
          f"({single} words, {len(terms) - single} two-word phrases) for {len(order)} faculty")


if __name__ == "__main__":
    main()
