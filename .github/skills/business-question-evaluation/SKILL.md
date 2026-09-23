---
name: business-question-evaluation
description: Answer the five Contoso Pharmacy business questions against the semantic model, record the answers in a run file (evaluation/runs/<label>.json), grade the run, and compare runs before and after model changes. Use when asked to test the model with business questions, create a baseline or after run, grade answers, or explain why a question scored 0 or 1.
---
# Business question evaluation

The lab measures whether model changes make AI answers better. The same five questions are answered against the baseline model and the AI-ready model, each run is graded 0 to 2 per question, and the two runs are compared.

## Rules that keep the test honest

- Get the questions only from `pwsh ./scripts/Get-BusinessQuestions.ps1` (add `-Json` for machine output). It prints the ID, the question, paraphrases, and the `answer_columns` you must use.
- Never read `evaluation/expected/`, `evaluation/questions.yaml`, `tools/python/pharmacy_demo/modelgen/`, or `tools/python/pharmacy_demo/samples.py`, and never run `pharmacy_demo dax-queries`. They contain the answers. The repo's hooks deny these.
- Answer from the model as it is now. On the baseline model, use the names you find (for example `fact_rx_fill`), and don't fix the model first. A low baseline score is the expected result.
- Don't write the `grade` block. Only the grader writes it.

## Step 1. Answer each question

For each question:

1. Decide the interpretation. If the question is ambiguous (which month is "latest", what "unusually high" means), write your choice in `assumptions`.
2. Write one DAX query that returns exactly the `answer_columns`, one row per expected key. Use `EVALUATE` with `SUMMARIZECOLUMNS` or `ADDCOLUMNS`, and add `ORDER BY`.
3. Run it with Power BI Modeling MCP (`dax_query_operations`) against the model open in Power BI Desktop.
4. Copy the result rows into the run file. Rename the keys to the `answer_columns` names.

If Power BI Desktop isn't available (macOS, Linux, or the cloud agent), stop and say so. Don't invent numbers. The learner can use the sample runs in `evaluation/runs/sample-*.json` instead.

## Step 2. Write the run file

Save as `evaluation/runs/<label>.json`. The format is in [references/run-file.md](references/run-file.md) and the schema is `evaluation/run.schema.json`. Common labels:

| Label | Model state | Lab |
|---|---|---|
| `local-baseline` | `baseline` | 05 |
| `local-ai-ready` | `ai-ready` | 10 |

## Step 3. Grade and compare

```powershell
pwsh ./scripts/Grade-QuestionRun.ps1 -Run local-baseline
pwsh ./scripts/Compare-QuestionRuns.ps1 -Before local-baseline -After local-ai-ready
```

The comparison is written to `out/question-comparison.md`. With no Desktop, compare the illustrative runs:

```powershell
pwsh ./scripts/Compare-QuestionRuns.ps1 -Before sample-baseline -After sample-ai-ready
```

## Step 4. Explain the result

For each question that scored below 2, give the grader's reason and the model gap behind it. Typical baseline gaps:

| Question | Usual baseline problem | Model fix |
|---|---|---|
| Q01 fills by region and month | Raw names, no measure, fact date used for months | Business names, `[Prescriptions Filled]`, Date relationship |
| Q02 category volume change | No time-comparison measure, unclear "latest month" | `[MoM Change]`, AI instruction for December 2025 |
| Q03 processing time by store | Minutes summed instead of averaged | `[Avg Processing Time (min)]` |
| Q04 unusually high refills | No definition of "unusual" | `[Refill Rate Index vs Chain]` and the 1.25 threshold |
| Q05 previous period | "Previous period" undefined | `[Prescriptions Filled PM]`, `[MoM %]`, AI instruction |

Scoring details are in `evaluation/rubric.md`. Agent output varies, so suggest a second run before drawing conclusions from a one-point difference.
