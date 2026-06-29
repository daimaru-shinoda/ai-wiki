"""Google Drive API 認証ヘルパー（サービスアカウント）。"""

from __future__ import annotations
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def build_drive_service(credentials_path: str | Path | None = None):
    """Drive API サービスオブジェクトを返す。

    credentials_path を省略すると環境変数 GOOGLE_APPLICATION_CREDENTIALS を使う。
    """
    path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not path:
        raise ValueError(
            "認証情報が見つかりません。GOOGLE_APPLICATION_CREDENTIALS 環境変数を設定するか"
            " credentials_path を指定してください。"
        )
    creds = service_account.Credentials.from_service_account_file(
        str(path), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)
