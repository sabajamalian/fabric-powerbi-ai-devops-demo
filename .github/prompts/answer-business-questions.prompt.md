---
name: answer-business-questions
description: Answer the five business questions against the current model, save the run file with the given label, and grade it.
agent: question-tester
argument-hint: Run label, for example local-baseline
---
Answer the Contoso Pharmacy business questions against the model open in Power BI Desktop.

Run label: `${input:label:local-baseline or local-ai-ready}`

1. List the questions with `pwsh ./scripts/Get-BusinessQuestions.ps1`.
2. Answer each one with a DAX query through Power BI Modeling MCP. Record your assumptions.
3. Save `evaluation/runs/${input:label}.json` in the format from the `business-question-evaluation` skill.
4. Grade it with `pwsh ./scripts/Grade-QuestionRun.ps1 -Run ${input:label}`.
5. Report the score per question.

If Power BI Desktop or the MCP server isn't available, stop and tell me. Don't make up numbers.
