"""drive_lister.py のユニットテスト（Drive API はモック）。"""

import threading
from unittest.mock import MagicMock
from src.drive_lister import list_files

SAMPLE_FILES = [
    {
        "id": "file1",
        "name": "経費精算マニュアル.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "webViewLink": "https://drive.google.com/file/d/file1",
        "modifiedTime": "2026-06-01T00:00:00Z",
    },
    {
        "id": "file2",
        "name": "就業規則.pdf",
        "mimeType": "application/pdf",
        "webViewLink": "https://drive.google.com/file/d/file2",
        "modifiedTime": "2026-05-15T00:00:00Z",
    },
]


def _make_service(*responses: list[dict]):
    """execute() 呼び出しごとに responses を順番に返すモック（スレッドセーフ版）。"""
    lock = threading.Lock()
    queue = [{"files": r} for r in responses]

    def execute_side_effect():
        with lock:
            return queue.pop(0)

    service = MagicMock()
    service.files().list().execute.side_effect = execute_side_effect
    return service


# ---- 非再帰 ---------------------------------------------------------------- #

def test_list_files_returns_files():
    service = _make_service(SAMPLE_FILES)
    result = list_files("folder123", service)
    assert len(result) == 2
    assert result[0]["id"] == "file1"


def test_list_files_empty_folder():
    service = _make_service([])
    result = list_files("folder123", service)
    assert result == []


def test_list_files_passes_folder_id():
    service = _make_service(SAMPLE_FILES)
    list_files("folder_xyz", service)
    call_kwargs = service.files().list.call_args
    assert "folder_xyz" in call_kwargs.kwargs.get("q", "") or \
           "folder_xyz" in str(call_kwargs)


def test_list_files_adds_folder_path_empty_for_root():
    service = _make_service(SAMPLE_FILES)
    result = list_files("folder123", service)
    assert all(f["folder_path"] == "" for f in result)


# ---- 再帰（max_workers=1 で決定的に検証） ---------------------------------- #

def test_list_files_recursive_finds_subfolder_files():
    subfolder = {"id": "sub1", "name": "サブフォルダ"}
    sub_file = {
        "id": "file3",
        "name": "議事録.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "webViewLink": "https://drive.google.com/file/d/file3",
        "modifiedTime": "2026-06-10T00:00:00Z",
    }
    service = _make_service(
        SAMPLE_FILES,  # ルートのファイル
        [subfolder],   # ルートのサブフォルダ
        [sub_file],    # サブフォルダのファイル
        [],            # サブフォルダのサブフォルダ（なし）
    )
    result = list_files("root", service, recursive=True, max_workers=1)

    assert len(result) == 3
    root_files = [f for f in result if f["folder_path"] == ""]
    sub_files  = [f for f in result if f["folder_path"] == "サブフォルダ"]
    assert len(root_files) == 2
    assert len(sub_files) == 1
    assert sub_files[0]["id"] == "file3"


def test_list_files_recursive_nested_path():
    parent = {"id": "sub1", "name": "親フォルダ"}
    child  = {"id": "sub2", "name": "子フォルダ"}
    deep_file = {
        "id": "file_deep",
        "name": "深いファイル.pdf",
        "mimeType": "application/pdf",
        "webViewLink": "https://drive.google.com/file/d/deep",
        "modifiedTime": "2026-06-01T00:00:00Z",
    }
    service = _make_service(
        [],           # ルートのファイル
        [parent],     # ルートのサブフォルダ
        [],           # 親フォルダのファイル
        [child],      # 親フォルダのサブフォルダ
        [deep_file],  # 子フォルダのファイル
        [],           # 子フォルダのサブフォルダ
    )
    result = list_files("root", service, recursive=True, max_workers=1)

    assert len(result) == 1
    assert result[0]["folder_path"] == "親フォルダ/子フォルダ"


def test_list_files_recursive_avoids_cycle():
    subfolder = {"id": "root", "name": "自己参照"}
    service = _make_service(
        [],           # ルートのファイル
        [subfolder],  # ルートのサブフォルダ（root 自身を指す）
    )
    result = list_files("root", service, recursive=True, max_workers=1)
    assert result == []


# ---- 並列（件数の一致のみ検証） -------------------------------------------- #

def test_list_files_parallel_same_count_as_sequential():
    """max_workers > 1 でも件数が変わらないことを確認する。"""
    subfolder = {"id": "sub1", "name": "並列テスト"}
    sub_file = {
        "id": "file3",
        "name": "並列ファイル.pdf",
        "mimeType": "application/pdf",
        "webViewLink": "https://drive.google.com/file/d/file3",
        "modifiedTime": "2026-06-10T00:00:00Z",
    }

    def make():
        return _make_service(SAMPLE_FILES, [subfolder], [sub_file], [])

    result_seq = list_files("root", make(), recursive=True, max_workers=1)
    result_par = list_files("root", make(), recursive=True, max_workers=4)

    assert len(result_seq) == len(result_par) == 3
