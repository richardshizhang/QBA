# Grant match check

Written by scripts/fetch_grants.py on 2026-11-20. Decisions live in data/grant-ids.json (reviewed 2026-11-20).

**Coverage (48 QCB faculty, adjunct excluded):** NIH 36 with any grant, 25 active; NSF 27 with any award, 11 active; either source 43 with any, 33 active.

Both sources are searched by name, so every match is a decision: NIH by PI profile id, NSF lead PIs by piId,
and NSF co-PIs by the email NSF lists for them. ✔︎ checked by hand, ⚠️ please look. Identities the
searches found that aren't kept are listed under each person; a namesake co-PI is named, not emailed.
NSF awards keep the original PI's id after a PI change, so a few kept awards show another person's name.

A grant is one NIH core project (fiscal years, renewals and center projects collapse into it) or one NSF award.
Active means the project end date is on or after 2026-11-20. Counts are grants (active).

| | Faculty | Group | NIH profile | NSF lead-PI id | NSF co-PI email | NIH grants | NSF awards | Note |
|---|---|---|---|---|---|---|---|---|
| ✔︎ | [Helen Berman](#helen-berman) | core | 1863385 | 000040270 | berman@rcsb.rutgers.edu | 5 (0) | 16 (0) | All NIH grants are from Rutgers (PDB, FY1985–2015, many P41 subprojects); none at USC. NSF: all at Rutgers and earlier, before USC. Two awards now show Stephen Burley or Brinda Vallat as PI after she retired from Rutgers, but keep her piId. |
| ✔︎ | [Peter Calabrese](#peter-calabrese) | core | 10479989 | 269693945 | — | 1 (0) | 1 (0) | NSF: one 2001 individual postdoctoral fellowship (the awardee is listed as himself). |
| ✔︎ | [Mark Chaisson](#mark-chaisson) | core | 12570721 | 270030671 | — | 2 (1) | 1 (0) |  |
| ✔︎ | [Liang Chen](#liang-chen) | core | 9049911 | — | — | 4 (1) | 0 (0) | Kept Liang Chen at USC; LIANGJING Chen and QiLiang Chen are other people (RePORTER matches first names loosely). NSF: the only Liang Chen lead PI is at Nebraska, a namesake. |
| ✔︎ | [Tsu-Pei Chiu](#tsu-pei-chiu) | core | — | — | — | 0 (0) | 0 (0) | No NIH, NSF, OpenAlex or ORCID grants found. |
| ✔︎ | [Michael "Doc" Edge](#michael-edge) | core | 15288832 | — | — | 2 (1) | 0 (0) |  |
| ⚠️ | [Geoffrey Fudenberg](#geoffrey-fudenberg) | core | 9583561 | — | — | 1 (0) | 0 (0) | No active grant found: his NIGMS R35 (R35GM143116) ended 2026-05-31 and RePORTER lists nothing newer. A renewal may not be listed yet. |
| ✔︎ | [Vsevolod "Seva" Katritch](#vsevolod-katritch) | core | 7027821 | — | — | 17 (5) | 0 (0) |  |
| ✔︎ | [Steve Kay](#steve-kay) | core | 1876731 | 000185296 | stevek@scripps.edu, stevekay@usc.edu | 14 (2) | 10 (0) | One 2012 Scripps NSF award moved to a new PI and id; kept by hand from OpenAlex. |
| ✔︎ | [Adam MacLean](#adam-maclean) | core | 14896432 | 270043324 | — | 1 (1) | 2 (2) |  |
| ✔︎ | [Jazlyn Mooney](#jazlyn-mooney) | core | 12652752 | 270035169 | — | 1 (1) | 1 (0) | NSF: one 2021 individual postdoctoral fellowship. |
| ✔︎ | [Remo Rohs](#remo-rohs) | core | 10803025 | 269885281 | — | 3 (1) | 1 (0) |  |
| ✔︎ | [Andrew Smith](#andrew-smith) | core | 9475565 | — | — | 4 (0) | 0 (0) | 14 NIH profiles named Andrew Smith; kept Andrew David Smith at USC. All NSF Andrew Smiths are other people. NSF: seven Andrew Smiths, none at USC or with his email. |
| ✔︎ | [Fengzhu Sun](#fengzhu-sun) | core | 2091713 | 000264386 | fsun@usc.edu | 5 (0) | 5 (1) |  |
| ⚠️ | [Andrew McMahon](#andrew-mcmahon) | emeritus | 1862596 | — | — | 18 (0) | 0 (0) | No active grant found: his last USC R01 (R01DK126925) ended 2026-05-31 and RePORTER lists nothing newer. A renewal or new grant may not be listed yet. |
| ✔︎ | [Simon Tavaré](#simon-tavare) | emeritus | 2429478 | 000169421, 270032712 | stavare@usc.edu | 2 (0) | 8 (0) | NSF: piId 270032712 is his 2020 Columbia award (same person, new id when he moved); 'Tavaré' with the accent returns nothing, so the search uses 'Tavare'. |
| ✔︎ | [Michael Waterman](#michael-waterman) | emeritus | 1965101 | 000116781 | msw@usc.edu | 2 (0) | 9 (0) | Michael R Waterman (Vanderbilt, biochemistry) is a namesake. |
| ✔︎ | [Don B. Arnold](#don-b-arnold) | joint | 6712304 | — | — | 11 (1) | 0 (0) | Donald Hayes Arnold (Vanderbilt) is a namesake. |
| ✔︎ | [Charleston Chiang](#charleston-chiang) | joint | 8505272 | — | — | 4 (3) | 0 (0) | NSF: the USC rows under 'Chiang' are Cindy Chiang (linguistics) and others; none are his. |
| ✔︎ | [Rosa Di Felice](#rosa-di-felice) | joint | — | — | — | 0 (0) | 0 (0) | No NIH, NSF, OpenAlex or ORCID grants found (NSF search tried 'Di Felice', 'DiFelice' and 'Felice'). NSF: 'Di Felice' returns nothing and 'Felice' returns 32 awards, none hers. |
| ✔︎ | [Arun Durvasula](#arun-durvasula) | joint | 15615575 | — | — | 1 (1) | 0 (0) |  |
| ✔︎ | [Stacey Finley](#stacey-finley) | joint | 10296807 | 269949226 | — | 4 (2) | 2 (1) |  |
| ✔︎ | [Peter Foster](#peter-foster) | joint | — | — | — | 0 (0) | 0 (0) | No NIH, NSF, OpenAlex or ORCID grants found; NSF's USC Fosters are Ian Foster on ISI awards. |
| ✔︎ | [Scott Fraser](#scott-fraser) | joint | 1920651, 3412628, 3412627 | 000118460 | sfraser@provost.usc.edu | 22 (1) | 11 (0) | Two tiny 1990s duplicate NIH profiles are the same person; kept all three. NSF: emails on 1980s UC Irvine awards show his current USC address, so the match is safe. A Fraser at Monterey Peninsula College is a namesake. |
| ✔︎ | [Krishna Garikipati](#krishna-garikipati) | joint | — | 000262092 | garikipa@usc.edu | 0 (0) | 14 (2) | NSF lists him as Krishnakumar, so a 'Krishna Garikipati' search finds nothing; the script searches by surname. |
| ✔︎ | [Steven Gazal](#steven-gazal) | joint | 14444240 | — | — | 3 (1) | 0 (0) |  |
| ✔︎ | [Christoph Haselwandter](#christoph-haselwandter) | joint | — | 269889433 | cah77@usc.edu | 0 (0) | 6 (2) |  |
| ✔︎ | [Andrei Irimia](#andrei-irimia) | joint | 10530401 | — | — | 4 (3) | 0 (0) |  |
| ✔︎ | [Eva Kanso](#eva-kanso) | joint | 11674326 | 000152488, 269771792 | kanso@usc.edu | 1 (0) | 9 (1) | NIH grant is multi-PI with the University of Iowa. NSF gave her two lead-PI ids; both carry kanso@usc.edu. |
| ✔︎ | [Judith Kribelbauer](#judith-kribelbauer) | joint | 80496036 | — | — | 1 (1) | 0 (0) | NIH lists her as Judith Kribelbauer-Swietek. |
| ✔︎ | [Jerry S.H. Lee](#jerry-s-h-lee) | joint | — | — | — | 0 (0) | 0 (0) | No grants found: the NIH Jerry Lees are Loma Linda and other namesakes, and NSF, OpenAlex and ORCID have none. |
| ✔︎ | [Naomi Levine](#naomi-levine) | joint | — | 269916347 | n.levine@usc.edu | 0 (0) | 7 (3) |  |
| ✔︎ | [Sheng Li](#sheng-li) | joint | 12243946 | — | — | 6 (3) | 0 (0) | 15 NIH profiles named Sheng Li; kept the Jackson Lab → USC one (epigenomics). 7845608 (UTHealth Houston, rehabilitation) and the rest are other people. NSF: the Sheng Li at Virginia and Sheng-San Li (Florida) are namesakes; no NSF awards for him. |
| ✔︎ | [Ruishan Liu](#ruishan-liu) | joint | — | — | ruishanl@usc.edu | 0 (0) | 2 (2) |  |
| ✔︎ | [Yan Liu](#yan-liu) | joint | — | 269867875 | yanliu.cs@usc.edu | 0 (0) | 11 (3) | No NIH grants. RePORTER's loose first-name match returns Zhaoyang Liu (USC), who is someone else. NSF: the ASU and Illinois Yan Lius are namesakes. |
| ✔︎ | [Nicholas Mancuso](#nicholas-mancuso) | joint | 14130117 | — | — | 2 (2) | 0 (0) |  |
| ✔︎ | [Aiichiro Nakano](#aiichiro-nakano) | joint | — | 000174407 | anakano@usc.edu | 0 (0) | 20 (0) |  |
| ✔︎ | [Paul Newton](#paul-newton) | joint | — | 000146689 | newton@usc.edu | 0 (0) | 10 (0) | Paul A Newton (UC Berkeley, 1986–87 NIH) is a namesake. |
| ✔︎ | [Meisam Razaviyayn](#meisam-razaviyayn) | joint | 15943922 | 269983325 | razaviya@usc.edu | 1 (0) | 4 (2) |  |
| ✔︎ | [Bodour Salhia](#bodour-salhia) | joint | 9176624 | — | salhia@usc.edu | 6 (4) | 1 (0) |  |
| ✔︎ | [Julia Schwartzman](#julia-schwartzman) | joint | 11917761 | — | — | 1 (0) | 0 (0) | One 2017 NIH fellowship at Mass Eye and Ear, before USC. |
| ✔︎ | [Chang (April) Shu](#chang-shu) | joint | 14363184 | — | — | 1 (1) | 0 (0) | Kept Chang Shu at USC Preventive Medicine (autism, R01MH143902). |
| ✔︎ | [Rory Spence](#rory-spence) | joint | — | — | — | 0 (0) | 0 (0) | No NIH, NSF, OpenAlex or ORCID grants found. |
| ✔︎ | [Paul Thomas](#paul-thomas) | joint | 8818058 | 269899430 | pdthomas@usc.edu | 6 (1) | 3 (0) | 8 NIH profiles; kept Paul D. Thomas (PANTHER, USC). |
| ✔︎ | [Paul Thompson](#paul-thompson) | joint | 6111760 | 269693312 | — | 41 (15) | 1 (0) | 9 NIH profiles; kept Paul M. Thompson (UCLA → USC, ENIGMA). Many grants are center subprojects. P20RR017698 (2008–11, University of South Carolina, peptide-based borono-lectins) is Paul R. Thompson, a chemist, filed under the same RePORTER profile, so it's left out. NSF: kept only Paul M Thompson (thompson@ini.usc.edu); Paul B Thompson (Michigan State), Dartmouth and Florida Paul Thompsons are namesakes. |
| ✔︎ | [Arthur Toga](#arthur-toga) | joint | 6855806 | 000171992 | toga@loni.usc.edu | 44 (9) | 6 (0) | Kept Arthur W. Toga (UCLA → USC). 81 of his NIH records are center subprojects, collapsed into their parent grants. |
| ✔︎ | [Peter Yingxiao Wang](#peter-yingxiao-wang) | joint | 8661093 | 269793423 | ywang283@usc.edu | 15 (6) | 8 (0) |  |
| ✔︎ | [Arieh Warshel](#arieh-warshel) | joint | 1864711 | 000159775, 000197820 | — | 5 (1) | 9 (1) | NSF: the older id 000159775 (USC 1983–85) has no email but is the same USC chemistry PI. |

## Details

### Helen Berman
<a id="helen-berman"></a>

NIH profiles whose name fits:
- kept: [1863385](https://reporter.nih.gov/search/results?pi_profile_id=1863385) Helen M Berman, FY1985–2015, 52 rows, Rutgers, The State Univ Of N.J., Baylor College Of Medicine

NSF identities whose name fits:
- kept: lead PI 000040270 (Brinda Vallat / Helen M Berman / Stephen K Burley), 1990–2018, 12 awards, Rutgers University New Brunswick
- kept: co-PI berman@rcsb.rutgers.edu, 1975–2005, 4 awards, Institute For Cancer Research, Bowling Green State University

All NIH grants are from Rutgers (PDB, FY1985–2015, many P41 subprojects); none at USC. NSF: all at Rutgers and earlier, before USC. Two awards now show Stephen Burley or Brinda Vallat as PI after she retired from Rutgers, but keep her piId.

### Peter Calabrese
<a id="peter-calabrese"></a>

NIH profiles whose name fits:
- kept: [10479989](https://reporter.nih.gov/search/results?pi_profile_id=10479989) Peter Paul Calabrese, FY2014–2017, 4 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 269693945 (Peter P Calabrese), 2001–2001, 1 awards, Calabrese, Peter P

NSF: one 2001 individual postdoctoral fellowship (the awardee is listed as himself).

### Mark Chaisson
<a id="mark-chaisson"></a>

NIH profiles whose name fits:
- kept: [12570721](https://reporter.nih.gov/search/results?pi_profile_id=12570721) Mark Chaisson, FY2020–2026, 10 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 270030671 (Mark J Chaisson), 2021–2021, 1 awards, University of Southern California

### Liang Chen
<a id="liang-chen"></a>

NIH profiles whose name fits:
- kept: [9049911](https://reporter.nih.gov/search/results?pi_profile_id=9049911) Liang Chen, FY2011–2026, 11 rows, University Of Southern California, University Of California Riverside
- rejected: [6910461](https://reporter.nih.gov/search/results?pi_profile_id=6910461) Liangjing Chen Chen, FY2002–2019, 8 rows, Asuragen, Inc., Ambion Diagnostics, Inc.
- rejected: [12283719](https://reporter.nih.gov/search/results?pi_profile_id=12283719) Liang Chen, FY2016–2026, 4 rows, Rbhs-New Jersey Medical School, State University Of New York At Buffalo

NSF identities whose name fits:
- rejected: lead PI 270033960 (Liang Chen), 2024–2024, 1 awards, University of Nebraska-Lincoln

Kept Liang Chen at USC; LIANGJING Chen and QiLiang Chen are other people (RePORTER matches first names loosely). NSF: the only Liang Chen lead PI is at Nebraska, a namesake.

### Tsu-Pei Chiu
<a id="tsu-pei-chiu"></a>

No NIH, NSF, OpenAlex or ORCID grants found.

No NIH or NSF records under this name.

### Michael "Doc" Edge
<a id="michael-edge"></a>

NIH profiles whose name fits:
- kept: [15288832](https://reporter.nih.gov/search/results?pi_profile_id=15288832) Michael Donald Edge, FY2018–2026, 8 rows, University Of Southern California, University Of California At Davis

### Geoffrey Fudenberg
<a id="geoffrey-fudenberg"></a>

NIH profiles whose name fits:
- kept: [9583561](https://reporter.nih.gov/search/results?pi_profile_id=9583561) Geoffrey Fudenberg, FY2021–2025, 5 rows, University Of Southern California

No active grant found: his NIGMS R35 (R35GM143116) ended 2026-05-31 and RePORTER lists nothing newer. A renewal may not be listed yet.

### Vsevolod "Seva" Katritch
<a id="vsevolod-katritch"></a>

NIH profiles whose name fits:
- kept: [7027821](https://reporter.nih.gov/search/results?pi_profile_id=7027821) Vsevolod Katritch, FY2002–2026, 35 rows, University Of Southern California, Washington University

### Steve Kay
<a id="steve-kay"></a>

NIH profiles whose name fits:
- kept: [1876731](https://reporter.nih.gov/search/results?pi_profile_id=1876731) Steve A Kay, FY1991–2026, 95 rows, Scripps Research Institute, The, University Of California, San Diego

NSF identities whose name fits:
- kept: lead PI 000185296 (Steve A Kay), 1991–1997, 6 awards, University of Virginia Main Campus, The Scripps Research Institute
- kept: co-PI stevek@scripps.edu, 1993–2006, 2 awards, Oregon State University, University of Virginia Main Campus
- kept: co-PI stevekay@usc.edu, 2008–2008, 1 awards, Keystone Symposia on Molecular and Cellular Biology

NSF awards kept by hand: 1158254.

One 2012 Scripps NSF award moved to a new PI and id; kept by hand from OpenAlex.

### Adam MacLean
<a id="adam-maclean"></a>

NIH profiles whose name fits:
- kept: [14896432](https://reporter.nih.gov/search/results?pi_profile_id=14896432) Adam L Maclean, FY2021–2025, 5 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 270043324 (Adam L MacLean), 2021–2024, 2 awards, University of Southern California

### Jazlyn Mooney
<a id="jazlyn-mooney"></a>

NIH profiles whose name fits:
- kept: [12652752](https://reporter.nih.gov/search/results?pi_profile_id=12652752) Jazlyn Ambry Mooney, FY2025–2026, 2 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 270035169 (Jazlyn Mooney), 2021–2021, 1 awards, Mooney, Jazlyn

NSF: one 2021 individual postdoctoral fellowship.

### Remo Rohs
<a id="remo-rohs"></a>

NIH profiles whose name fits:
- kept: [10803025](https://reporter.nih.gov/search/results?pi_profile_id=10803025) Remo Rohs, FY2013–2026, 14 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 269885281 (Remo Rohs), 2014–2014, 1 awards, University of Southern California

### Andrew Smith
<a id="andrew-smith"></a>

NIH profiles whose name fits:
- kept: [9475565](https://reporter.nih.gov/search/results?pi_profile_id=9475565) Andrew David Smith, FY2010–2023, 16 rows, University Of Southern California
- rejected: [10284996](https://reporter.nih.gov/search/results?pi_profile_id=10284996) Andrew Michael Smith, FY2010–2026, 50 rows, University Of Illinois At Urbana-Champaign, Emory University
- rejected: [1899634](https://reporter.nih.gov/search/results?pi_profile_id=1899634) Andrew Smith, FY2002–2018, 38 rows, Cornell University, Maine State Dept/Health/Human Servs
- rejected: [12176044](https://reporter.nih.gov/search/results?pi_profile_id=12176044) Andrew Craig Smith, FY2019–2025, 7 rows, University Of Colorado Denver, Regis University
- rejected: [11015418](https://reporter.nih.gov/search/results?pi_profile_id=11015418) Andrew Howard Smith, FY2015–2026, 6 rows, Yale University, Icahn School Of Medicine At Mount Sinai
- rejected: [10940788](https://reporter.nih.gov/search/results?pi_profile_id=10940788) Andrew Dennis Smith, FY2016–2021, 3 rows, University Of Alabama At Birmingham, Imageiq, Inc.
- rejected: [11852257](https://reporter.nih.gov/search/results?pi_profile_id=11852257) Andrew E Smith, FY2013–2015, 3 rows, Maine State Dept/Health/Human Servs
- rejected: [9811181](https://reporter.nih.gov/search/results?pi_profile_id=9811181) Andrew Smith, FY2008–2010, 3 rows, Maine State Dept/Health/Human Servs
- rejected: [8213670](https://reporter.nih.gov/search/results?pi_profile_id=8213670) Andrew H Smith, FY2006–2008, 3 rows, Vanderbilt University
- rejected: [7895741](https://reporter.nih.gov/search/results?pi_profile_id=7895741) Andrew M Smith, FY2004–2007, 3 rows, Texas A&M University Health Science Ctr
- rejected: [11836437](https://reporter.nih.gov/search/results?pi_profile_id=11836437) Andrew E Smith, FY2013–2014, 2 rows, Maine State Dept/Health/Human Servs
- rejected: [6233768](https://reporter.nih.gov/search/results?pi_profile_id=6233768) Andrew L Smith, FY1998–1999, 2 rows, Emory University
- rejected: [8338921](https://reporter.nih.gov/search/results?pi_profile_id=8338921) Andrew M Smith, FY2006–2006, 1 rows, Ithaca College
- rejected: [3188670](https://reporter.nih.gov/search/results?pi_profile_id=3188670) Andrew T Smith, FY1991–1991, 1 rows, Arizona State University-Tempe Campus

NSF identities whose name fits:
- rejected: lead PI 000119580 (Andrew T Smith), 1977–2008, 4 awards, Arizona State University, University of Miami
- rejected: lead PI 269923047 (Andrew M Smith), 2017–2025, 3 awards, University of Illinois at Urbana-Champaign
- rejected: lead PI 269903300 (Andrew Smith), 2013–2019, 2 awards, Appalachian State University
- rejected: lead PI 000209508 (Andrew M Smith), 1992–1996, 2 awards, Butler University, Fellowships
- rejected: lead PI 269723169 (Andrew J Smith), 2026–2026, 1 awards, University of Maryland, College Park
- rejected: lead PI 270037626 (Andrew M Smith), 2020–2020, 1 awards, Iowa State University
- rejected: lead PI 269695424 (Andrew B Smith), 2004–2004, 1 awards, University of Nebraska-Lincoln
- rejected: co-PI Andrew J Smith, 2003–2026, 17 awards, University of Maryland, College Park, Michigan Technological University
- rejected: co-PI Andrew M Smith, 2015–2023, 2 awards, University of Illinois at Urbana-Champaign
- rejected: co-PI Andrew Smith, 2012–2012, 2 awards, University of Utah
- rejected: co-PI Andrew John Smith, 2015–2015, 1 awards, University of Massachusetts Amherst
- rejected: co-PI Andrew M Smith, 2001–2001, 1 awards, Ithaca College

14 NIH profiles named Andrew Smith; kept Andrew David Smith at USC. All NSF Andrew Smiths are other people. NSF: seven Andrew Smiths, none at USC or with his email.

### Fengzhu Sun
<a id="fengzhu-sun"></a>

NIH profiles whose name fits:
- kept: [2091713](https://reporter.nih.gov/search/results?pi_profile_id=2091713) Fengzhu Sun, FY1998–2020, 17 rows, University Of Southern California, Emory University

NSF identities whose name fits:
- kept: lead PI 000264386 (Fengzhu Sun), 2003–2022, 3 awards, University of Southern California
- kept: co-PI fsun@usc.edu, 2011–2011, 2 awards, University of Southern California

### Andrew McMahon
<a id="andrew-mcmahon"></a>

NIH profiles whose name fits:
- kept: [1862596](https://reporter.nih.gov/search/results?pi_profile_id=1862596) Andrew P. Mcmahon, FY1994–2024, 138 rows, Harvard University, University Of Southern California

No active grant found: his last USC R01 (R01DK126925) ended 2026-05-31 and RePORTER lists nothing newer. A renewal or new grant may not be listed yet.

### Simon Tavaré
<a id="simon-tavare"></a>

NIH profiles whose name fits:
- kept: [2429478](https://reporter.nih.gov/search/results?pi_profile_id=2429478) Simon Tavare, FY2002–2013, 18 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 000169421 (Simon Tavare), 1986–1995, 4 awards, University of Southern California, University of Utah
- kept: lead PI 270032712 (Simon Tavare), 2020–2020, 1 awards, Columbia University
- kept: co-PI stavare@usc.edu, 1990–2011, 3 awards, University of Southern California

NSF: piId 270032712 is his 2020 Columbia award (same person, new id when he moved); 'Tavaré' with the accent returns nothing, so the search uses 'Tavare'.

### Michael Waterman
<a id="michael-waterman"></a>

NIH profiles whose name fits:
- kept: [1965101](https://reporter.nih.gov/search/results?pi_profile_id=1965101) Michael Spencer Waterman, FY1986–2006, 17 rows, University Of Southern California
- rejected: [1858093](https://reporter.nih.gov/search/results?pi_profile_id=1858093) Michael R Waterman, FY1985–2012, 69 rows, Vanderbilt University, Ut Southwestern Medical Center

NSF identities whose name fits:
- kept: lead PI 000116781 (Michael S Waterman), 1975–2001, 6 awards, University of Southern California, Idaho State University
- kept: co-PI msw@usc.edu, 1986–2015, 3 awards, University of Southern California, Mathematical Sciences Research Institute

Michael R Waterman (Vanderbilt, biochemistry) is a namesake.

### Don B. Arnold
<a id="don-b-arnold"></a>

NIH profiles whose name fits:
- kept: [6712304](https://reporter.nih.gov/search/results?pi_profile_id=6712304) Donald B Arnold, FY2002–2026, 92 rows, University Of Southern California
- rejected: [8029094](https://reporter.nih.gov/search/results?pi_profile_id=8029094) Donald Hayes Arnold, FY2008–2024, 16 rows, Vanderbilt University, Vanderbilt University Medical Center

Donald Hayes Arnold (Vanderbilt) is a namesake.

### Charleston Chiang
<a id="charleston-chiang"></a>

NIH profiles whose name fits:
- kept: [8505272](https://reporter.nih.gov/search/results?pi_profile_id=8505272) Charleston Chiang, FY2013–2026, 19 rows, University Of Southern California, University Of California Los Angeles

NSF: the USC rows under 'Chiang' are Cindy Chiang (linguistics) and others; none are his.

### Rosa Di Felice
<a id="rosa-di-felice"></a>

No NIH, NSF, OpenAlex or ORCID grants found (NSF search tried 'Di Felice', 'DiFelice' and 'Felice'). NSF: 'Di Felice' returns nothing and 'Felice' returns 32 awards, none hers.

No NIH or NSF records under this name.

### Arun Durvasula
<a id="arun-durvasula"></a>

NIH profiles whose name fits:
- kept: [15615575](https://reporter.nih.gov/search/results?pi_profile_id=15615575) Arun Durvasula, FY2025–2026, 2 rows, University Of Southern California

### Stacey Finley
<a id="stacey-finley"></a>

NIH profiles whose name fits:
- kept: [10296807](https://reporter.nih.gov/search/results?pi_profile_id=10296807) Stacey Deleria Finley, FY2010–2026, 14 rows, University Of Southern California, Johns Hopkins University

NSF identities whose name fits:
- kept: lead PI 269949226 (Stacey Finley), 2016–2024, 2 awards, University of Southern California

### Peter Foster
<a id="peter-foster"></a>

No NIH, NSF, OpenAlex or ORCID grants found; NSF's USC Fosters are Ian Foster on ISI awards.

No NIH or NSF records under this name.

### Scott Fraser
<a id="scott-fraser"></a>

NIH profiles whose name fits:
- kept: [1920651](https://reporter.nih.gov/search/results?pi_profile_id=1920651) Scott E Fraser, FY1988–2026, 77 rows, California Institute Of Technology, University Of Southern California
- kept: [3412628](https://reporter.nih.gov/search/results?pi_profile_id=3412628) Scott E Fraser, FY1995–1996, 2 rows, ?, California Institute Of Technology
- kept: [3412627](https://reporter.nih.gov/search/results?pi_profile_id=3412627) Scott E Fraser, FY1996–1996, 1 rows, ?

NSF identities whose name fits:
- kept: lead PI 000118460 (Scott E Fraser), 1981–1990, 6 awards, University of California-Irvine, Gordon Research Conferences
- kept: co-PI sfraser@provost.usc.edu, 1986–2018, 5 awards, University of Southern California, Portland State University
- rejected: co-PI Scott Fraser, 2011–2015, 2 awards, Monterey Peninsula College

Two tiny 1990s duplicate NIH profiles are the same person; kept all three. NSF: emails on 1980s UC Irvine awards show his current USC address, so the match is safe. A Fraser at Monterey Peninsula College is a namesake.

### Krishna Garikipati
<a id="krishna-garikipati"></a>

NSF identities whose name fits:
- kept: lead PI 000262092 (Krishnakumar Garikipati), 2000–2025, 7 awards, Regents of the University of Michigan - Ann Arbor, University of Southern California
- kept: co-PI garikipa@usc.edu, 2003–2026, 7 awards, Regents of the University of Michigan - Ann Arbor, University of California-Santa Barbara

NSF lists him as Krishnakumar, so a 'Krishna Garikipati' search finds nothing; the script searches by surname.

### Steven Gazal
<a id="steven-gazal"></a>

NIH profiles whose name fits:
- kept: [14444240](https://reporter.nih.gov/search/results?pi_profile_id=14444240) Steven Gazal, FY2018–2026, 10 rows, University Of Southern California, Harvard University D/B/A Harvard School Of Public Health

### Christoph Haselwandter
<a id="christoph-haselwandter"></a>

NSF identities whose name fits:
- kept: lead PI 269889433 (Christoph Haselwandter), 2012–2021, 3 awards, University of Southern California
- kept: co-PI cah77@usc.edu, 2018–2025, 3 awards, University of Southern California

### Andrei Irimia
<a id="andrei-irimia"></a>

NIH profiles whose name fits:
- kept: [10530401](https://reporter.nih.gov/search/results?pi_profile_id=10530401) Andrei Irimia, FY2017–2026, 11 rows, University Of Southern California

### Eva Kanso
<a id="eva-kanso"></a>

NIH profiles whose name fits:
- kept: [11674326](https://reporter.nih.gov/search/results?pi_profile_id=11674326) Eva Kanso, FY2021–2024, 4 rows, University Of Iowa, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 269771792 (Eva Kanso), 2007–2026, 7 awards, University of Southern California
- kept: lead PI 000152488 (Eva Kanso), 2021–2021, 1 awards, University of Southern California
- kept: co-PI kanso@usc.edu, 2021–2021, 1 awards, University of California-Irvine

NIH grant is multi-PI with the University of Iowa. NSF gave her two lead-PI ids; both carry kanso@usc.edu.

### Judith Kribelbauer
<a id="judith-kribelbauer"></a>

NIH profiles whose name fits:
- kept: [80496036](https://reporter.nih.gov/search/results?pi_profile_id=80496036) Judith Kribelbauer-Swietek, FY2026–2026, 2 rows, University Of Southern California

NIH lists her as Judith Kribelbauer-Swietek.

### Jerry S.H. Lee
<a id="jerry-s-h-lee"></a>

NIH profiles whose name fits:
- rejected: [3300748](https://reporter.nih.gov/search/results?pi_profile_id=3300748) Jerry W Lee, FY1987–1987, 2 rows, Loma Linda University
- rejected: [11174937](https://reporter.nih.gov/search/results?pi_profile_id=11174937) Jerry Winfield Lee, FY2009–2009, 1 rows, Loma Linda University

No grants found: the NIH Jerry Lees are Loma Linda and other namesakes, and NSF, OpenAlex and ORCID have none.

### Naomi Levine
<a id="naomi-levine"></a>

NSF identities whose name fits:
- kept: lead PI 269916347 (Naomi M Levine), 2013–2024, 3 awards, University of Southern California, Gordon Research Conferences
- kept: co-PI n.levine@usc.edu, 2013–2022, 4 awards, University of Southern California, Woods Hole Oceanographic Institution

### Sheng Li
<a id="sheng-li"></a>

NIH profiles whose name fits:
- kept: [12243946](https://reporter.nih.gov/search/results?pi_profile_id=12243946) Sheng Li, FY2019–2026, 16 rows, Jackson Laboratory, University Of Southern California
- rejected: [7845608](https://reporter.nih.gov/search/results?pi_profile_id=7845608) Sheng Li, FY2006–2026, 14 rows, University Of Texas Hlth Sci Ctr Houston, Rehabtek, Llc
- rejected: [1969792](https://reporter.nih.gov/search/results?pi_profile_id=1969792) Shengqiang Li, FY1995–2026, 13 rows, Sciogen, Llc, Medimmune Vaccines, Inc.
- rejected: [10982058](https://reporter.nih.gov/search/results?pi_profile_id=10982058) Shengxu Li, FY2016–2020, 5 rows, Tulane University Of Louisiana
- rejected: [1869218](https://reporter.nih.gov/search/results?pi_profile_id=1869218) Shengwen Calvin Li, FY1996–1998, 3 rows, Harvard Medical School, Whitehead Institute For Biomedical Res

NSF identities whose name fits:
- rejected: lead PI 270018094 (Sheng Li), 2023–2024, 3 awards, University of Virginia Main Campus
- rejected: lead PI 269985088 (Sheng Li), 2018–2018, 1 awards, University of Georgia Research Foundation Inc
- rejected: lead PI 000100797 (Sheng-San Li), 1977–1977, 1 awards, University of Florida
- rejected: co-PI Sheng-San Li, 1985–1985, 1 awards, University of Florida

15 NIH profiles named Sheng Li; kept the Jackson Lab → USC one (epigenomics). 7845608 (UTHealth Houston, rehabilitation) and the rest are other people. NSF: the Sheng Li at Virginia and Sheng-San Li (Florida) are namesakes; no NSF awards for him.

### Ruishan Liu
<a id="ruishan-liu"></a>

NSF identities whose name fits:
- kept: co-PI ruishanl@usc.edu, 2026–2026, 2 awards, University of Southern California, Virginia Polytechnic Institute and State University

### Yan Liu
<a id="yan-liu"></a>

NIH profiles whose name fits:
- rejected: [1882189](https://reporter.nih.gov/search/results?pi_profile_id=1882189) Yang Liu, FY1992–2020, 97 rows, Ohio State University, University Of Michigan At Ann Arbor
- rejected: [9482107](https://reporter.nih.gov/search/results?pi_profile_id=9482107) Yang Liu, FY2009–2026, 33 rows, University Of Pittsburgh At Pittsburgh, University Of Illinois At Urbana-Champaign
- rejected: [9744018](https://reporter.nih.gov/search/results?pi_profile_id=9744018) Yang Liu, FY2009–2026, 16 rows, Emory University
- rejected: [10915597](https://reporter.nih.gov/search/results?pi_profile_id=10915597) Yan Liu, FY2017–2026, 14 rows, Northwestern University, Indiana University Indianapolis
- rejected: [11383728](https://reporter.nih.gov/search/results?pi_profile_id=11383728) Yansheng Liu, FY2020–2026, 13 rows, Yale University
- rejected: [10655667](https://reporter.nih.gov/search/results?pi_profile_id=10655667) Yanhong Liu, FY2014–2026, 12 rows, Baylor College Of Medicine
- rejected: [7518011](https://reporter.nih.gov/search/results?pi_profile_id=7518011) Yanjun Liu, FY2006–2017, 12 rows, Charles R. Drew University Of Med & Sci
- rejected: [16456431](https://reporter.nih.gov/search/results?pi_profile_id=16456431) Yang Liu, FY2023–2026, 7 rows, Yale University
- rejected: [78801344](https://reporter.nih.gov/search/results?pi_profile_id=78801344) Yang Liu, FY2023–2026, 5 rows, Utah State Higher Education System--University Of Utah
- rejected: [11954239](https://reporter.nih.gov/search/results?pi_profile_id=11954239) Yang-Yu Liu, FY2019–2023, 5 rows, Brigham And Women'S Hospital
- rejected: [78678313](https://reporter.nih.gov/search/results?pi_profile_id=78678313) Yanqing Liu, FY2025–2026, 3 rows, Van Andel Research Institute
- rejected: [15923840](https://reporter.nih.gov/search/results?pi_profile_id=15923840) Yang Liu, FY2019–2021, 3 rows, University Of Georgia
- rejected: [10602082](https://reporter.nih.gov/search/results?pi_profile_id=10602082) Yanni Liu, FY2017–2019, 3 rows, University Of Michigan At Ann Arbor
- rejected: [8772168](https://reporter.nih.gov/search/results?pi_profile_id=8772168) Yanze Liu, FY2006–2008, 3 rows, Natural Pharmacia International, Inc.
- rejected: [78914087](https://reporter.nih.gov/search/results?pi_profile_id=78914087) Yan Liu, FY2025–2026, 2 rows, Imperial College Of Science, Technology And Medicine
- rejected: [9092512](https://reporter.nih.gov/search/results?pi_profile_id=9092512) Yan None Liu, FY2009–2010, 2 rows, University Of Michigan At Ann Arbor
- rejected: [3082886](https://reporter.nih.gov/search/results?pi_profile_id=3082886) Yanxi Liu, FY2006–2007, 2 rows, Carnegie-Mellon University
- rejected: [6713279](https://reporter.nih.gov/search/results?pi_profile_id=6713279) Yanping Liu, FY2003–2004, 2 rows, Medical College Of Wisconsin
- rejected: [6684213](https://reporter.nih.gov/search/results?pi_profile_id=6684213) Yang Liu, FY2001–2002, 2 rows, Stanford University
- rejected: [79193003](https://reporter.nih.gov/search/results?pi_profile_id=79193003) Yang Liu, FY2026–2026, 1 rows, Cleveland Clinic Lerner Com-Cwru
- rejected: [16308974](https://reporter.nih.gov/search/results?pi_profile_id=16308974) Yang Liu, FY2026–2026, 1 rows, University Of Texas Hlth Sci Ctr Houston
- rejected: [10205712](https://reporter.nih.gov/search/results?pi_profile_id=10205712) Yan Liu, FY2010–2010, 1 rows, University Of Washington
- rejected: [8299267](https://reporter.nih.gov/search/results?pi_profile_id=8299267) Yanhui Liu, FY2010–2010, 1 rows, Dynadx Corporation
- rejected: [8501049](https://reporter.nih.gov/search/results?pi_profile_id=8501049) Yanlei Liu, FY2006–2006, 1 rows, Biopath Laboratory, Inc.
- rejected: [6626924](https://reporter.nih.gov/search/results?pi_profile_id=6626924) Yanshun Liu, FY1999–1999, 1 rows, Stanford University

NSF identities whose name fits:
- kept: lead PI 269867875 (Yan Liu), 2011–2024, 6 awards, University of Southern California
- rejected: lead PI 269805087 (Yan Liu), 2008–2016, 2 awards, Arizona State University
- kept: co-PI yanliu.cs@usc.edu, 2016–2024, 5 awards, University of Southern California
- rejected: co-PI Yan Liu, 2011–2014, 2 awards, Arizona State University
- rejected: co-PI Yan Liu, 2017–2017, 1 awards, University of Illinois at Urbana-Champaign

No NIH grants. RePORTER's loose first-name match returns Zhaoyang Liu (USC), who is someone else. NSF: the ASU and Illinois Yan Lius are namesakes.

### Nicholas Mancuso
<a id="nicholas-mancuso"></a>

NIH profiles whose name fits:
- kept: [14130117](https://reporter.nih.gov/search/results?pi_profile_id=14130117) Nicholas Mancuso, FY2021–2026, 10 rows, University Of Southern California

### Aiichiro Nakano
<a id="aiichiro-nakano"></a>

NSF identities whose name fits:
- kept: lead PI 000174407 (Aiichiro Nakano), 1997–2021, 4 awards, University of Southern California, Louisiana State University
- kept: co-PI anakano@usc.edu, 1991–2022, 16 awards, University of Southern California, Louisiana State University

### Paul Newton
<a id="paul-newton"></a>

NIH profiles whose name fits:
- rejected: [1942927](https://reporter.nih.gov/search/results?pi_profile_id=1942927) Paul A Newton, FY1986–1987, 2 rows, University Of California Berkeley

NSF identities whose name fits:
- kept: lead PI 000146689 (Paul K Newton), 1990–2008, 8 awards, University of Southern California, University of Illinois at Urbana-Champaign
- kept: co-PI newton@usc.edu, 1995–2000, 2 awards, University of Southern California

Paul A Newton (UC Berkeley, 1986–87 NIH) is a namesake.

### Meisam Razaviyayn
<a id="meisam-razaviyayn"></a>

NIH profiles whose name fits:
- kept: [15943922](https://reporter.nih.gov/search/results?pi_profile_id=15943922) Meisam Razaviyayn, FY2019–2021, 3 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 269983325 (Meisam Razaviyayn), 2022–2024, 2 awards, University of Southern California
- kept: co-PI razaviya@usc.edu, 2017–2024, 2 awards, University of Southern California

### Bodour Salhia
<a id="bodour-salhia"></a>

NIH profiles whose name fits:
- kept: [9176624](https://reporter.nih.gov/search/results?pi_profile_id=9176624) Bodour Salhia, FY2017–2026, 14 rows, University Of Southern California

NSF identities whose name fits:
- kept: co-PI salhia@usc.edu, 2019–2019, 1 awards, University of Southern California

### Julia Schwartzman
<a id="julia-schwartzman"></a>

NIH profiles whose name fits:
- kept: [11917761](https://reporter.nih.gov/search/results?pi_profile_id=11917761) Julia Ashley Schwartzman, FY2017–2017, 1 rows, Massachusetts Eye And Ear Infirmary

One 2017 NIH fellowship at Mass Eye and Ear, before USC.

### Chang (April) Shu
<a id="chang-shu"></a>

NIH profiles whose name fits:
- kept: [14363184](https://reporter.nih.gov/search/results?pi_profile_id=14363184) Chang Shu, FY2026–2026, 1 rows, University Of Southern California

Kept Chang Shu at USC Preventive Medicine (autism, R01MH143902).

### Rory Spence
<a id="rory-spence"></a>

No NIH, NSF, OpenAlex or ORCID grants found.

No NIH or NSF records under this name.

### Paul Thomas
<a id="paul-thomas"></a>

NIH profiles whose name fits:
- kept: [8818058](https://reporter.nih.gov/search/results?pi_profile_id=8818058) Paul D. Thomas, FY2008–2026, 48 rows, University Of Southern California, New York University School Of Medicine
- rejected: [8086311](https://reporter.nih.gov/search/results?pi_profile_id=8086311) Paul G. Thomas, FY2005–2026, 50 rows, St. Jude Children'S Research Hospital, Johns Hopkins University
- rejected: [2409570](https://reporter.nih.gov/search/results?pi_profile_id=2409570) Paul E Thomas, FY1991–2007, 28 rows, Univ Of Med/Dent Nj-R W Johnson Med Sch, Rutgers, The State Univ Of N.J.
- rejected: [3810255](https://reporter.nih.gov/search/results?pi_profile_id=3810255) Paul A Thomas, FY1985–1989, 8 rows, Illinois Cancer Center
- rejected: [10111600](https://reporter.nih.gov/search/results?pi_profile_id=10111600) Paul M Thomas, FY2019–2020, 4 rows, Northwestern University, Intact Genomics, Inc.
- rejected: [6314314](https://reporter.nih.gov/search/results?pi_profile_id=6314314) Paul R Thomas, FY1993–1993, 1 rows, National Academy Of Sciences
- rejected: [6314312](https://reporter.nih.gov/search/results?pi_profile_id=6314312) Paul R Thomas, FY1992–1992, 1 rows, National Academy Of Sciences
- rejected: [6314310](https://reporter.nih.gov/search/results?pi_profile_id=6314310) Paul R Thomas, FY1991–1991, 1 rows, National Academy Of Sciences

NSF identities whose name fits:
- kept: lead PI 269899430 (Paul Thomas), 2015–2019, 2 awards, University of Southern California
- kept: co-PI pdthomas@usc.edu, 2018–2018, 1 awards, Phoenix Bioinformatics Corporation

8 NIH profiles; kept Paul D. Thomas (PANTHER, USC).

### Paul Thompson
<a id="paul-thompson"></a>

NIH profiles whose name fits:
- kept: [6111760](https://reporter.nih.gov/search/results?pi_profile_id=6111760) Paul M Thompson, FY1998–2026, 165 rows, University Of Southern California, University Of California Los Angeles
- rejected: [7944530](https://reporter.nih.gov/search/results?pi_profile_id=7944530) Paul R Thompson, FY2007–2026, 35 rows, Univ Of Massachusetts Med Sch Worcester, University Of South Carolina At Columbia
- rejected: [1918036](https://reporter.nih.gov/search/results?pi_profile_id=1918036) Paul Davis Thompson, FY1985–2010, 13 rows, Hartford Hospital, Miriam Hospital
- rejected: [6363499](https://reporter.nih.gov/search/results?pi_profile_id=6363499) Paul A. Thompson, FY2004–2017, 6 rows, Washington University, Sanford Research/Usd
- rejected: [6359909](https://reporter.nih.gov/search/results?pi_profile_id=6359909) Paul Thompson, FY1999–2001, 3 rows, Hartford Hospital
- rejected: [3372385](https://reporter.nih.gov/search/results?pi_profile_id=3372385) Paul A Thompson, FY1992–1994, 3 rows, Case Western Reserve University
- rejected: [16207497](https://reporter.nih.gov/search/results?pi_profile_id=16207497) Paul N Thompson, FY2020–2021, 2 rows, Montana State University - Bozeman
- rejected: [6230605](https://reporter.nih.gov/search/results?pi_profile_id=6230605) Paul A Thompson, FY1996–1996, 1 rows, Case Western Reserve University
- rejected: [3372383](https://reporter.nih.gov/search/results?pi_profile_id=3372383) Paul D Thompson, FY1985–1985, 1 rows, Roger Williams Hospital

NSF identities whose name fits:
- kept: lead PI 269693312 (Paul M Thompson), 2018–2018, 1 awards, University of Southern California
- rejected: lead PI 000167994 (Paul B Thompson / Tarla R Peterson), 1988–2010, 5 awards, Texas A&M Research Foundation, Michigan State University
- rejected: lead PI 269729656 (Paul Thompson), 2014–2014, 1 awards, Dartmouth College
- rejected: lead PI 000069018 (Paul Thompson), 1989–1989, 1 awards, University of Florida
- rejected: co-PI Paul B Thompson, 2004–2023, 2 awards, Michigan State University

NIH grants left out by hand (someone else's, under a kept profile): P20RR017698.

9 NIH profiles; kept Paul M. Thompson (UCLA → USC, ENIGMA). Many grants are center subprojects. P20RR017698 (2008–11, University of South Carolina, peptide-based borono-lectins) is Paul R. Thompson, a chemist, filed under the same RePORTER profile, so it's left out. NSF: kept only Paul M Thompson (thompson@ini.usc.edu); Paul B Thompson (Michigan State), Dartmouth and Florida Paul Thompsons are namesakes.

### Arthur Toga
<a id="arthur-toga"></a>

NIH profiles whose name fits:
- kept: [6855806](https://reporter.nih.gov/search/results?pi_profile_id=6855806) Arthur W Toga, FY1990–2026, 384 rows, University Of Southern California, University Of California Los Angeles
- rejected: [3193612](https://reporter.nih.gov/search/results?pi_profile_id=3193612) Arthur N Toga, FY1985–1990, 2 rows, Washington University
- rejected: [3193616](https://reporter.nih.gov/search/results?pi_profile_id=3193616) Arthur W Toga, FY1985–1985, 1 rows, Washington University
- rejected: [3193614](https://reporter.nih.gov/search/results?pi_profile_id=3193614) Arthur W Toga, FY1985–1985, 1 rows, Washington University

NSF identities whose name fits:
- kept: lead PI 000171992 (Arthur W Toga), 1990–2001, 5 awards, University of California-Los Angeles
- kept: co-PI toga@loni.usc.edu, 1999–1999, 1 awards, University of California-Los Angeles

Kept Arthur W. Toga (UCLA → USC). 81 of his NIH records are center subprojects, collapsed into their parent grants.

### Peter Yingxiao Wang
<a id="peter-yingxiao-wang"></a>

NIH profiles whose name fits:
- kept: [8661093](https://reporter.nih.gov/search/results?pi_profile_id=8661093) Yingxiao Wang, FY2009–2026, 67 rows, University Of California, San Diego, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 269793423 (Yingxiao Wang), 2009–2025, 5 awards, University of California-San Diego, Gordon Research Conferences
- kept: co-PI ywang283@usc.edu, 2008–2014, 3 awards, University of Illinois at Urbana-Champaign, University of California-San Diego

### Arieh Warshel
<a id="arieh-warshel"></a>

NIH profiles whose name fits:
- kept: [1864711](https://reporter.nih.gov/search/results?pi_profile_id=1864711) Arieh Warshel, FY1985–2026, 101 rows, University Of Southern California

NSF identities whose name fits:
- kept: lead PI 000197820 (Arieh Warshel), 1998–2022, 7 awards, University of Southern California
- kept: lead PI 000159775 (Arieh Warshel), 1983–1985, 2 awards, University of Southern California

NSF: the older id 000159775 (USC 1983–85) has no email but is the same USC chemistry PI.

