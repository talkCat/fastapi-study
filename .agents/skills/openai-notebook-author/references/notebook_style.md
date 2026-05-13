# Notebook Style

Use this reference when creating or updating teaching notebooks in this repository.

## Naming

- Keep notebook numbering zero-padded: `001`, `002`, `003`.
- Keep series separated by domain:
  - `notebooks/openai/` for OpenAI API and stock-agent learning
  - `notebooks/codex/` for Codex / Skills / workflow learning

## Writing Rhythm

Follow the established teaching rhythm used in the existing notebooks:

1. Title and learning goals
2. Core concept explanation
3. Minimal runnable example
4. Progressive expansion
5. Stage summary and next step

## Repo Sync

When a new notebook is added:

- update `notebooks/README.md`
- update `docs/openai_chat_agent_learning_plan.md` if it belongs to the OpenAI learning path
- keep examples aligned with the repo's current file names and directory layout

## Editing Rule

Do not create empty optional folders just to make the tree look complete. Add `scripts/`, `references/`, or `assets/` only when the skill really needs them.

