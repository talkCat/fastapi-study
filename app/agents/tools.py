import json
import re
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

from bs4 import BeautifulSoup

from app.agents.skill_runtime import SkillRuntimeAdapter
from app.agents.tool_runtime import ToolRuntimeAdapter
from app.agents.types import PermissionDecision, ToolCall, ToolDefinition, ToolResult


class ToolRegistry:
    def __init__(
        self,
        skill_runtime_adapter: SkillRuntimeAdapter | None = None,
        tool_runtime_adapter: ToolRuntimeAdapter | None = None,
    ):
        self._tools: dict[str, ToolDefinition] = {}
        self._dynamic_tool_names: set[str] = set()
        self.register(
            ToolDefinition(
                name="echo",
                description="Return the provided text. Useful for smoke tests.",
                risk_level="low",
                parallel_safe=True,
                handler=self._echo,
            )
        )
        self.skill_runtime_adapter = skill_runtime_adapter or SkillRuntimeAdapter()
        self.tool_runtime_adapter = tool_runtime_adapter or ToolRuntimeAdapter()
        self.register(
            ToolDefinition(
                name="skill.scripts.list",
                description="List Python scripts available inside an installed or built-in skill package.",
                risk_level="low",
                parallel_safe=True,
                handler=self._skill_scripts_list,
            )
        )
        self.register(
            ToolDefinition(
                name="skill.python.run",
                description="Run a Python script from a skill package with argv-style arguments. This is generic and requires approval.",
                risk_level="medium",
                parallel_safe=False,
                handler=self._skill_python_run,
            )
        )
        self.register(
            ToolDefinition(
                name="web_fetch",
                description="Fetch a public HTTP(S) URL and return a stripped text preview. Useful for search skills that reference web_fetch.",
                risk_level="low",
                parallel_safe=False,
                handler=self._web_fetch,
            )
        )
        self.register(
            ToolDefinition(
                name="web.search",
                description="Run a lightweight web search through public search result pages and return extracted result items. No API key required.",
                risk_level="low",
                parallel_safe=False,
                handler=self._web_search,
            )
        )
        self._register_runtime_tools()

    def register(self, definition: ToolDefinition, dynamic: bool = False) -> None:
        self._tools[definition.name] = definition
        if dynamic:
            self._dynamic_tool_names.add(definition.name)

    def _register_runtime_tools(self) -> None:
        for name in list(self._dynamic_tool_names):
            self._tools.pop(name, None)
        self._dynamic_tool_names.clear()
        for definition in self.tool_runtime_adapter.load_tool_definitions():
            self.register(definition, dynamic=True)
        for definition in self.skill_runtime_adapter.load_tool_definitions():
            self.register(definition, dynamic=True)

    def refresh_dynamic_tools(self) -> None:
        self._register_runtime_tools()

    def list_tools(self) -> list[ToolDefinition]:
        self.refresh_dynamic_tools()
        return sorted(self._tools.values(), key=lambda item: item.name)

    def get(self, name: str) -> ToolDefinition | None:
        self.refresh_dynamic_tools()
        return self._tools.get(name)

    def decide_permission(self, call: ToolCall, auto_approve: bool = False) -> PermissionDecision:
        definition = self.get(call.name)
        if definition is None:
            return "deny"
        if definition.risk_level == "low":
            return "allow"
        if definition.risk_level == "medium":
            return "allow" if auto_approve else "ask"
        return "ask"

    def execute(self, call: ToolCall) -> ToolResult:
        self.refresh_dynamic_tools()
        definition = self.get(call.name)
        if definition is None:
            return ToolResult(ok=False, tool_name=call.name, error="Tool not found")
        try:
            result = definition.handler(call.arguments)
            return ToolResult(ok=True, tool_name=call.name, result=result)
        except Exception as exc:
            return ToolResult(ok=False, tool_name=call.name, error=str(exc))

    def _echo(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"text": str(arguments.get("text", ""))}

    def _skill_scripts_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.skill_runtime_adapter.list_python_scripts(
            skill_name=str(arguments.get("skill_name") or arguments.get("skill") or ""),
        )

    def _skill_python_run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        args = arguments.get("args")
        if args is None:
            args = arguments.get("argv")
        return self.skill_runtime_adapter.run_python_script(
            skill_name=str(arguments.get("skill_name") or arguments.get("skill") or ""),
            script=str(arguments.get("script") or ""),
            args=args if isinstance(args, list) else [],
            timeout_seconds=int(arguments.get("timeout_seconds") or 20),
            output_format=str(arguments.get("output_format") or "text"),
            max_output_chars=int(arguments.get("max_output_chars") or 20000),
        )

    def _web_fetch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        url = str(arguments.get("url") or "").strip()
        if not url:
            raise ValueError("url is required")
        return _fetch_public_url(
            url=url,
            timeout_seconds=int(arguments.get("timeout_seconds") or 10),
            max_chars=int(arguments.get("max_chars") or 6000),
        )

    def _web_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")

        engines = arguments.get("engines")
        selected_engines = engines if isinstance(engines, list) and engines else ["bing_cn", "duckduckgo"]
        max_chars = int(arguments.get("max_chars") or 6000)
        timeout_seconds = int(arguments.get("timeout_seconds") or 10)
        urls = [_build_search_url(str(engine), query) for engine in selected_engines[:4]]
        results = []
        errors = []
        for engine, url in urls:
            try:
                fetched = _fetch_public_url(
                    url=url,
                    timeout_seconds=timeout_seconds,
                    max_chars=max_chars,
                    include_html=True,
                )
                items = _extract_search_items(engine=engine, html=str(fetched.get("html") or ""))
                results.append(
                    {
                        "engine": engine,
                        "url": url,
                        "status": fetched["status"],
                        "items": items,
                        "item_count": len(items),
                        "text_preview": fetched["text"],
                        "truncated": fetched["truncated"],
                    }
                )
            except Exception as exc:
                errors.append({"engine": engine, "url": url, "error": str(exc)})

        if not results and errors:
            raise RuntimeError(f"All search engines failed: {json.dumps(errors, ensure_ascii=False)}")

        top_results = []
        seen_urls = set()
        ranked_items = _rank_search_items(
            [item for result in results for item in result["items"]]
        )
        for item in ranked_items:
            item_url = item.get("url")
            if item_url and item_url in seen_urls:
                continue
            if item_url:
                seen_urls.add(item_url)
            top_results.append(item)
            if len(top_results) >= 10:
                break

        return {
            "query": query,
            "engines": [item["engine"] for item in results],
            "top_results": top_results,
            "results": results,
            "errors": errors,
        }

