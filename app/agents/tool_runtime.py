import importlib.util
import inspect
import json
import sys
from types import UnionType
from pathlib import Path
from typing import Any, Union
from typing import get_args, get_origin

from app.agents.skills import project_root
from app.agents.types import ToolDefinition


class ToolRuntimeAdapter:
    def __init__(self, builtin_dir: Path | None = None):
        root = project_root()
        self.builtin_dir = builtin_dir or root / "app" / "agents" / "tool_packages"

    def load_tool_definitions(self) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []
        if not self.builtin_dir.exists():
            return definitions
        for package_dir in sorted(path for path in self.builtin_dir.iterdir() if path.is_dir()):
            manifest = self._load_manifest(package_dir)
            if not manifest:
                continue
            for raw_tool in manifest.get("tools", []):
                if isinstance(raw_tool, dict):
                    definitions.append(self._build_tool_definition(package_dir, manifest, raw_tool))
        return definitions

    def _load_manifest(self, package_dir: Path) -> dict[str, Any] | None:
        manifest_path = package_dir / "tool.json"
        if not manifest_path.exists():
            return None
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid tool manifest for {package_dir.name}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Tool manifest must be an object: {manifest_path}")
        return data

    def _build_tool_definition(
        self,
        package_dir: Path,
        manifest: dict[str, Any],
        raw_tool: dict[str, Any],
    ) -> ToolDefinition:
        name = str(raw_tool.get("name") or "").strip()
        if not name:
            raise ValueError(f"Tool package {package_dir.name} has a tool without a valid name")

        module_path = self._resolve_module_path(package_dir, str(raw_tool.get("module") or manifest.get("module") or ""))
        handler_name = str(raw_tool.get("handler") or "").strip()
        if not handler_name:
            raise ValueError(f"Tool package {package_dir.name} tool {name} is missing handler")

        risk_level = str(raw_tool.get("risk_level") or "medium")
        if risk_level not in {"low", "medium", "high"}:
            raise ValueError(f"Invalid risk_level for tool {name}: {risk_level}")

        input_schema = raw_tool.get("parameters")
        if not isinstance(input_schema, dict):
            input_schema = _infer_input_schema(module_path, handler_name)

        return ToolDefinition(
            name=name,
            description=str(raw_tool.get("description") or f"Tool from package {package_dir.name}"),
            risk_level=risk_level,
            parallel_safe=bool(raw_tool.get("parallel_safe", False)),
            handler=self._module_handler(
                package_dir=package_dir,
                module_path=module_path,
                handler_name=handler_name,
            ),
            input_schema=input_schema,
        )

    def _resolve_module_path(self, package_dir: Path, module: str) -> Path:
        module_path = (package_dir / module).resolve()
        package_root = package_dir.resolve()
        if package_root != module_path and package_root not in module_path.parents:
            raise ValueError(f"Tool module escapes package directory: {module}")
        if not module_path.exists() or not module_path.is_file():
            raise ValueError(f"Tool module not found: {module_path}")
        if module_path.suffix != ".py":
            raise ValueError(f"Only Python tool modules are supported: {module_path}")
        return module_path

    def _module_handler(self, package_dir: Path, module_path: Path, handler_name: str):
        def handler(arguments: dict[str, Any]) -> dict[str, Any]:
            module = _load_module(module_path, f"fastapi_study_tool_{package_dir.name}_{module_path.stem}")
            target = getattr(module, handler_name, None)
            if target is None or not callable(target):
                raise AttributeError(f"Handler not found: {handler_name} in {module_path}")
            normalized_arguments = _normalize_tool_arguments(arguments)
            result = target(**normalized_arguments)
            if not isinstance(result, dict):
                raise TypeError(f"Tool handler must return dict: {module_path}::{handler_name}")
            return result

        return handler


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    module_dir = str(path.parent)
    inserted = False
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        inserted = True
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(module_dir)
    return module


def _normalize_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        return {}
    normalized = dict(arguments)
    alias_pairs = [
        ("cmd", "command"),
        ("argv", "args"),
        ("script", "code"),
        ("body", "json_body"),
        ("data", "json_body"),
        ("dir", "cwd"),
        ("workdir", "cwd"),
        ("timeout", "timeout_seconds"),
    ]
    for old_name, new_name in alias_pairs:
        if old_name in normalized and new_name not in normalized:
            normalized[new_name] = normalized.pop(old_name)
    return normalized


def _infer_input_schema(module_path: Path, handler_name: str) -> dict[str, Any]:
    module = _load_module(module_path, f"fastapi_study_tool_schema_{module_path.stem}_{handler_name}")
    target = getattr(module, handler_name, None)
    if target is None or not callable(target):
        raise AttributeError(f"Handler not found: {handler_name} in {module_path}")

    signature = inspect.signature(target)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
            continue
        properties[parameter.name] = _annotation_to_json_schema(parameter.annotation)
        if parameter.default is inspect._empty:
            required.append(parameter.name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _annotation_to_json_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect._empty:
        return {}

    origin = get_origin(annotation)
    if origin is None:
        if annotation is str:
            return {"type": "string"}
        if annotation is int:
            return {"type": "integer"}
        if annotation is float:
            return {"type": "number"}
        if annotation is bool:
            return {"type": "boolean"}
        if annotation in {dict, Any}:
            return {"type": "object"}
        if annotation is list:
            return {"type": "array"}
        return {}

    args = [item for item in get_args(annotation) if item is not type(None)]
    if origin in {list, tuple, set}:
        item_schema = _annotation_to_json_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    if origin is dict:
        return {"type": "object"}
    if origin is UnionType:  # pragma: no cover
        return _annotation_to_json_schema(args[0]) if args else {}
    if origin is Union:
        return _annotation_to_json_schema(args[0]) if args else {}
    return {}
