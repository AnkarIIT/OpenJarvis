#!/bin/bash
# Clone all JARVIS sub-projects for first-time setup.
# Run this after: git clone https://github.com/AnkarIIT/OpenJarvis.git
# 
# These projects are listed in .gitignore but are required for full functionality.
# Each is an independent git repo that must be cloned separately.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

clone_repo() {
    local repo_url="$1"
    local target_dir="$2"
    if [ -d "$target_dir" ]; then
        echo "✓ $target_dir already exists, skipping..."
    else
        echo "Cloning $repo_url → $target_dir"
        git clone "$repo_url" "$target_dir"
    fi
}

echo "=== JARVIS Sub-Project Initializer ==="
echo ""

clone_repo "https://github.com/AnkarIIT/ai-marketing-skills.git" "$PROJECT_DIR/ai-marketing-skills"
clone_repo "https://github.com/AnkarIIT/ai-memory-vault.git" "$PROJECT_DIR/ai-memory-vault"
clone_repo "https://github.com/AnkarIIT/ai-visualizer.git" "$PROJECT_DIR/ai-visualizer"
clone_repo "https://github.com/AnkarIIT/backtalk.git" "$PROJECT_DIR/backtalk"
clone_repo "https://github.com/AnkarIIT/barehands.git" "$PROJECT_DIR/barehands"
clone_repo "https://github.com/AnkarIIT/fullstack-agent.git" "$PROJECT_DIR/fullstack-agent"
clone_repo "https://github.com/AnkarIIT/prompts.git" "$PROJECT_DIR/prompts"

echo ""
echo "=== All sub-projects initialized! ==="
echo "Run: pip install -e . && jarvis --install && jarvis"
