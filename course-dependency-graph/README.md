# QBIO Course Map

An interactive prerequisite map of USC's **Quantitative Biology (BS)**, built for QBA members planning their course order.

**Live:** https://richardshizhang.github.io/QBA/course-dependency-graph/

- **Columns are prerequisite steps.** Every course sits to the right of all its prerequisites, so working left to right is a safe order.
- **Click a course** to highlight what it needs (orange) and what it unlocks (blue). The side panel shows the exact prerequisite logic, corequisites, restrictions, a description, and which terms it actually ran.
- **Tick the circles** next to courses you've taken. The map then shows what you can take next, and the requirements panel tracks rough progress. Ticks are saved in the browser only.
- **Enter AP and placement credit** under "AP & placement credit" (e.g. AP Calc BC 5 waives MATH 125 and 126; AP CS A waives CSCI 102). Courses that an exam can waive carry an `AP` badge.
- **Mark advisor waivers** with the "Waive" button in a course's or requirement box's details. A waiver covers the whole requirement line, e.g. all of Physics I, and STARS shows it as CW (course waiver) or RW (requirement waiver). Waived requirements count toward progress and unlock the courses that need them, with a note that those departments may still have to approve.
- **Boxes with several codes** are one catalogue requirement line with alternatives (e.g. Physics I = PHYS 135a / 151 / 161 / 171).
- Solid arrow = required. Dashed arrow = one of several options, or needed by only some of the alternatives in the box.

It's a static page with no build step and no dependencies beyond two Google Fonts.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole app: layout, rendering and interaction. |
| `graph-data.js` | Generated data (`window.QBIO_DATA`). Don't edit by hand. |
| `data/requirements.json` | The major's requirements, hand-transcribed from the catalogue. |
| `scripts/update_data.py` | Fetches prerequisites and offering history, then writes `graph-data.js`. |

## Updating for a new catalogue year

1. Open the new catalogue's QBIO program page and update `data/requirements.json`. That covers the `courses` (catalogue code, title, units), the `slots` (each "X or Y" line is one slot) and the `sections` (rules such as "choose 3"). Also update the `catalogue` and `source` fields.
2. Regenerate the data:

   ```bash
   python3 scripts/update_data.py
   ```

   This only needs Python 3.9+ and its standard library. Raw API responses are cached in `.cache/`, so reruns are fast. Delete `.cache/` to force fresh data. Some departments take a minute or more per request, so the first run takes a few minutes.
3. Open `index.html` in a browser to check it.

## Where the data comes from

- **Requirements:** the [USC Catalogue 2026-2027 program page](https://catalogue.usc.edu/preview_program.php?catoid=22&poid=32504). catalogue.usc.edu blocks scripted access with a bot check, so this is transcribed by hand (from a saved PDF of the page).
- **Prerequisites, corequisites, descriptions, restrictions, offering history:** the USC Schedule of Classes JSON API at `classes.usc.edu/api`. The script scans the last 11 terms, including summers, and uses each course's most recent listing.

## AP and exam credit

The `examCredit` block in `data/requirements.json` encodes which exams waive which courses. Sources:

- [USC Registrar AP credit chart](https://arr.usc.edu/ap-exam-credit-at-usc/). Every AP score of 4 or 5 earns 4 elective units, but AP scores don't earn USC course equivalence. Departments waive prerequisites, and the major advisor applies AP credit to degree requirements. The waivers that matter here:
  - Calc AB → MATH 125
  - Calc BC 4 → MATH 125; Calc BC 5 → MATH 125 + 126
  - Chemistry → CHEM 105a
  - Biology → BISC 120 or 220, at the Biology advisor's discretion
  - Psychology → PSYC 100
  - Precalculus → MATH 108
- [Viterbi CS curriculum 2026](https://viterbiadmission.usc.edu/wp-content/uploads/2026/06/CS_Curriculum_2026.pdf) and the [Dornsife QBIO advising sheet](https://dornsife.usc.edu/advising/wp-content/uploads/sites/96/2023/09/Quantitative-Biology-BS.pdf). AP Computer Science A (4 or 5) or the CSCI 102 Challenge Exam lets you skip CSCI 102 and start with CSCI 103.

On STARS, AP credit shows as `AP` plus the College Board exam number with `COMP` (general credit), e.g. `AP68:COMP 4.0 TR AP CALCULUS BC`. It only counts for a major requirement after the advisor adds a substitution, which appears as a note like `RE - SUB AP68:COMP FOR MATH125` (RE = requirement exchange). The codes AP68, AP31, AP25, AP20 and AP85 were confirmed on a real STARS report. AP66 (Calculus AB) follows the same College Board numbering but hasn't been seen on a report yet.

AP Physics and AP Statistics earn elective and GE credit but aren't on the waiver list.

## Known gaps

- MATH 127, MATH 227, BISC 434 and QBIO 479 weren't offered in any scanned term, so the map can't show their prerequisites.
- Schedule of Classes prerequisite data can be thinner than the catalogue's wording. For example, QBIO 494 doesn't list QBIO 493, and BISC 220 lists no prerequisites even though its description recommends BISC 120.
- Entry-level prerequisites that most students place out of (MATH 108, CHEM 050) are treated as met.
- Progress tracking doesn't enforce the no-double-counting rules between Computing, Specialization and Electives, and it can't count research units.

This is an unofficial planning aid. Students should confirm their plan with a QBIO advisor and their STARS report.

## Hosting

The map is hosted with GitHub Pages from the `main` branch of [richardshizhang/QBA](https://github.com/richardshizhang/QBA). Pushing to `main` republishes it, usually within a minute or two. Any other static host works too: serve `index.html` and `graph-data.js` side by side.
