"""テキスト → 中間 JSON に変換する AI 分類器（Gemini 版）。"""

from __future__ import annotations
import json
import os
import jsonschema
from google import genai
from google.genai import types

SCHEMA = {
    "type": "object",
    "required": ["doc_type", "title", "summary", "audience", "key_points", "related"],
    "properties": {
        "doc_type": {"type": "string", "enum": ["手順書", "規程", "議事録", "FAQ"]},
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "audience": {"type": "array", "items": {"type": "string"}},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "related": {"type": "array", "items": {"type": "string"}},
        "scope": {"type": "string"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "todos": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

# Gemini structured output 用スキーマ（enum は nullable 非対応のため文字列で指定）
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string", "enum": ["手順書", "規程", "議事録", "FAQ"]},
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "audience": {"type": "array", "items": {"type": "string"}},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "related": {"type": "array", "items": {"type": "string"}},
        "scope": {"type": "string"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "todos": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["doc_type", "title", "summary", "audience", "key_points", "related"],
}

PROMPT = """\
あなたは社内文書を分析するアシスタントです。
以下の文書テキストを読み、指定の JSON スキーマに従って情報を抽出してください。

ルール:
- doc_type は文書の性質から 手順書 / 規程 / 議事録 / FAQ のいずれかを選ぶ
- title は文書のタイトルまたは内容を表す適切な名称
- summary は文書の目的を1〜2文で説明
- audience は対象読者（例: 新人、全員、営業部）
- key_points は要点を3〜5点
- related は関連しそうな文書名（不明なら空配列）
- doc_type が sop なら scope / decisions / todos / questions は不要
- doc_type が policy なら scope を記入、それ以外は不要
- doc_type が minutes なら decisions と todos を記入
- doc_type が faq なら questions を記入

文書テキスト:
"""


def classify(text: str, gemini_api_key: str | None = None) -> dict:
    """文書テキストを Gemini で分類し、スキーマ検証済みの dict を返す。"""
    api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 環境変数が設定されていません。")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=PROMPT + text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )
    data = json.loads(response.text)
    jsonschema.validate(data, SCHEMA)
    return data
