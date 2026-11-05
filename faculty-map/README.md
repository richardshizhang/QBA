# QCB Faculty Research Map

An interactive map of USC's Quantitative and Computational Biology faculty (core, joint and emeritus). Faculty who work on similar problems or use similar techniques sit close together, and lines connect people who have published together.

- **Two map views, t-SNE and UMAP**, animate between each other. Nearby means similar research; distances between far-apart groups don't mean much.
- **Tree** shows the full hierarchy of who is similar to whom, cut into 9 clusters. **List** has everyone in a table.
- **Click a person** for their research terms, QCB co-authors, most similar colleagues, and recent papers. **Click a line** for the papers a pair share.
- **Search** by name or topic, such as "cancer" or "MRI", to light up who works on it.
- **Filter** by core, joint and emeritus faculty, and show all collaborations, the closest only, or none.
- **Find your place on the map.** Type your interests and experience and a "You" dot flies in, with lines to your closest faculty labeled with shared keywords. Or throw a dot: flick it from the corner, or drag it anywhere, to see who works near that spot and what the area is about. It all runs in the browser, so nothing typed is sent anywhere.

Open `index.html` in a browser. It's a static page with no build step and no dependencies beyond a Google Font.

**Status:** first version of the page is done. All 48 core, joint and emeritus faculty are matched to their publication records in [OpenAlex](https://openalex.org), a free database of scholarly papers. Their papers are downloaded and filtered (10,435 distinct papers kept), collaboration edges are built (51 pairs), and each person has three research-feature vectors. The map's positions and clusters are exported to `data/layout.json` (t-SNE and UMAP on SPECTER2 for all 48 people, with an average-linkage tree cut into 9 clusters), and the interactive page is built. The cluster names in `data/cluster-names.json` are drafts.

## Plan

1. **Roster.** Scrape https://www.qcb-dornsife.usc.edu/faculty. ✔︎
2. **Match faculty to OpenAlex author profiles**, checked by hand. ✔︎
3. **Download papers.** Fetch titles, abstracts, topics and authorship details, dropping namesakes' papers, reviewer reports and supplementary files. ✔︎
4. **Collaboration edges.** Count co-authored papers, down-weighting huge consortium papers. ✔︎
5. **Research similarity.** Compare TF-IDF on abstracts, OpenAlex topic profiles and scientific-text embeddings (SPECTER2). ✔︎
6. **Problem vs. technique.** Give each a separate similarity score (later).
7. **Dimensionality reduction and clustering.** Compare PCA, MDS, t-SNE and UMAP in `analysis.ipynb`, then export the chosen views. ✔︎
8. **Interactive page** like the [course map](../course-dependency-graph/). ✔︎

Emeriti are included. The adjunct member (UCLA) is left out.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole page: layout, drawing and interaction. |
| `map-data.js` | Generated data (`window.QCB_MAP`). Don't edit by hand. |
| `match-data.js` | Generated table for matching typed text (`window.QCB_MATCH`), about 600 KB. The page loads it only when someone clicks into the text box. |
| `scripts/build_map_data.py` | Combines the layout, roster, edges, features and papers into `map-data.js`. |
| `scripts/build_match_data.py` | Builds `match-data.js`. With `--evaluate`, also measures accuracy on held-out papers. |
| `scripts/scrape_faculty.py` | Scrapes the faculty page into `data/faculty.json`: group, title, departments, rank, contact details and links. |
| `scripts/resolve_authors.py` | Matches each person to OpenAlex author IDs. Writes `data/openalex-authors.json` and the review page `data/id-review.md`. |
| `scripts/fetch_papers.py` | Downloads everyone's papers as trimmed records into `data/papers/papers.json`, filters them, and writes `data/paper-report.md`. |
| `scripts/build_edges.py` | Builds collaboration edges from the kept papers into `data/edges.json` and writes `data/collaboration-report.md`. |
| `scripts/build_features.py` | Builds each person's TF-IDF, topic and SPECTER2 vectors into `data/features/faculty-features.npz` and writes `data/features/features-report.md`. |
| `scripts/openalex.py` | Shared OpenAlex API access (key, budget, retries). |
| `analysis.ipynb` | Dimensionality reduction, clustering and the collaboration overlay. Exports the chosen layouts and tree to `data/layout.json`. Set the representation only in the cell that builds `X`: everything after it reads `X`, `S` and `D` from there, and changing `REP` anywhere else only changes plot titles. |
| `data/faculty.json` | Generated roster. Don't edit by hand; rerun the scraper. |
| `data/openalex-authors.json` | Faculty → OpenAlex author IDs. Entries with `"status": "verified"` were checked by hand and survive reruns. `openalex` lists every profile that belongs to the person, since OpenAlex often splits one career across several profiles. `dois` lists papers for anyone OpenAlex never linked to a profile. |
| `data/id-review.md` | Most-cited and most-recent papers for each match, plus the possible extra profiles, for checking by eye. |
| `data/paper-overrides.json` | Hand corrections to the paper filter: `{"person-id": {"keep": [...], "drop": [...]}}` with OpenAlex work IDs. |
| `data/paper-report.md` | Papers kept and dropped per person: off-profile drops, plus kept papers with unusual topics to check. |
| `data/papers/` | Downloaded paper records and cached SPECTER2 paper embeddings (gitignored, about 40 MB). Rebuild with `scripts/fetch_papers.py` and `scripts/build_features.py`. |
| `data/edges.json` | One entry per pair of faculty who share papers: strength, paper counts by author-list size, papers where both list USC, years, and up to 8 example papers. Also each person's number of QCB co-authors and total strength. |
| `data/collaboration-report.md` | All edges in a table, the most connected faculty, and those with no QCB co-authors. |
| `data/features/faculty-features.npz` | The 48 faculty's feature matrices (`tfidf`, `topics`, `subfields`, `fields`, `specter`) with vocabularies and topic names. Committed (about 1.3 MB) so the notebook runs from a fresh clone. |
| `data/features/features-report.md` | Top terms, top topics and nearest neighbours per person under each representation, and how much the representations agree. |
| `data/cluster-names.json` | Hand-written cluster names and colors. Each entry names one member as its `anchor`, so a name stays with its group if cluster numbers change. |
| `data/layout.json` | Positions and the tree, written by the notebook's last cell. `faculty` has each person's cluster and one `[x, y]` per layout (0–1, same scale on both axes, layouts rotated to line up). `tree` holds the full average-linkage tree: in `merges`, node numbers below the faculty count are people in `faculty` order, and n+i is `merges[i]`. |
| `data/raw/` | Cached page and author-search responses (gitignored). |

## Running

The data scripts need only the Python standard library. Features and the notebook need numpy, scikit-learn, scipy, matplotlib, seaborn and umap-learn. SPECTER2 embeddings also need torch, transformers and the `adapters` library, which goes in a project virtual environment so it can't disturb other Python work:

```bash
python3 scripts/scrape_faculty.py
python3 scripts/resolve_authors.py
python3 scripts/fetch_papers.py
python3 scripts/build_edges.py
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install adapters
.venv/bin/python scripts/build_features.py
```

Then run `analysis.ipynb` to export `data/layout.json`, and build the page's data:

```bash
python3 scripts/build_map_data.py
python3 scripts/build_match_data.py
```

If you change the number of clusters, `build_map_data.py` lists any groups that still need an entry in `data/cluster-names.json`.

The SPECTER2 model download is about 440 MB (into `~/.cache/huggingface`). Embedding all 10,435 papers takes about four minutes on an Apple-silicon GPU. Paper embeddings are cached, so later runs take seconds.

After editing `data/paper-overrides.json`, reapply the filters without downloading again:

```bash
python3 scripts/fetch_papers.py --refilter
```

OpenAlex bills in credits: a name search costs 10, a filtered list 1, and a lookup by ID nothing. Without a key, everyone on your network shares 1,000 credits a day, which is enough for about 30 faculty in the matching step. A free key from https://openalex.org/settings/api raises that to 10,000. Save the key in a file named `.openalex-key` in this folder (it's gitignored), or set `OPENALEX_API_KEY`. Author searches are cached in `data/raw/openalex/`. Paper downloads aren't cached raw: only the trimmed records are kept, and a full download costs about 120 credits.

### What a paper record keeps

Title, year, type, venue, citation count, the plain-text abstract (about 70% of kept papers have one), OpenAlex's primary topic with its subfield and field, keywords, and the number of authors. For each faculty member on the paper, it also keeps their author position, their institutions on that paper, and whether one of those was USC. Full author lists are used while downloading, to build each person's co-author network, and are then thrown away. OpenAlex's list responses show at most 100 authors, so author counts are capped at 100. On those consortium papers, a faculty member listed after the 100th has no recorded affiliation, so the off-profile check below skips them.

### How papers are filtered

- **Not research:** peer reviews, errata, supplementary figures and tables, datasets, "Data from …" deposits, reference entries, placeholder records ("OUP accepted manuscript", "Contributors"), other people's dissertations, non-English duplicates, retractions.
- **Duplicates:** the same title under several IDs (preprint and journal version, conference paper and book chapter) becomes one record.
- **Off-profile:** for each person, papers linked through shared co-authors to a paper they published at USC are trusted. Other papers are dropped if their co-author cluster's topics barely overlap the trusted ones (topic cosine similarity below 0.15), or if they're lone papers in a rarely-used subfield. For people with few USC papers, their largest co-author cluster is trusted too. This removes namesakes' papers: Andrew Smith's NASA motor designs, a UK ophthalmologist in Scott Fraser's profile, a glioblastoma lab in April Shu's. It also drops genuine early work in another field, such as Doc Edge's psychology papers or Ruishan Liu's optics papers, which suits a map of current research.
- **By hand:** papers with a USC affiliation always pass, so a namesake *at USC* gets through. The report lists kept papers with unusual topics so they can be dropped in `data/paper-overrides.json`.

### How collaboration is measured

Two faculty members are linked when both are kept authors of the same paper. Each shared paper adds 1/(authors − 1) to the pair's **strength**, which is Newman's collaboration weight. A two-author paper adds 1, a ten-author paper 0.11, and a 100-author consortium paper about 0.01. So Kanso and Newton's 17 small papers (strength 9.4) outweigh Irimia and Thompson's 23 mostly consortium papers (0.9). Paper counts, broken down by author-list size, are kept alongside, as is the number of papers on which both list a USC affiliation.

Strengths run from 0.01 to about 100: Toga and Thompson share 683 papers going back to their UCLA lab. The map will need a log scale for line widths. 39 of the 48 faculty have at least one QCB co-author. The other 9 are listed at the end of the collaboration report.

### Colors on the map

Nine clusters is more than color alone can carry: on a scatter any two hues can sit side by side, and eight hues can't all stay distinct for colorblind readers. So the cluster names are written on the map, hovering a legend entry highlights that cluster, and the List view has everything as text. Hues were assigned by computing which clusters are neighbors in either layout and choosing the arrangement that keeps neighbors most distinct. The ninth cluster reuses a hue as a hollow marker rather than adding a ninth color: "Protein structure & drug design" shares its hue with "Gene regulation & genome structure", its neighbor in the tree.

### Matching a student to faculty

SPECTER2 is far too big to run in a browser, and the page has no server, so what someone types can't be embedded the way the papers were. Instead, `build_match_data.py` precomputes one row of 48 numbers for each of about 7,700 research terms, saying how strongly the term points at each person. Each number averages two signals: how much that person's papers use the term (TF-IDF), and how close the papers using the term are to that person in SPECTER2 space. The second reaches people who work on a topic in different words. Both are z-scored across faculty, then stored as one byte each.

The browser pulls the known terms out of the text, matching two-word phrases first, and averages their rows, weighting rarer terms more. Generic words ("does", "changes", "research") are ignored. Words it doesn't know ("python", "premed") are shown to the student rather than silently dropped.

**Accuracy.** Given only the title of a held-out paper, with the table built without it, the real author ranks first 68% of the time, in the top 3 85%, and in the top 5 88% (chance for top 5 is 10%). Averaging the two signals beat either alone: word use got 91% and meaning 86% top 5 on the full vocabulary, against 93% for the combined table, before shrinking it to fit a web page. Titles are written in the author's own vocabulary, though, so a student's words will do worse than these numbers suggest.

**Where the dot goes.** t-SNE and UMAP have no exact way to add a new point, so the dot sits at the weighted average of its closest matches, nudged off any mark it would cover. That's an estimate of where it belongs. A thrown dot works in reverse: it blends the people nearest where it lands, and is compared with everyone by cosine similarity using the faculty similarity matrix.

**Percentages** compare each person with the dot's closest match, who is always 100%. A typed dot's scores come from word matches and a thrown dot's from cosine similarity, so the two aren't comparable with each other.

### Research features

Every person gets three vectors built from their kept papers. Recent papers count most (weight halves every 10 years), first- and last-author papers count fully, middle-author papers half, and papers with more than 50 authors half again. That way Thompson's 2,500 consortium-heavy papers describe his own lab's work and don't swamp everything else.

- **TF-IDF**: words and two-word phrases from titles, abstracts and keywords. Each person's term frequencies are the weighted mean of their papers'. The IDF counts how many *faculty* use a term rather than how many papers, so prolific people don't set the vocabulary.
- **Topics**: shares of OpenAlex's topic labels (1,485 topics appear), plus coarser subfield and field shares.
- **SPECTER2**: [allenai/specter2](https://huggingface.co/allenai/specter2), a model trained so that papers which cite each other land close together, with its proximity adapter for similarity search. Each person's vector is the weighted mean of their papers' embeddings. Raw SPECTER2 vectors all point roughly the same way, so centre them (subtract the mean) before comparing.

The three agree well but not perfectly: rank correlation of 0.78 between TF-IDF and topics, and 0.69 between either and SPECTER2. Each person's nearest neighbours fall into the communities you'd expect: statistical and population genetics, neuroimaging, physics and mechanics of living systems, molecular simulation, machine learning, protein–DNA binding, ocean microbes.

### What OpenAlex gets wrong

- **Split profiles:** one person spread across several author IDs (e.g. Steve Kay's plant-clock papers). The resolver flags same-name profiles with overlapping topics, and the correct ones get added by hand.
- **Merged profiles:** other people's papers inside a correct profile (Liang Chen, Sheng Li, Andrew Smith, Yingxiao Wang, April Shu). The paper filter above handles these. For April Shu, the automatic pick merged so many Chang Shus that it was rejected; the profile carrying her ORCID is used instead.
- **Unlinked authors:** Peter Foster's papers are in OpenAlex, but under no author profile. His papers come from the DOIs on his lab website.
