# AI-readiness checklist

Use this when you assess or review the model. Each item maps to a rule so findings stay consistent. This is guidance for agents and reviewers, not a score.

## Can an AI find the right object?

- [ ] Names are business words a pharmacy manager would say (C01).
- [ ] Every table, visible column, and measure has a description under 200 characters (C02, C03).
- [ ] Keys, IDs, and sort helpers are hidden, so they aren't offered as answers (C04).
- [ ] Raw codes have a decoded, readable column (C06).
- [ ] Each table has a default label for its rows (C14).
- [ ] Synonyms cover the words people actually use: fills, scripts, drug category, turnaround time (C15, `fabric/ai-prep/synonyms.yaml`).

## Will the numbers be right?

- [ ] Every fact-to-dimension relationship exists and is many-to-one (C07).
- [ ] Filters flow one way, from dimensions to the fact table (C08).
- [ ] Columns that must not be added up have `summarizeBy: none` (C05).
- [ ] The date table is marked and auto date/time is off, so time intelligence works (C09, C10).
- [ ] Month and weekday names sort in calendar order (C11).

## Is the business logic explicit?

- [ ] Common questions have an explicit measure instead of relying on implicit sums (C12).
- [ ] Measures have format strings and live in the agreed display folders (C13).
- [ ] Terms that need a definition are defined in the AI instructions draft: latest month, previous period, unusually high refill activity, processing time (C15).
- [ ] Each business question has a verified answer candidate with trigger phrases (C15).

## How to report findings

Write one row per finding: rule, severity (high, medium, low), object (for example `column fact_rx_fill[qty]`), finding, and fix. Group by rule and put high severity first.
