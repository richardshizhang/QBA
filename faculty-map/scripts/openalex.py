"""Shared OpenAlex API access for the faculty map scripts.

OpenAlex bills in credits: a search costs 10, a filtered list 1, a lookup by ID
nothing. Without a key everyone on your network shares 1,000 credits a day; a free key
from https://openalex.org/settings/api gives 10,000. Put the key in the
OPENALEX_API_KEY environment variable or in a file named .openalex-key next to this
project's README (it is gitignored).
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openalex.org"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(ROOT, ".openalex-key")

credits_left = None  # from the last response's X-RateLimit-Remaining header


class OutOfBudget(Exception):
    pass


def api_key():
    if os.environ.get("OPENALEX_API_KEY"):
        return os.environ["OPENALEX_API_KEY"].strip()
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            return f.read().strip() or None
    return None


def short(oa_id):
    """'https://openalex.org/A123' -> 'A123'."""
    return oa_id.rsplit("/", 1)[-1] if oa_id else oa_id


def get_json(path, params, cache_dir=None):
    """GET {API}{path}?params. With cache_dir, responses are cached on disk by URL
    (the API key is not part of it)."""
    global credits_left
    query = urllib.parse.urlencode(params, safe=":|,*")
    url = f"{API}{path}?{query}"
    cache = None
    if cache_dir:
        cache = os.path.join(cache_dir, hashlib.sha1(url.encode()).hexdigest() + ".json")
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
    key = api_key()
    full = url + (f"&api_key={key}" if key else "")
    req = urllib.request.Request(full, headers={"User-Agent": "QBA faculty map (USC student project)"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
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
    if cache:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(data, f)
    return data
