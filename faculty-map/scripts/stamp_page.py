#!/usr/bin/env python3
"""Stamp index.html with a version of the data files it loads.

Browsers keep these files for a while, and a normal reload fetches a new page without
fetching its scripts again. A page that needs new data would then run on old data, so
every data URL carries this version and changes whenever the data does.

The build scripts run this, or:

    python3 scripts/stamp_page.py
"""

import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "index.html")
DATA = ("map-data.js", "map-data-extended.js", "match-data.js", "match-data-extended.js")


def stamp():
    digest = hashlib.sha1()
    for name in DATA:
        with open(os.path.join(ROOT, name), "rb") as f:
            digest.update(f.read())
    version = digest.hexdigest()[:10]
    with open(PAGE, encoding="utf-8") as f:
        page, found = re.subn(r'src="map-data\.js(\?v=\w+)?"', f'src="map-data.js?v={version}"', f.read())
    if found != 1:
        raise SystemExit("index.html should load map-data.js exactly once")
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"stamped index.html with data version {version}")


if __name__ == "__main__":
    stamp()
