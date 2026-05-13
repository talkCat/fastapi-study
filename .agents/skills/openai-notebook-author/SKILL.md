---
name: openai-notebook-author
description: Create or update teaching notebooks in this repo. Use when adding a new numbered notebook under notebooks/openai or notebooks/codex, keeping the existing teaching rhythm, and syncing related docs.
---

# OpenAI Notebook Author

Use this skill when the task is to add or revise teaching notebooks in this repository.

## Workflow

1. Inspect the latest notebook in the target series under `notebooks/openai/` or `notebooks/codex/`.
2. Read the matching planning or guide document before editing:
   - `docs/openai_chat_agent_learning_plan.md` for OpenAI notebooks
   - `docs/skills_vs_tools_guide.md` for Codex / Skills notebooks
3. Keep the same teaching rhythm:
   - title and learning goals
   - core concept explanation
   - runnable examples
   - stage summary and next step
4. Keep numbering and file naming consistent with the existing series.
5. Validate the generated notebook JSON with `scripts/validate_notebook.py`.
6. Update `notebooks/README.md` and any related learning-plan docs when a new notebook is added.

## References

- Read `references/notebook_style.md` when you need the repo's notebook naming and writing conventions.

## Scripts

- Run `scripts/validate_notebook.py <path-to-notebook>` after creating or modifying a notebook.

