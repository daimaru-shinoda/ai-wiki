"""Drive フォルダ → GROWI ページ自動生成パイプライン。"""

from __future__ import annotations
import os
from datetime import date
from pathlib import Path

from src.drive_lister import list_files
from src.extractor import extract
from src.classifier import classify
from src.formatter import format_page
from src.growi_writer import GrowiWriter
from src.state import load as load_state, save as save_state, needs_update


def build_prefilled_form_url(base_form_url: str, file_id: str, today: str) -> str:
    """PLACEHOLDER_DOC_ID と PLACEHOLDER_DATE を実値に置換したプレフィル URL を返す。"""
    return (
        base_form_url
        .replace("PLACEHOLDER_DOC_ID", file_id)
        .replace("PLACEHOLDER_DATE", today)
    )


def run(
    folder_id: str,
    department: str,
    drive_service,
    growi: GrowiWriter,
    form_base_url: str,
    gemini_api_key: str | None = None,
    state_path: Path = Path("state.json"),
) -> list[str]:
    """パイプラインを実行し、更新した GROWI パスのリストを返す。"""
    files = list_files(folder_id, drive_service)
    state = load_state(state_path)
    updated_paths = []
    today = date.today().isoformat()

    for f in files:
        if not needs_update(f, state):
            print(f"  スキップ: {f['name']}（未更新）")
            continue

        print(f"  処理中: {f['name']}")
        text = extract(f, service=drive_service, gemini_api_key=gemini_api_key)
        doc = classify(text, gemini_api_key=gemini_api_key)

        doc["drive_url"] = f["webViewLink"]
        doc["last_updated"] = f["modifiedTime"][:10]
        doc["department"] = department

        prefilled_url = build_prefilled_form_url(form_base_url, f["id"], today)
        markdown = format_page(doc, prefilled_url)

        filename_stem = os.path.splitext(f["name"])[0]
        growi_path = f"/docs/{department}/{doc['doc_type']}/{filename_stem}"
        growi.upsert(growi_path, markdown)
        updated_paths.append(growi_path)

        # 処理成功したら state を更新
        state[f["id"]] = f["modifiedTime"]

    save_state(state, state_path)
    return updated_paths
