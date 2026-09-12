# Requires PowerShell 7+ or Windows PowerShell 5.1+
# Run with: powershell -ExecutionPolicy Bypass -File scripts/setup_friend.ps1
# Or: .\scripts\setup_friend.ps1

# Complete setup for a friend who just cloned OpenJarvis.
# Run this on a fresh clone to get everything working.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗"
Write-Host "║   JARVIS - Friend Setup Script           ║"
Write-Host "╚══════════════════════════════════════════╝"
Write-Host ""

# Step 0: Ensure pipx is available
Write-Host "[0/5] Ensuring pipx is available..."
$pipxExists = Get-Command pipx -ErrorAction SilentlyContinue
if (-not $pipxExists) {
    Write-Host "pipx not found, installing..."
    python -m pip install --user pipx
    # Add pipx to PATH on Windows
    $pythonScripts = python -c "import sys, site; print(site.getusersitepackages().replace('site-packages', 'Scripts'))"
    Write-Host "Add this to PATH: $pythonScripts"
    Write-Host "Run: [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';$pythonScripts', 'User')"
    Write-Host "Or restart PowerShell after adding to PATH."
}

# Step 0b: Install JARVIS via pipx if available, else fallback to pip
Write-Host ""
Write-Host "[0.5/5] Installing JARVIS..."
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    pipx install git+https://github.com/AnkarIIT/OpenJarvis.git
} else {
    Write-Host "pipx not available, using pip install..."
    pip install -e ".[all,dev]"
}

# Step 1: Clone sub-projects
Write-Host ""
Write-Host "[1/5] Cloning sub-projects..."
if (Test-Path "$ProjectDir\ai-marketing-skills") {
    Write-Host "✓ ai-marketing-skills already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/ai-marketing-skills.git "$ProjectDir\ai-marketing-skills"
}
if (Test-Path "$ProjectDir\ai-memory-vault") {
    Write-Host "✓ ai-memory-vault already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/ai-memory-vault.git "$ProjectDir\ai-memory-vault"
}
if (Test-Path "$ProjectDir\ai-visualizer") {
    Write-Host "✓ ai-visualizer already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/ai-visualizer.git "$ProjectDir\ai-visualizer"
}
if (Test-Path "$ProjectDir\backtalk") {
    Write-Host "✓ backtalk already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/backtalk.git "$ProjectDir\backtalk"
}
if (Test-Path "$ProjectDir\barehands") {
    Write-Host "✓ barehands already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/barehands.git "$ProjectDir\barehands"
}
if (Test-Path "$ProjectDir\fullstack-agent") {
    Write-Host "✓ fullstack-agent already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/fullstack-agent.git "$ProjectDir\fullstack-agent"
}
if (Test-Path "$ProjectDir\prompts") {
    Write-Host "✓ prompts already exists, skipping..."
} else {
    git clone https://github.com/AnkarIIT/prompts.git "$ProjectDir\prompts"
}

# Step 2: Install Python dependencies
Write-Host ""
Write-Host "[2/5] Installing Python dependencies..."
Set-Location $ProjectDir
pip install -e ".[all,dev]"

# Step 3: Add to PATH if needed
Write-Host ""
Write-Host "[3/5] Setting up PATH..."
$scriptsDir = python -c "import sys; print(sys.executable.replace('python.exe', 'Scripts'))"
Write-Host "Add to PATH: $scriptsDir"
Write-Host "Run: [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';$scriptsDir', 'User')"
Write-Host "Then restart PowerShell or close and reopen this window."

# Step 4: Install
Write-Host ""
Write-Host "[4/5] Running jarvis --install..."
jarvis --install
if ($LASTEXITCODE -ne 0) {
    Write-Host "Install failed - try running 'jarvis --install' manually" -ForegroundColor Yellow
}

# Step 5: Test
Write-Host ""
Write-Host "[5/5] Testing..."
jarvis --models
if ($LASTEXITCODE -ne 0) {
    Write-Host "Models detection had issues - check Ollama is running" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗"
Write-Host "║   Setup complete! Run: jarvis            ║"
Write-Host "╚══════════════════════════════════════════╝"
