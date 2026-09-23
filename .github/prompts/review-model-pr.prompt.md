---
name: review-model-pr
description: Review semantic model and report changes on this branch before opening a pull request.
agent: model-reviewer
argument-hint: Base branch (default main)
---
Review the semantic model and report changes on this branch against `${input:base:main}`.

Run the validation, read the diff under `fabric/`, and return your review in the format from your instructions. Put anything that would break the model, the report, or the lab checks under **Blocking**.
