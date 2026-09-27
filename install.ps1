# Jarvis Agent installer for Windows (PowerShell)
# Installs: uv, Python 3.11, Node.js, ripgrep, ffmpeg

$ErrorActionPreference = "Stop"

$JARVIS_HOME = if ($env:JARVIS_HOME) { $env:JARVIS_HOME } else { "$env:LOCALAPPDATA\jarvis" }
$INSTALL_DIR = "$JARVIS_HOME\jarvis-agent"
$REPO = "https://github.com/AnkarIIT/OpenJarvis"

Write-Host "╔══════════════════════════════════════════════════════╗"
Write-Host "║         Jarvis Agent Installer                      ║"
Write-Host "║         https://github.com/AnkarIIT/OpenJarvis      ║"
Write-Host "╚══════════════════════════════════════════════════════╝"
Write-Host ""

Write-Host "[1/7] Checking prerequisites..."

# Check for PowerShell 5.1+
$psVersion = $PSVersionTable.PSVersion.Major
if ($psVersion -lt 5) {
    Write-Host "  PowerShell version too old. Please upgrade to PowerShell 5.1+."
    exit 1
}

# Check for git
git --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  git not found. Installing git..."
    winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to install git via winget. Please install git manually."
        Write-Host "  Download from: https://git-scm.com/download/win64"
        exit 1
    }
}

# Check for curl (Windows 10+ has curl built-in)
curl --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  curl not found."
    exit 1
}

# Check for unzip (Windows 10+ has tar, use tar for extraction)
tar --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  tar not found."
    exit 1
}

Write-Host "[2/7] Creating Jarvis home directory..."
New-Item -ItemType Directory -Force -Path $JARVIS_HOME | Out-Null
New-Item -ItemType Directory -Force -Path "$JARVIS_HOME\bin" | Out-Null

Write-Host "[3/7] Installing uv (Python package manager)..."
$UV_VERSION = "0.5.23"
$UV_URL = "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-pc-windows-msvc.zip"
$UV_ZIP = "$JARVIS_HOME\uv.zip"

Write-Host "  Downloading uv $UV_VERSION..."
Invoke-WebRequest -Uri $UV_URL -OutFile $UV_ZIP -UseBasicParsing

Write-Host "  Extracting uv..."
tar -xf $UV_ZIP -C $JARVIS_HOME
Remove-Item $UV_ZIP -Force

# Move uv.exe to bin
$uvExe = Get-ChildItem -Path "$JARVIS_HOME" -Filter "uv.exe" -Recurse -File | Select-Object -First 1
if ($uvExe) {
    Move-Item -Force -Path $uvExe.FullName -Destination "$JARVIS_HOME\bin\uv.exe"
}

$env:PATH = "$JARVIS_HOME\bin;$env:PATH"
Write-Host "  uv installed. Version: $(& "$JARVIS_HOME\bin\uv.exe" --version)"

Write-Host "[4/7] Creating Python virtual environment..."
$venvDir = "$JARVIS_HOME\venv"

if (-not (Test-Path "$venvDir\Scripts\python.exe")) {
    Write-Host "  Creating venv with Python 3.11..."
    & "$JARVIS_HOME\bin\uv.exe" venv $venvDir --python 3.11
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to create venv. Trying with system Python..."
        python -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to create venv. Please install Python 3.11+ and try again."
            exit 1
        }
    }
}

$env:VIRTUAL_ENV = $venvDir
$env:PATH = "$venvDir\Scripts;$env:PATH"

Write-Host "[5/7] Installing Jarvis Agent from git..."
if (Test-Path $INSTALL_DIR) {
    Write-Host "  Existing installation found at $INSTALL_DIR"
    Write-Host "  Updating..."
    Set-Location $INSTALL_DIR
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to update. Removing and re-cloning..."
        Remove-Item -Recurse -Force $INSTALL_DIR
        git clone $REPO $INSTALL_DIR
    }
} else {
    Write-Host "  Cloning repository..."
    git clone $REPO $INSTALL_DIR
}

Set-Location $INSTALL_DIR

Write-Host "[6/7] Installing dependencies..."
if (Test-Path "pyproject.toml") {
    & "$JARVIS_HOME\bin\uv.exe" pip install -e ".[all]" 
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to install dependencies. Trying basic install..."
        & "$JARVIS_HOME\bin\uv.exe" pip install -e .
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to install dependencies. Please check your Python environment."
            exit 1
        }
    }
} else {
    Write-Host "  pyproject.toml not found. Installing from setup.py..."
    & "$JARVIS_HOME\bin\uv.exe" pip install -e .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install. Please check the repository."
        exit 1
    }
}

Write-Host "[7/7] Setting up shell integration..."

# Add to user PATH permanently
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$JARVIS_HOME\bin*") {
    [Environment]::SetEnvironmentVariable("PATH", "$JARVIS_HOME\bin;$currentPath", "User")
    Write-Host "  Added $JARVIS_HOME\bin to user PATH"
}

if (Test-Path "$env:USERPROFILE\.bashrc") {
    $bashrc = Get-Content "$env:USERPROFILE\.bashrc"
    if ($bashrc -notmatch "JARVIS_HOME") {
        @"
# Jarvis Agent
export JARVIS_HOME="$JARVIS_HOME"
export PATH="$JARVIS_HOME\bin;$env:VIRTUAL_ENV\Scripts:\$PATH"
"@ | Add-Content -Path "$env:USERPROFILE\.bashrc"
        Write-Host "  Added to ~/.bashrc"
    }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗"
Write-Host "║              Installation Complete!                 ║"
Write-Host "╚══════════════════════════════════════════════════════╝"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart PowerShell or run: $env:PATH = `"$JARVIS_HOME\bin;$env:VIRTUAL_ENV\Scripts;$env:PATH`""
Write-Host "  2. Run: jarvis"
Write-Host ""
Write-Host "For updates: cd $INSTALL_DIR && git pull origin main"
Write-Host ""
Write-Host "Documentation: https://github.com/AnkarIIT/OpenJarvis/wiki"
