<#
.SYNOPSIS
    Runs the shruggie-feedtools test suite with colored output.
.DESCRIPTION
    Executes pytest with per-test verbosity, colored pass/fail indicators,
    and a summary report. Supports silent mode for CI pipelines.
.PARAMETER Silent
    Suppress all output. Only exit code is emitted. Use in CI/CD pipelines.
.PARAMETER Coverage
    Generate a coverage report alongside test results.
.PARAMETER Filter
    pytest -k expression to run a subset of tests.
.PARAMETER FailFast
    Stop on first test failure.
.EXAMPLE
    ./scripts/test.ps1
    ./scripts/test.ps1 -Coverage -FailFast
    ./scripts/test.ps1 -Silent
    ./scripts/test.ps1 -Filter "test_dates"
#>
[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Suppress output, exit code only")]
    [switch]$Silent,

    [Parameter(HelpMessage = "Generate coverage report")]
    [switch]$Coverage,

    [Parameter(HelpMessage = "pytest -k filter expression")]
    [string]$Filter,

    [Parameter(HelpMessage = "Stop on first failure")]
    [switch]$FailFast
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Locate project root
# ---------------------------------------------------------------------------

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $ScriptDir

while ($ProjectRoot -ne "") {
    if (Test-Path (Join-Path $ProjectRoot "pyproject.toml")) {
        break
    }
    $Parent = Split-Path -Parent $ProjectRoot
    if ($Parent -eq $ProjectRoot) {
        Write-Error "Could not find pyproject.toml in any parent directory."
        exit 1
    }
    $ProjectRoot = $Parent
}

# ---------------------------------------------------------------------------
# Ensure venv is ready
# ---------------------------------------------------------------------------

& (Join-Path $ScriptDir "venv-setup.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Error "venv-setup.ps1 failed. Cannot run tests."
    exit 1
}

$VenvDir = Join-Path $ProjectRoot ".venv"
$ActivateScript = Join-Path $VenvDir "Scripts" "Activate.ps1"
& $ActivateScript

$VenvPython = Join-Path $VenvDir "Scripts" "python.exe"

# ---------------------------------------------------------------------------
# Silent mode — minimal output
# ---------------------------------------------------------------------------

if ($Silent) {
    & $VenvPython -m pytest --tb=no --no-header -q
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Build pytest command
# ---------------------------------------------------------------------------

$PythonVersion = & $VenvPython --version 2>&1
$Timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor White
Write-Host "  shruggie-feedtools Test Suite" -ForegroundColor White
Write-Host "  $PythonVersion | $Timestamp" -ForegroundColor DarkGray
Write-Host ("=" * 60) -ForegroundColor White
Write-Host ""

$PytestArgs = @("--tb=short", "-v")

if ($Coverage) {
    $PytestArgs += "--cov=shruggie_feedtools"
    $PytestArgs += "--cov-report=term-missing"
}

if ($Filter) {
    $PytestArgs += "-k"
    $PytestArgs += $Filter
}

if ($FailFast) {
    $PytestArgs += "-x"
}

# ---------------------------------------------------------------------------
# Run pytest and capture output
# ---------------------------------------------------------------------------

$StartTime = Get-Date

& $VenvPython -m pytest @PytestArgs 2>&1 | ForEach-Object {
    $line = $_
    if ($line -match "PASSED") {
        Write-Host "  ✓ PASS  " -NoNewline -ForegroundColor Green
        Write-Host ($line -replace "PASSED", "").Trim()
    }
    elseif ($line -match "FAILED") {
        Write-Host "  ✗ FAIL  " -NoNewline -ForegroundColor Red
        Write-Host ($line -replace "FAILED", "").Trim()
    }
    elseif ($line -match "SKIPPED") {
        Write-Host "  ○ SKIP  " -NoNewline -ForegroundColor Yellow
        Write-Host ($line -replace "SKIPPED", "").Trim()
    }
    elseif ($line -match "^tests[\\/]") {
        Write-Host ""
        Write-Host "  $line" -ForegroundColor White
    }
    else {
        Write-Host "  $line"
    }
}

$ExitCode = $LASTEXITCODE
$Elapsed = (Get-Date) - $StartTime

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor White

if ($ExitCode -eq 0) {
    Write-Host "  ALL TESTS PASSED" -ForegroundColor Green
}
else {
    Write-Host "  SOME TESTS FAILED" -ForegroundColor Red
}

Write-Host "  Duration: $($Elapsed.TotalSeconds.ToString('F1'))s" -ForegroundColor DarkGray
Write-Host ("=" * 60) -ForegroundColor White
Write-Host ""

exit $ExitCode
