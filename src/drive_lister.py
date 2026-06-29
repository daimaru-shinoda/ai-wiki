"""Google Drive フォルダ内の文書一覧とメタデータを取得する。"""

from __future__ import annotations
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
}

FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"

_SHARED = {"supportsAllDrives": True, "includeItemsFromAllDrives": True}


def list_files(
    folder_id: str,
    service,
    *,
    recursive: bool = False,
    max_workers: int = 1,
) -> list[dict]:
    """フォルダ内のサポート対象ファイル一覧を返す。

    recursive=True のとき、サブフォルダを再帰的に探索する。
    max_workers > 1 でフォルダ単位の並列取得を有効にする。
    フォルダショートカットは循環の原因になるため常に無視する。

    Returns:
        [{"id", "name", "mimeType", "webViewLink", "modifiedTime", "folder_path"}, ...]
        folder_path: ルート直下は ""、サブフォルダは "SubA/SubB" 形式
    """
    visited: set[str] = set()
    lock = threading.Lock()

    if not recursive:
        return _fetch_one(folder_id, "", service, lock, visited, fetch_subfolders=False)[0]

    all_files: list[dict] = []
    pending = [(folder_id, "")]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while pending:
            futures = {
                executor.submit(_fetch_one, fid, path, service, lock, visited): path
                for fid, path in pending
            }
            pending = []
            for future in as_completed(futures):
                files, subfolders, parent_path = future.result()
                all_files.extend(files)
                for sf in subfolders:
                    sub_path = f"{parent_path}/{sf['name']}" if parent_path else sf["name"]
                    pending.append((sf["id"], sub_path))

    return all_files


def _fetch_one(
    folder_id: str,
    path: str,
    service,
    lock: threading.Lock,
    visited: set[str],
    fetch_subfolders: bool = True,
) -> tuple[list[dict], list[dict], str]:
    """1 フォルダ分のファイルとサブフォルダを取得する。

    Returns:
        (files, subfolders, path)
        files: folder_path 付きファイルリスト
        subfolders: {"id", "name"} のリスト
        path: このフォルダ自身のパス（呼び出し元が sub_path を組み立てるために使う）
    """
    with lock:
        if folder_id in visited:
            return [], [], path
        visited.add(folder_id)

    file_q = (
        f"'{folder_id}' in parents and trashed = false"
        f" and mimeType != '{SHORTCUT_MIME}' and ("
        + " or ".join(f"mimeType = '{m}'" for m in SUPPORTED_MIME_TYPES)
        + ")"
    )
    raw_files = (
        service.files()
        .list(q=file_q, fields="files(id, name, mimeType, webViewLink, modifiedTime)", **_SHARED)
        .execute()
        .get("files", [])
    )
    files = [{**f, "folder_path": path} for f in raw_files]

    if not fetch_subfolders:
        return files, [], path

    folder_q = (
        f"'{folder_id}' in parents and trashed = false"
        f" and mimeType = '{FOLDER_MIME}'"
    )
    subfolders = (
        service.files()
        .list(q=folder_q, fields="files(id, name)", **_SHARED)
        .execute()
        .get("files", [])
    )

    return files, subfolders, path
