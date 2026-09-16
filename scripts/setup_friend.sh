#!/bin/bash
# Complete setup for a friend who just cloned OpenJarvis.
# Run this on a fresh clone to get everything working.
# Usage: bash scripts/setup_friend.sh  (NOT: python scripts/setup_friend.sh)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════╗"
echo "║   JARVIS - Friend Setup Script           ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Step 1: Clone sub-projects
echo ""
echo "[1/5] Cloning sub-projects..."
bash "$SCRIPT_DIR/init_submodules.sh"

# Step 2: Install Python dependencies
echo ""
echo "[2/5] Installing Python dependencies..."
cd "$PROJECT_DIR"
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# Step 3: Add to PATH if needed
echo ""
echo "[3/5] Setting up PATH..."
case "$(uname)" in
    MINGW*|MSYS*|CYGWIN*)
        SCRIPTS_DIR="$(python -c 'import sys; print(sys.executable)')"
        SCRIPTS_DIR="$(dirname "$SCRIPTS_DIR")/Scripts"
        echo "Add to PATH: $SCRIPTS_DIR"
        echo "Then restart Git Bash or run: export PATH=\"\$PATH:$SCRIPTS_DIR\""
        ;;
    *)
        echo "Run: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        echo "Then: source ~/.bashrc"
        ;;
esac

# Step 4: Install
echo ""
echo "[4/5] Running jarvis --install..."
python -m jarvis.main --install || {
    echo "Install failed - run 'python -m jarvis.main --install' to see the full error"
    exit 1
}

# Step 5: Test
echo ""
echo "[5/5] Testing..."
python -m jarvis.main --models || echo "Models detection had issues - check Ollama is running"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup complete! Run: jarvis            ║"
echo "╚══════════════════════════════════════════╝"
