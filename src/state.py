"""処理済みファイルの状態管理（file_id → 最終処理日時）。"""

from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("state.json")


def load(path: Path = DEFAULT_PATH) -> dict[str, str]:
    """state.json を読み込んで {file_id: modifiedTime} の dict を返す。"""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save(state: dict[str, str], path: Path = DEFAULT_PATH) -> None:
    """state.json に書き込む。"""
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def needs_update(file_meta: dict, state: dict[str, str]) -> bool:
    """Drive の modifiedTime が state より新しければ True。"""
    file_id = file_meta["id"]
    modified = file_meta["modifiedTime"]
    return state.get(file_id) != modified
