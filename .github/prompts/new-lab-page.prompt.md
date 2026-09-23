---
name: new-lab-page
description: Draft a new lab page for the lab site from the lab template and the checks in lab/checks.yaml (maintainers).
agent: lab-author
argument-hint: Lab number and title
---
Draft lab page `${input:lab:Lab number and title, for example 16 Fabric data agents}`.

1. Load the `lab-page-authoring` skill.
2. Read the checks for this lab in `lab/checks.yaml`. If there are none, propose check entries (id, anchor, description, hint) and wait for my approval before adding them.
3. Write `site/src/content/docs/labs/<NN>-<slug>.mdx` with the ten sections in order and a `### Step N.` heading for every check anchor.
4. Run `npm run check` and `npm run build` in `site/`.
5. List every UI label or behavior you couldn't verify.
