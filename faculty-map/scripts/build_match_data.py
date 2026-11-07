#!/usr/bin/env python3
"""Build match-data.js and match-data-extended.js, which match a student's words to faculty.

The page is static, so it can't run SPECTER2 on what someone types. Instead this script
precomputes a row for every research word and phrase it knows, saying how strongly the
term points at each faculty member. Two signals are averaged:

- meaning: SPECTER2's embedding of the term itself, compared with each person's. This
  knows what "protein engineering" means even if few papers use those exact words.
- evidence: how much of a person's work uses the term. A title, a keyword or repeated
  use counts in full, and one mention in an abstract only counts for PASSING. Dividing
  by the square root of their papers lets a specialist beat someone prolific, and
  MIN_BODY stops one paper looking like a specialty for someone with very few.

Each signal is z-scored across faculty for every term. In the browser a student's text
is split into the longest terms it can find, so a phrase is never read as its separate
words. Their rows are then averaged, weighted by how rare each term is, which takes a
few milliseconds and sends nothing anywhere.

Terms come from every paper on the expanded map, so the QCB table also knows phrases
only related fields use. A phrase is a run of up to MAX_WORDS words with no punctuation or
function word between them, seen in at least MIN_PAPERS papers. Two checks keep filler
out: its words must sit together at least as often as chance, and a common phrase's
papers must be about something, which "better understanding" isn't. Keywords from
scripts/fetch_keywords.py add standard phrases no paper here uses, as long as all their
words are familiar here, which keeps "metabolic engineering" and loses "gothic fiction".

    .venv/bin/python scripts/build_match_data.py              # build both files
    .venv/bin/python scripts/build_match_data.py --evaluate   # also report accuracy

--evaluate holds out a quarter of the single-author-lead papers, builds the tables
without them, and asks how often the real author ranks highly given a paper's title,
or given a phrase they used in at least two of those papers.
"""

import argparse
import base64
import collections
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_features as bf  # noqa: E402  (loads torch before scikit-learn when present)
import stamp_page  # noqa: E402

import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS  # noqa: E402

ROOT = bf.ROOT
OUT = os.path.join(ROOT, "match-data.js")
OUT_EXTENDED = os.path.join(ROOT, "match-data-extended.js")
LAYOUT = os.path.join(ROOT, "data", "layout.json")
LAYOUT_EXTENDED = os.path.join(ROOT, "data", "layout-extended.json")
KEYWORDS = os.path.join(ROOT, "data", "raw", "openalex-keywords.json")

