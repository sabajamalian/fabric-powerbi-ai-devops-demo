---
name: lab-page-authoring
description: Write or update a self-paced lab page for the Contoso Pharmacy lab site (Astro Starlight, site/src/content/docs/labs/*.mdx), including the required frontmatter, the ten fixed sections, step anchors that match lab/checks.yaml, site components, and the screenshot checklist. Use when creating a new lab, changing lab steps, fixing a lab-feedback issue, or adding a verify check to a lab.
---
# Authoring a lab page

Lab pages live in `site/src/content/docs/labs/NN-<slug>.mdx`. The build fails when a page breaks the rules below, so follow them exactly.

## Frontmatter

```yaml
---
title: "Lab 07: Handoffs, names, and descriptions"
description: "Use the model-improver agent to rename objects, add descriptions, and fix the report."
lab:
  number: 7
  durationMinutes: 45
  level: intermediate            # intro | intermediate | advanced
  platforms: [windows, macos-file-mode]
  requiresDesktop: false
  surfaces: [vscode]
  primitives: [custom-agent, handoff, prompt-file, skill]
  startCheckpoint: lab06-complete
  endCheckpoint: lab07-complete
  # lastVerified: 2026-10-01    # add only after a full run on Windows 11
---
```

- `startCheckpoint` and `endCheckpoint` must be names in `lab/checkpoints.json`, or `none`.
- `platforms` values: `windows`, `macos`, `macos-file-mode`. Use `macos-file-mode` when macOS works only without Power BI Desktop.
- Set `requiresDesktop: true` only when no step can be done without Desktop.
- Add `lastVerified` (a date) only after you run the whole lab on Windows 11. Without it, the page says the lab hasn't been verified yet; with a date older than 90 days, it warns that menus may have moved.

## The ten sections, in this order

Use these exact `##` headings:

1. `## At a glance`: just `<LabMeta />`.
2. `## Why this matters`: three to five sentences.
3. `## Concepts`: short definitions with links to `/reference/` pages.
4. `## Before you begin`: expected start state and `<CatchUp />`.
5. `## Steps`: see below.
6. `## Verify your work`: `<VerifyStep lab="07" />`.
7. `## Troubleshooting`: `<details>` blocks, one per symptom.
8. `## Knowledge check`: two or three `<KnowledgeCheck />`.
9. `## Recap and next`: what the learner built, and the next lab.
10. `## Go further`: optional challenges.

## Steps and anchors

Each step is an `###` heading that starts with `Step N.`. The site gives it the anchor `#step-N` automatically, and `lab/checks.yaml` links failed checks to that anchor:

```mdx
### Step 4. Run the improver

1. Open Copilot Chat (**Ctrl+Alt+I**, or **View > Chat**).
2. Pick **model-improver** from the agent dropdown.
3. Type `/improve-names-and-descriptions` and press **Enter**.

**You should see:** a plan listing the tables it will rename, then edits to the `.tmdl` files.

<WhatVaries mustMatch={["Every table uses the business name", "The lint passes"]} />

<Checkpoint lab="07" step="4" />
```

- Number steps from 1 with no gaps. Every `anchor` used in `lab/checks.yaml` for this lab must exist on the page.
- Each step says what to do, the exact UI path or command, and what the learner should see.
- Give both the Command Palette command and the menu path for VS Code actions, because menu labels move between releases.
- Commands use Windows PowerShell 7 first. Add a macOS tab only where the step works on macOS:

```mdx
<Tabs syncKey="os">
  <TabItem label="Windows">
    ```powershell
    pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 07
    ```
  </TabItem>
  <TabItem label="macOS">
    ```bash
    pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 07
    ```
  </TabItem>
</Tabs>
```

Components are listed in [references/components.md](references/components.md).

## Writing style

- Second person, present tense, short sentences.
- No em dashes, no en dashes, no emojis. Use "to" for ranges ("10 to 15 minutes").
- Show real repo files with `<RepoFile path="..." />` instead of pasting them, so the page can't drift from the code.
- For agent steps, say what varies (wording, order) and what must not (the files changed, the check result).
- Never include tenant IDs, workspace IDs, email addresses, or real customer names. The build runs an identifier guard.

## Screenshot checklist

- [ ] Captured on Windows 11 with the synthetic model and a demo account.
- [ ] Account menus, avatars, emails, organization names, and user paths cropped or blurred.
- [ ] PNG, at most 1600 px wide, at `site/src/assets/screenshots/labNN/stepNN-<slug>.png`.
- [ ] Alt text describes the state so the step makes sense without the image.

## Check your work

```powershell
cd site
npm run check     # section order, frontmatter, anchors, dashes, identifiers
npm run build     # includes the link and anchor validator
```
