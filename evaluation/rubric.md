# Answer quality rubric

Each question in `questions.yaml` is scored 0, 1, or 2 by `scripts/Grade-QuestionRun.ps1`. A run's total is the sum across questions (10 points for the five questions).

| Score | Meaning | How the grader decides |
|---|---|---|
| 2 | Correct | Every expected row is present, keys match exactly (case and spacing ignored), every value is within the question's tolerance, and there are no extra rows. For `ranking` questions the order also matches. |
| 1 | Partially correct | The full check fails, but the question's `partial` rule passes (see below). |
| 0 | Wrong or missing | Neither check passes, or the answer is missing. |

## Partial credit rules

| Rule | Passes when |
|---|---|
| `row_fraction` | At least `min` of the expected rows are present with correct values. |
| `top_key` | The first row's key matches the expected first row (for example, the right slowest store). |
| `any_key` | At least one expected key is present and no more than one unexpected key is returned. |
| `column_match` | The named column matches the expected value (for example, the right December total with the wrong comparison). |

## Matching rules

- Column names are matched after lowercasing and replacing spaces and punctuation with `_`. The agent should still use the `answer_columns` names.
- Percent and rate columns (`*_pct`, `*_rate`, `*_index`) accept either a fraction (0.25) or a percentage (25). The grader normalizes.
- Numbers within tolerance count as equal. Tolerances live in `questions.yaml`.

## Human override

A reviewer can add `grade_override: { score, reason }` to an answer in a run file when the grader is too strict or too lenient, for example when the agent stated a reasonable alternative interpretation. The grader reports overrides separately so they're visible in the comparison table.

## What this rubric doesn't measure

It measures whether the answer matches the default interpretation in the question set. It doesn't score explanation quality, DAX style, or speed. Agent output varies between runs, so compare at least two runs per model state before drawing conclusions.
