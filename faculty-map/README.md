# QCB Faculty Research Map

An interactive map of USC's Quantitative and Computational Biology faculty (core, joint and emeritus). Faculty who work on similar problems or use similar techniques sit close together, and lines connect people who have published together.

- **Two map views, t-SNE and UMAP**, animate between each other. Nearby means similar research; distances between far-apart groups don't mean much.
- **3D** turns either map view into a globe that spins slowly. Drag to turn it, Pause stops it, and marks in front are bigger and darker.
- **Tree** shows the full hierarchy of who is similar to whom, cut into 9 clusters. **List** has everyone in a table.
- **Mark size** shows lab size, so bigger marks are bigger labs.
- **Dark mode** follows the system until someone flips the switch, and their choice stays in that browser.
- **Tutorial** walks through the real page in 12 steps, and people can try each control as they go.
- **Click a person** for their photo, lab size, h-index, citations, papers per year, research terms, QCB co-authors, most similar colleagues, and recent papers. **Click a line** for the papers a pair share.
- **QCB PhD students** fan out around their lab's mark when it's selected, and the panel lists them with their papers.
- **Randomize** highlights someone at random, working through everyone on show before anyone repeats.
- **Save** faculty to a list with their emails and lab websites, marked with a star on the map. It stays in the browser, and Copy list takes it elsewhere.
- **Search** by name or topic, such as "cancer" or "MRI", to light up who works on it. A PhD student's name finds their lab.
- **Filter** by core, joint and emeritus faculty, and show all collaborations, the closest only, or none.
- **Find your place on the map.** Type your interests and experience and a "You" dot flies in, with lines to your closest faculty labeled with shared keywords. Or throw a dot: flick it from the corner, or drag it anywhere, to see who works near that spot and what the area is about. It all runs in the browser, so nothing typed is sent anywhere.

