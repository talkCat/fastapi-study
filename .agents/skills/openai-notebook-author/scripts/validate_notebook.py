#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_notebook.py <path-to-notebook>")
        return 1

    path = Path(sys.argv[1]).resolve()
    if not path.exists():
        print(f"not-found: {path}")
        return 2

    try:
        with path.open("r", encoding="utf-8") as f:
            notebook = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"json-error: {exc}")
        return 3

    required_keys = {"cells", "metadata", "nbformat", "nbformat_minor"}
    missing = sorted(required_keys - notebook.keys())
    if missing:
        print(f"missing-keys: {missing}")
        return 4

    if not isinstance(notebook.get("cells"), list):
        print("invalid-cells: expected list")
        return 5

    print("notebook-json-ok")
    print(f"path={path}")
    print(f"cells={len(notebook['cells'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
