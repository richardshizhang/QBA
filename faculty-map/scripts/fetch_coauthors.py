#!/usr/bin/env python3
"""Download the full author lists of faculty papers since 2018, as trimmed records.

data/papers/papers.json only records faculty authors. Finding PhD students on papers
and estimating lab sizes needs everyone else too, so this looks up each kept paper
and stores, for each author: OpenAlex ID, name, author position, whether they listed
USC on that paper, and whether they're marked as corresponding author. Raw API
responses are never written to disk.

Output goes to data/papers/coauthors.json (gitignored).

    python3 scripts/fetch_coauthors.py

A full run costs about 90 OpenAlex credits (one per 50 papers).
Only the standard library is used.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openalex  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS = os.path.join(ROOT, "data", "papers", "papers.json")
OUT = os.path.join(ROOT, "data", "papers", "coauthors.json")

USC = "https://openalex.org/I1174212"
SINCE = 2018
BATCH = 50


def trim_authorship(a):
    insts = a.get("institutions") or []
    return [openalex.short(a["author"].get("id")), a["author"].get("display_name"), a.get("author_position"),
            any(USC in (i.get("lineage") or [i.get("id")]) for i in insts), bool(a.get("is_corresponding"))]


def main():
    with open(PAPERS, encoding="utf-8") as f:
        works = json.load(f)["works"]
    ids = sorted(w["id"] for w in works.values() if (w["year"] or 0) >= SINCE
                 and any(i["keep"] for i in w["faculty"].values()))
    out = {}
    for start in range(0, len(ids), BATCH):
        batch = ids[start:start + BATCH]
        data = openalex.get_json("/works", {"filter": "openalex_id:" + "|".join(batch), "per-page": BATCH,
                                            "select": "id,authorships"})
        for w in data["results"]:
            out[openalex.short(w["id"])] = [trim_authorship(a) for a in w["authorships"]]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"since": SINCE, "works": out}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out)} of {len(ids)} papers, {os.path.getsize(OUT) / 1e6:.1f} MB; "
          f"credits left {openalex.credits_left}")


if __name__ == "__main__":
    main()
