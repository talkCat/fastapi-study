# AGENTS.md

This file is the long-term working memory for this repository.

Use it at the start of a new session to understand what this repo is for, what is already built, and how to continue work without re-discovering the same context.

## Project Purpose

This repository is a learning-oriented FastAPI project.

It has two parallel goals:

1. Teach FastAPI backend structure in a way that is friendly to a Java developer.
2. Teach OpenAI / agent development step by step, from basic chat to structured outputs, function calling, simple stock-agent demos, and repo-local Skills.

This is not just an app repo. It is also a teaching repo.

When editing or adding content, prefer clarity, progressive learning order, and small runnable examples over abstract architecture talk.

## Primary Learning Tracks

### FastAPI learning track

Main references:

- `README.md`
- `docs/database_query_and_response_guide.md`
- `docs/async_concurrency_guide.md`
- `docs/python_syntax_notes.md`

This track explains:

- controller/service/dao style flow
- unified response wrapping
- async IO vs thread pool usage
- Python syntax for a Java-oriented learner

### OpenAI / agent learning track

Main references:

- `docs/openai_chat_agent_learning_plan.md`
- `notebooks/README.md`
- `notebooks/openai/001-openai-chat-basics.ipynb`
- `notebooks/openai/002-openai-chat-history.ipynb`
- `notebooks/openai/003-openai-structured-output.ipynb`
- `notebooks/openai/004-openai-function-calling.ipynb`
- `notebooks/openai/005-stock-agent-demo-v1.ipynb`

This track already covers:

1. basic chat
2. chat history / context
3. structured output
4. function calling
5. minimal stock-agent demo

### Codex / Skills learning track

Main references:

- `docs/skills_vs_tools_guide.md`
- `notebooks/codex/001-codex-skill-development.ipynb`
- `notebooks/codex/002-build-a-minimal-weather-skill.ipynb`

Repo-local Skills already created:

- `.agents/skills/openai-notebook-author/`
- `.agents/skills/weather-query-assistant/`

These are used for teaching real Skill structure and development workflow.

## Important Repo Conventions

### Teaching style

When writing docs or notebooks:

- assume the learner is strong in Java but weaker in Python / agent ecosystems
- prefer concrete explanations over broad abstractions
- explain why something exists before making it more advanced
- use small steps with visible outputs

### Notebook style

When adding or editing notebooks:

- keep numbering zero-padded: `001`, `002`, `003`
- keep series separated by domain:
  - `notebooks/openai/`
  - `notebooks/codex/`
- preserve the existing rhythm:
  1. title and learning goals
  2. core concept explanation
  3. minimal runnable examples
  4. progressive expansion
  5. stage summary and next step

After adding a new notebook:

- update `notebooks/README.md`
- update related planning docs when needed

### Skill development style

When creating a new repo-local Skill:

- start from the smallest useful structure
- `SKILL.md` is required
- `agents/openai.yaml` is recommended
- add `references/` only when details become too large for `SKILL.md`
- add `scripts/` only when there is real repeated or deterministic work
- do not create empty optional directories just to make the tree look complete

## Current Real Skills

### `openai-notebook-author`

Path:

- `.agents/skills/openai-notebook-author/`

Purpose:

- create or update teaching notebooks in this repo
- keep teaching rhythm consistent
- sync related docs

Important files:

- `SKILL.md`
- `references/notebook_style.md`
- `scripts/validate_notebook.py`

### `weather-query-assistant`

Path:

- `.agents/skills/weather-query-assistant/`

Purpose:

- teach how to build a minimal Skill from scratch
- keep the first version intentionally small

Important files:

- `SKILL.md`
- `agents/openai.yaml`

## How To Start a New Session

If the request is about FastAPI backend learning:

1. read `README.md`
2. open the relevant guide in `docs/`
3. inspect the matching router/service/schema files before answering

If the request is about OpenAI notebooks or stock-agent learning:

1. read `docs/openai_chat_agent_learning_plan.md`
2. inspect the latest notebook in the target series
3. keep naming and teaching rhythm consistent

If the request is about Skills / Codex / OpenClaw-style workflow:

1. read `docs/skills_vs_tools_guide.md`
2. inspect `notebooks/codex/001-codex-skill-development.ipynb`
3. inspect the real skill directories under `.agents/skills/`
4. prefer teaching through real repo-local Skills instead of only abstract definitions

## Good Next Steps

If the user asks what to build next, these are the most natural follow-ups:

1. continue the Codex lessons:
   - lesson 3: add `references/` to the weather skill
   - lesson 4: add a small script such as location normalization
2. connect the stock-agent demo to a real FastAPI endpoint
3. keep extending the OpenAI learning notebooks in small, staged lessons

## Things To Avoid

- Do not turn teaching content into a generic architecture essay.
- Do not add complexity before the current stage is stable.
- Do not create empty directories in Skills unless they are actually needed.
- Do not silently break the numbering or style of the notebook series.
- Do not assume OpenClaw-specific repo files exist unless they are actually present in this repo.

## Short Summary

This repo is a staged learning workspace for:

- FastAPI backend patterns
- OpenAI API usage
- structured output and function calling
- minimal agents
- real repo-local Skill development

When unsure, continue by preserving teaching clarity, concrete examples, and the repo's existing staged learning structure.
