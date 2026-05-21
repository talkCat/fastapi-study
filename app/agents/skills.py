import json
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from app.agents.types import SkillContract, SkillDescriptor, SkillResolver, SkillRouting, SkillTrigger


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    raw_frontmatter = "\n".join(lines[1:end_index])
    try:
        metadata = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid SKILL frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError("SKILL frontmatter must be a mapping")

    body = "\n".join(lines[end_index + 1:]).strip()
    return metadata, body


def _read_default_prompt(skill_dir: Path) -> str | None:
    config_path = skill_dir / "agents" / "openai.yaml"
    if not config_path.exists():
        return None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("default_prompt")
    return str(value).strip() if value else None


def _safe_skill_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    if not normalized:
        raise ValueError("Skill name is empty after normalization")
    return normalized


class SkillRegistry:
    def __init__(
        self,
        builtin_dir: Path | None = None,
        installed_dir: Path | None = None,
    ):
        root = project_root()
        self.builtin_dir = builtin_dir or root / ".agents" / "skills"
        self.installed_dir = installed_dir or root / "app" / "agents" / "installed_skills"
        self.installed_dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> list[SkillDescriptor]:
        skills: dict[str, SkillDescriptor] = {}
        for source, base_dir in (("builtin", self.builtin_dir), ("installed", self.installed_dir)):
            if not base_dir.exists():
                continue
            for skill_dir in sorted(path for path in base_dir.iterdir() if path.is_dir()):
                skill = self.load_skill(skill_dir, source=source)
                if skill:
                    skills[skill.name] = skill
        return sorted(skills.values(), key=lambda item: item.name)

    def get_skill(self, name: str) -> SkillDescriptor | None:
        normalized = _safe_skill_name(name)
        for skill in self.list_skills():
            if skill.name == normalized:
                return skill
        return None

    def load_skill(self, skill_dir: Path, source: str) -> SkillDescriptor | None:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None

        text = skill_file.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        name = _safe_skill_name(str(metadata.get("name") or skill_dir.name))
        description = str(metadata.get("description") or "No description")
        contract = _load_skill_contract(skill_dir, metadata, body)
        return SkillDescriptor(
            name=name,
            description=description,
            path=skill_dir,
            source=source,
            instructions=body,
            default_prompt=_read_default_prompt(skill_dir),
            contract=contract,
        )

    def install_unpacked_skill(self, source_path: str, overwrite: bool = False) -> SkillDescriptor:
        source_dir = Path(source_path).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError("Skill source_path must be an existing directory")
        if not (source_dir / "SKILL.md").exists():
            raise ValueError("Skill package must contain SKILL.md")

        loaded = self.load_skill(source_dir, source="source")
        if loaded is None:
            raise ValueError("Invalid skill package")

        target_dir = (self.installed_dir / loaded.name).resolve()
        installed_root = self.installed_dir.resolve()
        if installed_root not in target_dir.parents:
            raise ValueError("Invalid skill install target")

        if target_dir.exists():
            if not overwrite:
                raise FileExistsError(f"Skill already installed: {loaded.name}")
            shutil.rmtree(target_dir)

        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".ipynb_checkpoints")
        shutil.copytree(source_dir, target_dir, ignore=ignore)
        installed = self.load_skill(target_dir, source="installed")
        if installed is None:
            raise ValueError("Installed skill cannot be loaded")
        return installed

    def select_skills(self, message: str, requested_names: list[str] | None = None) -> list[SkillDescriptor]:
        available = self.list_skills()
        if requested_names:
            selected = []
            for name in requested_names:
                skill = self.get_skill(name)
                if skill and skill not in selected:
                    selected.append(skill)
            return selected

        lowered = message.lower()
        scored: list[tuple[int, SkillDescriptor]] = []
        for skill in available:
            score = _score_skill_match(skill, message, lowered)
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda item: (-item[0], item[1].name))
        if scored:
            return [skill for _, skill in scored[:4]]

        # If the local skill set is small, pass the available skills through so the
        # planner can still use their instructions even when keyword heuristics miss.
        return available[:4]


