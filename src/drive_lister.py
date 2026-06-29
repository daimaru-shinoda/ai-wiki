"""Google Drive フォルダ内の文書一覧とメタデータを取得する。"""

from __future__ import annotations
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from googleapiclient.errors import HttpError

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
    service=None,
    *,
    recursive: bool = False,
    max_workers: int = 1,
    service_factory: Callable | None = None,
) -> list[dict]:
    """フォルダ内のサポート対象ファイル一覧を返す。

    service: サービスオブジェクト（シングルスレッド用）
    service_factory: サービスを生成するファクトリ関数（並列モード推奨）
      httplib2 はスレッド非安全なため、max_workers > 1 の場合は
      service_factory を渡してスレッドごとに独立した接続を生成すること。
    """
    _local = threading.local()

    def get_svc():
        if service_factory is not None:
            if not hasattr(_local, "instance"):
                _local.instance = service_factory()
            return _local.instance
        return service

    visited: set[str] = set()
    lock = threading.Lock()

    if not recursive:
        return _fetch_one(folder_id, "", get_svc, lock, visited, fetch_subfolders=False)[0]

    all_files: list[dict] = []
    pending = [(folder_id, "")]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while pending:
            futures = {
                executor.submit(_fetch_one, fid, path, get_svc, lock, visited): path
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
    get_svc: Callable,
    lock: threading.Lock,
    visited: set[str],
    fetch_subfolders: bool = True,
) -> tuple[list[dict], list[dict], str]:
    with lock:
        if folder_id in visited:
            return [], [], path
        visited.add(folder_id)

    svc = get_svc()

    file_q = (
        f"'{folder_id}' in parents and trashed = false"
        f" and mimeType != '{SHORTCUT_MIME}' and ("
        + " or ".join(f"mimeType = '{m}'" for m in SUPPORTED_MIME_TYPES)
        + ")"
    )
    raw_files = _execute_with_retry(
        svc.files().list(q=file_q, fields="files(id, name, mimeType, webViewLink, modifiedTime)", **_SHARED),
        context=f"files in {path or '/'}",
    )
    files = [{**f, "folder_path": path} for f in raw_files]

    if not fetch_subfolders:
        return files, [], path

    folder_q = (
        f"'{folder_id}' in parents and trashed = false"
        f" and mimeType = '{FOLDER_MIME}'"
    )
    subfolders = _execute_with_retry(
        svc.files().list(q=folder_q, fields="files(id, name)", **_SHARED),
        context=f"subfolders in {path or '/'}",
    )

    return files, subfolders, path


def _execute_with_retry(request, context: str, retries: int = 3) -> list:
    """API リクエストを実行し、5xx エラーは指数バックオフでリトライする。
    リトライ上限を超えた場合は空リストを返して処理を継続する。
    """
    delay = 2.0
    for attempt in range(retries):
        try:
            return request.execute().get("files", [])
        except HttpError as e:
            if e.resp.status < 500:
                raise
            if attempt < retries - 1:
                print(f"  [warn] {context}: HTTP {e.resp.status}, {delay:.0f}s 後にリトライ ({attempt+1}/{retries-1})", file=sys.stderr)
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  [skip] {context}: HTTP {e.resp.status} が続くためスキップします", file=sys.stderr)
                return []
