# Installed Skills

This directory is the app-managed install target for unpacked skill packages.

Installable skill package requirements:

- It must be a directory.
- It must contain `SKILL.md`.
- `SKILL.md` should include frontmatter with `name` and `description`.
- It may optionally contain `agents/skill.json` as the contract manifest.

Contract-based plugin conventions:

- `SKILL.md`: human-readable instructions plus YAML frontmatter metadata.
- `agents/skill.json`:
  - `trigger.keywords / patterns / examples`
  - `routing.preferred_tools`
  - `routing.planner_hint / answer_hint`
  - `routing.resolver.script` for deterministic plan resolution
- `agents/tools.json` remains optional for declarative tool definitions.
- `scripts/*.py` can be executed through the shared `skill.python.run` runtime tool.

Runtime tools stay outside skill packages. Skills describe how to work; tools provide callable execution.

Platform-maintained generic tools now live under:

- `app/agents/tool_packages/`

Examples:

- `files/`: local file read/write/list
- `shell/`: shell command execution and process inspection
- `python/`: Python code execution
- `http/`: HTTP GET/POST requests

Each tool package is contract-based:

- `tool.json`: manifest
- `*.py`: implementation module referenced by the manifest

The runtime scans these tool packages automatically. Skills should depend on the tool names, not on hardcoded Python paths.
