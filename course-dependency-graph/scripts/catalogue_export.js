// Export course text (prerequisites, terms offered, descriptions) from the USC catalogue.
//
// catalogue.usc.edu blocks scripted downloads, so this runs in your own browser:
//   1. Open the program page, e.g.
//      https://catalogue.usc.edu/preview_program.php?catoid=22&poid=32504
//   2. Open DevTools (Cmd+Option+J in Chrome), paste this whole file into the Console, press Enter.
//      (Chrome may ask you to type "allow pasting" first.)
//   3. It fetches each course page one at a time and downloads catalogue-courses.json.
//      Save it as course-dependency-graph/data/catalogue-courses.json and rerun
//      python3 scripts/update_data.py.
//
// It reads every course linked from the program page, plus courses linked from those
// courses' prerequisite text (one level), at about 2-3 pages per second.
(async () => {
  const DELAY_MS = 400;
  const EXTRA_LIMIT = 80;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const coidOf = href => (href.match(/[?&]coid=(\d+)/) || [])[1];

  const catoidHere = (location.search.match(/[?&]catoid=(\d+)/) || [])[1];

  // Program pages link courses with onclick="showCourse('22', '367576', this, 'a:2:{...}')";
  // links inside course text keep the id in href, onclick (acalogPopup) or rel instead.
  function linksIn(root) {
    const out = new Map();
    root.querySelectorAll("a").forEach(a => {
      const attrs = ["href", "onclick", "rel"].map(n => a.getAttribute(n) || "").join(" ");
      const show = attrs.match(/showCourse\(\s*['"]?(\d+)['"]?\s*,\s*['"]?(\d+)['"]?\s*,\s*this\s*,\s*['"]([^'"]*)['"]/);
      const coid = show ? show[2] : coidOf(attrs);
      if (!coid || out.has(coid)) return;
      const catoid = show ? show[1] : (attrs.match(/[?&]catoid=(\d+)/) || [])[1] || catoidHere;
      out.set(coid, { coid, catoid, options: show ? show[3] : "", label: a.textContent.trim() });
    });
    return out;
  }

  // Same request the page makes when you click a course; the full course page is the fallback.
  const urlsFor = item => [
    new URL(`/ajax/preview_course.php?catoid=${item.catoid}&coid=${item.coid}` +
      (item.options ? `&display_options=${encodeURIComponent(item.options)}` : "") + "&show", location.href).href,
    new URL(`/preview_course_nopop.php?catoid=${item.catoid}&coid=${item.coid}`, location.href).href,
  ];

  // Course pages have no layout when parsed off-screen, so rebuild line breaks by hand.
  function blockText(el) {
    el.querySelectorAll("script, style, noscript").forEach(n => n.remove());
    el.querySelectorAll("br").forEach(n => n.replaceWith("\n"));
    el.querySelectorAll("p, div, h1, h2, h3, h4, li, tr, hr, table").forEach(n => n.append("\n"));
    return el.textContent.replace(/ /g, " ").replace(/[ \t]+/g, " ").replace(/ *\n */g, "\n").replace(/\n{2,}/g, "\n").trim();
  }

  async function fetchCourse(item) {
    for (const url of urlsFor(item)) {
      for (let attempt = 1; attempt <= 2; attempt++) {
        const res = await fetch(url, { credentials: "include" });
        const html = await res.text();
        if (res.status === 200 && /Units|Prerequisite|\d{3}/.test(html) && html.trim().length > 80) {
          const doc = new DOMParser().parseFromString(html, "text/html");
          const title = doc.querySelector("#course_preview_title");
          const block = (title && (title.closest("td.block_content") || title.closest("td") || title.parentElement)) ||
            doc.querySelector("td.block_content") || doc.body;
          return { url, block, text: blockText(block.cloneNode(true)) };
        }
        await sleep(2000); // bot-check token may need refreshing; try once more
      }
    }
    throw new Error("empty response");
  }

  if (!location.hostname.endsWith("catalogue.usc.edu")) {
    console.error("Run this on a catalogue.usc.edu program page.");
    return;
  }
  const queue = [...linksIn(document).values()];
  if (!queue.length) {
    // Print a few course-looking links so the format can be added above.
    const samples = [...document.querySelectorAll("a")].filter(a => /^[A-Z]{2,5}\s\d{3}/.test(a.textContent.trim())).slice(0, 3);
    console.error("Found 0 course links. Is this a catalogue program page? Sample links:\n" +
      (samples.map(a => a.outerHTML.slice(0, 400)).join("\n") || "(no links that start with a course code)"));
    return;
  }
  const seen = new Set(queue.map(c => c.coid));
  const courses = [], failed = [];
  let extra = 0;
  console.log(`Found ${queue.length} courses on this page. Fetching...`);
  for (let i = 0; i < queue.length; i++) {
    const item = queue[i];
    try {
      const { block, text } = await fetchCourse(item);
      courses.push({ coid: item.coid, url: urlsFor(item)[1], label: item.label, text });
      if (i < seen.size && extra < EXTRA_LIMIT) {
        // Follow courses linked from this course's text (e.g. CSCI 102 from CSCI 103).
        for (const link of linksIn(block).values()) {
          if (!seen.has(link.coid) && extra < EXTRA_LIMIT) { seen.add(link.coid); queue.push(link); extra++; }
        }
      }
    } catch (err) {
      failed.push({ ...item, error: String(err) });
    }
    if ((i + 1) % 10 === 0) console.log(`  ${i + 1}/${queue.length}`);
    await sleep(DELAY_MS);
  }

  const data = {
    source: location.href,
    catalogue: (document.querySelector("select[name=catalog] option[selected]") || {}).textContent || document.title,
    exported: new Date().toISOString(),
    courses,
    failed,
  };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: "application/json" }));
  a.download = "catalogue-courses.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  console.log(`Done: ${courses.length} courses saved to catalogue-courses.json` + (failed.length ? `, ${failed.length} failed (listed in the file)` : "."));
})();