MAX_WORDS = 4         # in a phrase
MIN_PAPERS = 5        # a term has to appear in this many papers
MIN_TOGETHER = 0.0    # how often a phrase's words sit together, as log(seen / chance)
COMMON = 20           # from this many papers on, a phrase also has to be about something:
MIN_TIGHTNESS = 2.0   # the length of its papers' summed embeddings over sqrt(papers), about 1 by chance
PASSING = 0.2         # what one mention in an abstract counts for
MIN_BODY = 50         # nobody counts as having fewer weighted papers than this
PHRASE_SPREAD = 0.005  # stops a phrase almost nobody uses turning a faint signal into a strong one
KEYWORD_WORDS = 20    # every word of an outside keyword has to be in this many papers
Z_RANGE = 6.0         # table values are stored as int8 covering -6..6
# Each term stores the people it points at most, and everyone else shares one floor.
# Held-out accuracy doesn't change down to 10 of 48 people, or 16 of 161.
TOP_PEOPLE = {"qcb": 10, "all": 16}
HELD_OUT = 0.25
MAP_SIZES = {}

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
    "ai": "artificial intelligence", "ml": "machine learning", "dl": "deep learning", "nlp": "natural language processing",
    "llm": "large language model", "llms": "large language models", "neuro": "neuroscience", "bio": "biology",
    "stats": "statistics", "math": "mathematical", "maths": "mathematical", "modelling": "modeling",
    "tumour": "tumor", "tumours": "tumors", "scrna-seq": "single-cell rna-seq",
    # In these papers "coding" nearly always means coding regions of DNA.
    "coding": "computational", "programming": "computational",
}
# scikit-learn's stop list includes words that mean something here, so "computer vision"
# and "immune system" could never be phrases. Only true function words break a phrase.
MEANINGFUL = {
    "amount", "another", "back", "became", "become", "becomes", "bill", "bottom", "call", "co", "con", "computer", "cry",
    "de", "describe", "detail", "eg", "eight", "eleven", "empty", "etc", "few", "fifteen", "fifty", "fill", "find", "fire",
    "first", "five", "forty", "found", "four", "front", "full", "get", "give", "go", "hundred", "ie", "inc", "interest",
    "keep", "last", "least", "less", "ltd", "made", "many", "mill", "mine", "more", "most", "mostly", "move", "much", "name",
    "next", "nine", "one", "other", "others", "own", "part", "put", "re", "same", "see", "seem", "seemed", "seems",
    "serious", "several", "show", "side", "sincere", "six", "sixty", "system", "take", "ten", "thick", "thin", "three",
    "top", "twelve", "twenty", "two", "un",
}
FUNCTION_WORDS = (set(ENGLISH_STOP_WORDS) - MEANINGFUL) | {
    "across", "among", "based", "can", "did", "does", "has", "hence", "per", "shall", "toward", "towards", "upon",
    "using", "versus", "via", "vs", "whereas", "within", "without", "yet",
}
LONE_WORDS = {"computer", "system", "systems"}   # stop words that also work alone


def stem(word):
    """Plurals count as the same word. The page's readText() has a copy of this."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")) else word


IGNORED = (set(bf.STOP_WORDS) | STUDENT_STOP | {stem(w) for w in set(bf.STOP_WORDS) | STUDENT_STOP}) - LONE_WORDS


def runs(text):
    """Stretches of words with nothing between them, as (words, what joins each to the
    last). The page's runsOf() splits text the same way."""
    text = re.sub(r"['’]", "", re.sub(r"['’]s\b", "", re.sub(r"<[^>]+>", " ", text).lower()))
    for part in re.split(r"[^a-z0-9\s-]+", text):
        words, joins = [], []
        for token in part.split():
            for n, word in enumerate(filter(None, token.split("-"))):
                if len(word) < 3 or word[0].isdigit() or word in FUNCTION_WORDS:
                    if words:
                        yield words, joins
                    words, joins = [], []
                else:
                    words.append(word)
                    joins.append("-" if n else " ")
        if words:
            yield words, joins


def terms_in(run):
    """Every term in a run of words, as (key, how it was written)."""
    words, joins = run
    keys = [stem(w) for w in words]
    for n in range(1, MAX_WORDS + 1):
        for i in range(len(keys) - n + 1):
            written = words[i] + "".join(joins[j] + words[j] for j in range(i + 1, i + n))
            yield " ".join(keys[i:i + n]), written


def count_terms(papers):
    """Each paper's terms with how much each counts, how many papers have each term, and
    how often each appears."""
    per_paper, papers_with, times = [], collections.Counter(), collections.Counter()
    for w in papers:
        headline = collections.Counter(key for part in (w["title"] or "", *w["keywords"]) for run in runs(part) for key, _ in terms_in(run))
        body = collections.Counter(key for run in runs(w["abstract"] or "") for key, _ in terms_in(run))
        evidence = {key: PASSING if n == 1 else 1.0 for key, n in body.items()}
        evidence.update(dict.fromkeys(headline, 1.0))
        per_paper.append(evidence)
        papers_with.update(evidence.keys())
        times.update(headline)
        times.update(body)
    return per_paper, papers_with, times


def term_matrix(per_paper, keys):
    index = {t: k for k, t in enumerate(keys)}
    hits = [(r, index[t], float(n)) for r, found in enumerate(per_paper) for t, n in found.items() if t in index]
    rows, cols, values = zip(*hits)
    return sp.csr_matrix((values, (rows, cols)), shape=(len(per_paper), len(keys)))


