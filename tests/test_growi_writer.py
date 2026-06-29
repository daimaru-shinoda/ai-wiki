"""growi_writer.py のユニットテスト（HTTP はモック）。"""

import pytest
from unittest.mock import MagicMock, patch
from src.growi_writer import GrowiWriter

BASE_URL = "https://growi.example.com"
TOKEN = "test-token"


def _writer():
    return GrowiWriter(BASE_URL, TOKEN)


def _mock_get_none():
    resp = MagicMock()
    resp.status_code = 404
    resp.raise_for_status = MagicMock()
    return resp


def _mock_get_existing():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "page": {
            "_id": "existing_id",
            "path": "/docs/marketing/sop/経費精算",
            "revision": {"_id": "revision_id"},
        }
    }
    resp.raise_for_status = MagicMock()
    return resp


def _mock_post_put():
    resp = MagicMock()
    resp.json.return_value = {"page": {"_id": "new_id"}}
    resp.raise_for_status = MagicMock()
    return resp


@patch("src.growi_writer.requests.get")
@patch("src.growi_writer.requests.post")
def test_upsert_creates_page_when_not_exists(mock_post, mock_get):
    mock_get.return_value = _mock_get_none()
    mock_post.return_value = _mock_post_put()

    writer = _writer()
    writer.upsert("/docs/marketing/sop/経費精算", "# 経費精算マニュアル")

    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"]["path"] == "/docs/marketing/sop/経費精算"


@patch("src.growi_writer.requests.get")
@patch("src.growi_writer.requests.put")
def test_upsert_updates_page_when_exists(mock_put, mock_get):
    mock_get.return_value = _mock_get_existing()
    mock_put.return_value = _mock_post_put()

    writer = _writer()
    writer.upsert("/docs/marketing/sop/経費精算", "# 更新後")

    mock_put.assert_called_once()
    payload = mock_put.call_args.kwargs["json"]
    assert payload["pageId"] == "existing_id"
    assert payload["revisionId"] == "revision_id"
    assert payload["body"] == "# 更新後"
