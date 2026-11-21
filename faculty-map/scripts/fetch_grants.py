#!/usr/bin/env python3
"""Fetch the QCB faculty's federal grants from NIH RePORTER and the NSF Award API.

Both sources are searched by name, so matching is a decision made by hand, kept in
data/grant-ids.json: NIH by PI profile id, NSF lead PIs by piId and NSF co-PIs by the
email NSF lists for them (co-PIs have no id). Writes:

    data/grants.json         trimmed records: no amounts, no other people's names or emails
    data/grants-review.md    the match check: every identity the searches found, kept or not

A grant is one NIH core project (fiscal years, renewals and the person's projects inside
a center grant collapse into it) or one NSF award. Raw responses are cached for the day in
gitignored data/raw/grants/, so a rerun the same day is quick.

Traps this handles:
- RePORTER matches first names loosely (Liang finds LIANGJING), and common names have many
  profiles (15 Sheng Lis), so nothing is kept by name alone.
- NSF matches whole name tokens (Krishna doesn't find Krishnakumar) and drops accents (search
  Tavare, not Tavaré), so it searches by surname when that returns few enough awards.
- NSF's offset is 0-based.
- After a PI change an NSF award keeps the original PI's piId but shows the new PI's name,
  so a kept piId claims rows under other names. An award that moved to a new id entirely
  is listed in nsf_awards.
- RePORTER sometimes files a namesake's grant under a kept profile (Paul R. Thompson's South
  Carolina P20 sits under Paul M. Thompson's), so nih_skip lists core projects to leave out.
- NSF shows a PI's current email even on old awards, so a USC email is strong evidence.

    python3 scripts/fetch_grants.py
"""

import collections
import datetime as dt
import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TODAY = dt.date.today().isoformat()
CACHE = os.path.join(DATA, "raw", "grants", TODAY)
AGENT = "faculty-map-grants-script"

NIH_URL = "https://api.reporter.nih.gov/v2/projects/search"
NIH_FIELDS = ["ApplId", "SubprojectId", "FiscalYear", "ProjectNum", "CoreProjectNum", "ProjectTitle",
              "Organization", "PrincipalInvestigators", "ActivityCode", "AgencyIcAdmin",
              "ProjectStartDate", "ProjectEndDate"]
NSF_URL = "https://api.nsf.gov/services/v1/awards.json"
NSF_FIELDS = ("id,title,awardeeName,pdPIName,piFirstName,piLastName,piEmail,piId,coPDPI,"
              "startDate,expDate,transType,dirAbbr,divAbbr")
NSF_SURNAME_MAX = 300   # search by surname alone when it finds at most this many awards
USC = "southern california"


def cached(key, fetch):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, hashlib.sha1(key.encode()).hexdigest() + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    for attempt in range(5):
        try:
            data = fetch()
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))
    with open(path, "w") as f:
        json.dump(data, f)
    return data