def _load_skill_contract(skill_dir: Path, frontmatter: dict[str, Any], body: str) -> SkillContract:
    manifest_path = skill_dir / "agents" / "skill.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid skill manifest for {skill_dir.name}: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ValueError(f"Skill manifest must be a JSON object: {manifest_path}")

    merged = _deep_merge_dict(_contract_from_frontmatter(frontmatter), manifest)
    trigger_data = merged.get("trigger") or {}
    routing_data = merged.get("routing") or {}
    metadata = merged.get("metadata") if isinstance(merged.get("metadata"), dict) else {}

    keywords = _unique_strings(trigger_data.get("keywords"))
    if not keywords:
        keywords = _infer_keywords(frontmatter, body)

    inferred_routing = _infer_routing(skill_dir=skill_dir, frontmatter=frontmatter, body=body)
    preferred_tools = _unique_strings(routing_data.get("preferred_tools"))
    if not preferred_tools:
        preferred_tools = inferred_routing["preferred_tools"]

    planner_hint = str(routing_data.get("planner_hint")).strip() if routing_data.get("planner_hint") else None
    if not planner_hint:
        planner_hint = inferred_routing["planner_hint"]

    answer_hint = str(routing_data.get("answer_hint")).strip() if routing_data.get("answer_hint") else None
    if not answer_hint:
        answer_hint = inferred_routing["answer_hint"]

    resolver_data = routing_data.get("resolver") if isinstance(routing_data.get("resolver"), dict) else None
    resolver = None
    if resolver_data and resolver_data.get("script"):
        resolver = SkillResolver(
            script=str(resolver_data["script"]),
            timeout_seconds=int(resolver_data.get("timeout_seconds") or 10),
            output_format="json",
        )

    return SkillContract(
        schema_version=str(merged.get("schema_version") or "1.0"),
        category=str(merged.get("category")).strip() if merged.get("category") else None,
        tags=_unique_strings(merged.get("tags")),
        trigger=SkillTrigger(
            keywords=keywords,
            patterns=_unique_strings(trigger_data.get("patterns")),
            examples=_unique_strings(trigger_data.get("examples")),
        ),
        routing=SkillRouting(
            preferred_tools=preferred_tools,
            planner_hint=planner_hint,
            answer_hint=answer_hint,
            resolver=resolver,
        ),
        metadata=metadata,
        raw=merged,
    )


def _contract_from_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "schema_version": str(frontmatter.get("schema_version") or "1.0"),
        "category": frontmatter.get("category"),
        "tags": frontmatter.get("tags"),
        "metadata": frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {},
    }

    trigger = frontmatter.get("trigger") if isinstance(frontmatter.get("trigger"), dict) else {}
    if not trigger and isinstance(frontmatter.get("triggers"), dict):
        trigger = frontmatter.get("triggers")
    contract["trigger"] = {
        "keywords": trigger.get("keywords") or frontmatter.get("keywords"),
        "patterns": trigger.get("patterns") or frontmatter.get("patterns"),
        "examples": trigger.get("examples") or frontmatter.get("examples"),
    }

    routing = frontmatter.get("routing") if isinstance(frontmatter.get("routing"), dict) else {}
    contract["routing"] = {
        "preferred_tools": routing.get("preferred_tools") or frontmatter.get("preferred_tools"),
        "planner_hint": routing.get("planner_hint") or frontmatter.get("planner_hint"),
        "answer_hint": routing.get("answer_hint") or frontmatter.get("answer_hint"),
    }
    return contract


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(current, value)
        else:
            merged[key] = value
    return merged


def _unique_strings(value: Any) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
    return normalized


def _infer_keywords(frontmatter: dict[str, Any], body: str) -> list[str]:
    candidates: list[str] = []
    for raw in [frontmatter.get("name"), frontmatter.get("description"), body]:
        if not raw:
            continue
        for token in re.split(r"[\s,;:(){}\[\]/|]+", str(raw)):
            cleaned = token.strip().strip("#*-_")
            if len(cleaned) < 2:
                continue
            if cleaned.lower() in {"skill", "workflow", "overview", "style", "scripts", "related", "tools"}:
                continue
            candidates.append(cleaned)
    return _unique_strings(candidates[:24])


