"""各種ファイル形式からテキストを抽出する関数群。"""

from __future__ import annotations
import io
import os
from pathlib import Path


def _download_drive_file(file_id: str, service) -> bytes:
    from googleapiclient.http import MediaIoBaseDownload
    buf = io.BytesIO()
    request = service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def extract_pdf_bytes(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ocr_pdf_bytes(data: bytes, gemini_api_key: str | None = None) -> str:
    """Gemini に PDF を渡してテキストを OCR 抽出する。"""
    from google import genai
    from google.genai import types
    api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 環境変数が設定されていません。")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[
            types.Part.from_bytes(data=data, mime_type="application/pdf"),
            "この文書に含まれるテキストをすべて抽出してください。レイアウトは無視してテキストのみを出力してください。",
        ],
    )
    return response.text


def extract_google_doc(file_id: str, service) -> str:
    """Drive API service を使って Google ドキュメントをプレーンテキストで取得。"""
    data = (
        service.files()
        .export(fileId=file_id, mimeType="text/plain")
        .execute()
    )
    return data.decode("utf-8") if isinstance(data, bytes) else data


def extract(file_meta: dict, service=None, gemini_api_key: str | None = None) -> str:
    """file_meta（drive_lister の出力）からテキストを抽出する。

    スキャン PDF は Gemini OCR にフォールバックする。
    file_meta は {"id": ..., "mimeType": ..., "name": ...} の形式。
    """
    mime = file_meta.get("mimeType", "")
    file_id = file_meta["id"]

    if mime == "application/vnd.google-apps.document":
        return extract_google_doc(file_id, service)

    if mime == "application/pdf":
        data = _download_drive_file(file_id, service)
        text = extract_pdf_bytes(data)
        if text.strip():
            return text
        # テキスト層がない → Gemini OCR にフォールバック
        return ocr_pdf_bytes(data, gemini_api_key)

    if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        data = _download_drive_file(file_id, service)
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    raise ValueError(f"Unsupported mimeType: {mime!r}")
