#!/usr/bin/env bash
# Jarvis Agent installer for Linux, macOS, WSL2, Termux
# Installs: uv, Python 3.11, Node.js, ripgrep, ffmpeg, Git Bash (MinGit on Windows)
set -euo pipefail

JARVIS_HOME="${JARVIS_HOME:-$HOME/.jarvis}"
REPO="https://github.com/AnkarIIT/OpenJarvis"
INSTALL_DIR="$JARVIS_HOME/jarvis-agent"

echo "╔══════════════════════════════════════════════════════╗"
echo "║         Jarvis Agent Installer                      ║"
echo "║         https://github.com/AnkarIIT/OpenJarvis      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "[1/7] Checking prerequisites..."

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "freebsd"* ]]; then
    OS="freebsd"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo "  Detected OS: $OS"

# Check for git
if ! command -v git &> /dev/null; then
    echo "  git not found. Installing git..."
    if [[ "$OS" == "macos" ]]; then
        brew install git || { echo "Failed to install git via brew"; exit 1; }
    elif [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y git || { echo "Failed to install git via apt"; exit 1; }
        elif command -v yum &> /dev/null; then
            sudo yum install -y git || { echo "Failed to install git via yum"; exit 1; }
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm git || { echo "Failed to install git via pacman"; exit 1; }
        else
            echo "Please install git manually and re-run this script."
            exit 1
        fi
    fi
fi

# Check for curl
if ! command -v curl &> /dev/null; then
    echo "  curl not found. Installing curl..."
    if [[ "$OS" == "macos" ]]; then
        brew install curl || { echo "Failed to install curl via brew"; exit 1; }
    elif [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y curl || { echo "Failed to install curl via apt"; exit 1; }
        elif command -v yum &> /dev/null; then
            sudo yum install -y curl || { echo "Failed to install curl via yum"; exit 1; }
        fi
    fi
fi

# Check for unzip
if ! command -v unzip &> /dev/null; then
    echo "  unzip not found. Installing unzip..."
    if [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y unzip || { echo "Failed to install unzip via apt"; exit 1; }
        elif command -v yum &> /dev/null; then
            sudo yum install -y unzip || { echo "Failed to install unzip via yum"; exit 1; }
        fi
    fi
fi

echo "[2/7] Creating Jarvis home directory..."
mkdir -p "$JARVIS_HOME"
mkdir -p "$JARVIS_HOME/bin"

echo "[3/7] Installing uv (Python package manager)..."
UV_VERSION="0.5.23"
UV_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_VERSION}-$(uname -s)-$(uname -m).tar.gz"
UV_TAR="$JARVIS_HOME/uv.tar.gz"

echo "  Downloading uv ${UV_VERSION}..."
curl -fsSL "$UV_URL" -o "$UV_TAR"

echo "  Extracting uv..."
cd "$JARVIS_HOME"
tar -xzf "$UV_TAR"
rm -f "$UV_TAR"

# Move uv binary to bin
if [[ -f "$JARVIS_HOME/uv" ]]; then
    mv "$JARVIS_HOME/uv" "$JARVIS_HOME/bin/uv"
elif [[ -f "$JARVIS_HOME/uv-${UV_VERSION}-$(uname -s)-$(uname -m)/uv" ]]; then
    mv "$JARVIS_HOME/uv-${UV_VERSION}-$(uname -s)-$(uname -m)/uv" "$JARVIS_HOME/bin/uv"
    rm -rf "$JARVIS_HOME/uv-${UV_VERSION}-$(uname -s)-$(uname -m)"
fi

chmod +x "$JARVIS_HOME/bin/uv"
export PATH="$JARVIS_HOME/bin:$PATH"
echo "  uv installed: $($JARVIS_HOME/bin/uv --version)"

echo "[4/7] Creating Python virtual environment..."
cd "$JARVIS_HOME"
$VIRTUAL_ENV/bin/python --version 2>/dev/null || {
    $JARVIS_HOME/bin/uv venv "$JARVIS_HOME/venv" --python 3.11 || {
        echo "  Failed to create venv. Trying with system Python..."
        python3 -m venv "$JARVIS_HOME/venv" || {
            echo "Failed to create venv. Please install Python 3.11+ and try again."
            exit 1
        }
    }
}
export VIRTUAL_ENV="$JARVIS_HOME/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

echo "[5/7] Installing Jarvis Agent from git..."
if [[ -d "$INSTALL_DIR" ]]; then
    echo "  Existing installation found at $INSTALL_DIR"
    echo "  Updating..."
    cd "$INSTALL_DIR"
    git pull origin main || {
        echo "Failed to update. Removing and re-cloning..."
        rm -rf "$INSTALL_DIR"
        git clone "$REPO" "$INSTALL_DIR"
    }
else
    echo "  Cloning repository..."
    git clone "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo "[6/7] Installing dependencies..."
if [[ -f "pyproject.toml" ]]; then
    $JARVIS_HOME/bin/uv pip install -e ".[all]" || {
        echo "  Failed to install dependencies. Trying basic install..."
        $JARVIS_HOME/bin/uv pip install -e . || {
            echo "Failed to install dependencies. Please check your Python environment."
            exit 1
        }
    }
else
    echo "  pyproject.toml not found. Installing from setup.py..."
    $JARVIS_HOME/bin/uv pip install -e . || {
        echo "Failed to install. Please check the repository."
        exit 1
    }
fi

echo "[7/7] Setting up shell integration..."

# Add to shell profile
if [[ -f "$HOME/.bashrc" ]]; then
    if ! grep -q "JARVIS_HOME" "$HOME/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME/.bashrc"
        echo "# Jarvis Agent" >> "$HOME/.bashrc"
        echo "export JARVIS_HOME=\"$JARVIS_HOME\"" >> "$HOME/.bashrc"
        echo "export PATH=\"$JARVIS_HOME/bin:$JARVIS_HOME/venv/bin:\$PATH\"" >> "$HOME/.bashrc"
        echo "  Added to ~/.bashrc"
    fi
fi

if [[ -f "$HOME/.zshrc" ]]; then
    if ! grep -q "JARVIS_HOME" "$HOME/.zshrc" 2>/dev/null; then
        echo "" >> "$HOME/.zshrc"
        echo "# Jarvis Agent" >> "$HOME/.zshrc"
        echo "export JARVIS_HOME=\"$JARVIS_HOME\"" >> "$HOME/.zshrc"
        echo "export PATH=\"$JARVIS_HOME/bin:$JARVIS_HOME/venv/bin:\$PATH\"" >> "$HOME/.zshrc"
        echo "  Added to ~/.zshrc"
    fi
fi

# Also add for current session
export JARVIS_HOME="$JARVIS_HOME"
export PATH="$JARVIS_HOME/bin:$JARVIS_HOME/venv/bin:$PATH"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
echo "  2. Run: jarvis"
echo ""
echo "For updates: cd $INSTALL_DIR && git pull origin main"
echo ""
echo "Documentation: https://github.com/AnkarIIT/OpenJarvis/wiki"
