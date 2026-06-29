# ai-wiki セットアップスクリプト
# 使い方: .\setup.ps1

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    [NG] $msg" -ForegroundColor Red }

$ok = $true

# ---- 1. Python バージョン確認 ------------------------------------------------
Write-Step "Python バージョン確認"
try {
    $ver = python --version 2>&1
    $match = $ver -match "Python (\d+)\.(\d+)"
    if ($match) {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
            Write-Ok "$ver"
        } else {
            Write-Fail "$ver（3.11 以上が必要です）"; $ok = $false
        }
    }
} catch {
    Write-Fail "python コマンドが見つかりません"; $ok = $false
}

# ---- 2. 依存パッケージインストール -------------------------------------------
Write-Step "依存パッケージのインストール"
python -m pip install -e ".[dev]" --quiet
Write-Ok "pip install 完了"

# ---- 3. .env ファイル確認 / 生成 ---------------------------------------------
Write-Step ".env ファイル確認"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn ".env.example をコピーしました → .env を編集して各値を設定してください"
} else {
    Write-Ok ".env が存在します"
}

# 必須キーのチェック
$required = @("DRIVE_FOLDER_ID", "GEMINI_API_KEY", "GROWI_BASE_URL", "GROWI_API_TOKEN")
$envContent = Get-Content ".env" -ErrorAction SilentlyContinue
foreach ($key in $required) {
    $line = $envContent | Where-Object { $_ -match "^$key=(.+)" }
    if ($line -and $Matches[1] -notmatch "^\s*$|your-|sk-ant-\.\.\.|AIza\.\.\.|1xxx") {
        Write-Ok "$key 設定済み"
    } else {
        Write-Warn "$key が未設定です"
    }
}

# ---- 4. サービスアカウント認証情報確認 -----------------------------------------
Write-Step "サービスアカウント認証情報確認"
$credPath = $envContent |
    Where-Object { $_ -match "^GOOGLE_APPLICATION_CREDENTIALS=(.+)" } |
    ForEach-Object { $Matches[1] }

if (-not $credPath) {
    $credPath = "credentials/service_account.json"
}

if (Test-Path $credPath) {
    Write-Ok "$credPath が存在します"
} else {
    Write-Warn "$credPath が見つかりません"
    Write-Host "        → GCP コンソールでサービスアカウントキーを作成し、$credPath に配置してください" -ForegroundColor Yellow
}

# ---- 5. テスト実行 -----------------------------------------------------------
Write-Step "テスト実行"
python -m pytest tests/ -q 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Ok "すべてのテストが通過しました"
} else {
    Write-Fail "テストが失敗しています"; $ok = $false
}

# ---- 結果サマリ --------------------------------------------------------------
Write-Host ""
if ($ok) {
    Write-Host "セットアップ完了。次のステップ:" -ForegroundColor Green
    Write-Host "  1. .env の未設定項目を埋める"
    Write-Host "  2. 共有ドライブにサービスアカウントを閲覧者として追加する"
    Write-Host "  3. python list_inventory.py dump.csv  # 文書一覧の確認"
    Write-Host "  4. python main.py                     # パイプライン実行"
} else {
    Write-Host "未解決の問題があります。上記の [!] / [NG] を確認してください。" -ForegroundColor Yellow
}
