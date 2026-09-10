#!/bin/bash
# Complete setup for a friend who just cloned OpenJarvis.
# Run this on a fresh clone to get everything working.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════╗"
echo "║   JARVIS - Friend Setup Script           ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Step 1: Clone sub-projects
echo "[1/5] Cloning sub-projects..."
bash "$SCRIPT_DIR/init_submodules.sh"

# Step 2: Install Python dependencies
echo ""
echo "[2/5] Installing Python dependencies..."
cd "$PROJECT_DIR"
pip install -e ".[all,dev]"

# Step 3: Add to PATH if needed
echo ""
echo "[3/5] Setting up PATH..."
case "$(uname)" in
    MINGW*|MSYS*|CYGWIN*)
        SCRIPTS_DIR="$(python -c 'import sys; print(sys.executable)')"
        SCRIPTS_DIR="$(dirname "$SCRIPTS_DIR")/Scripts"
        echo "Add to PATH: $SCRIPTS_DIR"
        ;;
    *)
        echo "Run: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        ;;
esac

# Step 4: Install
echo ""
echo "[4/5] Running jarvis --install..."
jarvis --install || echo "Install failed - try running 'jarvis --install' manually"

# Step 5: Test
echo ""
echo "[5/5] Testing..."
jarvis --models || echo "Models detection had issues - check Ollama is running"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup complete! Run: jarvis            ║"
echo "╚══════════════════════════════════════════╝"
