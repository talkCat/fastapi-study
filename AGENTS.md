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
- `notebooks/agent-practice/001-weather-assistant-agent.ipynb`
- `notebooks/harness-engineering/001-claude-code-harness-engineering.ipynb`

This track already covers:

1. basic chat
2. chat history / context
3. structured output
4. function calling
5. minimal stock-agent demo
6. weather assistant agent practice with a repo-local Skill-backed tool
7. Harness Engineering principles for Claude Code style coding agents

### Harness Engineering / Claude Code design track

Main references:

- `notebooks/harness-engineering/README.md`
- `notebooks/harness-engineering/001-claude-code-harness-engineering.ipynb`
- `docs/skills_vs_tools_guide.md`

This track teaches:

1. Prompt as control plane, not personality decoration
2. Query Loop as the agent heartbeat
3. Tools as managed execution interfaces with permission gates
4. Context as working memory with budget governance
5. Error recovery as the main path, not an edge case
6. Sub-agent isolation and independent verification
7. Team policy as the basis for reliable agent adoption

### Codex / Skills learning track

Main references:

- `docs/skills_vs_tools_guide.md`
- `notebooks/codex/001-codex-skill-development.ipynb`
- `notebooks/codex/002-build-a-minimal-weather-skill.ipynb`
- `notebooks/codex/003-refactor-a-skill-with-references.ipynb`
- `notebooks/codex/004-add-a-script-to-a-skill.ipynb`
- `notebooks/codex/005-wire-a-skill-into-a-mini-workflow.ipynb`
- `notebooks/codex/006-run-a-full-weather-skill-session.ipynb`
- `notebooks/codex/007-handle-errors-and-fallbacks-in-a-skill.ipynb`
- `notebooks/codex/008-implement-a-real-open-meteo-fallback.ipynb`
- `notebooks/codex/009-validate-a-skill-end-to-end.ipynb`
- `notebooks/codex/010-final-recap-how-a-skill-grows.ipynb`

Repo-local Skills already created:

- `.agents/skills/openai-notebook-author/`
- `.agents/skills/weather-query-assistant/`

Repo-local Tools already created:

- `.agents/tools/weather/`

This track now contains a complete 10-lesson weather-skill line that teaches:

1. reading a real Skill
2. building a minimal Skill
3. introducing `references/`
4. introducing `scripts/`
5. wiring a mini workflow
6. running a full session
7. handling errors and fallbacks
8. implementing a real Open-Meteo fallback
9. validating the Skill end to end
10. final recap of the growth path

These repo-local Skills are used for teaching real Skill structure, workflow growth, fallback design, and validation.

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

- teach the full lifecycle of growing a repo-local Skill from minimal structure to a usable, validated workflow
- provide a concrete weather-query example with primary and fallback paths

Important files:

- `SKILL.md`
- `agents/openai.yaml`
- `references/weather_sources.md`
- `scripts/normalize_location.py`
- `scripts/build_wttr_query.py`
- `scripts/build_open_meteo_query.py`
- `scripts/validate_weather_skill.py`

Related tool files:

- `.agents/tools/weather/fetch_weather.py`
- `.agents/tools/weather/validate_weather_tool.py`

Current state:

- has a primary `wttr.in` query-building path
- has an Open-Meteo fallback query-building path
- uses a separated structured weather tool under `.agents/tools/weather/`
- has a minimal validation script
- is the canonical teaching example for the Codex / Skills notebook series

## How To Start a New Session

If the request is about FastAPI backend learning:

1. read `README.md`
2. open the relevant guide in `docs/`
3. inspect the matching router/service/schema files before answering

If the request is about OpenAI notebooks or stock-agent learning:

1. read `docs/openai_chat_agent_learning_plan.md`
2. inspect the latest notebook in the target series
3. keep naming and teaching rhythm consistent

If the request is about agent practice notebooks:

1. read `docs/openai_chat_agent_learning_plan.md`
2. inspect `notebooks/agent-practice/`
3. keep repo-local Skills and runtime Tools separated: Skills under `.agents/skills/`, Tools under `.agents/tools/`
4. reuse existing repo-local Skills and Tools when possible instead of duplicating tool logic inside notebooks

If the request is about Harness Engineering, Claude Code interaction patterns, or coding-agent reliability:

1. inspect `notebooks/harness-engineering/`
2. keep the teaching focus on engineering controls rather than model cleverness
3. explain reliability through Prompt control plane, Query Loop, Tool permissions, Context budget, Recovery, independent verification, and team policy
4. avoid claiming exact Claude Code source behavior unless source files are actually present or cited

If the request is about Skills / Codex / OpenClaw-style workflow:

1. read `docs/skills_vs_tools_guide.md`
2. inspect `notebooks/codex/001-codex-skill-development.ipynb`
3. inspect the rest of the Codex notebook series if the request is about the weather skill growth path
4. inspect the real skill directories under `.agents/skills/`
5. prefer teaching through real repo-local Skills instead of only abstract definitions

## Good Next Steps

If the user asks what to build next, these are the most natural follow-ups:

1. continue the Codex lessons:
   - the 10-lesson weather-skill line is complete
   - the next natural step is to migrate the same growth pattern to a new Skill topic
2. connect the stock-agent demo to a real FastAPI endpoint
3. keep extending the OpenAI learning notebooks in small, staged lessons
4. continue the Harness Engineering series with a minimal query-loop implementation
5. refine `AGENTS.md` when major repo context changes

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
- a complete weather-skill teaching line from minimal Skill to validated workflow
- Harness Engineering principles for reliable coding-agent systems

When unsure, continue by preserving teaching clarity, concrete examples, and the repo's existing staged learning structure.
