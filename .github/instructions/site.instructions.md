---
applyTo: "site/**"
description: Rules for the self-paced lab site (Astro Starlight).
---
# Lab site

- Lab pages live in `site/src/content/docs/labs/NN-slug.mdx` and follow the ten-section template. Load the `lab-page-authoring` skill before writing or editing a lab page.
- Show repository files with the `RepoFile` component, never by pasting their contents, so the site can't drift from the repo.
- Every lab ends with a `VerifyStep` whose `lab` matches an entry in `lab/checks.yaml`. Step headings use ids `step-1`, `step-2`, and so on, because lab check hints link to them.
- Windows PowerShell 7 comes first in every tab set. Mark Windows-only steps with `PlatformBadge`.
- No analytics, external scripts, fonts, or images from other hosts. `npm run check` fails the build if the output references another site.
- Write in plain, direct language: short sentences, no em or en dashes, no emojis. Screenshots show synthetic data and a demo account only.
- Run `npm run check` and `npm run build` in `site/` before you commit.
