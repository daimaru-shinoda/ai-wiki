"""Drive フォルダ内の文書一覧を CSV で出力する。

ファイル名から種別を軽量推測するだけで、テキスト抽出・AI 呼び出しは行わない。
UTF-8 BOM 付きで書き出すため Excel・Google Sheets どちらでも文字化けしない。

使い方:
    python list_inventory.py                        # コンソール出力
    python list_inventory.py dump.csv               # ファイル保存
    python list_inventory.py dump.csv --workers 4   # 並列数指定
"""

from __future__ import annotations
import argparse
import csv
import os
import sys
from dotenv import load_dotenv

from src.auth import build_drive_service
from src.drive_lister import list_files
from src.state import load as load_state

load_dotenv()

# ---- 種別推測キーワード ---------------------------------------------------- #

_RULES: list[tuple[str, list[str]]] = [
    ("議事録", ["議事録", "会議", "ミーティング", "定例", "mtg", "打ち合わせ", "minutes"]),
    ("FAQ",   ["faq", "よくある質問", "q&a", "qa", "質問集"]),
    ("規程",  ["規程", "規則", "方針", "ポリシー", "基準", "規定", "policy"]),
    ("手順書", ["マニュアル", "手順", "ガイド", "方法", "how", "sop", "手引き", "フロー"]),
]


def guess_doc_type(filename: str) -> str:
    lower = filename.lower()
    for doc_type, keywords in _RULES:
        if any(kw in lower for kw in keywords):
            return doc_type
    return "要確認"


# ---- MIME タイプ表示名 ------------------------------------------------------ #

_MIME_LABEL = {
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
    "application/pdf": "PDF",
}


def mime_label(mime: str) -> str:
    return _MIME_LABEL.get(mime, mime)


# ---- CSV 出力 -------------------------------------------------------------- #

HEADERS = ["フォルダ", "ファイル名", "形式", "更新日", "種別（推測）", "処理済", "Drive URL"]


def build_rows(files: list[dict], state: dict) -> list[list[str]]:
    rows = []
    for f in files:
        rows.append([
            f.get("folder_path", ""),
            f["name"],
            mime_label(f["mimeType"]),
            f["modifiedTime"][:10],
            guess_doc_type(f["name"]),
            "✓" if f["id"] in state else "",
            f.get("webViewLink", ""),
        ])
    return rows


def write_csv(files: list[dict], state: dict, dest: str | None) -> None:
    rows = build_rows(files, state)
    if dest:
        with open(dest, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp)
            w.writerow(HEADERS)
            w.writerows(rows)
        print(f"保存しました: {dest}", file=sys.stderr)
    else:
        # stdout へ出力（パイプ用。BOM なし utf-8）
        w = csv.writer(sys.stdout)
        w.writerow(HEADERS)
        w.writerows(rows)


# ---- 診断 ------------------------------------------------------------------ #

def _diagnose(folder_id: str, service) -> None:
    print("\n[診断] フォルダ内の全アイテムを確認しています...", file=sys.stderr)
    q = f"'{folder_id}' in parents and trashed = false"
    result = service.files().list(
        q=q, fields="files(id, name, mimeType)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    items = result.get("files", [])

    if not items:
        print(
            "[診断] フォルダ直下にアイテムがありません。\n"
            "  考えられる原因:\n"
            "  - DRIVE_FOLDER_ID が間違っている\n"
            "  - サービスアカウントがフォルダに共有されていない\n"
            "  → Drive でフォルダを開き、サービスアカウントのメールアドレスに閲覧権限を付与してください",
            file=sys.stderr,
        )
    else:
        print(f"[診断] {len(items)} 件のアイテムが見つかりましたが、対象MIMEタイプ外です:", file=sys.stderr)
        for item in items:
            print(f"  - {item['name']}  ({item['mimeType']})", file=sys.stderr)
        print(
            "\n  対応形式: Google ドキュメント / Word(.docx) / PDF\n"
            "  上記以外（スプレッドシート・スライド等）は現在スキップされます",
            file=sys.stderr,
        )


# ---- main ------------------------------------------------------------------ #

def main() -> None:
    folder_id = os.environ.get("DRIVE_FOLDER_ID")
    if not folder_id:
        print("エラー: DRIVE_FOLDER_ID が設定されていません（.env を確認してください）", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Drive フォルダ内の文書一覧を CSV で出力する")
    parser.add_argument("output", nargs="?", help="出力先 CSV ファイル（省略時はコンソール）")
    parser.add_argument("--workers", type=int, default=4, metavar="N", help="並列フォルダ取得数（デフォルト: 4）")
    args = parser.parse_args()

    svc = build_drive_service()

    # ルートフォルダ名を取得してパスの基点にする
    root_meta = svc.files().get(
        fileId=folder_id, fields="name", supportsAllDrives=True
    ).execute()
    root_name = root_meta["name"]
    print(f"ルートフォルダ: {root_name}", file=sys.stderr)

    print(f"ファイル一覧を取得中... (並列数: {args.workers})", file=sys.stderr)
    files = list_files(folder_id, recursive=True, max_workers=args.workers, service_factory=build_drive_service)
    state = load_state()

    print(f"{len(files)} 件取得しました", file=sys.stderr)
    if not files:
        _diagnose(folder_id, svc)
        return

    # folder_path にルートフォルダ名を付加する
    for f in files:
        sub = f.get("folder_path", "")
        f["folder_path"] = f"{root_name}/{sub}" if sub else root_name

    write_csv(files, state, args.output)


if __name__ == "__main__":
    main()