def choose_terms(per_paper, papers_with, times, E):
    """The keys of the words and phrases papers use often enough."""
    tokens = sum(n for t, n in times.items() if " " not in t)

    def together(key):
        words = key.split()
        return min(math.log(times[f"{a} {b}"] * tokens / (times[a] * times[b])) for a, b in zip(words, words[1:]))

    common = [t for t, n in papers_with.items() if n >= MIN_PAPERS]
    words = [t for t in common if " " not in t and t not in IGNORED]
    phrases = [t for t in common if " " in t and any(w not in IGNORED for w in t.split()) and together(t) >= MIN_TOGETHER]
    used = (term_matrix(per_paper, phrases) > 0).astype(np.float32)
    n = np.asarray(used.sum(axis=0)).ravel()
    tightness = np.linalg.norm(used.T.tocsr() @ E, axis=1) / np.sqrt(n)
    return words + [t for t, papers, tight in zip(phrases, n, tightness) if papers < COMMON or tight >= MIN_TIGHTNESS]


def keyword_terms(known, papers_with):
    """OpenAlex keywords that aren't terms yet, as {key: how it's written}."""
    if not os.path.exists(KEYWORDS):
        return {}
    with open(KEYWORDS, encoding="utf-8") as f:
        names = json.load(f)
    found = {}
    for name in names:
        pieces = list(runs(name))
        if len(pieces) == 1 and 2 <= len(pieces[0][0]) <= MAX_WORDS:
            key, written = list(terms_in(pieces[0]))[-1]
            if key not in known and all(papers_with[w] >= KEYWORD_WORDS for w in key.split()):
                found.setdefault(key, written)
    return found


def embed_terms(terms):
    """SPECTER2 vectors for terms, each read as a paper's title."""
    from adapters import AutoAdapterModel
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(bf.MODEL)
    model = AutoAdapterModel.from_pretrained(bf.MODEL, revision=bf.MODEL_REVISION)
    model.load_adapter(bf.ADAPTER, source="hf", load_as="proximity", set_active=True)
    device = "mps" if bf.torch.backends.mps.is_available() else "cuda" if bf.torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    vectors = np.zeros((len(terms), model.config.hidden_size), dtype=np.float32)
    shortest_first = np.argsort([len(t) for t in terms])   # keeps padding per batch small
    for start in range(0, len(terms), 128):
        batch = shortest_first[start:start + 128]
        inputs = tok([terms[i] for i in batch], padding=True, truncation=True, max_length=32,
                     return_tensors="pt", return_token_type_ids=False).to(device)
        with bf.torch.no_grad():
            vectors[batch] = model(**inputs).last_hidden_state[:, 0, :].float().cpu().numpy()
    return bf.normalize_rows(vectors - vectors.mean(axis=0))


def people_vectors(W, E):
    totals = W.sum(axis=1, keepdims=True)
    F = bf.normalize_rows((W / np.where(totals == 0, 1, totals)) @ E)
    return bf.normalize_rows(F - F.mean(axis=0))


def build_terms(papers, E):
    """Terms from `papers`: their keys, how they're written, their embeddings, and the
    papers x terms evidence. E holds the same papers."""
    per_paper, papers_with, times = count_terms(papers)
    keys = choose_terms(per_paper, papers_with, times, E)
    written = dict(zip(keys, written_forms(papers, keys)))
    written.update(keyword_terms(written, papers_with))
    keys = sorted(written)
    terms = [written[k] for k in keys]
    return keys, terms, embed_terms(terms), term_matrix(per_paper, keys)


def rarity_of(C):
    """A term no paper uses still only counts as rare as the rarest term from the papers."""
    return np.log((1 + C.shape[0]) / (1 + np.maximum(np.asarray((C > 0).sum(axis=0)).ravel(), MIN_PAPERS))) + 1