Open `index.html` in a browser. It's a static page with no build step and no dependencies beyond a Google Font and the GoatCounter visit counter.

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
| `map-data.js` | Generated data (`window.QCB_MAP`): the QCB faculty, arranged by field and by technique. Don't edit by hand. |
| `map-data-extended.js` | Generated data (`window.QCB_MAP_EXTENDED`), about 930 KB: everyone else on the expanded map, loaded when someone turns on "Expand into related fields". |
| `match-data.js` | Generated table for matching typed text (`window.QCB_MATCH`), about 3 MB, or 1.4 MB as sent. The page loads it only when someone clicks into the text box. |
| `match-data-extended.js` | The same table for all 161 people (`window.QCB_MATCH_EXTENDED`), about 4 MB, or 2 MB as sent, loaded the first time someone matches text on the expanded map. |
| `scripts/build_map_data.py` | Combines the layouts, rosters, edges, features, papers and methods into `map-data.js` and `map-data-extended.js`. |
| `scripts/build_match_data.py` | Builds `match-data.js` and `match-data-extended.js`. Needs the `.venv`, as it runs SPECTER2 on every term. With `--evaluate`, also measures accuracy on held-out papers. |
| `scripts/stamp_page.py` | Puts a version of the data files on `index.html`'s data URLs, so a browser can't pair the page with an old cached copy. Both build scripts run it. |
| `scripts/fetch_keywords.py` | Downloads OpenAlex's 30,000 most used keywords into `data/raw/openalex-keywords.json`, for `build_match_data.py`. |
| `scripts/build_layouts_3d.py` | Works out a 3D twin of every flat layout into `data/layouts-3d.json`, with the same method and settings. |
| `scripts/scrape_faculty.py` | Scrapes the faculty page into `data/faculty.json`: group, title, departments, rank, contact details and links. |
| `scripts/scrape_departments.py` | Reads five more departments, the Brain and Creativity Institute and hand-picked labs, and merges them with the QCB roster into `data/roster-extended.json` and the review page `data/roster-report.md`. QCB records always win. |
| `scripts/scrape_lab_sizes.py` | Counts each lab's current members from its website into `data/lab-sizes.json` and `data/lab-size-report.md`. |
| `scripts/webfetch.py` | Shared polite fetching for those two: reads robots.txt, waits the site's crawl delay, caches pages, and stops at a bot challenge rather than retrying. |
| `scripts/scrape_students.py` | Scrapes the QCB PhD student and postdoc pages into `data/raw/students.json`: names, roles and labs only. |
| `scripts/fetch_coauthors.py` | Downloads full author lists for faculty papers since 2018 into `data/papers/coauthors.json`. |
| `scripts/fetch_student_papers.py` | Finds students' and postdocs' OpenAlex profiles through their advisors' papers, and downloads their USC papers into `data/papers/student-works.json`. |
| `scripts/build_labs.py` | Works out each lab's size and its students' paper lists into `data/labs.json` and `data/lab-report.md`. |
| `scripts/resolve_authors.py` | Matches each person to OpenAlex author IDs. Writes `data/openalex-authors.json` and the review page `data/id-review.md`. |
| `scripts/fetch_papers.py` | Downloads everyone's papers as trimmed records into `data/papers/papers.json`, filters them, and writes `data/paper-report.md`. |
| `scripts/build_edges.py` | Builds collaboration edges from the kept papers into `data/edges.json` and writes `data/collaboration-report.md`. |
| `scripts/build_features.py` | Builds each person's TF-IDF, topic and SPECTER2 vectors into `data/features/faculty-features.npz` and writes `data/features/features-report.md`. |
| `scripts/scrape_lab_research.py` | Reads each lab's home and research pages and its profile's research statement. The text goes to the gitignored `data/raw/lab-research.json`; `data/lab-research.json` keeps only which pages were read. |
| `scripts/build_methods.py` | Describes each lab by how it works rather than what it studies, at one level per method: demonstrated by its papers or website, potential from the data it generates, or firsthand. Writes `data/features/methods-features.npz`, `methods-report.md` and `data/lab-methods.json`. |
| `scripts/combined.py` | Merges the QCB and extended rosters and paper sets for the `--extended` build steps, regrouping duplicates across the two. |
| `scripts/openalex.py` | Shared OpenAlex API access (key, budget, retries). |
| `analysis.ipynb` | Dimensionality reduction, clustering and the collaboration overlay. Exports the chosen layouts and tree to `data/layout.json`. Set the representation only in the cell that builds `X`: everything after it reads `X`, `S` and `D` from there, and changing `REP` anywhere else only changes plot titles. |
| `data/faculty.json` | Generated roster. Don't edit by hand; rerun the scraper. |
| `data/openalex-authors.json` | Faculty → OpenAlex author IDs. Entries with `"status": "verified"` were checked by hand and survive reruns. `openalex` lists every profile that belongs to the person, since OpenAlex often splits one career across several profiles. `dois` lists papers for anyone OpenAlex never linked to a profile. |
| `data/openalex-authors-extended.json` | The same mapping for the named and department tiers, from `scripts/resolve_authors.py --extended`. Kept apart so the QCB mapping behind the live map doesn't change. Same fields, with `dois` for people whose papers OpenAlex never linked to a profile and `status: "unresolved"` for anyone still unmatched. |
| `data/id-review-extended.md` | The review page for that mapping. |
| `data/id-review.md` | Most-cited and most-recent papers for each match, plus the possible extra profiles, for checking by eye. |
| `data/paper-overrides.json` | Hand corrections to the paper filter: `{"person-id": {"keep": [...], "drop": [...]}}` with OpenAlex work IDs. |
| `data/paper-overrides-extended.json` | Hand corrections to the paper filter for the extended roster, in the same format as `data/paper-overrides.json`. |
| `data/paper-report-extended.md` | The paper report for the extended roster, from `scripts/fetch_papers.py --extended`. Its papers are in the gitignored `data/papers/papers-extended.json`, about 38 MB. |
| `data/paper-report.md` | Papers kept and dropped per person: off-profile drops, plus kept papers with unusual topics to check. |
| `data/papers/` | Downloaded paper records and cached SPECTER2 paper embeddings (gitignored, about 40 MB). Rebuild with `scripts/fetch_papers.py` and `scripts/build_features.py`. |
| `data/edges.json` | One entry per pair of faculty who share papers: strength, paper counts by author-list size, papers where both list USC, years, and up to 8 example papers. Also each person's number of QCB co-authors and total strength. |
| `data/collaboration-report.md` | All edges in a table, the most connected faculty, and those with no QCB co-authors. |
| `data/features/faculty-features.npz` | The 48 faculty's feature matrices (`tfidf`, `topics`, `subfields`, `fields`, `specter`) with vocabularies and topic names. Committed (about 1.3 MB) so the notebook runs from a fresh clone. |
| `data/features/features-report.md` | Top terms, top topics and nearest neighbours per person under each representation, and how much the representations agree. |
| `data/student-overrides.json` | Hand decisions on students' profiles and papers: `{"person-id": {"openalex": [...], "drop": [...], "note": "why"}}`. |
| `data/labs.json` | Size and source for every lab, plus PhD students in a lab and their papers. Generated. |
| `data/lab-report.md` | Website counts next to estimates, and every student's papers, for checking by eye. |
| `data/edges-extended.json` | Collaboration edges across QCB and the extended roster, from `scripts/build_edges.py --extended`, with `data/collaboration-report-extended.md` beside it. Same format as `data/edges.json`. |
| `data/features/extended-features.npz` | Feature matrices for all 161 people, from `scripts/build_features.py --extended`, with `extended-features-report.md` beside it. Same format as `faculty-features.npz`. New paper embeddings are in the gitignored `data/papers/specter2-extended.npz`. |
| `data/method-taxonomy.json` | The 37 quantitative and computational methods, with the terms that mark `analysis` (the paper does this work) and `data` (the paper generates data this work could use). |
| `data/lab-method-notes.json` | Firsthand reports of what people did in a lab, which papers can't show: `{"person-id": {"methods": ["computer-vision"], "note": "why"}}`. The notes appear on the page, so keep them anonymous. |
| `data/lab-methods.json` | Each lab's methods with their level and evidence, for the page: share of papers, an example paper, whether its website says so, and any firsthand note. It holds no website text. |
| `data/cluster-names.json` | Hand-written cluster names and colors. Each entry names one member as its `anchor`, so a name stays with its group if cluster numbers change. `cluster-names-methods.json`, `cluster-names-extended.json` and `cluster-names-extended-methods.json` do the same for the other three maps. |
| `data/layouts-3d.json` | The 3D twin of every layout in `data/layout*.json`, with its trustworthiness flat and in 3D. People sit inside a unit sphere. |
| `data/layout.json` | Positions and the tree, written by the notebook's last cell. `faculty` has each person's cluster and one `[x, y]` per layout (0–1, same scale on both axes, layouts rotated to line up). `tree` holds the full average-linkage tree: in `merges`, node numbers below the faculty count are people in `faculty` order, and n+i is `merges[i]`. |
| `data/layout-extended.json` | The same for all 161 people. `layout-methods.json` and `layout-extended-methods.json` are the technique layouts for the QCB faculty and for everyone. |
| `analysis-extended.ipynb` | A copy of `analysis.ipynb` for all 161 people, reading the `-extended` files. `REP` and `SCOPE` pick which layout its last cell writes, and it never writes `data/layout.json`. Saved without outputs. |
| `data/roster-extended.json` | Everyone from QCB and the other departments, one record each. `tier` is `qcb`, `named`, `department` or `secondary` (teaching, emeritus, adjunct, and joint or affiliate listings). `affiliations` lists QCB first, so joint faculty read as joint before their other department. `listed_on` shows which pages list them. Not used by the live map yet. |
| `data/roster-report.md` | Parsed counts for each listing, people to check, missing titles and pages that couldn't be read. |
| `data/lab-sizes.json` | Member count per lab with its source page and dates, or `null` and a `status` saying why there's no count. Counts only: names stay out of this public repo. |
| `data/lab-size-overrides.json` | Hand-checked counts: `{"person-id": {"members": 12}}`. These replace the automatic count on every run. |
| `data/lab-size-report.md` | All labs by size, with how many are counted and checked. |
| `data/raw/` | Cached pages, author-search responses and the names behind lab counts (gitignored). |

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
.venv/bin/python scripts/build_layouts_3d.py
python3 scripts/build_map_data.py
.venv/bin/python scripts/build_match_data.py
```

If you change the number of clusters, `build_map_data.py` lists any groups that still need an entry in `data/cluster-names.json`.

The SPECTER2 model download is about 440 MB (into `~/.cache/huggingface`). Embedding all 10,435 papers takes about four minutes on an Apple-silicon GPU. Paper embeddings are cached, so later runs take seconds.

To rebuild the extended roster, lab counts and methods:

```bash
python3 scripts/scrape_departments.py
python3 scripts/scrape_lab_sizes.py
python3 scripts/resolve_authors.py --extended
python3 scripts/fetch_papers.py --extended
python3 scripts/build_edges.py --extended
.venv/bin/python scripts/build_features.py --extended
python3 scripts/scrape_lab_research.py
python3 scripts/build_methods.py
```

Then export the layouts from `analysis-extended.ipynb` and build the page's data:

| `REP` | `SCOPE` | `K` | Writes |
|---|---|---|---|
| `"specter"` | `"extended"` | 9 | `data/layout-extended.json` |
| `"methods"` | `"extended"` | 12 | `data/layout-extended-methods.json` |
| `"methods"` | `"qcb"` | 7 | `data/layout-methods.json` |

```bash
.venv/bin/python scripts/build_layouts_3d.py
python3 scripts/build_map_data.py
.venv/bin/python scripts/build_match_data.py
```

The scrapers read saved pages from `data/raw/web/` first and need only the standard library. `--offline` uses saved pages alone. A few limits are worth knowing:

- **Use `analysis-extended.ipynb` for this data.** `analysis.ipynb` reads the QCB files, and its last cell writes `data/layout.json`, which the live map uses.
- **Keck profiles** (`keck.usc.edu/faculty-search/`) sit behind a Cloudflare bot challenge, so most biostatistics faculty have no title or lab link. Don't try to get past it. Saving those pages from a browser would work.
- **MCB and the Brain and Creativity Institute** are read from browser copies in `../other_department_faculty/`, because Dornsife's `Disallow: /*/page/` covers MCB pages 2–4. That folder isn't in the repo. Without it, the roster loses 31 of MCB's 43 people, and `data/roster-report.md` says so.
- **BME asks for 10 seconds between requests**, so its profile pages take a few minutes.
- **`data/lab-sizes.json` is the source for lab size.** It includes the PI and undergraduates.

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

### Fields, techniques and related fields

The page opens on the QCB faculty by field, as it always has. Two controls change the map:

- **By field / By technique** swaps what positions and clusters are built from: SPECTER2 embeddings of papers, or the method profiles from `scripts/build_methods.py`.
- **Expand into related fields** adds the other 113 people in `scripts/combined.py`. `map-data-extended.js` and `match-data-extended.js` load on first use, so the default page doesn't pay for them.

Both controls float over the top of the map. Each map opens on its own layout: expanded By field opens on MDS, and the others on t-SNE (`OPENS_ON` in `index.html`). A layout someone picks stays on any map that has it.

Each combination is a "world" in the data, with its own positions, clusters, tree and similarity matrix. People are numbered QCB first, so a person keeps their number in every world and a selection survives a switch. Everyone is laid out again on the expanded map, so QCB faculty move. The expanded maps use the t-SNE and MDS that were chosen for them, where the QCB maps use t-SNE and UMAP.

Clicking someone shows their methods in the panel, strongest evidence first. Opening a method shows its evidence and lights up every lab that has it.

### Matching a student to faculty

SPECTER2 is far too big to run in a browser, and the page has no server, so what someone types can't be embedded the way the papers were. Instead, `build_match_data.py` runs it ahead of time on about 66,000 research words and phrases, and stores how strongly each one points at each person. Each score averages two signals, both z-scored across faculty:

- **Meaning:** SPECTER2's embedding of the term itself, compared with each person's. This knows what "metabolic engineering" means even though no paper here uses those words.
- **Evidence:** how much of a person's work uses the term. A title, a keyword or repeated use counts in full, and one mention in an abstract counts for 0.2. It's divided by the square root of their papers, so a specialist can beat someone prolific, with a floor of 50 weighted papers so one paper can't look like a specialty for someone with very few. Meaning alone reads "directed evolution" as evolution, and this is what puts Warshel first.

**Phrases.** "Protein engineering" isn't protein plus engineering, so the browser splits text into the fewest known terms, and a phrase is never read as its words. Phrases are runs of up to four words with no punctuation or function word between them, seen in at least 5 papers across all 161 people, so the QCB table knows phrases only related fields use. Filler is dropped if its words don't sit together more than chance, or if its papers aren't about anything. OpenAlex's 30,000 most used keywords add 5,700 standard phrases no paper here uses, as long as all their words are familiar here. scikit-learn's stop list includes "computer" and "system", so `FUNCTION_WORDS` is a shorter list, or "computer vision" and "immune system" could never be phrases.

If two words aren't a known phrase, they're matched separately, and on a short query the panel says so. Generic words ("does", "changes", "research") are ignored. Words it doesn't know ("python", "premed") are shown to the student rather than silently dropped.

Each term stores only the people it points at most, 10 on the QCB map and 16 on the expanded one, with one floor for everyone else. Held-out accuracy doesn't change, and it's what lets this many terms fit a web page.

**Accuracy.** Given only the title of a held-out paper, with the tables built without it, the real author ranks first 78% of the time, in the top 3 90%, and in the top 5 93%. On the expanded map that's 70%, 84% and 88%. Before phrases and term meanings, the QCB figures were 68%, 85% and 88%, and the expanded top 5 was 82%. Given a phrase, someone with at least two held-out papers on it makes the top 5 94% of the time, or 89% on the expanded map. Titles are written in the author's own vocabulary, though, so a student's words will do worse than these numbers suggest, and a rare phrase can still put someone first on a single paper: Judith Kribelbauer leads "gene therapy" that way.

**Where the dot goes.** t-SNE and UMAP have no exact way to add a new point, so the dot sits at the weighted average of its closest matches, nudged off any mark it would cover. That's an estimate of where it belongs. A thrown dot works in reverse: it blends the people nearest where it lands, and is compared with everyone by cosine similarity using the faculty similarity matrix.

**Percentages** compare each person with the dot's closest match, who is always 100%. A typed dot's scores come from word matches and a thrown dot's from cosine similarity, so the two aren't comparable with each other.

### 3D

`build_layouts_3d.py` reads each layout file's method and settings and reruns them with a third component, so changing a layout in a notebook and rerunning keeps the two views in step. Each result is turned to line up with its flat map (orthogonal Procrustes), so 3D starts out looking like the map it came from.

| Map | Layout | Trustworthiness, flat | In 3D |
| --- | --- | ---: | ---: |
| QCB by field | t-SNE | 0.936 | 0.955 |
| QCB by field | UMAP | 0.948 | 0.956 |
| QCB by technique | t-SNE | 0.911 | 0.925 |
| QCB by technique | UMAP | 0.902 | 0.926 |
| Expanded by field | t-SNE | 0.980 | 0.983 |
| Expanded by field | MDS | 0.914 | 0.942 |
| Expanded by technique | t-SNE | 0.975 | 0.980 |
| Expanded by technique | MDS | 0.895 | 0.947 |

t-SNE needs different settings in 3D. scikit-learn's defaults stall at a poor map with this few people (0.79 on the QCB map), so it uses the exact method at learning rate 25 and keeps the best of 5 runs by KL divergence. That method squares a precomputed distance matrix in place, so every run needs its own copy.

The page draws 3D with the same SVG marks as the flat map: rotating and projecting just gives every person a new position, size and depth. That keeps clicks, student dots and your dot working, at 60 frames a second with 161 people, or about 26 on a CPU slowed 4x. The globe stops while someone is pointing at a mark, reading a panel or has a dot out, and people who ask their system for less motion start with it still. A dot sits at the front of the globe, so people on the far side count as further from it.

### Saved faculty

The list is ids in `localStorage`, so it lasts in that browser and survives a rebuild of the data. Nothing is sent anywhere. If storage fails, as in a private window, it lasts until the page closes. Someone saved from the related fields makes the Saved panel load `map-data-extended.js`, and opening them switches the map on. Emails come from the rosters, which have them for 47 of the 48 QCB faculty and 82 of the 113 others.

### Lab sizes

A mark's area shows lab size. QCB's own rosters place people in only 13 of the 48 labs, because students from other programs aren't listed, and not every lab has a website that can be read. So each size comes from the best source available:

- **Lab website (25 labs):** everyone the lab's website lists as a current member, PI and undergraduates included, from `data/lab-sizes.json`. 21 of these were checked by hand. Labs differ in who they list and how often they update, so compare them loosely. A lab is never smaller than the people QCB places in it plus the PI, which adds one to Edge, MacLean and Sun. `CAVEATS` in `build_labs.py` adds a warning on the page for three counts: Thompson's and Nakano's are whole centers, and Chiang's is probably high.
- **Estimate (18 labs):** USC co-authors on the person's senior-author papers since 2023 who appear on at least two of them or as first author on one, plus anyone QCB lists in the lab, plus the PI. People with three or more senior-author papers of their own are treated as collaborators. Across the 21 labs with both, the median estimate matches the website count, but 5 are off by more than a factor of two. Estimates run high for labs with turnover and low for new labs.
- **Unknown (5 labs):** no website count and too few recent USC papers, so the mark stays at its smallest. That doesn't mean there's no lab.

Labs of up to three people share the smallest mark. Above that, area is proportional to size.

### PhD students and their papers

Names alone can't be trusted here: the roster has a Wei Liu and a Yue Huang. So `fetch_student_papers.py` accepts an OpenAlex profile only if it appears on a paper by the student's advisor or has been checked by hand in `data/student-overrides.json`. It then keeps papers where the student listed USC or a QCB faculty member is a co-author, which removes namesakes on merged profiles but also earlier work elsewhere. `build_labs.py` removes conference abstracts, data deposits and repeat records.

26 of the 38 students in labs have papers, and those titles were read through by hand once for anything that didn't fit the lab. Students who haven't joined a lab aren't shown. Postdocs count toward lab size but aren't listed on the page.

### Photos and stats

Photos load from the department's Wix site rather than being copied here, so they follow its updates. If one fails to load, the panel simply leaves it out.

The h-index, citations and papers per year use the same filtered papers as the map. That filter also removes real early work in another field, so a few people score well below their OpenAlex profile: Michael Edge 16 against 21, Christoph Haselwandter 15 against 20, and Ruishan Liu 8 against 14. In other cases the filter is what removes a namesake's papers, as with April Shu (14 against 25).

### Visit counts

The page counts visits with [GoatCounter](https://www.goatcounter.com), which sets no cookies and collects no personal data. It only sees that the page was opened (plus referrer, browser and screen size), never what a student types, and the page keeps nothing in its URL. The "How this was made" dialog says this. Stats share the course map's dashboard at https://richardshizhang.goatcounter.com, listed by page path (sign in to see them).

GoatCounter ignores visits from `localhost` and from opening `index.html` as a local file, so local testing doesn't inflate the numbers. To turn counting off, delete the `data-goatcounter` `<script>` tag near the top of `index.html`.

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
