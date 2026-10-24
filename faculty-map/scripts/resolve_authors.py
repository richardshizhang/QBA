#!/usr/bin/env python3
"""Match each faculty member to their OpenAlex author profile(s).

Reads data/faculty.json and, for every core, joint and emeritus faculty member:

1. searches OpenAlex authors by name (plus nickname / middle-name variants), limited
   to people who were ever affiliated with USC or one of its child institutions;
2. picks the most likely profile from name match, how well its topics fit the
   person's departments, years at USC and publication count;
3. looks for "split" profiles: same-name authors with overlapping topics, which is
   how OpenAlex often stores the pre-USC part of a career;
4. pulls a few most-cited and most-recent papers so a person can check the match.

Writes data/openalex-authors.json (the mapping later scripts use) and
data/id-review.md (a table for checking it by eye). Entries whose "status" is
"verified" in data/openalex-authors.json are kept as they are on reruns (and cost no
API calls), so corrections made by hand stick. A verified entry lists every author
ID that belongs to the person in "openalex"; for someone OpenAlex never linked to a
profile, "dois" lists their papers instead.

    python3 scripts/resolve_authors.py
    python3 scripts/resolve_authors.py --only remo-rohs yan-liu   # redo a few
    python3 scripts/resolve_authors.py --review-only              # just rewrite the review

API responses are cached in data/raw/openalex/, so reruns cost nothing. OpenAlex bills
in credits: a name search costs 10, a filtered list 1, a lookup by ID nothing. Without
a key everyone on your network shares 1,000 credits a day; a free key from
https://openalex.org/settings/api gives 10,000. Put the key in the OPENALEX_API_KEY
environment variable or in a file named .openalex-key next to this project's README
(it is gitignored). A full first run uses roughly 1,200 credits. If the budget runs
out midway, everything finished so far is still written; rerun after midnight UTC.
Only the standard library is used.
"""

import argparse
import concurrent.futures as futures
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openalex.org"
USC = "https://openalex.org/I1174212"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACULTY = os.path.join(ROOT, "data", "faculty.json")
MAPPING = os.path.join(ROOT, "data", "openalex-authors.json")
REVIEW = os.path.join(ROOT, "data", "id-review.md")
CACHE = os.path.join(ROOT, "data", "raw", "openalex")

AUTHOR_FIELDS = ("id,display_name,display_name_alternatives,orcid,works_count,cited_by_count,"
                 "last_known_institutions,affiliations,topics,summary_stats")
WORK_FIELDS = "id,title,publication_year,cited_by_count,primary_location"

# OpenAlex fields (topic.field.display_name) we expect each department's research to
# land in. Used only to break ties between same-name authors.
BIO = "Biochemistry, Genetics and Molecular Biology"
DEPT_FIELDS = {
    "Quantitative and Computational Biology": [BIO, "Computer Science", "Mathematics", "Agricultural and Biological Sciences"],
    "Aerospace and Mechanical Engineering": ["Engineering", "Physics and Astronomy", "Mathematics"],
    "Biochemistry": [BIO, "Chemistry"],
    "Biological Sciences": ["Agricultural and Biological Sciences", BIO, "Neuroscience", "Immunology and Microbiology", "Environmental Science"],
    "Biomedical Engineering": ["Engineering", "Medicine", BIO, "Neuroscience"],
    "Cancer Biology": ["Medicine", BIO],
    "Chemical Engineering and Materials Science": ["Chemical Engineering", "Materials Science", "Engineering"],
    "Chemistry": ["Chemistry", BIO],
    "Computer Science": ["Computer Science"],
    "Earth Sciences": ["Earth and Planetary Sciences", "Environmental Science"],
    "Electrical and Computer Engineering": ["Engineering", "Computer Science"],
    "Gerontology": ["Neuroscience", "Medicine", "Psychology"],
    "Industrial and Systems Engineering": ["Decision Sciences", "Engineering", "Computer Science", "Mathematics"],
    "Mathematics": ["Mathematics"],
    "Medicine": ["Medicine"],
    "Molecular Microbiology and Immunology": ["Immunology and Microbiology", BIO],
    "Neurology": ["Neuroscience", "Medicine"],
    "Ophthalmology": ["Medicine", "Neuroscience"],
    "Pediatrics": ["Medicine"],
    "Pharmacology and Pharmaceutical Sciences": ["Pharmacology, Toxicology and Pharmaceutics", "Chemistry", BIO],
    "Physics and Astronomy": ["Physics and Astronomy"],
    "Physiology and Biophysics": [BIO, "Physics and Astronomy"],
    "Population and Public Health Sciences": ["Medicine", BIO],
    "Psychiatry and Behavioral Sciences": ["Psychology", "Neuroscience", "Medicine"],
    "Radiology": ["Medicine", "Neuroscience"],
    "Stem Cell Biology and Regenerative Medicine": [BIO, "Medicine"],
}