def _build_search_url(engine: str, query: str) -> tuple[str, str]:
    encoded = urllib.parse.urlencode({"q": query})
    keyword = urllib.parse.quote_plus(query)
    normalized = engine.strip().lower().replace("-", "_")
    if normalized in {"bing", "bing_cn"}:
        return "bing_cn", f"https://cn.bing.com/search?{encoded}&ensearch=0&format=rss"
    if normalized in {"bing_int", "bing_global"}:
        return "bing_int", f"https://cn.bing.com/search?{encoded}&ensearch=1&format=rss"
    if normalized in {"duckduckgo", "ddg"}:
        return "duckduckgo", f"https://duckduckgo.com/html/?{encoded}"
    if normalized == "baidu":
        return "baidu", f"https://www.baidu.com/s?wd={keyword}"
    if normalized == "sogou":
        return "sogou", f"https://www.sogou.com/web?query={keyword}"
    raise ValueError(f"Unsupported search engine: {engine}")


def _fetch_public_url(
    url: str,
    timeout_seconds: int,
    max_chars: int,
    include_html: bool = False,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")
    if not parsed.netloc:
        raise ValueError("URL host is required")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read(max(max_chars * 8, 2048))
        charset = response.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="replace")
        text = _html_to_text(html)
        preview = text[:max_chars]
        result = {
            "url": url,
            "status": getattr(response, "status", 200),
            "content_type": response.headers.get("content-type", ""),
            "text": preview,
            "truncated": len(text) > max_chars,
        }
        if include_html:
            result["html"] = html
        return result


def _html_to_text(value: str) -> str:
    parser = "xml" if value.lstrip().startswith(("<?xml", "<rss")) else "lxml"
    soup = BeautifulSoup(value, parser)
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    cleaned = soup.get_text("\n")
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*", "\n", cleaned)
    return "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())


def _extract_search_items(engine: str, html: str, max_items: int = 8) -> list[dict[str, str]]:
    if "<rss" in html[:500].lower() or "<item>" in html[:2000].lower():
        return _extract_rss_items(engine=engine, xml_text=html, max_items=max_items)

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    normalized = engine.strip().lower()
    if normalized.startswith("bing"):
        items = _extract_bing_items(soup, max_items=max_items)
    elif normalized == "duckduckgo":
        items = _extract_duckduckgo_items(soup, max_items=max_items)
    elif normalized == "baidu":
        items = _extract_generic_items(soup, selectors=[".result", ".c-container"], max_items=max_items)
    elif normalized == "sogou":
        items = _extract_generic_items(soup, selectors=[".results .vrwrap", ".rb"], max_items=max_items)
    else:
        items = _extract_generic_items(soup, selectors=["li", "article", ".result"], max_items=max_items)

    return _dedupe_search_items(items)[:max_items]


