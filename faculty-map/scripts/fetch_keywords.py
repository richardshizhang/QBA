#!/usr/bin/env python3
"""Download OpenAlex's most used research keywords into data/raw/openalex-keywords.json.

scripts/build_match_data.py adds them to the terms a student can use, so a standard
phrase still counts as one idea when no faculty paper happens to use those exact words.

    python3 scripts/fetch_keywords.py

OpenAlex has about 1.9 million keywords, and all of them would cost most of a day's
credits. PAGES keeps this to the most used, at 1 credit per page of 200.
"""

import json
import os

import openalex

OUT = os.path.join(openalex.ROOT, "data", "raw", "openalex-keywords.json")
PAGES = 150


def main():
    names, cursor = [], "*"
    for _ in range(PAGES):
        page = openalex.get_json("/keywords", {"per-page": 200, "cursor": cursor, "sort": "works_count:desc",
                                               "select": "display_name,works_count"})
        names += [k["display_name"] for k in page["results"]]
        cursor = page["meta"].get("next_cursor")
        if not cursor:
            break
    print(f"the last keyword kept has {page['results'][-1]['works_count']} works")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sorted(set(names)), f, ensure_ascii=False, indent=0)
    print(f"wrote {os.path.relpath(OUT, openalex.ROOT)}: {len(set(names))} keywords, {openalex.credits_left} credits left")


if __name__ == "__main__":
    main()
