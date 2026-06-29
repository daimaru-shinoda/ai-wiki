"""パイプライン実行エントリポイント。"""

import os
from dotenv import load_dotenv
from src.auth import build_drive_service
from src.growi_writer import GrowiWriter
from src.pipeline import run

load_dotenv()

def main():
    service = build_drive_service()
    growi = GrowiWriter(
        base_url=os.environ["GROWI_BASE_URL"],
        api_token=os.environ["GROWI_API_TOKEN"],
    )

    print("パイプライン開始...")
    updated = run(
        folder_id=os.environ["DRIVE_FOLDER_ID"],
        department=os.environ.get("DEPARTMENT", "marketing"),
        drive_service=service,
        growi=growi,
        form_base_url=os.environ.get("FORM_BASE_URL", ""),
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
    )

    print(f"\n完了: {len(updated)} ページを更新しました")
    for path in updated:
        print(f"  {path}")


if __name__ == "__main__":
    main()
