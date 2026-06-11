from __future__ import annotations

import os
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MIYUN_PROJECT = Path("/home/dev/bxc/miyun_pro/miyun_pro")
DEFAULT_ES_USER = "elastic"
DEFAULT_ES_PASSWORD = "elastic@2024"


@dataclass(frozen=True)
class MiyunRuntimeConfig:
    project_root: Path
    es_addresses: str
    es_user: str | None
    es_password: str | None = field(repr=False)
    embedding_base_url: str
    analyzer: str = "ik_smart"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_env_default(source: str, key: str, fallback: str) -> str:
    pattern = rf'{re.escape(key)}\s*=\s*(?:os\.)?ENV\.get\("{re.escape(key)}",\s*"([^"]+)"\)'
    match = re.search(pattern, source)
    return match.group(1) if match else fallback


def _extract_field_default(source: str, field_name: str, fallback: str) -> str:
    pattern = rf'{re.escape(field_name)}:\s*str\s*=\s*Field\(.*?default="([^"]+)"'
    match = re.search(pattern, source, flags=re.DOTALL)
    return match.group(1) if match else fallback


def load_miyun_runtime_config(project_root: str | Path | None = None) -> MiyunRuntimeConfig:
    root = Path(project_root or os.getenv("MIYUN_PROJECT", DEFAULT_MIYUN_PROJECT)).resolve()
    config_py = _read_text(root / "llmos" / "config.py")
    config_base_py = _read_text(root / "llmos" / "base" / "config_base.py")

    es_default = _extract_env_default(
        config_py,
        "es_addresses",
        "http://192.168.102.19:9200",
    )
    embedding_default = _extract_field_default(
        config_base_py,
        "embedding_openai_api_base",
        "http://192.168.102.19:8082/v1",
    )

    es_user = os.getenv("es_user", DEFAULT_ES_USER)
    es_password = os.getenv("es_password", DEFAULT_ES_PASSWORD)
    os.environ.setdefault("es_user", es_user)
    os.environ.setdefault("es_password", es_password)

    return MiyunRuntimeConfig(
        project_root=root,
        es_addresses=os.getenv("es_addresses", es_default),
        es_user=es_user,
        es_password=es_password,
        embedding_base_url=os.getenv("embedding_openai_api_base", embedding_default),
    )


def add_miyun_project_to_path(project_root: str | Path | None = None) -> Path:
    root = Path(project_root or os.getenv("MIYUN_PROJECT", DEFAULT_MIYUN_PROJECT)).resolve()
    root_str = str(root)
    if root_str not in os.sys.path:
        os.sys.path.insert(0, root_str)
    return root


def _elasticsearch_client_major_version() -> int | None:
    try:
        import elasticsearch
    except ModuleNotFoundError:
        return None

    version = getattr(elasticsearch, "VERSION", None) or getattr(
        elasticsearch, "__version__", None
    )
    if isinstance(version, tuple) and version:
        return int(version[0])
    if isinstance(version, str) and version:
        return int(version.split(".", 1)[0])
    return None


def elasticsearch_kwargs(
    config: MiyunRuntimeConfig, client_major_version: int | None = None
) -> dict:
    kwargs = {"hosts": config.es_addresses}
    if config.es_user and config.es_password:
        auth_key = (
            "http_auth"
            if client_major_version is not None and client_major_version < 8
            else "basic_auth"
        )
        kwargs[auth_key] = (config.es_user, config.es_password)
    return kwargs


def create_elasticsearch_client(config: MiyunRuntimeConfig):
    from elasticsearch import Elasticsearch

    return Elasticsearch(
        **elasticsearch_kwargs(
            config, client_major_version=_elasticsearch_client_major_version()
        )
    )


def install_langchain_text_splitter_compat() -> None:
    try:
        import langchain.text_splitter  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    try:
        from langchain_text_splitters import TextSplitter
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "缺少 langchain-text-splitters，请先执行 pip install -r requirements.txt"
        ) from exc

    module = types.ModuleType("langchain.text_splitter")
    module.TextSplitter = TextSplitter
    sys.modules["langchain.text_splitter"] = module


def install_langchain_retriever_compat() -> None:
    try:
        import langchain.retrievers.ensemble  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    class EnsembleRetriever:
        def __init__(self, retrievers=None, weights=None):
            self.retrievers = retrievers or []
            self.weights = weights or [1 / len(self.retrievers)] * len(
                self.retrievers or [1]
            )

        def weighted_reciprocal_rank(self, doc_lists):
            scores = {}
            docs_by_key = {}
            weights = self.weights or [1 / len(doc_lists)] * len(doc_lists)
            rank_constant = 60

            for list_index, docs in enumerate(doc_lists):
                weight = weights[list_index] if list_index < len(weights) else 1
                for rank, doc in enumerate(docs, start=1):
                    key = f"{getattr(doc, 'page_content', str(doc))}|{getattr(doc, 'metadata', {})}"
                    docs_by_key.setdefault(key, doc)
                    scores[key] = scores.get(key, 0.0) + weight / (rank_constant + rank)

            return [
                docs_by_key[key]
                for key, _ in sorted(
                    scores.items(), key=lambda item: item[1], reverse=True
                )
            ]

    retrievers_module = types.ModuleType("langchain.retrievers")
    ensemble_module = types.ModuleType("langchain.retrievers.ensemble")
    ensemble_module.EnsembleRetriever = EnsembleRetriever
    retrievers_module.ensemble = ensemble_module
    sys.modules["langchain.retrievers"] = retrievers_module
    sys.modules["langchain.retrievers.ensemble"] = ensemble_module


def install_miyun_langchain_compat() -> None:
    install_langchain_text_splitter_compat()
    install_langchain_retriever_compat()
