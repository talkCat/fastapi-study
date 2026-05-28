from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Literal
from uuid import uuid4

from app.agents.skills import project_root
from app.agents.types import PermissionDecision


SubAgentRole = Literal["research", "implementation", "verification"]


@dataclass
class SubAgentTask:
    task_id: str
    parent_run_id: str
    role: SubAgentRole
    objective: str
    user_message: str
    relevant_history: list[dict[str, str]] = field(default_factory=list)
    selected_skill_summaries: list[dict] = field(default_factory=list)
    prior_observations: list[dict] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    max_steps: int = 2

    @classmethod
    def create(
        cls,
        parent_run_id: str,
        role: str,
        objective: str,
        user_message: str,
        relevant_history: list[dict[str, str]] | None = None,
        selected_skill_summaries: list[dict] | None = None,
        prior_observations: list[dict] | None = None,
        allowed_tools: list[str] | None = None,
        allowed_paths: list[str] | None = None,
        constraints: list[str] | None = None,
        max_steps: int = 2,
    ) -> "SubAgentTask":
        normalized_role = role if role in {"research", "implementation", "verification"} else "research"
        return cls(
            task_id=f"{normalized_role}-{uuid4().hex[:8]}",
            parent_run_id=parent_run_id,
            role=normalized_role,  # type: ignore[arg-type]
            objective=objective,
            user_message=user_message,
            relevant_history=relevant_history or [],
            selected_skill_summaries=selected_skill_summaries or [],
            prior_observations=prior_observations or [],
            allowed_tools=allowed_tools or [],
            allowed_paths=allowed_paths or [],
            constraints=constraints or [],
            max_steps=max_steps,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubAgentResult:
    task_id: str
    parent_run_id: str
    role: str
    ok: bool
    summary: str
    findings: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    proposed_next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SynthesisResult:
    accepted_findings: list[str] = field(default_factory=list)
    rejected_findings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    next_action: Literal["answer", "tool", "delegate", "ask_user"] = "answer"
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class SubAgentPolicy:
    """Small policy gate for subagent delegation.

    The first learning version only allows read-only research by default.
    Implementation work is intentionally gated until write scopes and approval
    are introduced.
    """

    READ_ONLY_TOOLS = {"repo.search", "repo.read", "test.run"}
    IMPLEMENTATION_TOOLS = {"repo.write"}

    def __init__(self, root: Path | None = None):
        self.root = (root or project_root()).resolve()

    def decide(self, task: SubAgentTask) -> PermissionDecision:
        if task.role == "research":
            if not self._paths_are_safe(task.allowed_paths):
                return "deny"
            if not set(task.allowed_tools or {"repo.search", "repo.read"}).issubset(self.READ_ONLY_TOOLS):
                return "deny"
            return "allow"
        if task.role == "verification":
            if not self._paths_are_safe(task.allowed_paths):
                return "deny"
            if not set(task.allowed_tools or self.READ_ONLY_TOOLS).issubset(self.READ_ONLY_TOOLS):
                return "deny"
            return "allow"
        if task.role == "implementation":
            if not self._paths_are_safe(task.allowed_paths):
                return "deny"
            if not task.allowed_paths:
                return "deny"
            if not set(task.allowed_tools or self.IMPLEMENTATION_TOOLS).issubset(self.IMPLEMENTATION_TOOLS):
                return "deny"
            return "ask"
        return "deny"

    def _paths_are_safe(self, paths: list[str]) -> bool:
        for raw_path in paths:
            if not raw_path:
                continue
            try:
                resolved = (self.root / raw_path).resolve()
            except OSError:
                return False
            if resolved != self.root and self.root not in resolved.parents:
                return False
        return True


class ResearchSubAgent:
    """Read-only research worker used by the coordinator.

    This worker deliberately returns a compact report instead of mutating the
    parent run. It inspects only coordinator-approved paths.
    """

    def __init__(self, root: Path | None = None):
        self.root = (root or project_root()).resolve()

    def run(self, task: SubAgentTask) -> SubAgentResult:
        findings: list[str] = []
        evidence: list[dict] = []
        risks: list[str] = []
        missing_evidence: list[str] = []

        paths = task.allowed_paths or ["app/agents", "tests"]
        for raw_path in paths[:8]:
            resolved = self._resolve_allowed_path(raw_path)
            if resolved is None:
                risks.append(f"跳过越界路径: {raw_path}")
                continue
            if not resolved.exists():
                missing_evidence.append(f"路径不存在: {raw_path}")
                continue
            if resolved.is_file():
                evidence.append(self._file_evidence(raw_path, resolved, task.objective))
                findings.append(f"确认文件存在: {raw_path}")
                continue
            entries = sorted(item.name for item in resolved.iterdir() if not item.name.startswith("__pycache__"))
            evidence.append(
                {
                    "type": "directory",
                    "path": raw_path,
                    "entries": entries[:12],
                    "entry_count": len(entries),
                }
            )
            findings.append(f"确认目录存在: {raw_path}，包含 {len(entries)} 个条目")

        if task.prior_observations:
            findings.append(f"收到 {len(task.prior_observations)} 条上游观察，可供 coordinator 综合")
        if task.selected_skill_summaries:
            findings.append(f"当前已选中 {len(task.selected_skill_summaries)} 个 Skill 摘要")

        ok = not risks
        summary = (
            f"Research subagent 完成只读调查：{task.objective}"
            if ok
            else f"Research subagent 完成调查但发现边界风险：{task.objective}"
        )
        return SubAgentResult(
            task_id=task.task_id,
            parent_run_id=task.parent_run_id,
            role=task.role,
            ok=ok,
            summary=summary,
            findings=findings,
            evidence=evidence,
            risks=risks,
            missing_evidence=missing_evidence,
            proposed_next_actions=["coordinator 综合 research 结果后决定下一步"],
        )

    def _resolve_allowed_path(self, raw_path: str) -> Path | None:
        try:
            resolved = (self.root / raw_path).resolve()
        except OSError:
            return None
        if resolved != self.root and self.root not in resolved.parents:
            return None
        return resolved

    def _file_evidence(self, raw_path: str, resolved: Path, objective: str) -> dict:
        line_count = None
        preview = ""
        matches: list[dict] = []
        related_symbols: list[dict] = []
        try:
            text = resolved.read_text(encoding="utf-8")
            lines = text.splitlines()
            line_count = len(lines)
            preview = text[:800]
            terms = _objective_terms(objective)
            matches = _matching_lines(lines, terms)
            related_symbols = _matching_symbols(lines, terms)
            for symbol in _related_symbols(lines, matches):
                if symbol not in related_symbols:
                    related_symbols.append(symbol)
        except UnicodeDecodeError:
            preview = "<binary or non-utf8 file>"
        except OSError as exc:
            preview = f"<read failed: {exc}>"
        return {
            "type": "file",
            "path": raw_path,
            "line_count": line_count,
            "preview": preview,
            "matches": matches,
            "related_symbols": related_symbols,
        }


class VerificationSubAgent:
    """Independent checker for coordinator-visible evidence."""

    def __init__(self, root: Path | None = None):
        self.root = (root or project_root()).resolve()

    def run(self, task: SubAgentTask) -> SubAgentResult:
        findings: list[str] = []
        evidence: list[dict] = []
        risks: list[str] = []
        missing_evidence: list[str] = []

        observed_results = [
            step.get("subagent_result")
            for step in task.prior_observations
            if isinstance(step, dict) and isinstance(step.get("subagent_result"), dict)
        ]
        tool_results = [
            step.get("tool_result")
            for step in task.prior_observations
            if isinstance(step, dict) and isinstance(step.get("tool_result"), dict)
        ]

        if observed_results:
            findings.append(f"发现 {len(observed_results)} 个 subagent 结果，可用于独立验证")
            for result in observed_results:
                role = str(result.get("role") or "")
                ok = bool(result.get("ok"))
                changed_files = result.get("changed_files") if isinstance(result.get("changed_files"), list) else []
                evidence.append(
                    {
                        "type": "subagent_result",
                        "role": role,
                        "ok": ok,
                        "changed_files": changed_files,
                        "summary": result.get("summary"),
                    }
                )
                if not ok:
                    risks.append(f"{role or 'subagent'} result was not ok")
                for changed_file in changed_files:
                    self._verify_changed_file(str(changed_file), evidence, missing_evidence, risks)
        else:
            missing_evidence.append("没有可验证的 subagent_result")

        if tool_results:
            findings.append(f"发现 {len(tool_results)} 个 tool_result")
            for result in tool_results:
                evidence.append(
                    {
                        "type": "tool_result",
                        "tool_name": result.get("tool_name"),
                        "ok": result.get("ok"),
                        "error": result.get("error"),
                    }
                )
                if not result.get("ok"):
                    risks.append(f"工具执行失败: {result.get('tool_name')}")

        ok = not risks and not missing_evidence
        return SubAgentResult(
            task_id=task.task_id,
            parent_run_id=task.parent_run_id,
            role=task.role,
            ok=ok,
            summary="Verification subagent 完成独立验证" if ok else "Verification subagent 发现证据缺口或风险",
            findings=findings,
            evidence=evidence,
            risks=risks,
            missing_evidence=missing_evidence,
            proposed_next_actions=[] if ok else ["补充缺失证据后再声称完成"],
        )

    def _verify_changed_file(
        self,
        raw_path: str,
        evidence: list[dict],
        missing_evidence: list[str],
        risks: list[str],
    ) -> None:
        resolved = self._resolve_allowed_path(raw_path)
        if resolved is None:
            risks.append(f"变更文件越界: {raw_path}")
            return
        if not resolved.exists():
            missing_evidence.append(f"变更文件不存在: {raw_path}")
            return
        try:
            text = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        except OSError as exc:
            risks.append(f"读取变更文件失败: {raw_path}: {exc}")
            return
        evidence.append(
            {
                "type": "changed_file",
                "path": raw_path,
                "line_count": len(text.splitlines()),
                "size_bytes": resolved.stat().st_size,
            }
        )

    def _resolve_allowed_path(self, raw_path: str) -> Path | None:
        try:
            resolved = (self.root / raw_path).resolve()
        except OSError:
            return None
        if resolved != self.root and self.root not in resolved.parents:
            return None
        return resolved


class ImplementationSubAgent:
    """Controlled implementation worker.

    The first implementation version accepts explicit file payloads from the
    coordinator plan. It does not invent file edits from natural language.
    """

    def __init__(self, root: Path | None = None):
        self.root = (root or project_root()).resolve()

    def run(self, task: SubAgentTask, files: list[dict] | None = None) -> SubAgentResult:
        findings: list[str] = []
        evidence: list[dict] = []
        changed_files: list[str] = []
        risks: list[str] = []
        missing_evidence: list[str] = []

        payload_files = files or []
        if not payload_files:
            missing_evidence.append("implementation plan 未提供 files 写入清单")

        allowed_roots = self._allowed_roots(task.allowed_paths)
        if not allowed_roots:
            risks.append("implementation task 缺少有效 allowed_paths")

        for item in payload_files[:8]:
            path = str(item.get("path") or "")
            content = item.get("content")
            if not path or not isinstance(content, str):
                risks.append("files 条目必须包含 path 和 string content")
                continue
            resolved = self._resolve_allowed_path(path)
            if resolved is None:
                risks.append(f"拒绝越界写入: {path}")
                continue
            if not self._is_under_allowed_roots(resolved, allowed_roots):
                risks.append(f"拒绝写入未授权路径: {path}")
                continue
            try:
                resolved.parent.mkdir(parents=True, exist_ok=True)
                resolved.write_text(content, encoding="utf-8")
            except OSError as exc:
                risks.append(f"写入失败: {path}: {exc}")
                continue
            changed_files.append(path)
            findings.append(f"已写入文件: {path}")
            evidence.append(
                {
                    "type": "changed_file",
                    "path": path,
                    "line_count": len(content.splitlines()),
                    "size_bytes": len(content.encode("utf-8")),
                }
            )

        ok = not risks and not missing_evidence and bool(changed_files)
        return SubAgentResult(
            task_id=task.task_id,
            parent_run_id=task.parent_run_id,
            role=task.role,
            ok=ok,
            summary="Implementation subagent 完成受控写入" if ok else "Implementation subagent 未完成受控写入",
            findings=findings,
            evidence=evidence,
            changed_files=changed_files,
            risks=risks,
            missing_evidence=missing_evidence,
            proposed_next_actions=["必须进入 independent verification"],
        )

    def _allowed_roots(self, paths: list[str]) -> list[Path]:
        roots: list[Path] = []
        for raw_path in paths:
            resolved = self._resolve_allowed_path(raw_path)
            if resolved is not None:
                roots.append(resolved)
        return roots

    def _resolve_allowed_path(self, raw_path: str) -> Path | None:
        try:
            resolved = (self.root / raw_path).resolve()
        except OSError:
            return None
        if resolved != self.root and self.root not in resolved.parents:
            return None
        return resolved

    def _is_under_allowed_roots(self, resolved: Path, allowed_roots: list[Path]) -> bool:
        for root in allowed_roots:
            if resolved == root or root in resolved.parents:
                return True
        return False


def _objective_terms(objective: str) -> list[str]:
    terms = [item.lower() for item in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", objective)]
    synonym_map = {
        "审批": ["approval", "approve", "approved"],
        "恢复": ["resume", "resumed", "resolution"],
        "方法": ["def "],
        "函数": ["def "],
        "工具": ["tool"],
        "委派": ["delegate", "subagent"],
        "验证": ["verification", "verify"],
    }
    for marker, synonyms in synonym_map.items():
        if marker in objective:
            terms.extend(synonyms)
    unique: list[str] = []
    for term in terms:
        if term not in unique:
            unique.append(term)
    return unique[:12]


def _matching_lines(lines: list[str], terms: list[str]) -> list[dict]:
    if not terms:
        return []
    matches: list[dict] = []
    for index, line in enumerate(lines, start=1):
        lowered = line.lower()
        matched_terms = [term for term in terms if term in lowered]
        if not matched_terms:
            continue
        matches.append(
            {
                "line": index,
                "text": line.strip()[:240],
                "terms": matched_terms[:5],
            }
        )
        if len(matches) >= 20:
            break
    return matches


def _related_symbols(lines: list[str], matches: list[dict]) -> list[dict]:
    symbols: list[dict] = []
    for match in matches[:12]:
        line_no = int(match.get("line") or 0)
        symbol = _nearest_symbol(lines, line_no)
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def _matching_symbols(lines: list[str], terms: list[str]) -> list[dict]:
    symbols: list[dict] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not (stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class ")):
            continue
        lowered = stripped.lower()
        if not any(term.strip() and term in lowered for term in terms):
            continue
        symbols.append({"line": index, "signature": stripped[:240]})
        if len(symbols) >= 12:
            break
    return symbols


def _nearest_symbol(lines: list[str], line_no: int) -> dict | None:
    start = min(max(line_no, 1), len(lines))
    for index in range(start, 0, -1):
        stripped = lines[index - 1].strip()
        if stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class "):
            return {"line": index, "signature": stripped[:240]}
    return None
