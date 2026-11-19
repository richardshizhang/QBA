# QBA projects

Tools for QBA, USC's Quantitative Biology Association. The whole folder is one git repo, pushed to GitHub. Each project has its own folder:

- `course-dependency-graph/`: the QBIO prerequisite map. It is also published as a claude.ai artifact; the course map memory note says how the artifact copy is built.
- `faculty-map/`: the QCB faculty research map. Its memory note has the branch and publishing steps.

New projects go in new sibling folders, and each one gets a row in the root README's project table.

## Publishing

GitHub Pages builds from `main`, so every push to `main` publishes. Ask before pushing, unless I say "ship it". "Ship it" means:

1. Commit the change, staging files by explicit path.
2. Push to `main` (for `faculty-map/`, follow the steps in its memory note).
3. If `course-dependency-graph/` changed, republish the course map artifact too.

The saved catalogue page and `other_department_faculty/` are local reference copies. Both are gitignored; never commit them.
