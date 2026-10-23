"""Parse course text exported from the USC catalogue (see catalogue_export.js).

Each exported course is the plain text of its catalogue page, e.g.

    QBIO 478 Computational Genome Analysis
    Units: 4
    Terms Offered: Sp
    Introduction to algorithms and statistics for genome analysis ...
    Prerequisite: QBIO 310
    Duplicates Credit In former BISC 478

Prerequisite and corequisite sentences are turned into the same structure the
Schedule of Classes uses: a list of groups that are all required, where a group
needs `n` of its options and an option is a bundle of courses taken together.

    python3 scripts/catalogue.py data/catalogue-courses.json   # print what was parsed
"""

import json
import re
import sys

# "CHEM 105bL" -> CHEM 105B. Lowercase a-d / z right after the number is a sequence
# letter; L, g, x, w and friends are suffixes (lab, GE, ...) that the map ignores.
CODE_RE = re.compile(r"\b([A-Z]{2,5})[  ]?(\d{3})([abcdz]?)[A-Za-z]{0,3}\b")

FIELD_RE = re.compile(
    r"^(Prerequisites?|Prerequisite\(s\)|Corequisites?|Corequisite\(s\)|Concurrent Enrollment|"
    r"Recommended Preparation|Registration Restrictions?|Restrictions?|Duplicates Credit(?: In| in| with)?|"
    r"Terms Offered|Units|Instruction Mode|Grading Option|Crosslisted (?:as|with)|Max Units)\s*:?\s*(.*)$"
)
FIELD_KEYS = {
    "prerequisite": "pre", "prerequisites": "pre", "prerequisite(s)": "pre",
    "corequisite": "co", "corequisites": "co", "corequisite(s)": "co", "concurrent enrollment": "conc",
    "recommended preparation": "rec", "registration restriction": "restr", "registration restrictions": "restr",
    "restriction": "restr", "restrictions": "restr", "terms offered": "terms", "units": "units",
}
UI_LINES = re.compile(r"^(Print-Friendly Page|Add to Portfolio|Back to Top|HELP|Facebook|Tweet|Print|.*opens a new window.*)$", re.I)


def norm_code(prefix, number, seq):
    return f"{prefix} {number}{seq.upper()}"


