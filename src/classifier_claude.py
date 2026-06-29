"""テキスト → 中間 JSON に変換する AI 分類器（Claude 版）。

Anthropic API クレジットが必要。
課金設定後に classifier.py の代替として使用可能。
"""

from __future__ import annotations
import json
import anthropic
import jsonschema
from src.classifier import SCHEMA, SYSTEM_PROMPT


def classify(text: str, client: anthropic.Anthropic | None = None) -> dict:
    """文書テキストを Claude で分類し、スキーマ検証済みの dict を返す。"""
    if client is None:
        client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text
    data = json.loads(raw)
    jsonschema.validate(data, SCHEMA)
    return data
