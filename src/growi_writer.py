"""GROWI ページを冪等に作成・更新する。"""

from __future__ import annotations
import requests


class GrowiWriter:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_token}"}

    def _get_page(self, path: str) -> dict | None:
        resp = requests.get(
            f"{self.base_url}/_api/v3/page",
            params={"path": path},
            headers=self.headers,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("page")

    def upsert(self, path: str, body: str) -> dict:
        """ページが存在すれば更新、なければ作成して結果を返す。"""
        existing = self._get_page(path)
        if existing:
            page_id = existing["_id"]
            revision_id = existing["revision"]["_id"]
            resp = requests.put(
                f"{self.base_url}/_api/v3/page",
                json={"pageId": page_id, "revisionId": revision_id, "body": body},
                headers=self.headers,
            )
        else:
            resp = requests.post(
                f"{self.base_url}/_api/v3/page",
                json={"path": path, "body": body},
                headers=self.headers,
            )
        resp.raise_for_status()
        return resp.json()
