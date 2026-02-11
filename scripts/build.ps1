<#
.SYNOPSIS
    Builds shruggie-feedtools release executables using PyInstaller.
.DESCRIPTION
    Compiles CLI and/or GUI executables. Optionally copies versioned
    artifacts to dist/release/ for GitHub release publishing.
.PARAMETER Target
    Build target: "cli", "gui", or "all". Default: "all"
.PARAMETER Release
    Copy final artifacts to dist/release/ with versioned filenames.
.PARAMETER Clean
    Delete build/ and dist/ directories before building.
.EXAMPLE
    ./scripts/build.ps1
    ./scripts/build.ps1 -Target cli -Release
    ./scripts/build.ps1 -Clean -Release
#>
[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Build target: cli, gui, or all")]
    [ValidateSet("cli", "gui", "all")]
    [string]$Target = "all",

    [Parameter(HelpMessage = "Copy artifacts to dist/release/ with versioned filenames")]
    [switch]$Release,

    [Parameter(HelpMessage = "Clean build directories before building")]
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$StartTime = Get-Date

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

Write-Host "Ensuring virtual environment is ready..." -ForegroundColor Cyan
& (Join-Path $ScriptDir "venv-setup.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Error "venv-setup.ps1 failed. Cannot build."
    exit 1
}

$VenvDir = Join-Path $ProjectRoot ".venv"
$ActivateScript = Join-Path $VenvDir "Scripts" "Activate.ps1"
& $ActivateScript

# ---------------------------------------------------------------------------
# Read version from _version.py
# ---------------------------------------------------------------------------

$VersionFile = Join-Path $ProjectRoot "src" "shruggie_feedtools" "_version.py"
$VersionContent = Get-Content $VersionFile -Raw
if ($VersionContent -match '__version__\s*=\s*"([^"]+)"') {
    $Version = $Matches[1]
}
else {
    Write-Error "Could not extract version from $VersionFile"
    exit 1
}

Write-Host "Building shruggie-feedtools v$Version" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Clean if requested
# ---------------------------------------------------------------------------

if ($Clean) {
    $BuildDir = Join-Path $ProjectRoot "build"
    $DistDir = Join-Path $ProjectRoot "dist"

    if (Test-Path $BuildDir) {
        Write-Host "Removing build/ ..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $BuildDir
    }
    if (Test-Path $DistDir) {
        if ($Release) {
            # Remove everything in dist/ except release/
            Get-ChildItem $DistDir -Exclude "release" | Remove-Item -Recurse -Force
        }
        else {
            Write-Host "Removing dist/ ..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $DistDir
        }
    }
}

# ---------------------------------------------------------------------------
# Build targets
# ---------------------------------------------------------------------------

Push-Location $ProjectRoot
$VenvPython = Join-Path $VenvDir "Scripts" "python.exe"

try {
    if ($Target -eq "cli" -or $Target -eq "all") {
        Write-Host "Building CLI target..." -ForegroundColor Cyan
        & $VenvPython -m PyInstaller `
            --onefile `
            --name "shruggie-feedtools-cli" `
            --console `
            (Join-Path "src" "shruggie_feedtools" "__main__.py")

        if ($LASTEXITCODE -ne 0) {
            Write-Error "PyInstaller CLI build failed."
            exit 1
        }
        Write-Host "CLI build complete." -ForegroundColor Green
    }

    if ($Target -eq "gui" -or $Target -eq "all") {
        Write-Host "Building GUI target..." -ForegroundColor Cyan
        & $VenvPython -m PyInstaller `
            --onefile `
            --name "shruggie-feedtools-gui" `
            --windowed `
            --add-data "src/shruggie_feedtools/gui;shruggie_feedtools/gui" `
            (Join-Path "src" "shruggie_feedtools" "gui" "app.py")

        if ($LASTEXITCODE -ne 0) {
            Write-Error "PyInstaller GUI build failed."
            exit 1
        }
        Write-Host "GUI build complete." -ForegroundColor Green
    }
}
finally {
    Pop-Location
}

# ---------------------------------------------------------------------------
# Release artifacts
# ---------------------------------------------------------------------------

if ($Release) {
    $ReleaseDir = Join-Path $ProjectRoot "dist" "release"
    if (-not (Test-Path $ReleaseDir)) {
        New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
    }

    $Arch = if ([System.Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }

    if ($Target -eq "cli" -or $Target -eq "all") {
        $CliSrc = Join-Path $ProjectRoot "dist" "shruggie-feedtools-cli.exe"
        $CliDst = Join-Path $ReleaseDir "shruggie-feedtools-cli-$Version-win-$Arch.exe"
        if (Test-Path $CliSrc) {
            Copy-Item $CliSrc $CliDst -Force
            $Size = (Get-Item $CliDst).Length
            Write-Host "  CLI: $CliDst ($Size bytes)" -ForegroundColor Green
        }
    }

    if ($Target -eq "gui" -or $Target -eq "all") {
        $GuiSrc = Join-Path $ProjectRoot "dist" "shruggie-feedtools-gui.exe"
        $GuiDst = Join-Path $ReleaseDir "shruggie-feedtools-gui-$Version-win-$Arch.exe"
        if (Test-Path $GuiSrc) {
            Copy-Item $GuiSrc $GuiDst -Force
            $Size = (Get-Item $GuiDst).Length
            Write-Host "  GUI: $GuiDst ($Size bytes)" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

$Elapsed = (Get-Date) - $StartTime
Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "  Target: $Target"
Write-Host "  Version: $Version"
Write-Host "  Duration: $($Elapsed.TotalSeconds.ToString('F1'))s"