def _infer_routing(skill_dir: Path, frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
    text = "\n".join(
        str(value)
        for value in (
            frontmatter.get("name") or "",
            frontmatter.get("description") or "",
            frontmatter.get("metadata") or "",
            body or "",
        )
    ).lower()
    preferred_tools: list[str] = []
    hint_parts: list[str] = []
    answer_parts: list[str] = []

    if _contains_shell_examples(text):
        preferred_tools.extend(["shell.exec", "http.get"])
        hint_parts.append("SKILL.md contains curl or shell command examples; prefer shell.exec for faithful command reproduction.")
        answer_parts.append("If shell execution fails, explain the failing command and suggest a simpler retry.")

    if _contains_http_examples(text):
        preferred_tools.extend(["http.get", "http.post", "web_fetch"])
        hint_parts.append("SKILL.md references HTTP endpoints; prefer http.get or http.post when a direct request is clearer than shell.exec.")

    if _contains_search_examples(text):
        preferred_tools.extend(["web.search", "web_fetch"])
        hint_parts.append("SKILL.md references search or news lookup; prefer web.search first, then web_fetch for a specific result URL.")

    if _skill_has_python_scripts(skill_dir):
        preferred_tools.extend(["skill.scripts.list", "skill.python.run"])
        hint_parts.append("This skill package contains Python scripts; inspect scripts with skill.scripts.list before running a specific script.")

    if "```python" in text or re.search(r"\bpython(?:3)?\b", text):
        preferred_tools.append("python.exec")
        hint_parts.append("SKILL.md contains Python usage examples; python.exec can be used for small deterministic transformations.")

    if _contains_file_workflow(text):
        preferred_tools.extend(["fs.read_text", "fs.write_text", "fs.write_json", "fs.list_dir"])
        hint_parts.append("SKILL.md mentions local files; use filesystem tools instead of inventing inline file content.")

    return {
        "preferred_tools": _unique_strings(preferred_tools),
        "planner_hint": " ".join(hint_parts) if hint_parts else None,
        "answer_hint": " ".join(answer_parts) if answer_parts else None,
    }


def _contains_shell_examples(text: str) -> bool:
    return any(token in text for token in ["curl ", "bash ", "sh ", "terminal", "command line"])


def _contains_http_examples(text: str) -> bool:
    return "http://" in text or "https://" in text or "api" in text


def _contains_search_examples(text: str) -> bool:
    return any(token in text for token in ["search", "news", "bing", "duckduckgo", "google", "baidu", "sogou"])


def _contains_file_workflow(text: str) -> bool:
    return any(token in text for token in ["json file", "yaml", "toml", "config", "read file", "write file", ".md", ".txt"])


def _skill_has_python_scripts(skill_dir: Path) -> bool:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists() or not scripts_dir.is_dir():
        return False
    return any(path.is_file() and path.suffix == ".py" for path in scripts_dir.rglob("*.py"))


def _score_skill_match(skill: SkillDescriptor, message: str, lowered: str) -> int:
    score = 0
    seen_hits: set[str] = set()

    if skill.name in lowered:
        score += 120

    corpus = [
        skill.name,
        skill.description,
        skill.contract.category or "",
        *skill.contract.tags,
    ]
    for token in _unique_strings(corpus):
        token_key = token.lower()
        if len(token_key) < 2 or token_key in seen_hits:
            continue
        if token_key in lowered:
            score += 8
            seen_hits.add(token_key)

    for keyword in skill.contract.trigger.keywords:
        token_key = keyword.lower()
        if token_key in seen_hits:
            continue
        if token_key in lowered:
            score += 24
            seen_hits.add(token_key)

    for example in skill.contract.trigger.examples:
        sample = example.lower().strip()
        if sample and sample in lowered:
            score += 16

    for pattern in skill.contract.trigger.patterns:
        try:
            if re.search(pattern, message, flags=re.IGNORECASE):
                score += 28
        except re.error:
            continue

    if skill.contract.routing.preferred_tools:
        for tool_name in skill.contract.routing.preferred_tools:
            short_name = tool_name.split(".")[-1].lower()
            if short_name and short_name in lowered:
                score += 6

    return score
