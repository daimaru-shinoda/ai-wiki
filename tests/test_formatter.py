"""formatter.py のユニットテスト（純粋関数 / 外部依存なし）。"""

import pytest
from src.formatter import format_page

BASE_DOC = {
    "title": "経費精算マニュアル",
    "summary": "経費を申請・精算する手順をまとめた文書",
    "audience": ["新人", "全員"],
    "drive_url": "https://drive.google.com/file/d/ABC123",
    "last_updated": "2026-06-01",
    "key_points": ["申請は月末締め", "領収書は電子提出"],
    "related": ["出張旅費規程"],
}
FORM_URL = "https://forms.gle/xyz?entry.file_id=ABC123"


def _make(overrides: dict) -> dict:
    return {**BASE_DOC, **overrides}


class TestSop:
    def test_contains_title(self):
        md = format_page(_make({"doc_type": "手順書"}), FORM_URL)
        assert "# 経費精算マニュアル" in md

    def test_contains_summary(self):
        md = format_page(_make({"doc_type": "手順書"}), FORM_URL)
        assert "経費を申請・精算する手順をまとめた文書" in md

    def test_contains_drive_link(self):
        md = format_page(_make({"doc_type": "手順書"}), FORM_URL)
        assert "https://drive.google.com/file/d/ABC123" in md

    def test_contains_key_points(self):
        md = format_page(_make({"doc_type": "手順書"}), FORM_URL)
        assert "申請は月末締め" in md
        assert "領収書は電子提出" in md

    def test_contains_improvement_section(self):
        md = format_page(_make({"doc_type": "手順書"}), FORM_URL)
        assert "改善提案フォーム" in md
        assert FORM_URL in md


class TestPolicy:
    def test_contains_scope(self):
        md = format_page(_make({"doc_type": "規程", "scope": "全社員"}), FORM_URL)
        assert "## 適用範囲" in md
        assert "全社員" in md

    def test_contains_revision_notice(self):
        md = format_page(_make({"doc_type": "規程", "scope": "全社員"}), FORM_URL)
        assert "規程改訂時" in md

    def test_contains_improvement_section(self):
        md = format_page(_make({"doc_type": "規程", "scope": "全社員"}), FORM_URL)
        assert "改善提案フォーム" in md


class TestMinutes:
    def test_contains_decisions(self):
        doc = _make({
            "doc_type": "議事録",
            "decisions": ["予算を承認", "担当者を決定"],
            "todos": ["議事録を共有"],
        })
        md = format_page(doc, FORM_URL)
        assert "## 決定事項" in md
        assert "予算を承認" in md

    def test_contains_todos(self):
        doc = _make({
            "doc_type": "議事録",
            "decisions": ["予算を承認"],
            "todos": ["議事録を共有", "次回日程調整"],
        })
        md = format_page(doc, FORM_URL)
        assert "## TODO" in md
        assert "議事録を共有" in md

    def test_no_improvement_section(self):
        doc = _make({
            "doc_type": "議事録",
            "decisions": [],
            "todos": [],
        })
        md = format_page(doc, FORM_URL)
        assert "改善提案フォーム" not in md


class TestFaq:
    def test_contains_questions(self):
        doc = _make({
            "doc_type": "FAQ",
            "questions": ["申請期限はいつ？", "領収書の形式は？"],
        })
        md = format_page(doc, FORM_URL)
        assert "## 想定質問" in md
        assert "申請期限はいつ？" in md

    def test_contains_improvement_section(self):
        doc = _make({"doc_type": "FAQ", "questions": []})
        md = format_page(doc, FORM_URL)
        assert "改善提案フォーム" in md


def test_unknown_doc_type_raises():
    with pytest.raises(ValueError, match="Unknown doc_type"):
        format_page(_make({"doc_type": "unknown"}), FORM_URL)