def clean(text):
    """'MATH 126\xa0, or MATH 127\xa0;' -> 'MATH 126, or MATH 127' (for display)."""
    text = re.sub(r"\s+", " ", text.replace(" ", " ")).strip()
    text = re.sub(r"\s+([,;.)])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    return text.rstrip(" ;,.")


def tokenize(text):
    """Courses, connectives and parentheses; anything else is noise (e.g. 'placement exam')."""
    tokens = []
    pos = 0
    pattern = re.compile(
        r"(?P<course>\b[A-Z]{2,5}[  ]?\d{3}[abcdz]?[A-Za-z]{0,3}\b)"
        r"|(?P<nfrom>\b(\d|one|two|three)\s+(?:from|of)\b)"
        r"|(?P<and>\band\b|;|&)"
        r"|(?P<or>\bor\b)"
        r"|(?P<lp>\()|(?P<rp>\))|(?P<comma>,)"
        r"|(?P<word>[A-Za-z][A-Za-z'\-]*)",
        re.I,
    )
    words = {"one": 1, "two": 2, "three": 3}
    for m in pattern.finditer(text):
        kind = m.lastgroup
        if kind == "course":
            cm = CODE_RE.match(m.group(0).replace(" ", " "))
            if cm and m.group(0)[:2].isupper():
                tokens.append(("course", norm_code(*cm.groups())))
            else:
                tokens.append(("word", m.group(0)))
        elif kind == "nfrom":
            n = m.group(0).split()[0].lower()
            tokens.append(("nfrom", int(n) if n.isdigit() else words[n]))
        else:
            tokens.append((kind, m.group(0)))
        pos = m.end()
    return resolve_commas(tokens)


def resolve_commas(tokens):
    """'A, B or C' -> A or B or C; 'A, B and C' -> A and B and C (same paren depth)."""
    out = list(tokens)
    for i, (kind, _) in enumerate(out):
        if kind != "comma":
            continue
        depth, repl = 0, None
        for k2, v2 in out[i + 1:]:
            if k2 == "lp":
                depth += 1
            elif k2 == "rp":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and k2 in ("and", "or"):
                repl = k2
                break
        # Inside "1 from (A, B, C)" commas separate options.
        out[i] = (repl or ("or" if inside_nfrom(out, i) else "and"), ",")
    return out


def inside_nfrom(tokens, i):
    depth = 0
    for j in range(i - 1, -1, -1):
        kind = tokens[j][0]
        if kind == "rp":
            depth += 1
        elif kind == "lp":
            if depth == 0:
                return j > 0 and tokens[j - 1][0] == "nfrom"
            depth -= 1
    return False


class Parser:
    """and_expr := or_expr (AND or_expr)* ; or_expr := atom (OR atom)* ;
    atom := COURSE | '(' and_expr ')' | NFROM '(' and_expr ')' . 'or' binds tighter than 'and',
    which is how catalogue sentences like 'A or B and C or D' read."""

    def __init__(self, tokens):
        self.t = [tok for tok in tokens if tok[0] != "word"]
        self.i = 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def and_expr(self):
        parts = [self.or_expr()]
        while self.peek() == "and":
            self.take()
            parts.append(self.or_expr())
        parts = [p for p in parts if p]
        return parts[0] if len(parts) == 1 else ("and", parts) if parts else None

    def or_expr(self):
        parts = [self.atom()]
        while self.peek() == "or":
            self.take()
            parts.append(self.atom())
        parts = [p for p in parts if p]
        return parts[0] if len(parts) == 1 else ("or", parts) if parts else None

    def atom(self):
        kind = self.peek()
        if kind == "course":
            return ("course", self.take()[1])
        if kind == "nfrom":
            n = self.take()[1]
            inner = self.atom()
            if inner and inner[0] in ("or", "and"):
                return ("nof", n, inner[1])
            return inner
        if kind == "lp":
            self.take()
            inner = self.and_expr()
            if self.peek() == "rp":
                self.take()
            return inner
        if kind in ("and", "or", "rp"):
            return None  # dangling connective, e.g. "MATH 108 or placement exam"
        return None


def leaves(node):
    if node[0] == "course":
        return [node[1]]
    items = node[1] if node[0] in ("and", "or") else node[2]
    return [c for child in items for c in leaves(child)]


def to_groups(node):
    """AND of groups; each group needs n of its option bundles."""
    if node is None:
        return []
    kind = node[0]
    if kind == "course":
        return [{"n": 1, "o": [[node[1]]]}]
    if kind == "and":
        return [g for child in node[1] for g in to_groups(child)]
    n = 1 if kind == "or" else node[1]
    children = node[1] if kind == "or" else node[2]
    return [{"n": n, "o": [leaves(c) for c in children]}]


def parse_requisite(text):
    """Returns (groups, complete). complete is False when the sentence had words the
    parser had to skip (e.g. 'or departmental approval'), so callers can show the raw text."""
    tokens = tokenize(text)
    parser = Parser(tokens)
    groups = to_groups(parser.and_expr())
    skipped = [v for k, v in tokens if k == "word"]
    return groups, not skipped and parser.i == len(parser.t)


def parse_course(text):
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    title_i = next((i for i, ln in enumerate(lines) if CODE_RE.match(ln)), None)
    if title_i is None:
        return None
    m = CODE_RE.match(lines[title_i])
    rec = {"code": norm_code(*m.groups()), "title": lines[title_i][m.end():].strip()}
    desc = []
    for ln in lines[title_i + 1:]:
        if UI_LINES.match(ln):
            continue
        again = CODE_RE.match(ln)
        if again and norm_code(*again.groups()) == rec["code"] and ln.endswith(rec["title"]):
            continue  # the course block repeats its title as a heading
        fm = FIELD_RE.match(ln)
        if fm:
            key = FIELD_KEYS.get(fm.group(1).lower())
            if key and fm.group(2):
                rec[key] = clean(fm.group(2))
            elif fm.group(1).lower().startswith("duplicates credit"):
                rec["dup"] = (fm.group(1) + " " + fm.group(2)).strip()
            continue
        if "pre" not in rec and "co" not in rec and len(ln) > 30:
            desc.append(ln)
    if desc:
        rec["desc"] = " ".join(desc)
    for key in ("pre", "co", "conc"):
        if key in rec:
            rec[key + "_groups"], rec[key + "_complete"] = parse_requisite(rec[key])
    return rec


def load(path):
    with open(path) as f:
        data = json.load(f)
    out = {}
    for course in data.get("courses", []):
        rec = parse_course(course.get("text", ""))
        if rec:
            rec["url"] = course.get("url")
            out[rec["code"]] = rec
    return data, out


if __name__ == "__main__":
    data, parsed = load(sys.argv[1])
    print(f"{len(parsed)} courses parsed from {data.get('catalogue', '?')} ({len(data.get('failed', []))} failed)")
    for code in sorted(parsed):
        rec = parsed[code]
        if "pre" in rec or "co" in rec:
            fmt = lambda gs: " AND ".join("[" + (f"{g['n']} of " if g["n"] > 1 else "") + " | ".join("+".join(b) for b in g["o"]) + "]" for g in gs) or "-"
            flag = "" if rec.get("pre_complete", True) and rec.get("co_complete", True) else "  (partial)"
            print(f"{code:10} PRE {rec.get('pre', '-')!r} -> {fmt(rec.get('pre_groups', []))}"
                  + (f"   CO {rec['co']!r} -> {fmt(rec.get('co_groups', []))}" if "co" in rec else "") + flag)
