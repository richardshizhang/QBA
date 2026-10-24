# QCB Faculty Research Map

A map of USC's Quantitative and Computational Biology faculty (core and joint). Faculty who work on similar problems or use similar techniques sit close together, and lines connect people who have published together.

**Status:** work in progress. The roster is scraped, and all 48 core, joint and emeritus faculty are matched to their publication records in [OpenAlex](https://openalex.org), a free database of scholarly papers, and checked by hand. The map itself isn't built yet.

## Plan

1. **Roster.** Scrape https://www.qcb-dornsife.usc.edu/faculty. ✔︎
2. **Match faculty to OpenAlex author profiles**, checked by hand. ✔︎
3. **Download papers.** Fetch titles, abstracts, topics and full author lists, dropping namesakes' papers, reviewer reports and supplementary files.
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
| `data/faculty.json` | Generated roster. Don't edit by hand; rerun the scraper. |
| `data/openalex-authors.json` | Faculty → OpenAlex author IDs. Entries with `"status": "verified"` were checked by hand and survive reruns. `openalex` lists every profile that belongs to the person, since OpenAlex often splits one career across several profiles. `dois` lists papers for anyone OpenAlex never linked to a profile. |
| `data/id-review.md` | Most-cited and most-recent papers for each match, plus the possible extra profiles, for checking by eye. |
| `data/raw/` | Cached page and API responses (gitignored). |

## Running

Only the Python standard library is needed so far.

```bash
python3 scripts/scrape_faculty.py
python3 scripts/resolve_authors.py
```

OpenAlex bills in credits: a name search costs 10, a filtered list 1, and a lookup by ID nothing. Without a key, everyone on your network shares 1,000 credits a day, which is enough for about 30 faculty. A free key from https://openalex.org/settings/api raises that to 10,000. Save the key in a file named `.openalex-key` in this folder (it's gitignored), or set `OPENALEX_API_KEY`. Responses are cached in `data/raw/openalex/`, so reruns are free, and if the budget runs out midway the script saves what it finished.

### What OpenAlex gets wrong

- **Split profiles:** one person spread across several author IDs (e.g. Steve Kay's plant-clock papers). The resolver flags same-name profiles with overlapping topics, and the correct ones get added by hand.
- **Merged profiles:** other people's papers inside a correct profile (Liang Chen, Sheng Li, Andrew Smith, Yingxiao Wang, April Shu). These get filtered paper by paper in step 3. For April Shu, the automatic pick merged so many Chang Shus that it was rejected; the profile carrying her ORCID is used instead.
- **Unlinked authors:** Peter Foster's papers are in OpenAlex, but under no author profile. His papers come from the DOIs on his lab website.
