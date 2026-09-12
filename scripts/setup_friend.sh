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

# Step 0: Ensure pipx is available
echo "[0/5] Ensuring pipx is available..."
if ! command -v pipx &> /dev/null; then
    echo "pipx not found, installing..."
    python -m pip install --user pipx
    # Add pipx to PATH on Windows (Git Bash / MSYS)
    case "$(uname)" in
        MINGW*|MSYS*|CYGWIN*)
            PYTHON_SCRIPTS="$(python -c 'import sys; import site; print(site.getusersitepackages().replace("site-packages", "Scripts"))')"
            echo "Add to PATH: $PYTHON_SCRIPTS"
            echo "Then restart Git Bash or run: export PATH=\"\$PATH:$PYTHON_SCRIPTS\""
            ;;
    esac
fi

# Step 1: Clone sub-projects
echo ""
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
jarvis --install || echo "Install failed - try running 'jarvis --install' manually"

# Step 5: Test
echo ""
echo "[5/5] Testing..."
jarvis --models || echo "Models detection had issues - check Ollama is running"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup complete! Run: jarvis            ║"
echo "╚══════════════════════════════════════════╝"
