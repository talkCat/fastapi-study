import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from app.agents.skills import SkillRegistry
from app.agents.types import SkillDescriptor, ToolDefinition

RiskLevel = Literal["low", "medium", "high"]


class SkillRuntimeAdapter:
    """Adapts skill scripts into managed runtime tools.

    `agents/tools.json` is supported as the preferred precise contract, but it
    is optional. Generic tools can list and execute Python scripts from a skill
    directory with Harness permission checks.
    """

    def __init__(self, skill_registry: SkillRegistry | None = None):
        self.skill_registry = skill_registry or SkillRegistry()

    def load_tool_definitions(self) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []
        for skill in self.skill_registry.list_skills():
            manifest = self._load_tool_manifest(skill)
            for raw_tool in manifest:
                definitions.append(self._build_tool_definition(skill, raw_tool))
        return definitions

    def resolve_plan(
        self,
        skill_name: str,
        message: str,
        available_tools: list[str] | None = None,
        selected_skills: list[str] | None = None,
    ) -> dict[str, Any] | None:
        skill = self._get_skill_or_raise(skill_name)
        resolver = skill.contract.routing.resolver
        if resolver is None:
            return None

        script_path = self._resolve_skill_script(skill, resolver.script)
        payload = {
            "message": message,
            "skill": skill.name,
            "available_tools": available_tools or [],
            "selected_skills": selected_skills or [],
            "preferred_tools": list(skill.contract.routing.preferred_tools),
            "trigger_keywords": list(skill.contract.trigger.keywords),
        }
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(skill.path),
            capture_output=True,
            text=True,
            timeout=resolver.timeout_seconds,
            check=False,
            input=json.dumps(payload, ensure_ascii=False),
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(
                f"Skill resolver {skill.name}/{resolver.script} failed with exit code {completed.returncode}: {stderr or stdout}"
            )
        if not stdout:
            return None
        parsed = json.loads(stdout)
        return parsed if isinstance(parsed, dict) else None

    def list_python_scripts(self, skill_name: str) -> dict[str, Any]:
        skill = self._get_skill_or_raise(skill_name)
        scripts = []
        for path in sorted(skill.path.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if any(part.startswith(".") for part in path.relative_to(skill.path).parts):
                continue
            scripts.append(
                {
                    "path": str(path.relative_to(skill.path)),
                    "size_bytes": path.stat().st_size,
                }
            )
        return {
            "skill": skill.name,
            "skill_path": str(skill.path),
            "scripts": scripts,
            "count": len(scripts),
        }

    def run_python_script(
        self,
        skill_name: str,
        script: str,
        args: list[Any] | None = None,
        timeout_seconds: int = 20,
        output_format: str = "text",
        max_output_chars: int = 20000,
    ) -> dict[str, Any]:
        skill = self._get_skill_or_raise(skill_name)
        script_path = self._resolve_skill_script(skill, script)
        if output_format not in {"text", "json"}:
            raise ValueError("output_format must be text or json")

        command = [sys.executable, str(script_path)]
        command.extend(str(item) for item in (args or []))
        completed = subprocess.run(
            command,
            cwd=str(skill.path),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(
                f"Skill script {skill.name}/{script} failed with exit code {completed.returncode}: {stderr or stdout}"
            )

        truncated = len(stdout) > max_output_chars
        stdout_preview = stdout[:max_output_chars]
        result: dict[str, Any] = {
            "skill": skill.name,
            "script": str(script_path.relative_to(skill.path)),
            "exit_code": completed.returncode,
            "stderr": stderr,
            "truncated": truncated,
        }
        if output_format == "json":
            result["json"] = json.loads(stdout) if stdout else None
        else:
            result["stdout"] = stdout_preview
        return result

    def _get_skill_or_raise(self, skill_name: str) -> SkillDescriptor:
        skill = self.skill_registry.get_skill(skill_name)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_name}")
        return skill

    def _load_manifest(self, skill: SkillDescriptor) -> dict[str, Any] | None:
        manifest_path = skill.path / "agents" / "tools.json"
        if not manifest_path.exists():
            return None
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid tools manifest for skill {skill.name}: {exc}") from exc

    def _load_tool_manifest(self, skill: SkillDescriptor) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        manifest = self._load_manifest(skill)
        if manifest and isinstance(manifest.get("tools"), list):
            items.extend(tool for tool in manifest["tools"] if isinstance(tool, dict))

        contract_tools = skill.contract.raw.get("tools")
        if isinstance(contract_tools, list):
            items.extend(tool for tool in contract_tools if isinstance(tool, dict))
        return items

    def _build_tool_definition(self, skill: SkillDescriptor, raw_tool: dict[str, Any]) -> ToolDefinition:
        local_name = _safe_tool_part(str(raw_tool.get("name") or ""))
        if not local_name:
            raise ValueError(f"Skill {skill.name} has a tool without a valid name")

        script = str(raw_tool.get("script") or "")
        script_path = self._resolve_skill_script(skill, script)

        risk_level = raw_tool.get("risk_level") or "medium"
        if risk_level not in {"low", "medium", "high"}:
            raise ValueError(f"Invalid risk_level for {skill.name}.{local_name}: {risk_level}")

        output_format = raw_tool.get("output_format") or "text"
        if output_format not in {"text", "json"}:
            raise ValueError(f"Invalid output_format for {skill.name}.{local_name}: {output_format}")

        timeout_seconds = int(raw_tool.get("timeout_seconds") or 20)
        argument_specs = raw_tool.get("arguments") or []
        if not isinstance(argument_specs, list):
            raise ValueError(f"arguments must be a list for {skill.name}.{local_name}")

        tool_name = f"skill.{skill.name}.{local_name}"
        return ToolDefinition(
            name=tool_name,
            description=str(raw_tool.get("description") or f"Run {local_name} from skill {skill.name}"),
            risk_level=risk_level,
            parallel_safe=bool(raw_tool.get("parallel_safe", False)),
            handler=self._script_handler(
                skill=skill,
                tool_name=tool_name,
                script_path=script_path,
                argument_specs=argument_specs,
                timeout_seconds=timeout_seconds,
                output_format=output_format,
            ),
            input_schema=_argument_specs_to_schema(argument_specs),
        )

    def _resolve_skill_script(self, skill: SkillDescriptor, script: str) -> Path:
        script_path = (skill.path / script).resolve()
        skill_root = skill.path.resolve()
        if skill_root != script_path and skill_root not in script_path.parents:
            raise ValueError(f"Skill script escapes skill directory: {script}")
        if "__pycache__" in script_path.parts:
            raise ValueError("Cannot execute __pycache__ files")
        if not script_path.exists() or not script_path.is_file():
            raise ValueError(f"Skill script not found: {script_path}")
        if script_path.suffix != ".py":
            raise ValueError(f"Only Python skill scripts are supported: {script_path}")
        return script_path

    def _script_handler(
        self,
        skill: SkillDescriptor,
        tool_name: str,
        script_path: Path,
        argument_specs: list[dict[str, Any]],
        timeout_seconds: int,
        output_format: str,
    ):
        def handler(arguments: dict[str, Any]) -> dict[str, Any]:
            command = [sys.executable, str(script_path)]
            for spec in argument_specs:
                name = str(spec.get("name") or "")
                if not name:
                    raise ValueError(f"Invalid argument spec in {tool_name}")
                required = bool(spec.get("required", False))
                has_value = name in arguments and arguments[name] is not None
                if required and not has_value:
                    raise ValueError(f"Missing required argument: {name}")
                if not has_value:
                    continue

                value = arguments[name]
                flag = spec.get("flag")
                if flag:
                    if isinstance(value, bool):
                        if value:
                            command.append(str(flag))
                    elif isinstance(value, list):
                        for item in value:
                            command.extend([str(flag), str(item)])
                    else:
                        command.extend([str(flag), str(value)])
                else:
                    if isinstance(value, list):
                        command.extend(str(item) for item in value)
                    else:
                        command.append(str(value))

            completed = subprocess.run(
                command,
                cwd=str(skill.path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
            if completed.returncode != 0:
                raise RuntimeError(
                    f"Skill tool {tool_name} failed with exit code {completed.returncode}: {stderr or stdout}"
                )

            result: dict[str, Any] = {
                "skill": skill.name,
                "tool": tool_name,
                "exit_code": completed.returncode,
                "stderr": stderr,
            }
            if output_format == "json":
                result["json"] = json.loads(stdout) if stdout else None
            else:
                result["stdout"] = stdout
            return result

        return handler


def _safe_tool_part(value: str) -> str:
    return value.strip().replace("_", "-").lower()


def _argument_specs_to_schema(argument_specs: list[dict[str, Any]]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for spec in argument_specs:
        name = str(spec.get("name") or "").strip()
        if not name:
            continue
        schema: dict[str, Any] = {"type": _json_type_name(str(spec.get("type") or "string"))}
        description = str(spec.get("description") or "").strip()
        if description:
            schema["description"] = description
        enum = spec.get("enum")
        if isinstance(enum, list) and enum:
            schema["enum"] = enum
        if schema["type"] == "array":
            schema["items"] = {"type": _json_type_name(str(spec.get("items_type") or "string"))}
        properties[name] = schema
        if bool(spec.get("required", False)):
            required.append(name)

    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def _json_type_name(value: str) -> str:
    normalized = value.strip().lower()
    return {
        "str": "string",
        "string": "string",
        "int": "integer",
        "integer": "integer",
        "float": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "dict": "object",
        "object": "object",
        "list": "array",
        "array": "array",
    }.get(normalized, "string")
