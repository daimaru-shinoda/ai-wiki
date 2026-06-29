"""中間 JSON → 種別別 Markdown に変換する純粋関数群。"""

from __future__ import annotations
from typing import Any


def _common_header(doc: dict[str, Any]) -> str:
    audience = "、".join(doc.get("audience", []))
    key_points = "\n".join(f"- {p}" for p in doc.get("key_points", []))
    return f"""\
# {doc["title"]}

> {doc["summary"]}

- **対象読者**: {audience}
- **原本**: [Drive で開く]({doc["drive_url"]})
- **最終更新**: {doc["last_updated"]}
- **カテゴリ**: {doc["doc_type"]}

## 要点

{key_points}"""


def _improvement_section(prefilled_form_url: str) -> str:
    return f"""\

## この文書を改善する

気づいた点があれば改善提案を送ってください → [改善提案フォーム]({prefilled_form_url})"""


def format_sop(doc: dict[str, Any], prefilled_form_url: str) -> str:
    return _common_header(doc) + "\n" + _improvement_section(prefilled_form_url) + "\n"


def format_policy(doc: dict[str, Any], prefilled_form_url: str) -> str:
    scope = doc.get("scope", "")
    body = _common_header(doc)
    body += f"\n\n## 適用範囲\n\n{scope}\n\n> 規程改訂時は必ず原本を確認してください。"
    body += "\n" + _improvement_section(prefilled_form_url) + "\n"
    return body


def format_minutes(doc: dict[str, Any]) -> str:
    decisions = "\n".join(f"- {d}" for d in doc.get("decisions", []))
    todos = "\n".join(f"- {t}" for t in doc.get("todos", []))
    body = _common_header(doc)
    body += f"\n\n## 決定事項\n\n{decisions}"
    body += f"\n\n## TODO\n\n{todos}\n"
    return body


def format_faq(doc: dict[str, Any], prefilled_form_url: str) -> str:
    questions = "\n".join(f"- {q}" for q in doc.get("questions", []))
    body = _common_header(doc)
    body += f"\n\n## 想定質問\n\n{questions}"
    body += "\n" + _improvement_section(prefilled_form_url) + "\n"
    return body


def format_page(doc: dict[str, Any], prefilled_form_url: str) -> str:
    """doc_type に応じて適切なフォーマッタを呼び出す。"""
    doc_type = doc.get("doc_type")
    if doc_type == "手順書":
        return format_sop(doc, prefilled_form_url)
    if doc_type == "規程":
        return format_policy(doc, prefilled_form_url)
    if doc_type == "議事録":
        return format_minutes(doc)
    if doc_type == "FAQ":
        return format_faq(doc, prefilled_form_url)
    raise ValueError(f"Unknown doc_type: {doc_type!r}")
