# CLAUDE.md

Drive 上の社内文書を AI で読み取り、GROWI に「案内ページ」を自動生成するパイプラインを構築するプロジェクト。

## このプロジェクトの目的

- 原本は Google Drive に置いたまま（Single Source of Truth）。
- GROWI には文書本体をコピーせず、「何があるか・どこにあるか・どう使うか・誰に聞くか」だけを書いて Drive へリンクする。
- 新規参入者のオンボーディング導線を作るのが主目的。
- まず **マーケティング部署** で始め、うまくいけば他部署へ横展開する（同一 wiki ではなく分ける可能性あり）。

## 開発方針

- **言語: Python**
- **TDD で進める。** 失敗するテストを先に書き、最小実装で通し、リファクタする。
- API 系（Drive / GROWI / AI）はモックで分離し、純粋関数（整形・スキーマ検証）を主要なテスト対象にする。
- `pytest` を使用。
- AI に推測させてよい範囲と、メタデータ由来で確定させる範囲を厳密に分ける（幻覚防止）。

## アーキテクチャ（パイプライン）

Drive 列挙 → 本文抽出 → 種別判定＋構造化(AI) → Markdown 整形 → GROWI 投入。

ユニット分割（各 TDD）:

1. **drive_lister** — フォルダ内の文書一覧とメタデータ取得（Drive API / モック）
2. **extractor** — docx / PDF / Google ドキュメント → テキスト
3. **classifier** — AI で種別判定＋構造化。出力 JSON をスキーマ検証
4. **formatter** — 中間 JSON ＋ Drive メタデータ ＋ プレフィルフォーム URL → 種別別 Markdown（**純粋関数 / 最優先でテスト**）
5. **growi_writer** — GROWI ページの作成 / 更新。冪等に行う（Drive API / モック）

着手順のおすすめ: 依存の少ない **formatter** から。入力 JSON → 期待 Markdown のテストが書きやすく、テンプレ 4 種を固められる。その後、外側の API 連携へ広げる。

## GROWI ページツリー

```
/onboarding              ← 新人が最初に開く入口（手書き、自動生成対象外）
  /onboarding/day1       ← 初日にやること（申請・アカウント・読む順）
  /onboarding/glossary   ← 用語集
  /onboarding/who-is-who ← 誰が何の担当か
  /onboarding/faq        ← つまずき FAQ
/docs/marketing/{種別}/{文書名}   ← 本パイプラインが自動生成する領域
  種別: sop（手順書） / policy（規程） / minutes（議事録） / faq（FAQ）
```

- **部署は分類軸ではなく上位スコープ**として持つ（メタデータ＋ツリー最上位）。将来 `/docs/marketing` 配下をまるごと別 wiki にエクスポートできるようにするため。
- 分類は「業務テーマ別」ではなく **文書種別（sop/policy/minutes/faq）を AI に判定させる**。
- 部署（department=marketing）は実行時に外から与える。**AI に推測させない。**

## 中間 JSON スキーマ

メタデータ由来（AI に推測させない）:

- `drive_url` — Drive API から
- `last_updated` — Drive API から
- `department` — 実行時に外部付与（例: marketing）

AI 生成（共通）:

- `doc_type` — sop / policy / minutes / faq
- `title`
- `summary` — これは何の文書か（1〜2 行）
- `audience` — 対象読者（配列）
- `key_points` — 要点（3〜5 点の配列）
- `related` — 関連文書（配列）

種別差分:

- **sop**: 追加なし
- **policy**: `scope`（適用範囲）
- **minutes**: `decisions`（決定事項）, `todos`
- **faq**: `questions`（想定質問）

例:

```json
{
  "doc_type": "sop",
  "title": "経費精算マニュアル",
  "summary": "経費を申請・精算する手順をまとめた文書",
  "audience": ["新人", "全員"],
  "key_points": ["申請は月末締め", "領収書は電子提出"],
  "related": ["出張旅費規程"]
}
```

## 案内ページ Markdown テンプレート

共通土台＋種別差分。ページ全体が自動生成領域（人間が書くブロックの保護は不要 = formatter にマージ処理は不要）。各ページ末尾に改善提案フォームへのリンクを固定で置く。

共通ヘッダ:

```markdown
# {title}

> {summary}

- **対象読者**: {audience}
- **原本**: [Drive で開く]({drive_url})
- **最終更新**: {last_updated}
- **カテゴリ**: {doc_type}

## 要点

- {key_points}
```

種別ごとの追加セクション:

- **sop**: `## 改善提案` セクション（フォームリンク。後述）
- **policy**: `## 適用範囲`（scope）＋ 改訂時の確認を促す文言
- **minutes**: `## 決定事項`（decisions）＋ `## TODO`（todos）。改善提案リンクは基本なし（記録のため）
- **faq**: `## 想定質問`（questions）。一覧性重視

末尾共通（minutes 以外）:

```markdown
## この文書を改善する

気づいた点があれば改善提案を送ってください → [改善提案フォーム]({prefilled_form_url})
```

## 改善提案の受け皿

- 保存先は **Google Form → スプレッドシート**（承認・否認の経緯を構造化データで残すため）。
- GROWI 側はフォームへリンクするだけ。
- **formatter は各ページのフォーム URL に対象文書を事前入力（プレフィル）する。** Drive ファイル ID をプレフィル URL に埋め込み、提案者がどの文書か選ぶ手間と取り違えをなくす。

フォーム項目（提案者入力）:

- 対象文書（GROWI ページ URL or Drive ファイル ID。プレフィル）
- 提案者
- 提案内容
- 提案日

シート側の運用列:

- ステータス（未対応 / 承認 / 否認）
- 対応者
- 判断理由（否認の経緯もここに残る）
- 対応日

## 運用ループ（崩してはいけない原則）

提案 → **Drive 原本を更新** → パイプライン再実行で案内ページ再生成。

- 改善提案が GROWI の案内ページだけを書き換えて原本と乖離しないこと。
- 案内ページは再生成で上書きされる前提なので、提案内容はフォーム/シート側に溜める。

## 環境メモ

- GCP / Google Workspace を利用（Drive 連携は google-api-python-client 想定）。
- GROWI は GCE 1 台 + docker-compose（本体 + MongoDB + Elasticsearch）で別途構築予定。アクセス制御は IAP or VPN を検討中（本パイプラインの実装範囲外）。
