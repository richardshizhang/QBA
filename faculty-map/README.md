# QCB Faculty Research Map

A map of USC's Quantitative and Computational Biology faculty (core and joint). Faculty who work on similar problems or use similar techniques sit close together, and lines connect people who have published together.

**Status:** work in progress. All 48 core, joint and emeritus faculty are matched to their publication records in [OpenAlex](https://openalex.org), a free database of scholarly papers, and their papers are downloaded and filtered (10,412 distinct papers kept). The map itself isn't built yet.

## Plan

1. **Roster.** Scrape https://www.qcb-dornsife.usc.edu/faculty. ✔︎
2. **Match faculty to OpenAlex author profiles**, checked by hand. ✔︎
3. **Download papers.** Fetch titles, abstracts, topics and authorship details, dropping namesakes' papers, reviewer reports and supplementary files. ✔︎
4. **Collaboration edges.** Count co-authored papers, down-weighting huge consortium papers.
5. **Research similarity.** Compare TF-IDF on abstracts, OpenAlex topic profiles and scientific-text embeddings (SPECTER2).
6. **Problem vs. technique.** Give each a separate similarity score (later).
7. **Dimensionality reduction and clustering.** Compare PCA, MDS, t-SNE and UMAP in a notebook.
8. **Interactive page** like the [course map](../course-dependency-graph/).

Emeriti are included and will sit behind a toggle. The adjunct member (UCLA) is left out.

## Files

| Path | What it is |
| --- | --- |
| `scripts/scrape_faculty.py` | Scrapes the faculty page into `data/faculty.json`: group, title, departments, rank, contact details and links. |
| `scripts/resolve_authors.py` | Matches each person to OpenAlex author IDs. Writes `data/openalex-authors.json` and the review page `data/id-review.md`. |
| `scripts/fetch_papers.py` | Downloads everyone's papers as trimmed records into `data/papers/papers.json`, filters them, and writes `data/paper-report.md`. |
| `scripts/openalex.py` | Shared OpenAlex API access (key, budget, retries). |
| `data/faculty.json` | Generated roster. Don't edit by hand; rerun the scraper. |
| `data/openalex-authors.json` | Faculty → OpenAlex author IDs. Entries with `"status": "verified"` were checked by hand and survive reruns. `openalex` lists every profile that belongs to the person, since OpenAlex often splits one career across several profiles. `dois` lists papers for anyone OpenAlex never linked to a profile. |
| `data/id-review.md` | Most-cited and most-recent papers for each match, plus the possible extra profiles, for checking by eye. |
| `data/paper-overrides.json` | Hand corrections to the paper filter: `{"person-id": {"keep": [...], "drop": [...]}}` with OpenAlex work IDs. |
| `data/paper-report.md` | Papers kept and dropped per person: off-profile drops, plus kept papers with unusual topics to check. |
| `data/papers/` | Downloaded paper records (gitignored, about 26 MB). Rebuild with `scripts/fetch_papers.py`. |
| `data/raw/` | Cached page and author-search responses (gitignored). |

## Running

Only the Python standard library is needed so far.

```bash
python3 scripts/scrape_faculty.py
python3 scripts/resolve_authors.py
python3 scripts/fetch_papers.py
```

After editing `data/paper-overrides.json`, reapply the filters without downloading again:

```bash
python3 scripts/fetch_papers.py --refilter
```

OpenAlex bills in credits: a name search costs 10, a filtered list 1, and a lookup by ID nothing. Without a key, everyone on your network shares 1,000 credits a day, which is enough for about 30 faculty in the matching step. A free key from https://openalex.org/settings/api raises that to 10,000. Save the key in a file named `.openalex-key` in this folder (it's gitignored), or set `OPENALEX_API_KEY`. Author searches are cached in `data/raw/openalex/`. Paper downloads aren't cached raw: only the trimmed records are kept, and a full download costs about 120 credits.

### What a paper record keeps

Title, year, type, venue, citation count, the plain-text abstract (about 70% of kept papers have one), OpenAlex's primary topic with its subfield and field, keywords, and the number of authors. For each faculty member on the paper, it also keeps their author position, their institutions on that paper, and whether one of those was USC. Full author lists are used while downloading, to build each person's co-author network, and are then thrown away. One consequence: author counts are capped at 100, which only matters for consortium papers.

### How papers are filtered

- **Not research:** peer reviews, errata, supplementary figures and tables, datasets, "Data from …" deposits, reference entries, other people's dissertations, non-English duplicates, retractions.
- **Duplicates:** the same title under several IDs (preprint and journal version, conference paper and book chapter) becomes one record.
- **Off-profile:** for each person, papers linked through shared co-authors to a paper they published at USC are trusted. Other papers are dropped if their co-author cluster's topics barely overlap the trusted ones (topic cosine similarity below 0.15), or if they're lone papers in a rarely-used subfield. For people with few USC papers, their largest co-author cluster is trusted too. This removes namesakes' papers: Andrew Smith's NASA motor designs, a UK ophthalmologist in Scott Fraser's profile, a glioblastoma lab in April Shu's. It also drops genuine early work in another field, such as Doc Edge's psychology papers or Ruishan Liu's optics papers, which suits a map of current research.
- **By hand:** papers with a USC affiliation always pass, so a namesake *at USC* gets through. The report lists kept papers with unusual topics so they can be dropped in `data/paper-overrides.json`.

### What OpenAlex gets wrong

- **Split profiles:** one person spread across several author IDs (e.g. Steve Kay's plant-clock papers). The resolver flags same-name profiles with overlapping topics, and the correct ones get added by hand.
- **Merged profiles:** other people's papers inside a correct profile (Liang Chen, Sheng Li, Andrew Smith, Yingxiao Wang, April Shu). The paper filter above handles these. For April Shu, the automatic pick merged so many Chang Shus that it was rejected; the profile carrying her ORCID is used instead.
- **Unlinked authors:** Peter Foster's papers are in OpenAlex, but under no author profile. His papers come from the DOIs on his lab website.
