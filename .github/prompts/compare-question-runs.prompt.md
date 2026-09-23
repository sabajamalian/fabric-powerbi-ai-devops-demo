---
name: compare-question-runs
description: Compare two graded question runs, write out/question-comparison.md, and explain which model changes caused each difference.
agent: question-tester
argument-hint: Before and after labels
---
Compare two question runs.

- Before: `${input:before:local-baseline}`
- After: `${input:after:local-ai-ready}`

1. Run `pwsh ./scripts/Compare-QuestionRuns.ps1 -Before ${input:before} -After ${input:after}`.
2. Read `out/question-comparison.md` and both run files.
3. For each question whose score changed, name the model change that most likely caused it (a measure, a description, an AI instruction, a relationship). Point to the file.
4. For any question still below 2, suggest the next change to try.

Agent answers vary between runs, so say when a one-point change could be noise.
