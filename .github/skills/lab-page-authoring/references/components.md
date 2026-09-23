# Lab site components

Import components with the `~/` alias. Starlight's own components come from `@astrojs/starlight/components`.

```mdx
import { Aside, Tabs, TabItem, Steps, FileTree, LinkButton } from '@astrojs/starlight/components';
import LabMeta from '~/components/LabMeta.astro';
import CatchUp from '~/components/CatchUp.astro';
import Checkpoint from '~/components/Checkpoint.astro';
import VerifyStep from '~/components/VerifyStep.astro';
import KnowledgeCheck from '~/components/KnowledgeCheck.astro';
import WhatVaries from '~/components/WhatVaries.astro';
import RepoFile from '~/components/RepoFile.astro';
import PlatformBadge from '~/components/PlatformBadge.astro';
import NextLab from '~/components/NextLab.astro';
import FeedbackLink from '~/components/FeedbackLink.astro';
import Mermaid from '~/components/Mermaid.astro';
```

## Lab components

| Component | Props | What it renders |
|---|---|---|
| `<LabMeta />` | none | Time, level, platforms, surfaces, primitives, start and end checkpoints, all from the `lab` frontmatter. Required in "At a glance". |
| `<CatchUp />` | `checkpoint` (optional; defaults to `lab.startCheckpoint`) | The `Restore-LabCheckpoint.ps1` command for learners who skipped the earlier labs. Required in "Before you begin". |
| `<Checkpoint lab="07" step="3" />` | `lab`, `step`, optional `label` | A "Done" tick box saved in local storage. Put one at the end of each step. `step` must match a `### Step N.` heading. |
| `<VerifyStep lab="07" />` | `lab` | The `Test-LabProgress.ps1` command in Windows and macOS tabs, sample output, and a table of this lab's checks from `lab/checks.yaml` with links to the step that fixes each one. Required in "Verify your work". |
| `<KnowledgeCheck question="..." options={[...]} answer={1} explanation="..." />` | `question`, `options`, `answer` (zero-based index), `explanation` | A multiple-choice question. Works without JavaScript as a `<details>` block. Two or three per lab. |
| `<WhatVaries mustMatch={['...']}>text</WhatVaries>` | `mustMatch` (list), optional slot text | For agent steps: what may differ between runs (slot) and what must be true (list). |
| `<RepoFile path="..." lines="1-12" />` | `path` (repo-relative), optional `lines` ("a-b"), `lang`, `title` | The real file, or a line range of it, with a link to GitHub. The build fails if the file or line doesn't exist. The file's folder must be listed in `site/src/plugins/vite-repo-files.mjs`. |
| `<PlatformBadge kind="windows-only" />` | `kind`: `windows-only`, `macos`, `file-mode`, `paid-plan`, `preview`, `optional` | A small badge for a step or section. |
| `<NextLab current="07" />` | `current` | The next lab on the learner's chosen track. Required in "Recap and next". |
| `<FeedbackLink />` | optional `step` | A link that opens a prefilled lab-feedback issue. |
| `<Mermaid code={`flowchart LR ...`} label="..." />` | `code`, `label` (screen-reader text, also the caption) | A diagram rendered in the browser from the bundled mermaid library. |

## Links

- Link to other pages with root-relative paths and a trailing slash: `[Lab 06](/labs/06-skills-and-assessor/)`. The site adds its base path at build time, and the link validator fails the build if the page or `#anchor` doesn't exist.
- In a component prop such as `LinkButton href`, Markdown links aren't rewritten. Import `{ url as siteUrl } from '~/lib/url'` and write `href={siteUrl('labs/06-skills-and-assessor/')}`. Don't import it as `url`, because every MDX page already exports a `url`.
- Step anchors are `#step-N`. Section anchors are the heading in lowercase with hyphens, for example `#verify-your-work`.

## Starlight components you'll use most

- `<Tabs syncKey="os">` with `<TabItem label="Windows">` and `<TabItem label="macOS">`. The same `syncKey` keeps every tab on the page, and on other pages, on the learner's choice.
- `<Aside type="note|tip|caution|danger" title="...">` for side notes. Use `caution` for anything that can lose work.
- `<Steps>` around an ordered list when a single step has several sub-steps with their own code blocks.
- `<FileTree>` for folder layouts.

## Markdown gotchas

- Leave a blank line after an opening JSX tag (`<TabItem label="Windows">`) and before its closing tag, or the Markdown inside won't render.
- Text like `<checkpoint>` in prose is read as HTML. Put it in backticks.
- MDX `{#id}` heading IDs aren't supported. Step anchors come from the `Step N.` heading text.
