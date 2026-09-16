# One-command Windows bootstrapper for OpenJarvis.
# Intended invocation:
# irm https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/scripts/install_windows.ps1 | iex

$ErrorActionPreference = "Stop"

function Find-Python {
    $candidates = @(
        @{ command = "py"; args = @("-3.12") },
        @{ command = "py"; args = @("-3.13") },
        @{ command = "py"; args = @("-3.11") },
        @{ command = "py"; args = @("-3.10") },
        @{ command = "python"; args = @() }
    )
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.command -ErrorAction SilentlyContinue)) {
            continue
        }
        try {
            & $candidate.command @($candidate.args) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
            if ($LASTEXITCODE -eq 0) {
                if ($candidate.args.Count -gt 0) {
                    $pythonPath = (& $candidate.command @($candidate.args) -c "import sys; print(sys.executable)").Trim()
                    if ($pythonPath) {
                        return $pythonPath
                    }
                }
                return (Get-Command $candidate.command).Source
            }
        } catch {
            continue
        }
    }
    return $null
}

function Install-WingetPackage([string]$Id) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Neither a supported Python installation nor winget was found. Install Python 3.10+ from https://www.python.org/downloads/windows/"
    }
    Write-Host "Installing $Id through winget..."
    & winget install --id $Id --exact --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed to install $Id (exit code $LASTEXITCODE)"
    }
}

Write-Host "OpenJarvis Windows installer" -ForegroundColor Cyan
$python = Find-Python
if (-not $python) {
    Install-WingetPackage "Python.Python.3.12"
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [Environment]::GetEnvironmentVariable("Path", "User")
    $python = Find-Python
}
if (-not $python) {
    throw "Python 3.10 or newer was installed but is not visible in this PowerShell session. Reopen PowerShell and run the command again."
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Install-WingetPackage "Git.Git"
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [Environment]::GetEnvironmentVariable("Path", "User")
}

Write-Host "Using Python command: $python"
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

Write-Host "Installing OpenJarvis and supported optional components..."
& $python -m pip install --upgrade "jarvis-tui[all] @ git+https://github.com/AnkarIIT/OpenJarvis.git"
if ($LASTEXITCODE -ne 0) { throw "OpenJarvis installation failed" }

Write-Host "Installing Playwright browser runtime..."
& $python -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Chromium installation failed; browser tools will remain unavailable until installed manually."
}

Write-Host "Running diagnostics..."
& $python -m jarvis.main doctor --json
if ($LASTEXITCODE -ne 0) { throw "JARVIS diagnostics failed" }

Write-Host ""
Write-Host "OpenJarvis installation complete." -ForegroundColor Green
Write-Host "Start with: jarvis"
Write-Host "If 'jarvis' is not recognized, use: $python -m jarvis.main"