def _extract_rss_items(engine: str, xml_text: str, max_items: int) -> list[dict[str, str]]:
    soup = BeautifulSoup(xml_text, "xml")
    items = []
    for item in soup.find_all("item"):
        title = _compact_text(item.title.get_text(" ", strip=True) if item.title else "")
        url = _compact_text(item.link.get_text(" ", strip=True) if item.link else "")
        snippet = _compact_text(item.description.get_text(" ", strip=True) if item.description else "")
        published_at = _compact_text(item.pubDate.get_text(" ", strip=True) if item.pubDate else "")
        if not title or not url:
            continue
        record = {
            "title": title[:180],
            "url": _unwrap_redirect_url(url),
            "snippet": snippet[:500],
            "engine": engine,
        }
        if published_at:
            record["published_at"] = published_at
        items.append(record)
        if len(items) >= max_items:
            break
    return _dedupe_search_items(items)


def _extract_bing_items(soup: BeautifulSoup, max_items: int) -> list[dict[str, str]]:
    items = []
    for block in soup.select("li.b_algo"):
        link = block.select_one("h2 a")
        if not link:
            continue
        snippet_node = block.select_one(".b_caption p") or block.select_one("p")
        item = _search_item_from_nodes(
            engine="bing_cn",
            link=link,
            snippet=_node_text(snippet_node),
        )
        if item:
            items.append(item)
        if len(items) >= max_items:
            break
    if items:
        return items
    return _extract_generic_items(soup, selectors=["li"], max_items=max_items)


def _extract_duckduckgo_items(soup: BeautifulSoup, max_items: int) -> list[dict[str, str]]:
    items = []
    for block in soup.select(".result"):
        link = block.select_one(".result__a") or block.select_one("a")
        if not link:
            continue
        snippet_node = block.select_one(".result__snippet")
        item = _search_item_from_nodes(
            engine="duckduckgo",
            link=link,
            snippet=_node_text(snippet_node),
        )
        if item:
            items.append(item)
        if len(items) >= max_items:
            break
    if items:
        return items
    return _extract_generic_items(soup, selectors=[".result", "article", "li"], max_items=max_items)


def _extract_generic_items(soup: BeautifulSoup, selectors: list[str], max_items: int) -> list[dict[str, str]]:
    items = []
    for selector in selectors:
        for block in soup.select(selector):
            link = block.select_one("a[href]")
            if not link:
                continue
            item = _search_item_from_nodes(
                engine="generic",
                link=link,
                snippet=_node_text(block),
            )
            if item:
                items.append(item)
            if len(items) >= max_items:
                return items
        if items:
            return items
    return items


def _search_item_from_nodes(engine: str, link, snippet: str) -> dict[str, str] | None:
    title = _node_text(link)
    url = str(link.get("href") or "").strip()
    if not title or not url:
        return None
    if url.startswith("/"):
        url = _unwrap_relative_search_url(engine, url)
    url = _unwrap_redirect_url(url)
    if not url.startswith(("http://", "https://")):
        return None
    compact_snippet = _compact_text(snippet)
    if compact_snippet.startswith(title):
        compact_snippet = compact_snippet[len(title):].strip(" -：:|")
    return {
        "title": title[:180],
        "url": url,
        "snippet": compact_snippet[:500],
        "engine": engine,
    }


def _unwrap_relative_search_url(engine: str, url: str) -> str:
    if engine.startswith("bing"):
        return urllib.parse.urljoin("https://cn.bing.com", url)
    if engine == "duckduckgo":
        return urllib.parse.urljoin("https://duckduckgo.com", url)
    return url


def _unwrap_redirect_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("uddg", "url", "u"):
        value = query.get(key)
        if value:
            candidate = urllib.parse.unquote(value[0])
            if candidate.startswith(("http://", "https://")):
                return candidate
    return url


def _dedupe_search_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped = []
    seen = set()
    for item in items:
        key = item.get("url") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _rank_search_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        _dedupe_search_items(items),
        key=lambda item: (_source_rank(item.get("url", "")), item.get("title", "")),
    )


def _source_rank(url: str) -> int:
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    official_hosts = (
        "gov.cn",
        "mfa.gov.cn",
        "fmprc.gov.cn",
        "cac.gov.cn",
        "xinhuanet.com",
        "people.com.cn",
        "cctv.com",
        "cgtn.com",
        "china.com.cn",
    )
    major_news_hosts = (
        "thepaper.cn",
        "caixin.com",
        "guancha.cn",
        "ifeng.com",
        "qq.com",
        "163.com",
        "sina.com.cn",
    )
    low_signal_hosts = (
        "zhihu.com",
        "baike.baidu.com",
        "sohu.com",
        "toutiao.com",
    )
    if any(host == item or host.endswith(f".{item}") for item in official_hosts):
        return 0
    if any(host == item or host.endswith(f".{item}") for item in major_news_hosts):
        return 5
    if any(host == item or host.endswith(f".{item}") for item in low_signal_hosts):
        return 20
    return 10


def _node_text(node) -> str:
    if node is None:
        return ""
    return _compact_text(node.get_text(" ", strip=True))


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(str(value))).strip()
