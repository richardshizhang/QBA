"""Polite web fetching for the roster and lab-size scripts.

Every request reads the site's robots.txt first, waits at least the crawl delay the
site asks for, and says who is asking. A refusal is final: a bot challenge or a 403
marks the host as blocked in data/raw/web/blocked.json, and nothing here retries it or
works around it. Pages are cached in data/raw/web/ by URL, so reruns cost nothing and
a page that is already saved is never requested again.
"""

import datetime
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "raw", "web")
BLOCKED = os.path.join(CACHE, "blocked.json")
AGENT = "QBA-faculty-map/1.0 (USC student project; +https://github.com/richardshizhang/QBA)"
MIN_DELAY = 1.5

CHALLENGE = re.compile(r"Just a moment\.\.\.|Enable JavaScript and cookies to continue|"
                       r"Attention Required!|cf-chl", re.I)

offline = False  # when True, get() only reads the cache


class Disallowed(Exception):
    """robots.txt asks crawlers to stay away from this URL."""


class RobotsUnreadable(Disallowed):
    """robots.txt could not be read, so the site counts as off limits for now."""


class Blocked(Exception):
    """The site refused us, or a bot challenge stands in front of the page."""


class NotCached(Exception):
    """Offline, and this page was never saved."""


class Page:
    def __init__(self, url, status, body):
        self.url, self.status, self.body = url, status, body

    @property
    def ok(self):
        return 200 <= self.status < 300


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


opener = urllib.request.build_opener(NoRedirect)
robots = {}  # host -> (rules, delay)
last_hit = {}  # host -> time of the last request


def host_of(url):
    return urllib.parse.urlsplit(url).netloc.lower()


def load_blocked():
    if os.path.exists(BLOCKED):
        with open(BLOCKED, encoding="utf-8") as f:
            return json.load(f)
    return {}


def mark_blocked(url, reason):
    blocked = load_blocked()
    blocked.setdefault(host_of(url), {"url": url, "reason": reason,
                                      "date": datetime.date.today().isoformat()})
    os.makedirs(CACHE, exist_ok=True)
    with open(BLOCKED, "w", encoding="utf-8") as f:
        json.dump(blocked, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- robots.txt

def parse_robots(text):
    """-> (rules, delay) that apply to every crawler. Rules are (allow, pattern).

    Lines above the first User-agent count too: bme.usc.edu puts its crawl delay there.
    """
    rules, delay, applies, in_agents = [], None, True, False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            applies = (applies or value == "*") if in_agents else value == "*"
            in_agents = True
            continue
        in_agents = False
        if not applies:
            continue
        if field == "crawl-delay":
            try:
                delay = float(value)
            except ValueError:
                pass
        elif field in ("allow", "disallow") and value:
            rules.append((field == "allow", value))
    return rules, delay


def pattern_matches(pattern, path):
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def rules_allow(rules, path):
    """The longest matching pattern decides; Allow wins a tie."""
    best = (-1, True)
    for allow, pattern in rules:
        if pattern_matches(pattern, path) and (len(pattern), allow) > best:
            best = (len(pattern), allow)
    return best[1]


def site_rules(url):
    host = host_of(url)
    if host not in robots:
        parts = urllib.parse.urlsplit(url)
        try:
            status, _, body = request(f"{parts.scheme}://{parts.netloc}/robots.txt")
        except OSError:
            raise RobotsUnreadable(f"could not read robots.txt for {host}")
        if status >= 500:
            raise RobotsUnreadable(f"robots.txt for {host} returned {status}")
        looks_like_robots = status == 200 and "<html" not in body[:500].lower()
        robots[host] = parse_robots(body) if looks_like_robots else ([], None)
    return robots[host]


# ---------------------------------------------------------------- fetching

def wait_for(host, delay):
    gap = time.time() - last_hit.get(host, 0)
    if gap < delay:
        time.sleep(delay - gap)
    last_hit[host] = time.time()


def request(url, data=None):
    """One HTTP request, no redirects followed. -> (status, location, body)."""
    req = urllib.request.Request(url, data=data, headers={"User-Agent": AGENT})
    try:
        with opener.open(req, timeout=45) as resp:
            return resp.status, None, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location"), e.read().decode("utf-8", errors="replace")


def cache_path(url, data):
    key = url + ("\n" + data.decode() if data else "")
    return os.path.join(CACHE, host_of(url) or "unknown", hashlib.sha1(key.encode()).hexdigest())


def store(url, status, body, data=None, final_url=None):
    path = cache_path(url, data)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".html", "w", encoding="utf-8") as f:
        f.write(body)
    with open(path + ".json", "w", encoding="utf-8") as f:
        json.dump({"url": url, "final_url": final_url or url, "status": status,
                   "fetched": datetime.date.today().isoformat()}, f, indent=1)


def fetched_on(url, data=None):
    path = cache_path(url, data) + ".json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["fetched"]
    return None


def get(url, data=None):
    """Fetch url and return a Page, following redirects one polite hop at a time.

    A missing page comes back with its status. Raises Disallowed, Blocked or NotCached.
    """
    path = cache_path(url, data)
    if os.path.exists(path + ".html"):
        with open(path + ".json", encoding="utf-8") as f:
            meta = json.load(f)
        with open(path + ".html", encoding="utf-8") as f:
            return Page(meta["final_url"], meta["status"], f.read())
    if offline:
        raise NotCached(url)

    current = url
    for _ in range(6):
        host = host_of(current)
        if host in load_blocked():
            raise Blocked(f"{host} refused an earlier request")
        rules, delay = site_rules(current)
        parts = urllib.parse.urlsplit(current)
        target = parts.path + (f"?{parts.query}" if parts.query else "")
        if not rules_allow(rules, target or "/"):
            raise Disallowed(current)
        wait_for(host, max(MIN_DELAY, delay or 0))
        try:
            status, location, body = request(current, data)
        except OSError as e:
            raise Blocked(f"{current}: {e}") if "403" in str(e) else e
        if status in (401, 403, 429) or CHALLENGE.search(body[:20000]) or (status == 202 and not body):
            mark_blocked(current, f"HTTP {status}")
            raise Blocked(f"{current} returned {status}")
        if status in (301, 302, 303, 307, 308) and location:
            current = urllib.parse.urljoin(current, location)
            data = None
            continue
        store(url, status, body, data if current == url else None, current)
        return Page(current, status, body)
    raise OSError(f"too many redirects from {url}")