def score_people(C, Q, W, E, keys):
    """The people x terms table. W and E hold the same papers as C."""
    meaning = (Q @ people_vectors(W, E).T).T
    evidence = np.asarray(W @ C) / np.sqrt(np.maximum(W.sum(axis=1, keepdims=True), MIN_BODY))
    spread = evidence.std(axis=0)
    phrases = np.array([" " in k for k in keys])
    spread[phrases] = np.maximum(spread[phrases], PHRASE_SPREAD)
    return 0.5 * (meaning - meaning.mean(axis=0)) / (meaning.std(axis=0) + 1e-6) + 0.5 * (evidence - evidence.mean(axis=0)) / (spread + 1e-6)


def split_run(words, index, rarity):
    """The fewest terms that cover a run: a phrase beats its words, and the rarer of two
    phrases wins a tie. Words that are ignored anyway cost nothing, so they don't push a
    split towards phrases that swallow them. Returns term numbers, or None for a word
    that isn't a term."""
    keys = [stem(w) for w in words]
    best, back = [0.0] + [math.inf] * len(keys), [None] * (len(keys) + 1)
    for i in range(len(keys)):
        for n in range(1, MAX_WORDS + 1):
            k = index.get(" ".join(keys[i:i + n]))
            if i + n > len(keys) or (n > 1 and k is None):
                continue
            if n > 1:
                cost = 1 - rarity[k] / (100 * rarity.max())
            else:
                cost = 1.2 if k is not None else 0 if keys[i] in IGNORED or words[i] in IGNORED else 2
            if best[i] + cost < best[i + n]:
                best[i + n], back[i + n] = best[i] + cost, (i, k)
    picked, i = [], len(keys)
    while i:
        i, k = back[i]
        picked.append(k)
    return picked


def embeddings(papers):
    lookup = {}
    for path in dict.fromkeys((bf.QCB_EMBED_CACHE, bf.EMBED_CACHE)):
        z = np.load(path)
        lookup.update(zip(z["ids"].tolist(), z["vectors"]))
    E = bf.normalize_rows(np.stack([np.asarray(lookup[w["id"]], dtype=np.float32) for w in papers]))
    return bf.normalize_rows(E - E.mean(axis=0))


def evaluate(papers, W, E):
    """Held-out accuracy on both maps, for the figures quoted on the page."""
    rng = np.random.default_rng(0)
    lead = [j for j, w in enumerate(papers) if (W[:, j] > 0).sum() == 1
            and any(i["keep"] and i.get("position") in ("first", "last") for i in w["faculty"].values())]
    test = sorted(rng.choice(lead, size=int(len(lead) * HELD_OUT), replace=False).tolist())
    train = np.setdiff1d(np.arange(len(papers)), test)
    keys, _, Q, C = build_terms([papers[j] for j in train], E[train])
    index, rarity = {t: k for k, t in enumerate(keys)}, rarity_of(C)
    author = {j: int(np.argmax(W[:, j] > 0)) for j in test}

    papers_on = collections.defaultdict(collections.Counter)
    for j, found in zip(test, count_terms([papers[j] for j in test])[0]):
        for t in found:
            if " " in t and t in index:
                papers_on[t][author[j]] += 1
    for name, n in (("QCB", MAP_SIZES["qcb"]), ("expanded", W.shape[0])):
        H = score_people(C, Q, W[:n, train], E[train], keys)
        ranks = []
        for j in test:
            if author[j] < n:
                hits = sorted({k for run in runs(papers[j]["title"] or "") for k in split_run(run[0], index, rarity) if k is not None})
                s = rarity[hits] @ H[:, hits].T if hits else None
                ranks.append(n if s is None else int((s > s[author[j]]).sum()) + 1)
        r = np.array(ranks)
        phrases = [(t, {a for a, papers_by in c.items() if papers_by >= 2 and a < n}) for t, c in papers_on.items()]
        phrases = [(t, people) for t, people in phrases if people]
        found = np.mean([bool(set(np.argsort(-H[:, index[t]])[:5]) & people) for t, people in phrases])
        print(f"{name} map, {len(r)} held-out titles: real author ranked 1st {np.mean(r <= 1):.0%}, top 3 {np.mean(r <= 3):.0%}, "
              f"top 5 {np.mean(r <= 5):.0%}. {len(phrases)} phrases: someone with 2 papers on it in the top 5 {found:.0%}")


