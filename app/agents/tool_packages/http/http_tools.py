import json
import urllib.parse
import urllib.request
from typing import Any


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 15,
    max_chars: int = 20000,
) -> dict[str, Any]:
    return _request("GET", url, None, headers, timeout_seconds, max_chars)


def http_post(
    url: str,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 15,
    max_chars: int = 20000,
) -> dict[str, Any]:
    body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
    merged_headers = {"Content-Type": "application/json", **(headers or {})}
    return _request("POST", url, body, merged_headers, timeout_seconds, max_chars)


def _request(
    method: str,
    url: str,
    body: bytes | None,
    headers: dict[str, str] | None,
    timeout_seconds: int,
    max_chars: int,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "User-Agent": "fastapi-study-agent/1.0",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        preview = text[:max_chars]
        result: dict[str, Any] = {
            "url": url,
            "method": method,
            "status": getattr(response, "status", 200),
            "content_type": response.headers.get("content-type", ""),
            "text": preview,
            "truncated": len(text) > max_chars,
        }
        if "json" in result["content_type"]:
            try:
                result["json"] = json.loads(text)
            except json.JSONDecodeError:
                result["json_error"] = "response content-type is json but body could not be decoded"
        return result