def nih_post(body):
    def fetch():
        req = urllib.request.Request(NIH_URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
        time.sleep(1.1)   # RePORTER asks for about one request a second
        return out
    return cached(json.dumps(body, sort_keys=True), fetch)


def nih_search(criteria):
    rows, offset = [], 0
    while True:
        d = nih_post({"criteria": criteria, "include_fields": NIH_FIELDS, "offset": offset, "limit": 500})
        rows += d["results"]
        offset += 500
        if offset >= d["meta"]["total"] or offset > 14500:
            return rows, d["meta"]["total"]


def nsf_get(params):
    url = NSF_URL + "?" + urllib.parse.urlencode(params)
    def fetch():
        req = urllib.request.Request(url, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.load(r)
        time.sleep(0.6)
        return out
    return cached(url, fetch)["response"]


def nsf_search(field, name):
    rows, offset = [], 0
    while True:
        d = nsf_get({field: name, "printFields": NSF_FIELDS, "rpp": 25, "offset": offset})
        got = d.get("award", [])
        rows += got
        total = d.get("metadata", {}).get("totalCount", len(got))
        offset += 25
        if not got or offset >= total or offset >= 3000:
            return rows, total


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return "".join(c for c in s if c.isalpha())


class Person:
    def __init__(self, p, ids):
        self.p, self.ids, self.id = p, ids, p["id"]
        self.reviewed = self.id in ids["people"]
        self.d = ids["people"].get(self.id, {})
        self.firsts = [p["first"]] + self.d.get("first", [])
        self.lasts = [p["last"]] + self.d.get("last", [])
        self.email = (p.get("email") or "").lower()

    def surname_ok(self, last):
        # A longer surname can carry a second part (Kribelbauer-Swietek); short ones can't
        # (Li must not match Lin).
        n = norm(last)
        return any(n == x or (len(x) >= 5 and n.startswith(x)) for x in map(norm, self.lasts))

    def first_ok(self, first):
        f = norm(first)
        return any(f == w or f.startswith(w) or (w.startswith(f) and len(f) > 1) for w in map(norm, self.firsts))


def iso(mdy):
    m, d, y = mdy.split("/")
    return f"{y}-{m}-{d}"


def tidy_title(t):
    """Older NIH titles are all capitals. Sentence case reads better; short words stay
    capitals since they're usually acronyms (DNA, HIV, MRI)."""
    t = " ".join((t or "").split())
    if not t.isupper():
        return t
    small = {"of", "and", "the", "in", "to", "for", "by", "on", "at", "an", "a", "as", "with", "from",
             "into", "its", "via", "or", "is", "are", "new", "how", "use", "can", "not", "all", "two", "one"}
    words = []
    for i, w in enumerate(t.split()):
        core = re.sub(r"[^A-Za-z]", "", w)
        if core.lower() in small or len(core) > 3 or not core:
            w = w.lower()
        words.append(w)
    out = " ".join(words)
    return out[:1].upper() + out[1:]


# Short, consistent names for institutions NIH and NSF spell differently or abbreviate. Keys are
# lowercase with punctuation turned into spaces.
ORG_NAMES = {
    "university of california los angeles": "UCLA",
    "university of california san diego": "UC San Diego",
    "university of california irvine": "UC Irvine",
    "university of california berkeley": "UC Berkeley",
    "university of california riverside": "UC Riverside",
    "university of california at davis": "UC Davis",
    "university of california santa barbara": "UC Santa Barbara",
    "california institute of technology": "Caltech",
    "rutgers university new brunswick": "Rutgers",
    "rutgers the state univ of n j": "Rutgers",
    "regents of the university of michigan ann arbor": "University of Michigan",
    "university of michigan at ann arbor": "University of Michigan",
    "university of illinois at urbana champaign": "University of Illinois Urbana-Champaign",
    "university of illinois at chicago": "University of Illinois Chicago",
    "scripps research institute the": "Scripps Research",
    "the scripps research institute": "Scripps Research",
    "university of virginia main campus": "University of Virginia",
    "university of north texas hlth sci ctr": "University of North Texas Health Science Center",
    "ut southwestern medical center": "UT Southwestern Medical Center",
    "university of pittsburgh at pittsburgh": "University of Pittsburgh",
    "university of south carolina at columbia": "University of South Carolina",
    "university of maryland baltimore": "University of Maryland, Baltimore",
    "harvard university d b a harvard school of public health": "Harvard School of Public Health",
    "brigham and women s hospital": "Brigham and Women's Hospital",
    "massachusetts eye and ear infirmary": "Massachusetts Eye and Ear",
    "new york university school of medicine": "NYU School of Medicine",
    "northern california institute res edu": "Northern California Institute for Research and Education",
    "sainte justine university hospital ctr": "Sainte-Justine University Hospital Center",
    "keystone symposia on molecular and cellular biology": "Keystone Symposia",
    "mellon pitts corporation mpc corp": "Mellon Pitts Corporation",
    "virginia polytechnic institute and state university": "Virginia Tech",
}


def org_name(name):
    """Where a grant is now, or None at USC."""
    if not name or USC in name.lower():
        return None
    key = " ".join(re.sub(r"[^a-z0-9]+", " ", name.lower()).split())
    if key in ORG_NAMES:
        return ORG_NAMES[key]
    if not name.isupper():
        return name
    small = {"of", "and", "the", "at", "in", "for"}
    words = [w if w in {"UCLA", "UCSD", "MIT", "SUNY"} else w.lower() if w.lower() in small else w.capitalize()
             for w in name.split()]
    return " ".join(words)[:1].upper() + " ".join(words)[1:]


# ---------------------------------------------------------------- NIH

def nih_grants(person, rows):
    """Collapse the rows where this person is a PI into one entry per core project."""
    mine = set(person.d.get("nih", []))
    skip = set(person.d.get("nih_skip", []))
    by_core = {}
    for r in rows:
        pis = r.get("principal_investigators") or []
        if not any(pi["profile_id"] in mine for pi in pis):
            continue
        core = r.get("core_project_num") or r["project_num"]
        if core in skip:
            continue
        g = by_core.setdefault(core, {"parent": [], "sub": []})
        g["sub" if r.get("subproject_id") else "parent"].append(r)
    out = []
    for core, g in by_core.items():
        rows_ = g["parent"] or g["sub"]
        latest = max(rows_, key=lambda r: (r["fiscal_year"], r["appl_id"]))
        both = g["parent"] + g["sub"]
        starts = [r["project_start_date"][:10] for r in both if r.get("project_start_date")]
        ends = [r["project_end_date"][:10] for r in both if r.get("project_end_date")]
        activity = latest.get("activity_code") or ""
        if activity.startswith("F"):
            role = "fellowship"
        elif g["parent"]:
            n = max(len(r.get("principal_investigators") or []) for r in g["parent"])
            role = "PI" if n == 1 else "multi-PI"
        else:
            role = "center project"
        entry = {
            "src": "NIH", "id": core, "kind": activity,
            "funder": (latest.get("agency_ic_admin") or {}).get("abbreviation"),
            "title": tidy_title(latest["project_title"]), "role": role,
            "org": org_name((latest.get("organization") or {}).get("org_name")),
            "start": min(starts) if starts else None, "end": max(ends) if ends else None,
            "url": f"https://reporter.nih.gov/project-details/{latest['appl_id']}",
        }
        if not g["parent"]:
            entry["projects"] = len({r["subproject_id"] for r in g["sub"]})
        out.append(entry)
    return out


def nih_candidates(person, rows):
    """Every PI profile in the name-search rows whose name fits, for the review."""
    prof = collections.defaultdict(lambda: {"names": set(), "orgs": collections.Counter(), "fy": [], "start": []})
    for r in rows:
        for pi in r.get("principal_investigators") or []:
            if not (person.surname_ok(pi["last_name"]) and person.first_ok(pi["first_name"])):
                continue
            g = prof[pi["profile_id"]]
            g["names"].add(" ".join(pi["full_name"].split()).title())
            g["orgs"][((r.get("organization") or {}).get("org_name") or "?").title()] += 1
            g["fy"].append(r["fiscal_year"])
            if r.get("project_start_date"):
                g["start"].append(r["project_start_date"][:10])
    return prof


# ---------------------------------------------------------------- NSF

def split_copi(s):
    parts = s.split()
    email = parts[-1].lower() if parts and "@" in parts[-1] else ""
    name = parts[:-1] if email else parts
    return (name[0] if name else ""), (name[-1] if name else ""), " ".join(name), email


def nsf_identities(person, rows):
    """Lead PIs grouped by piId and co-PIs grouped by email, among rows whose names fit."""
    lead = collections.defaultdict(lambda: {"names": set(), "emails": set(), "orgs": collections.Counter(), "start": [], "ids": []})
    co = collections.defaultdict(lambda: {"names": set(), "orgs": collections.Counter(), "start": [], "ids": []})
    named = {a.get("piId") for a in rows if person.surname_ok(a.get("piLastName")) and person.first_ok(a.get("piFirstName"))}
    for a in rows:
        start = iso(a["startDate"]) if a.get("startDate") else ""
        if a.get("piId") in named:
            g = lead[a["piId"]]
            g["names"].add(a.get("pdPIName")); g["emails"].add((a.get("piEmail") or "").lower())
            g["orgs"][a.get("awardeeName")] += 1; g["start"].append(start); g["ids"].append(a["id"])
        for c in a.get("coPDPI") or []:
            first, last, name, email = split_copi(c)
            if person.surname_ok(last) and person.first_ok(first):
                g = co[email or name]
                g["names"].add(name); g["orgs"][a.get("awardeeName")] += 1; g["start"].append(start); g["ids"].append(a["id"])
    return lead, co


def nsf_kept(person, lead, co):
    """piIds and co-PI keys this person is: the hand decisions, plus any carrying their email."""
    pis = set(person.d.get("nsf_pi", [])) | {k for k, g in lead.items() if person.email and person.email in g["emails"]}
    cos = set(person.d.get("nsf_co", [])) | ({person.email} & set(co))
    return pis, cos


def nsf_grants(person, rows, lead, co):
    pis, cos = nsf_kept(person, lead, co)
    role = {}
    for k in cos:
        for i in co[k]["ids"]:
            role[i] = "co-PI"
    for k in pis:
        for i in lead[k]["ids"]:
            role[i] = "PI"
    for i in person.d.get("nsf_awards", []):
        role.setdefault(i, "PI")
    by_id = {a["id"]: a for a in rows}
    out = []
    for i, r in role.items():
        a = by_id.get(i) or (nsf_get({"id": i, "printFields": NSF_FIELDS}).get("award") or [None])[0]
        if not a:
            continue
        title = " ".join(a["title"].split())
        fellowship = "fellowship" in (a.get("transType") or "").lower()
        prefixes = re.match(r"^((?:(?:collaborative research|career)\s*:\s*)*)(.*)$", title, flags=re.I)
        career = "career" in prefixes.group(1).lower()
        title = prefixes.group(2)
        kind = "CAREER" if career else ("fellowship" if fellowship else None)
        out.append({
            "src": "NSF", "id": i, "kind": kind,
            "funder": a.get("divAbbr") or a.get("dirAbbr"),
            "title": tidy_title(title), "role": "fellowship" if fellowship else r,
            "org": None if fellowship else org_name(a.get("awardeeName")),
            "start": iso(a["startDate"]) if a.get("startDate") else None,
            "end": iso(a["expDate"]) if a.get("expDate") else None,
            "url": f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={i}",
        })
    return out


# ---------------------------------------------------------------- review

def review(people, found, ids):
    reviewed = ids["reviewed"]
    tot = collections.Counter()
    table, sections = [], []
    for person in people:
        f = found[person.id]
        grants = f["grants"]
        nih = [g for g in grants if g["src"] == "NIH"]
        nsf = [g for g in grants if g["src"] == "NSF"]
        act = lambda gs: sum(1 for g in gs if (g["end"] or "") >= TODAY)   # noqa: E731
        tot["people"] += 1
        tot["nih"] += bool(nih); tot["nih_act"] += act(nih) > 0
        tot["nsf"] += bool(nsf); tot["nsf_act"] += act(nsf) > 0
        tot["any"] += bool(grants); tot["any_act"] += act(grants) > 0

        flags, sec = [], [f"### {person.p['name']}", f'<a id="{person.id}"></a>', ""]
        if not person.reviewed:
            flags.append("not reviewed yet")
        kept_nih = set(person.d.get("nih", []))
        if f["nih_cand"]:
            sec.append("NIH profiles whose name fits:")
            for pid, g in sorted(f["nih_cand"].items(), key=lambda kv: (kv[0] not in kept_nih, -len(kv[1]["fy"]))):
                new = pid not in kept_nih and person.reviewed and min(g["start"] or ["0"]) >= reviewed
                if new:
                    flags.append(f"new NIH profile {pid}")
                tag = "kept" if pid in kept_nih else ("**new, not reviewed**" if new else "rejected")
                orgs = ", ".join(o for o, _ in g["orgs"].most_common(2))
                sec.append(f"- {tag}: [{pid}](https://reporter.nih.gov/search/results?pi_profile_id={pid}) "
                           f"{' / '.join(sorted(g['names']))}, FY{min(g['fy'])}–{max(g['fy'])}, {len(g['fy'])} rows, {orgs}")
            sec.append("")
        lead, co = f["nsf_lead"], f["nsf_co"]
        pis, cos = nsf_kept(person, lead, co)
        if lead or co:
            sec.append("NSF identities whose name fits:")
            for k, g in sorted(lead.items(), key=lambda kv: (kv[0] not in pis, -len(kv[1]["ids"]))):
                auto = k not in person.d.get("nsf_pi", []) and k in pis
                new = k not in pis and person.reviewed and min(g["start"] or ["0"]) >= reviewed
                if new or auto:
                    flags.append(f"{'new' if new else 'kept by email'}: NSF lead PI {k}")
                tag = "kept by email" if auto else ("kept" if k in pis else ("**new, not reviewed**" if new else "rejected"))
                orgs = ", ".join(o for o, _ in g["orgs"].most_common(2))
                names = sorted(n for n in g["names"] if n)
                sec.append(f"- {tag}: lead PI {k} ({' / '.join(names)}), {min(g['start'])[:4]}–{max(g['start'])[:4]}, "
                           f"{len(g['ids'])} awards, {orgs}")
            for k, g in sorted(co.items(), key=lambda kv: (kv[0] not in cos, -len(kv[1]["ids"]))):
                auto = k not in person.d.get("nsf_co", []) and k in cos
                new = k not in cos and person.reviewed and min(g["start"] or ["0"]) >= reviewed
                if new or auto:
                    flags.append(f"{'new' if new else 'kept by email'}: NSF co-PI")
                tag = "kept by email" if auto else ("kept" if k in cos else ("**new, not reviewed**" if new else "rejected"))
                orgs = ", ".join(o for o, _ in g["orgs"].most_common(2))
                # Other people's emails stay out of the public repo.
                who = k if k in cos else " / ".join(sorted(g["names"]))
                sec.append(f"- {tag}: co-PI {who}, {min(g['start'])[:4]}–{max(g['start'])[:4]}, {len(g['ids'])} awards, {orgs}")
            sec.append("")
        if person.d.get("nsf_awards"):
            sec += [f"NSF awards kept by hand: {', '.join(person.d['nsf_awards'])}.", ""]
        if person.d.get("nih_skip"):
            sec += [f"NIH grants left out by hand (someone else's, under a kept profile): {', '.join(person.d['nih_skip'])}.", ""]
        if person.d.get("note"):
            sec += [person.d["note"], ""]
        if not f["nih_cand"] and not lead and not co:
            sec += ["No NIH or NSF records under this name.", ""]
        sections += sec

        mark = "⚠️" if flags or person.d.get("check") else "✔︎"
        note = "; ".join(flags) + (". " if flags else "") + person.d.get("note", "")
        table.append(f"| {mark} | [{person.p['name']}](#{person.id}) | {person.p['group']} | "
                     f"{', '.join(map(str, person.d.get('nih', []))) or '—'} | {', '.join(sorted(pis)) or '—'} | "
                     f"{', '.join(sorted(cos)) or '—'} | {len(nih)} ({act(nih)}) | {len(nsf)} ({act(nsf)}) | {note} |")
    lines = [
        "# Grant match check", "",
        f"Written by scripts/fetch_grants.py on {TODAY}. Decisions live in data/grant-ids.json (reviewed {reviewed}).", "",
        f"**Coverage ({tot['people']} QCB faculty, adjunct excluded):** NIH {tot['nih']} with any grant, {tot['nih_act']} active; "
        f"NSF {tot['nsf']} with any award, {tot['nsf_act']} active; either source {tot['any']} with any, {tot['any_act']} active.", "",
        "Both sources are searched by name, so every match is a decision: NIH by PI profile id, NSF lead PIs by piId,",
        "and NSF co-PIs by the email NSF lists for them. ✔︎ checked by hand, ⚠️ please look. Identities the",
        "searches found that aren't kept are listed under each person; a namesake co-PI is named, not emailed.",
        "NSF awards keep the original PI's id after a PI change, so a few kept awards show another person's name.", "",
        f"A grant is one NIH core project (fiscal years, renewals and center projects collapse into it) or one NSF award.",
        f"Active means the project end date is on or after {TODAY}. Counts are grants (active).", "",
        "| | Faculty | Group | NIH profile | NSF lead-PI id | NSF co-PI email | NIH grants | NSF awards | Note |",
        "|---|---|---|---|---|---|---|---|---|",
        *table, "", "## Details", "", *sections,
    ]
    with open(os.path.join(DATA, "grants-review.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return tot


def main():
    with open(os.path.join(DATA, "faculty.json")) as f:
        roster = [p for p in json.load(f)["faculty"] if p["group"] != "adjunct"]
    with open(os.path.join(DATA, "grant-ids.json")) as f:
        ids = json.load(f)
    people = [Person(p, ids) for p in roster]

    # NIH grants by profile id, in one search; the name searches are only for the review.
    profiles = sorted({i for person in people for i in person.d.get("nih", [])})
    by_profile, n = nih_search({"pi_profile_ids": profiles})
    print(f"NIH: {n} rows for {len(profiles)} profiles")
    found = {}
    for person in people:
        named = []
        for last in person.lasts:
            for first in person.firsts:
                rows, _ = nih_search({"pi_names": [{"first_name": first, "last_name": last}]})
                named += rows
        nsf_rows, seen = [], set()
        for last in person.lasts:
            for field in ("pdPIName", "coPDPI"):
                total = nsf_get({field: last, "printFields": "id", "rpp": 1, "offset": 0}).get("metadata", {}).get("totalCount", 0)
                names = [last] if total <= NSF_SURNAME_MAX else [f"{first} {last}" for first in person.firsts]
                for name in names:
                    for a in nsf_search(field, name)[0]:
                        if a["id"] not in seen:
                            seen.add(a["id"]); nsf_rows.append(a)
        lead, co = nsf_identities(person, nsf_rows)
        grants = nih_grants(person, by_profile) + nsf_grants(person, nsf_rows, lead, co)
        grants.sort(key=lambda g: (g["end"] or "", g["start"] or ""), reverse=True)
        found[person.id] = {"grants": grants, "nih_cand": nih_candidates(person, named), "nsf_lead": lead, "nsf_co": co}
        print(f"{person.id}: {len(grants)} grants")

    tot = review(people, found, ids)
    out = {
        "fetched": TODAY,
        "sources": {"NIH": "https://reporter.nih.gov", "NSF": "https://www.nsf.gov/awardsearch/"},
        "people": {pid: f["grants"] for pid, f in found.items()},
    }
    with open(os.path.join(DATA, "grants.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"wrote data/grants.json and data/grants-review.md: {tot['any']} of {tot['people']} with grants, "
          f"{tot['any_act']} active")


if __name__ == "__main__":
    main()
