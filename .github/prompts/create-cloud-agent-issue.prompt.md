---
name: create-cloud-agent-issue
description: Draft a model-change issue that Copilot cloud agent can pick up and finish without further questions.
agent: agent
argument-hint: The change you want, in a sentence
---
Draft a GitHub issue for this change so it can be assigned to Copilot cloud agent:

${input:change:For example, add a Refills PM measure and a Refill Rate MoM Change measure}

Follow the `model-change` issue form in `.github/ISSUE_TEMPLATE/model-change.yml`. Use its headings:

- **Goal**: the business behavior you want, in one or two sentences.
- **Objects in scope**: the exact table, column, and measure names in the current model. Check the TMDL so they exist.
- **Acceptance criteria**: a checklist the agent can verify itself. Keep the form's three default items and add specifics, such as exact measure names, display folders, and format strings.
- **Suggested custom agent**: `model-improver`.

Add an **Out of scope** line under Goal listing what the agent must not change.

The cloud agent runs on Linux without Power BI Desktop, so don't ask for anything that needs Desktop or live DAX results.

Show me the issue text. Don't create the issue unless I ask. If I do, create it with the `model-change` label, using `gh issue create` or the GitHub MCP server.
