"""classifier.py のユニットテスト（Gemini 呼び出しはモック）。"""

import json
import pytest
from unittest.mock import MagicMock, patch
from src.classifier import classify, SCHEMA
import jsonschema


VALID_SOP = {
    "doc_type": "手順書",
    "title": "経費精算マニュアル",
    "summary": "経費精算の手順を説明した文書",
    "audience": ["新人"],
    "key_points": ["月末締め"],
    "related": [],
}

VALID_MINUTES = {
    "doc_type": "議事録",
    "title": "2026年6月定例会議",
    "summary": "6月の定例会議の議事録",
    "audience": ["参加者"],
    "key_points": ["予算承認"],
    "related": [],
    "decisions": ["予算を承認"],
    "todos": ["議事録共有"],
}


def _mock_gemini(response_text: str):
    """Gemini クライアントのモックを返す。"""
    with patch("src.classifier.genai") as mock_genai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = response_text
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        yield mock_client


@patch("src.classifier.genai")
def test_classify_sop_returns_valid_dict(mock_genai):
    mock_response = MagicMock()
    mock_response.text = json.dumps(VALID_SOP)
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    result = classify("ダミーテキスト", gemini_api_key="dummy-key")
    assert result["doc_type"] == "手順書"
    assert result["title"] == "経費精算マニュアル"


@patch("src.classifier.genai")
def test_classify_minutes_returns_decisions(mock_genai):
    mock_response = MagicMock()
    mock_response.text = json.dumps(VALID_MINUTES)
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    result = classify("ダミーテキスト", gemini_api_key="dummy-key")
    assert "decisions" in result
    assert result["decisions"] == ["予算を承認"]



@patch("src.classifier.genai")
def test_classify_raises_on_invalid_json(mock_genai):
    mock_response = MagicMock()
    mock_response.text = "not json"
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    with pytest.raises(json.JSONDecodeError):
        classify("ダミーテキスト", gemini_api_key="dummy-key")


@patch("src.classifier.genai")
def test_classify_raises_on_schema_violation(mock_genai):
    invalid = {**VALID_SOP, "doc_type": "不明"}
    mock_response = MagicMock()
    mock_response.text = json.dumps(invalid)
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    with pytest.raises(jsonschema.ValidationError):
        classify("ダミーテキスト", gemini_api_key="dummy-key")


def test_schema_rejects_extra_fields():
    extra = {**VALID_SOP, "unexpected_field": "value"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(extra, SCHEMA)
