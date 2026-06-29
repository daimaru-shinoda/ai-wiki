# ai-wiki setup script
# Usage: .\setup.ps1

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    [NG] $msg" -ForegroundColor Red }

$allOk = $true

# ---- 1. Python version -------------------------------------------------------
Write-Step "Python version check"
$pyver = python --version 2>&1
if ($pyver -match "Python (\d+)\.(\d+)") {
    $major = [int]$Matches[1]; $minor = [int]$Matches[2]
    if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
        Write-Ok "$pyver"
    } else {
        Write-Fail "$pyver  (requires 3.11+)"; $allOk = $false
    }
} else {
    Write-Fail "python not found"; $allOk = $false
}

# ---- 2. Install dependencies -------------------------------------------------
Write-Step "Install dependencies"
python -m pip install -e ".[dev]" --quiet
Write-Ok "pip install done"

# ---- 3. .env setup -----------------------------------------------------------
Write-Step ".env check"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn "Copied .env.example -> .env  (please fill in each value)"
} else {
    Write-Ok ".env exists"
}

$envLines = Get-Content ".env" -ErrorAction SilentlyContinue

$required = @("DRIVE_FOLDER_ID", "GEMINI_API_KEY", "GROWI_BASE_URL", "GROWI_API_TOKEN")
foreach ($key in $required) {
    $line = $envLines | Where-Object { $_ -match "^$key=(.+)" }
    if ($line -and ($Matches[1] -notmatch "your-|AIza\.\.\.|1xxx|\.\.\.$")) {
        Write-Ok "$key set"
    } else {
        Write-Warn "$key not configured"
    }
}

# ---- 4. Service account credentials -----------------------------------------
Write-Step "Service account credentials"
$credPath = "credentials/service_account.json"
$credLine = $envLines | Where-Object { $_ -match "^GOOGLE_APPLICATION_CREDENTIALS=(.+)" }
if ($credLine) { $credPath = $Matches[1] }

if (Test-Path $credPath) {
    Write-Ok "$credPath found"
} else {
    Write-Warn "$credPath not found"
    Write-Host "        -> Create a service account key in GCP Console and place it at $credPath" -ForegroundColor Yellow
}

# ---- 5. Run tests ------------------------------------------------------------
Write-Step "Run tests"
python -m pytest tests/ -q
if ($LASTEXITCODE -eq 0) {
    Write-Ok "All tests passed"
} else {
    Write-Fail "Some tests failed"; $allOk = $false
}

# ---- Summary -----------------------------------------------------------------
Write-Host ""
if ($allOk) {
    Write-Host "Setup complete. Next steps:" -ForegroundColor Green
    Write-Host "  1. Fill in any missing values in .env"
    Write-Host "  2. Share the shared drive with the service account (Viewer)"
    Write-Host "  3. python list_inventory.py dump.csv"
    Write-Host "  4. python main.py"
} else {
    Write-Host "Some issues remain. Check the [!] / [NG] items above." -ForegroundColor Yellow
}
