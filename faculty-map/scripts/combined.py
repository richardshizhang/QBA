"""The QCB roster and the extended roster together, for the --extended build steps.

people() is everyone on the combined map: QCB core, joint and emeritus faculty, plus
the named and department tiers once their OpenAlex match is verified.

works() merges data/papers/papers.json and data/papers/papers-extended.json. A paper in
both sets becomes one record listing everyone on it, and duplicates are regrouped across
the two sets, so a preprint in one and its journal version in the other count once.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_papers  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(ROOT, "data", "roster-extended.json")
MAPPING = os.path.join(ROOT, "data", "openalex-authors-extended.json")


def people():
    with open(ROSTER, encoding="utf-8") as f:
        roster = json.load(f)["faculty"]
    with open(MAPPING, encoding="utf-8") as f:
        mapping = json.load(f)
    return [p for p in roster if p["tier"] == "qcb"
            or (p["tier"] in ("named", "department") and mapping.get(p["id"], {}).get("status") == "verified")]


def works():
    merged = {}
    for path in (fetch_papers.PAPERS, fetch_papers.EXTENDED_PAPERS):
        with open(path, encoding="utf-8") as f:
            for wid, w in json.load(f)["works"].items():
                if wid in merged:
                    merged[wid]["faculty"].update(w["faculty"])
                else:
                    merged[wid] = w
    fetch_papers.mark_duplicates(merged)
    return merged
