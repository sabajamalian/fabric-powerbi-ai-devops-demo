# Run file format

A run file records one set of answers to the five questions. Schema: `evaluation/run.schema.json`.

```json
{
  "label": "local-baseline",
  "model_state": "baseline",
  "created": "2026-01-20T15:04:05Z",
  "agent": "question-tester",
  "surface": "vscode",
  "model": "the chat model you ran with",
  "notes": "Baseline model, raw names.",
  "illustrative": false,
  "answers": [
    {
      "question_id": "Q03",
      "answer_text": "Average processing time per store, all of 2024 and 2025. Riverbend is slowest.",
      "dax": "EVALUATE\nSUMMARIZECOLUMNS(dim_store[store_nm], \"avg\", AVERAGE(fact_rx_fill[proc_mins]))",
      "assumptions": ["Whole data range, because no period was named."],
      "rows": [
        { "store": "Riverbend", "avg_processing_minutes": 14.2 }
      ]
    }
  ]
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `label` | yes | Lowercase letters, digits, hyphens. Use the file name without `.json`; comparisons show it as the column heading. |
| `model_state` | yes | `baseline`, `lab07`, `lab08`, `ai-ready`, or `other` |
| `created` | yes | UTC time, ISO 8601 |
| `agent` | no | The agent name, or `manual` |
| `surface` | no | `vscode`, `copilot-cli`, `cloud-agent`, `manual`, or `generated` |
| `model` | no | The chat model used |
| `notes` | no | Anything a reviewer should know |
| `illustrative` | no | `true` only for the generated sample runs |
| `answers` | yes | One entry per question you answered |

Each answer:

| Field | Required | Notes |
|---|---|---|
| `question_id` | yes | `Q01` to `Q05` |
| `answer_text` | no | One or two sentences, including the period used |
| `dax` | no | The query you ran |
| `assumptions` | no | List of interpretation choices |
| `rows` | yes | Objects keyed by the question's `answer_columns` |
| `grade_override` | no | `{ "score": 0-2, "reason": "..." }`, added by a human reviewer only |

The column names in the example above are illustrative. Use the exact `answer_columns` printed by `pwsh ./scripts/Get-BusinessQuestions.ps1`.

## Values

- Numbers are JSON numbers, not strings.
- Percent columns (`*_pct`, `*_rate`, `*_index`) may be a fraction (0.25) or a percentage (25).
- Month keys look like `2025-12`.