def written_forms(papers, keys):
    """The commonest way each term is written, hyphens and plurals included."""
    wanted, forms = set(keys), collections.defaultdict(collections.Counter)
    for w in papers:
        for part in (w["title"] or "", w["abstract"] or "", *w["keywords"]):
            for run in runs(part):
                for key, written in terms_in(run):
                    if key in wanted:
                        forms[key][written] += 1
    return [forms[k].most_common(1)[0][0] for k in keys]


def b64(data):
    return base64.b64encode(data).decode("ascii")


def to_bytes(values):
    return np.round(np.clip(values / Z_RANGE, -1, 1) * 127).astype(np.int8)


def write_table(path, name, H, top, terms, rarity):
    best = np.argsort(-H, axis=0)
    table = {
        "n": H.shape[0],
        "range": Z_RANGE,
        "top": top,
        "longest": MAX_WORDS,
        "terms": "|".join(terms),
        "rarity": b64(np.round(np.clip(rarity / rarity.max(), 0, 1) * 255).astype(np.uint8).tobytes()),
        "people": b64(best[:top].T.astype(np.uint8).tobytes()),
        "scores": b64(to_bytes(np.take_along_axis(H, best[:top], axis=0).T).tobytes()),
        "floor": b64(to_bytes(np.take_along_axis(H, best[top:top + 1], axis=0)[0]).tobytes()),
        "breaks": sorted(FUNCTION_WORDS),   # a phrase never runs across these
        "skip": sorted(IGNORED),            # ignored as single words, kept inside phrases
        "aliases": ALIASES,
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write("// Generated by scripts/build_match_data.py. Don't edit by hand.\n")
        f.write(f"window.{name} = ")
        json.dump(table, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"wrote {os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1000:.0f} KB) for {H.shape[0]} faculty")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evaluate", action="store_true", help="also report held-out accuracy")
    args = ap.parse_args()
    bf.EMBED_CACHE = bf.EXTENDED_EMBED_CACHE

    faculty, papers = bf.load(True)
    with open(LAYOUT, encoding="utf-8") as f:
        order = [p["id"] for p in json.load(f)["faculty"]]
    MAP_SIZES["qcb"] = len(order)
    with open(LAYOUT_EXTENDED, encoding="utf-8") as f:   # the same order as map-data-extended.js: QCB first
        order += [p["id"] for p in json.load(f)["faculty"] if p["id"] not in order]
    ids = [p["id"] for p in faculty]
    W = bf.weight_matrix(faculty, papers, bf.HALF_LIFE)[0][[ids.index(pid) for pid in order]]
    E = embeddings(papers)
    if args.evaluate:
        evaluate(papers, W, E)

    keys, terms, Q, C = build_terms(papers, E)
    rarity = rarity_of(C)
    assert all(" ".join(stem(w) for w in t.replace("-", " ").split()) == k for t, k in zip(terms, keys))
    write_table(OUT, "QCB_MATCH", score_people(C, Q, W[:MAP_SIZES["qcb"]], E, keys), TOP_PEOPLE["qcb"], terms, rarity)
    write_table(OUT_EXTENDED, "QCB_MATCH_EXTENDED", score_people(C, Q, W, E, keys), TOP_PEOPLE["all"], terms, rarity)
    phrases = sum(" " in k for k in keys)
    unused = int((np.asarray((C > 0).sum(axis=0)).ravel() == 0).sum())
    print(f"{len(keys)} terms: {len(keys) - phrases} words and {phrases} phrases, {unused} of them only from keywords")
    stamp_page.stamp()


if __name__ == "__main__":
    main()
