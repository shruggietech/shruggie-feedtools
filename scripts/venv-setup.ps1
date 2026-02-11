<#
.SYNOPSIS
    Sets up the Python virtual environment for shruggie-feedtools development.
.DESCRIPTION
    Checks for an existing .venv directory, validates the Python version,
    and creates/recreates the virtual environment as needed. Installs all
    development and GUI dependencies via editable install.
.PARAMETER PythonCmd
    Python interpreter command to use for venv creation. Default: "python"
.PARAMETER Force
    Force recreation of the virtual environment even if it already exists.
.EXAMPLE
    ./scripts/venv-setup.ps1
    ./scripts/venv-setup.ps1 -PythonCmd "py -3.12" -Force
#>
[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Python interpreter command")]
    [string]$PythonCmd = "python",

    [Parameter(HelpMessage = "Force recreation of virtual environment")]
    [switch]$Force
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

$VenvDir = Join-Path $ProjectRoot ".venv"
$ActivateScript = Join-Path $VenvDir "Scripts" "Activate.ps1"

# ---------------------------------------------------------------------------
# Helper: check Python version >= 3.12
# ---------------------------------------------------------------------------

function Test-PythonVersion {
    param([string]$Interpreter)

    try {
        $versionOutput = & $Interpreter --version 2>&1
        if ($versionOutput -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                return $true
            }
            Write-Warning "Python >=3.12 is required. Found: Python $major.$minor. Install from https://python.org"
            return $false
        }
        Write-Warning "Could not parse Python version from: $versionOutput"
        return $false
    }
    catch {
        Write-Error "Python interpreter '$Interpreter' not found. Install Python >=3.12 from https://python.org"
        return $false
    }
}

# ---------------------------------------------------------------------------
# Check if venv already exists and is valid
# ---------------------------------------------------------------------------

if ((Test-Path $VenvDir) -and -not $Force) {
    # Verify the Python version inside the venv
    $VenvPython = Join-Path $VenvDir "Scripts" "python.exe"
    if (Test-Path $VenvPython) {
        if (Test-PythonVersion -Interpreter $VenvPython) {
            Write-Host "Virtual environment OK: $VenvDir" -ForegroundColor Green
            exit 0
        }
        else {
            Write-Warning "Existing venv has wrong Python version. Recreating..."
            Remove-Item -Recurse -Force $VenvDir
        }
    }
    else {
        Write-Warning "Existing venv is missing python.exe. Recreating..."
        Remove-Item -Recurse -Force $VenvDir
    }
}

# ---------------------------------------------------------------------------
# Validate the requested Python interpreter
# ---------------------------------------------------------------------------

if (-not (Test-PythonVersion -Interpreter $PythonCmd)) {
    exit 1
}

# ---------------------------------------------------------------------------
# Create the virtual environment
# ---------------------------------------------------------------------------

if ($Force -and (Test-Path $VenvDir)) {
    Write-Host "Removing existing venv (--Force)..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvDir
}

Write-Host "Creating virtual environment at $VenvDir ..." -ForegroundColor Cyan
& $PythonCmd -m venv $VenvDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create virtual environment."
    exit 1
}

# ---------------------------------------------------------------------------
# Activate and install
# ---------------------------------------------------------------------------

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& $ActivateScript

Write-Host "Upgrading pip..." -ForegroundColor Cyan
& (Join-Path $VenvDir "Scripts" "python.exe") -m pip install --upgrade pip

Write-Host "Installing shruggie-feedtools in editable mode with dev and GUI extras..." -ForegroundColor Cyan
Push-Location $ProjectRoot
try {
    & (Join-Path $VenvDir "Scripts" "pip.exe") install -e ".[dev,gui]"
}
finally {
    Pop-Location
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed."
    exit 1
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Virtual environment ready: $VenvDir" -ForegroundColor Green
& (Join-Path $VenvDir "Scripts" "python.exe") --version
& (Join-Path $VenvDir "Scripts" "pip.exe") list --format=columns
