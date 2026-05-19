import subprocess
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]


def exec_command(
    command: str,
    cwd: str | None = None,
    timeout_seconds: int = 20,
    max_output_chars: int = 20000,
) -> dict[str, Any]:
    if not command.strip():
        raise ValueError("command is required")
    working_dir = _resolve_workspace_path(cwd or ".", allow_missing=False)
    completed = subprocess.run(
        command,
        cwd=str(working_dir),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    stdout = completed.stdout[:max_output_chars]
    stderr = completed.stderr[:max_output_chars]
    return {
        "command": command,
        "cwd": str(working_dir),
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": len(completed.stdout) > max_output_chars or len(completed.stderr) > max_output_chars,
    }


def list_processes(max_lines: int = 80) -> dict[str, Any]:
    completed = subprocess.run(
        ["ps", "-eo", "pid,ppid,stat,comm"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    lines = completed.stdout.strip().splitlines()
    preview = lines[:max_lines]
    return {
        "exit_code": completed.returncode,
        "lines": preview,
        "truncated": len(lines) > max_lines,
    }


def _resolve_workspace_path(path: str, allow_missing: bool = False) -> Path:
    candidate = Path(path).expanduser()
    target = (candidate if candidate.is_absolute() else WORKSPACE_ROOT / candidate).resolve()
    if WORKSPACE_ROOT != target and WORKSPACE_ROOT not in target.parents:
        raise ValueError(f"Path escapes workspace: {path}")
    if not allow_missing and not target.exists():
        raise FileNotFoundError(f"Path not found: {target}")
    return target