# Extra search strings for people who publish under a different form of their name.
SEARCH_EXTRA = {}

GROUPS = ("core", "joint", "emeritus")


# ---------------------------------------------------------------- OpenAlex access

class OutOfBudget(Exception):
    pass


KEY_FILE = os.path.join(ROOT, ".openalex-key")
credits_left = None  # from the last response's X-RateLimit-Remaining header


def api_key():
    if os.environ.get("OPENALEX_API_KEY"):
        return os.environ["OPENALEX_API_KEY"].strip()
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            return f.read().strip() or None
    return None


def get_json(path, params):
    """GET {API}{path}?params, cached on disk by URL (the API key is not part of it)."""
    query = urllib.parse.urlencode(params, safe=":|,")
    url = f"{API}{path}?{query}"
    cache = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    global credits_left
    key = api_key()
    full = url + (f"&api_key={key}" if key else "")
    req = urllib.request.Request(full, headers={"User-Agent": "QBA faculty map (USC student project)"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
                credits_left = resp.headers.get("X-RateLimit-Remaining", credits_left)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                body = exc.read().decode("utf-8", "replace")
                if "per second" not in body:
                    raise OutOfBudget(body[:300]) from exc
                # Burst limit (10 requests/second), not the daily budget: wait and retry.
            elif attempt == 5:
                raise RuntimeError(f"{url}: HTTP {exc.code}") from exc
        except Exception as exc:
            if attempt == 5:
                raise RuntimeError(f"{url}: {exc}") from exc
        time.sleep(1 + 2 * attempt)
    os.makedirs(CACHE, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def search_authors(name, filt=None, per_page=15):
    params = {"search": name, "select": AUTHOR_FIELDS, "per-page": per_page}
    if filt:
        params["filter"] = filt
    return get_json("/authors", params).get("results", [])


def top_works(author_ids, sort, n):
    params = {"filter": "author.id:" + "|".join(short(a) for a in author_ids),
              "sort": sort, "per-page": n, "select": WORK_FIELDS}
    return get_json("/works", params).get("results", [])


# ---------------------------------------------------------------- matching

def short(oa_id):
    return oa_id.rsplit("/", 1)[-1]


def tokens(name, join_hyphens=False):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    if "," in name:  # "Rohs, Remo" -> "Remo Rohs"
        last, _, first = name.partition(",")
        name = f"{first} {last}"
    name = re.sub(r"[\u2010\u2011-]", "" if join_hyphens else " ", name)
    return re.findall(r"[a-z]+", name)


def name_score(candidate, person):
    """1 = full first name and last name, 0.6 = initial and last name, 0 = no match.

    Hyphenated given names count as one name, so "Tie-Yan Liu" is not Yan Liu, while
    hyphenated surnames still match their parts ("Kribelbauer-Swietek").
    """
    last = tokens(person["last"])
    if not all(t in tokens(candidate) for t in last):
        return 0.0
    given = [t for t in tokens(candidate, join_hyphens=True) if not any(l in t for l in last)]
    firsts = [person["first"]]
    if person.get("nickname"):
        firsts.append(person["nickname"])
    if person.get("middle") and "." not in person["middle"]:
        firsts.append(person["middle"])  # Peter Yingxiao Wang publishes as Yingxiao Wang
    firsts = ["".join(tokens(f, join_hyphens=True)) for f in firsts]
    if any(f in given for f in firsts):
        return 1.0
    initials = {f[0] for f in firsts if f}
    if any(len(t) <= 2 and t[0] in initials for t in given):
        return 0.6
    return 0.0


def best_name_score(author, person):
    """Display name, or (slightly discounted) one of OpenAlex's alternative names.

    Alternatives are noisy on merged profiles, so only the primary pick uses them;
    split and namesake lists go by display name alone.
    """
    score = name_score(author["display_name"], person)
    for alt in author.get("display_name_alternatives") or []:
        score = max(score, 0.9 * name_score(alt, person))
    return score


def display_score(author, person):
    return name_score(author["display_name"], person)


def is_usc(inst):
    return USC in (inst.get("lineage") or [inst.get("id")])


def usc_years(author):
    years = set()
    for aff in author.get("affiliations") or []:
        if is_usc(aff["institution"]):
            years.update(aff["years"])
    return sorted(years)


def topic_fit(author, person):
    expected = set()
    for dept in person["departments"] or ["Quantitative and Computational Biology"]:
        expected.update(DEPT_FIELDS.get(dept, []))
    topics = author.get("topics") or []
    total = sum(t["count"] for t in topics)
    if not total:
        return 0.0
    return sum(t["count"] for t in topics if t["field"]["display_name"] in expected) / total


def topic_overlap(a, b):
    """Cosine similarity of two authors' topic-count vectors."""
    va = {t["id"]: t["count"] for t in a.get("topics") or []}
    vb = {t["id"]: t["count"] for t in b.get("topics") or []}
    dot = sum(v * vb.get(k, 0) for k, v in va.items())
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def score(author, person, ns):
    years = usc_years(author)
    last_usc = any(is_usc(i) for i in author.get("last_known_institutions") or [])
    return (3 * ns
            + 2 * topic_fit(author, person)
            + (1.5 if last_usc else 0)
            + 0.15 * min(len(years), 15)
            + math.log10(author["works_count"] + 1)
            + (0.3 if author.get("orcid") else 0))


def variants(person):
    out = [f"{person['first']} {person['last']}"]
    if person.get("middle"):
        out.append(f"{person['first']} {person['middle']} {person['last']}")
        if "." not in person["middle"]:
            out.append(f"{person['middle']} {person['last']}")
    if person.get("nickname"):
        out.append(f"{person['nickname']} {person['last']}")
    out += SEARCH_EXTRA.get(person["id"], [])
    return list(dict.fromkeys(out))


def summarize(author, person=None, primary=None):
    years = usc_years(author)
    out = {
        "id": short(author["id"]),
        "display_name": author["display_name"],
        "orcid": (author.get("orcid") or "").replace("https://orcid.org/", "") or None,
        "works_count": author["works_count"],
        "cited_by_count": author["cited_by_count"],
        "h_index": (author.get("summary_stats") or {}).get("h_index"),
        "usc_years": [years[0], years[-1]] if years else None,
        "last_known": [i["display_name"] for i in author.get("last_known_institutions") or []],
        "institutions": sorted(
            ({"name": a["institution"]["display_name"], "years": [min(a["years"]), max(a["years"])]}
             for a in author.get("affiliations") or []),
            key=lambda x: -x["years"][1])[:6],
        "topics": [t["display_name"] for t in (author.get("topics") or [])[:5]],
    }
    if person is not None:
        out["name_score"] = round(best_name_score(author, person), 2)
        out["topic_fit"] = round(topic_fit(author, person), 2)
    if primary is not None:
        out["topic_overlap"] = round(topic_overlap(author, primary), 2)
    return out


def resolve(person):
    usc_filter = "affiliations.institution.lineage:" + short(USC)
    found = {}
    for v in variants(person):
        for a in search_authors(v, usc_filter):
            found.setdefault(a["id"], a)
    scored = []
    for a in found.values():
        ns = best_name_score(a, person)
        if ns >= 0.6:
            scored.append((score(a, person, ns), a))
    fallback = False
    if not scored:  # new hire whose USC papers OpenAlex hasn't linked yet
        fallback = True
        for v in variants(person):
            for a in search_authors(v, per_page=25):
                ns = best_name_score(a, person)
                if ns >= 0.6:
                    scored.append((score(a, person, ns), a))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return {"person": person, "primary": None, "splits": [], "namesakes": [], "confidence": "check",
                "reasons": ["no OpenAlex author with a matching name"]}

    best_score, primary = scored[0]
    reasons = []
    if fallback:
        reasons.append("no USC-affiliated match; picked from an unfiltered search")
    if best_name_score(primary, person) < 1:
        reasons.append("name matches by initial only")
    if primary["works_count"] < 10:
        reasons.append(f"only {primary['works_count']} works")
    if topic_fit(primary, person) < 0.3:
        reasons.append("topics fit the departments poorly")

    # Same-name authors that share topics with the primary profile are probably
    # fragments of the same career; other USC namesakes are listed for context.
    top_topics = [short(t["id"]) for t in (primary.get("topics") or [])[:5]]
    pool = {a["id"]: a for _, a in scored[1:] if display_score(a, person) >= 0.6}
    if top_topics:
        for v in variants(person)[:2]:
            for a in search_authors(v, "topics.id:" + "|".join(top_topics), per_page=25):
                if a["id"] != primary["id"] and display_score(a, person) >= 0.6:
                    pool.setdefault(a["id"], a)
    splits, namesakes = [], []
    for a in pool.values():
        overlap = topic_overlap(a, primary)
        (splits if overlap >= 0.3 else namesakes).append((overlap, a))
    splits.sort(key=lambda x: -x[0])
    namesakes.sort(key=lambda x: -score(x[1], person, best_name_score(x[1], person)))

    rivals = [(sc, a) for sc, a in scored[1:] if display_score(a, person) >= 0.6]
    if rivals and rivals[0][0] > 0.85 * best_score and topic_overlap(rivals[0][1], primary) < 0.3:
        runner = rivals[0][1]
        reasons.append(f"close runner-up {short(runner['id'])} ({runner['display_name']})")

    return {
        "person": person,
        "primary": primary,
        "splits": [a for _, a in splits[:4]],
        "namesakes": [a for _, a in namesakes[:3]],
        "confidence": "check" if reasons else "high",
        "reasons": reasons,
    }


def sample_works(author_id, n_cited=4, n_recent=4):
    cited = top_works([author_id], "cited_by_count:desc", n_cited)
    recent = top_works([author_id], "publication_date:desc", n_recent)
    return cited, recent


def work_line(w):
    title = " ".join((w.get("title") or "(untitled)").split())
    if len(title) > 110:
        title = title[:107] + "..."
    venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
    bits = [str(w.get("publication_year") or "?")]
    if venue:
        bits.append(venue[:40])
    bits.append(f"{w.get('cited_by_count', 0)} cites")
    return f"{title} ({', '.join(bits)})"


# ---------------------------------------------------------------- output

def md_escape(text):
    return str(text).replace("|", "\\|")


def author_link(a):
    return f"[{a['id']}](https://openalex.org/{a['id']})"


def describe(a):
    usc = f"USC {a['usc_years'][0]}–{a['usc_years'][1]}" if a["usc_years"] else "never at USC"
    orcid = f" · ORCID [{a['orcid']}](https://orcid.org/{a['orcid']})" if a["orcid"] else ""
    return f"{author_link(a)} **{md_escape(a['display_name'])}** · {a['works_count']} works · {usc}{orcid}"


def write_review(entries, missing=()):
    lines = [
        "# OpenAlex author check",
        "",
        "Generated by `scripts/resolve_authors.py`. For each faculty member, check that the",
        "chosen profile's papers are theirs, and whether any of the *possible extra profiles*",
        "are the same person (often their pre-USC papers). Record decisions in",
        "`data/openalex-authors.json`: put every correct ID in `openalex`, set `status` to",
        "`verified`, and the next run keeps them.",
        "",
        "| | Faculty | Group | Profiles used | Works | At USC | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    order = sorted(entries, key=lambda e: (e["status"] == "verified", e["confidence"] == "high",
                                           GROUPS.index(e["group"]), e["name"]))
    for e in order:
        p = e["primary"]
        verified = e["status"] == "verified"
        mark = "✔︎" if verified else ("✅" if e["confidence"] == "high" else "⚠️")
        used = ", ".join(f"[{i}](https://openalex.org/{i})" for i in e["openalex"])
        if e.get("dois"):
            used = (used + "; " if used else "") + f"{len(e['dois'])} papers by DOI"
        primary_used = p and p["id"] in e["openalex"]
        usc = f"{p['usc_years'][0]}–{p['usc_years'][1]}" if primary_used and p["usc_years"] else "—"
        note = e.get("note") if verified else "; ".join(e["reasons"])
        lines.append(
            f"| {mark} | [{md_escape(e['name'])}](#{e['id']}) | {e['group']} | {used or '—'} | "
            f"{p['works_count'] if primary_used else '—'} | {usc} | {md_escape(note or '')} |")
    lines += ["", "⚠️ please look · ✅ confident automatic match · ✔︎ checked by hand", ""]
    if missing:
        lines += [f"**Not resolved yet ({len(missing)}):** {', '.join(missing)}. "
                  "Rerun the script once the OpenAlex budget resets.", ""]

    for e in order:
        lines += ["---", "", f'<a id="{e["id"]}"></a>', f"## {e['name']}", ""]
        lines.append(f"{e['group'].title()} · {md_escape(e['title'] or '')}")
        lines.append("")
        if e["status"] == "verified" and e.get("note"):
            lines += [f"> {md_escape(e['note'])}", ""]
        if e.get("dois"):
            lines.append(f"**Papers by DOI ({len(e['dois'])}):** "
                         + ", ".join(f"[{d}](https://doi.org/{d})" for d in e["dois"]))
            lines.append("")
        p = e["primary"]
        if not p:
            lines += ["**No OpenAlex profile found.**", ""]
            continue
        used = p["id"] in e["openalex"]
        label = "Chosen" if used else "Rejected automatic pick"
        lines.append(f"**{label}:** {describe(p)}")
        lines.append("")
        lines.append(f"Topics: {', '.join(p['topics'])}")
        lines.append("")
        inst = "; ".join(f"{i['name']} {i['years'][0]}–{i['years'][1]}" for i in p["institutions"])
        lines.append(f"Affiliations: {md_escape(inst)}")
        lines.append("")
        lines.append("Most cited:")
        lines += [f"- {md_escape(w)}" for w in e["sample"]["cited"]]
        lines.append("")
        lines.append("Most recent:")
        lines += [f"- {md_escape(w)}" for w in e["sample"]["recent"]]
        lines.append("")
        if e["splits"]:
            lines.append("**Possible extra profiles** (same name, overlapping topics):")
            lines.append("")
            for s in e["splits"]:
                tag = ""
                if e["status"] == "verified":
                    tag = "**✔︎ used** · " if s["id"] in e["openalex"] else "✗ left out · "
                lines.append(f"- {tag}{describe(s)} · topic overlap {s['topic_overlap']}")
                lines.append(f"  - {md_escape(', '.join(s['topics'][:3]))}")
                for w in s.get("sample", []):
                    lines.append(f"  - {md_escape(w)}")
            lines.append("")
        uses_namesake = any(s["id"] in e["openalex"] for s in e["namesakes"])
        if e["namesakes"] and (e["confidence"] != "high" or uses_namesake):
            lines.append("Other same-name authors at USC (topics differ from the chosen profile):")
            lines.append("")
            for s in e["namesakes"]:
                tag = ""
                if e["status"] == "verified":
                    tag = "**✔︎ used** · " if s["id"] in e["openalex"] else "✗ left out · "
                lines.append(f"- {tag}{describe(s)} · {md_escape(', '.join(s['topics'][:3]))}")
            lines.append("")
    with open(REVIEW, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", help="faculty ids to (re)resolve")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--review-only", action="store_true", help="no API calls; rewrite the review")
    args = ap.parse_args()

    with open(FACULTY, encoding="utf-8") as f:
        faculty = [p for p in json.load(f)["faculty"] if p["group"] in GROUPS]
    mapping = {}
    if os.path.exists(MAPPING):
        with open(MAPPING, encoding="utf-8") as f:
            mapping = json.load(f)

    def work(person):
        old = mapping.get(person["id"], {})
        if old.get("status") == "verified" and "primary" in old:
            return {**old, "id": person["id"], "name": person["name"]}
        res = resolve(person)
        p = res["primary"]
        prim = summarize(p, person) if p else None
        if prim:
            cited, recent = sample_works(p["id"])
            sample = {"cited": [work_line(w) for w in cited], "recent": [work_line(w) for w in recent]}
        else:
            sample = {"cited": [], "recent": []}
        splits = []
        for s in res["splits"]:
            info = summarize(s, person, p)
            info["sample"] = [work_line(w) for w in top_works([s["id"]], "cited_by_count:desc", 2)]
            splits.append(info)
        namesakes = [summarize(s, person, p) for s in res["namesakes"]]
        entry = {
            "id": person["id"], "name": person["name"], "group": person["group"], "title": person["title"],
            "primary": prim, "splits": splits, "namesakes": namesakes, "sample": sample,
            "confidence": res["confidence"], "reasons": res["reasons"],
        }
        entry["status"] = "auto"
        entry["openalex"] = [prim["id"]] if prim else []
        entry["note"] = old.get("note", "")
        return entry

    todo = [] if args.review_only else [p for p in faculty if not args.only or p["id"] in args.only]
    entries, out_of_budget = {}, None
    with futures.ThreadPoolExecutor(args.workers) as ex:
        jobs = {ex.submit(work, p): p for p in todo}
        for job in futures.as_completed(jobs):
            try:
                entry = job.result()
            except futures.CancelledError:
                continue
            except OutOfBudget as exc:
                out_of_budget = out_of_budget or str(exc)
                for other in jobs:
                    other.cancel()
                continue
            entries[entry["id"]] = entry
            p = entry["primary"]
            tag = "verified" if entry["status"] == "verified" else entry["confidence"]
            print(f"{tag:8} {entry['name']:28} {p['id'] if p else '-':12} "
                  f"{(p['display_name'] if p else ''):24} splits={len(entry['splits'])} "
                  f"{'; '.join(entry['reasons'])}")

    # Keep entries that weren't rerun this time (--only).
    for pid, old in mapping.items():
        if pid not in entries and "primary" in old:
            entries[pid] = {**old}

    ordered = {p["id"]: entries[p["id"]] for p in faculty if p["id"] in entries}
    with open(MAPPING, "w", encoding="utf-8") as f:
        keys = ("name", "status", "openalex", "dois", "note", "confidence", "reasons",
                "primary", "splits", "namesakes", "sample")
        json.dump({pid: {k: e[k] for k in keys if k in e} for pid, e in ordered.items()},
                  f, indent=2, ensure_ascii=False)
        f.write("\n")
    by_id = {p["id"]: p for p in faculty}
    write_review([{**e, "id": pid, "group": by_id[pid]["group"], "title": by_id[pid]["title"]}
                  for pid, e in ordered.items()],
                 [p["name"] for p in faculty if p["id"] not in ordered])
    n_check = sum(1 for e in ordered.values() if e["status"] != "verified" and e["confidence"] != "high")
    print(f"\nwrote {os.path.relpath(MAPPING, ROOT)} and {os.path.relpath(REVIEW, ROOT)}: "
          f"{len(ordered)} of {len(faculty)} faculty, {n_check} flagged for a look")
    if credits_left is not None:
        print(f"OpenAlex credits left today: {credits_left}")
    missing = [p["name"] for p in faculty if p["id"] not in ordered]
    if out_of_budget:
        sys.exit(f"\nOpenAlex budget used up before {len(missing)} faculty: {', '.join(missing)}.\n"
                 "Rerun after midnight UTC, or add a free API key (see the top of this script).")


if __name__ == "__main__":
    main()
