# QBIO Course Map

An interactive prerequisite map of USC's **Quantitative Biology (BS)**, built for QBA members planning their course order.

**Live:** https://richardshizhang.github.io/QBA/course-dependency-graph/

- **Columns are the earliest step you could take each course**, one step after its prerequisites. When a prerequisite can be met several ways, the column follows the fastest option (QBIO 475 sits right after QBIO 310, not after MATH 407).
- **Click a course** to highlight what it needs (orange) and what it unlocks (blue). The side panel shows the exact prerequisite logic, corequisites, restrictions, a description, and which terms it actually ran.
- **Tick the circles** next to courses you've taken. The map then shows what you can take next: those courses get a green outline, and thick green arrows run from what you've marked into them. Ticking one option of a requirement hides its alternatives (taking PHYS 135a hides 151/161/171; BISC 221 hides 220); unticking brings them back. The requirements panel tracks progress without double counting, as the catalogue requires: each course counts toward one requirement (Computing first, then Specialization, Capstone, and Electives last), and a course used elsewhere is marked "in Computing", "in Specialization" or "extra". Sections can be collapsed. Ticks are saved in the browser only.
- Specialization and Upper-Division Electives can also be satisfied with study-abroad credit: click the "Study abroad specialization 1–3" / "Study abroad elective 1–2" placeholders to count them (electives as 4 units each).
- AP credit unlocks later courses and counts for the foundational requirements (e.g. MATH 125), but not for Specialization or Electives: AP Calc BC 5 skips MATH 126 without satisfying a Specialization course (`"examCredit": false` on those sections).
- **Enter AP and placement credit** under "AP & placement credit" (e.g. AP Calc BC 5 waives MATH 125 and 126; AP CS A waives CSCI 102). Courses that an exam can waive carry an `AP` badge. Credited and waived courses move into an "AP & waived" column before step 1, and everything that depends on them shifts left; a requirement split across steps merges back into one box (e.g. with AP Calc, PHYS 151/161/171 join PHYS 135a at step 1). The column's **Hide** button (or the "AP & waived" checkbox in the header) removes it while keeping the shifted layout.
- **Mark advisor waivers** with the "Waive" button in a course's or requirement box's details. A waiver covers the whole requirement line, e.g. all of Physics I, and STARS shows it as CW (course waiver) or RW (requirement waiver). Waived requirements count toward progress and unlock the courses that need them, with a note that those departments may still have to approve.
- **Boxes with several codes** are one catalogue requirement line with alternatives (e.g. Physics I = PHYS 135a / 151 / 161 / 171). If the options open up at different steps, the requirement appears once per step, marked "also step N".
- Solid arrow = required. Dashed arrow = one of several options, or needed by only some of the alternatives in the box. Arrows show the fastest routes; selecting a course also highlights its slower alternatives.

It's a static page with no build step and no dependencies beyond two Google Fonts.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole app: layout, rendering and interaction. |
| `graph-data.js` | Generated data (`window.QBIO_DATA`). Don't edit by hand. |
| `data/requirements.json` | The major's requirements, hand-transcribed from the catalogue. |
| `data/catalogue-courses.json` | Catalogue text for each course (prerequisites, terms offered, descriptions), exported from the browser. |
| `scripts/catalogue_export.js` | Browser-console script that produces `data/catalogue-courses.json`. |
| `scripts/catalogue.py` | Parses catalogue prerequisite sentences into AND/OR groups. |
| `scripts/update_data.py` | Fetches offering history (and fallback prerequisites) from the Schedule of Classes, merges the catalogue export, then writes `graph-data.js`. |

## Updating for a new catalogue year

1. Open the new catalogue's QBIO program page and update `data/requirements.json`. That covers the `courses` (catalogue code, title, units), the `slots` (each "X or Y" line is one slot) and the `sections` (rules such as "choose 3"). Also update the `catalogue` and `source` fields.
2. Export the catalogue's course text. catalogue.usc.edu blocks scripts, so this runs in your own browser:
   1. Open the program page.
   2. Paste `scripts/catalogue_export.js` into the DevTools console (Cmd+Option+J). Chrome may ask you to type `allow pasting` first.
   3. It reads each course one at a time (about a minute) and downloads `catalogue-courses.json`. Save that file as `data/catalogue-courses.json`.
3. Regenerate the data:

   ```bash
   python3 scripts/update_data.py
   ```

   This only needs Python 3.9+ and its standard library. Raw API responses are cached in `.cache/`, so reruns are fast. Delete `.cache/` to force fresh data. Some departments take a minute or more per request, so the first run takes a few minutes. The script prints every prerequisite where the catalogue differs from the Schedule of Classes, plus any sentence it could only partly read; skim that list.
4. Open `index.html` in a browser to check it.

## Where the data comes from

- **Requirements:** the [USC Catalogue 2026-2027 program page](https://catalogue.usc.edu/preview_program.php?catoid=22&poid=32504). catalogue.usc.edu blocks scripted access with a bot check, so this is transcribed by hand (from a saved PDF of the page).
- **Prerequisites, corequisites, descriptions, "Terms Offered":** the catalogue's course entries, via `data/catalogue-courses.json`. The catalogue is the authority here. The Schedule of Classes left out some prerequisites, e.g. QBIO 478 and 482 both need QBIO 310, and QBIO 310 needs MATH 125.
- **Offering history, restrictions, and fallback prerequisites:** the USC Schedule of Classes JSON API at `classes.usc.edu/api`. The script scans the last 11 terms, including summers, and uses each course's most recent listing. Its prerequisites are used only for courses missing from the catalogue export.

## Map adjustments

`mapAdjustments` in `data/requirements.json` holds advice from QBIO students that changes only how the map is drawn:

- `hide.courses`: options QBIO students rarely take (MATH 127, 227 and 245). They're left off the map but still listed in the requirement's details.
- `hideWhenTaken`: once you take a course, hide the separate course it replaces. CSCI 103 and 113 hide each other, and CSCI 104 hides CSCI 114. (Options within one requirement line, like PHYS 135a vs 151, collapse automatically.)
- `typicalPrereqs`: draw a course after its usual prerequisite. CSCI 270 follows CSCI 104 rather than CSCI 114, because CSCI 113/114 is the lighter CS path. "Can take now" still uses the catalogue's full prerequisites.

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

- MATH 127, MATH 227, BISC 434 and QBIO 479 haven't run in any scanned term, so they have catalogue prerequisites but no offering history.
- Catalogue wording that isn't a course, such as "or math placement exam" or "departmental approval", is left off the map. The details panel quotes the full sentence instead.
- Entry-level prerequisites that most students place out of (MATH 108, CHEM 050) are treated as met.
- Progress tracking can't count research units, and elective units use each course's catalogue units (QBIO 499 counts as 1; study-abroad placeholders as 4).

This is an unofficial planning aid. Students should confirm their plan with a QBIO advisor and their STARS report.

## Hosting

The map is hosted with GitHub Pages from the `main` branch of [richardshizhang/QBA](https://github.com/richardshizhang/QBA). Pushing to `main` republishes it, usually within a minute or two. Any other static host works too: serve `index.html` and `graph-data.js` side by side.
