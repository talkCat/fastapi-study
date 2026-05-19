import json
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]


def read_text(path: str, encoding: str = "utf-8", max_chars: int = 20000) -> dict[str, Any]:
    target = _resolve_workspace_path(path)
    text = target.read_text(encoding=encoding)
    return {
        "path": str(target),
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "size_bytes": target.stat().st_size,
    }


def write_text(path: str, content: str, encoding: str = "utf-8", overwrite: bool = True) -> dict[str, Any]:
    target = _resolve_workspace_path(path, allow_missing=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    return {"path": str(target), "written": True, "size_bytes": target.stat().st_size}


def write_json(path: str, data: Any, ensure_ascii: bool = False, indent: int = 2, overwrite: bool = True) -> dict[str, Any]:
    target = _resolve_workspace_path(path, allow_missing=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8")
    return {"path": str(target), "written": True, "size_bytes": target.stat().st_size}


def list_dir(path: str = ".", max_entries: int = 200) -> dict[str, Any]:
    target = _resolve_workspace_path(path)
    if not target.is_dir():
        raise NotADirectoryError(f"Not a directory: {target}")
    items = []
    for child in sorted(target.iterdir(), key=lambda item: item.name)[:max_entries]:
        items.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "size_bytes": child.stat().st_size if child.is_file() else None,
            }
        )
    return {"path": str(target), "count": len(items), "entries": items}


def _resolve_workspace_path(path: str, allow_missing: bool = False) -> Path:
    candidate = Path(path).expanduser()
    target = (candidate if candidate.is_absolute() else WORKSPACE_ROOT / candidate).resolve()
    if WORKSPACE_ROOT != target and WORKSPACE_ROOT not in target.parents:
        raise ValueError(f"Path escapes workspace: {path}")
    if not allow_missing and not target.exists():
        raise FileNotFoundError(f"Path not found: {target}")
    return target
