#!/usr/bin/env bash
#
# Interactive launcher for viewing 3D models in OCP CAD Viewer.
# Run from the project root: ./mechanical/view.sh
#
# Scans mechanical/models/ for any folders containing build123d
# Python scripts (at any nesting depth). If OCP CAD Viewer isn't
# running on port 3939, starts it automatically in the background.
#
# Requires the mechanical/.venv virtual environment with build123d
# and ocp_vscode installed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
OCP_PORT=3939

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: virtual environment not found at $SCRIPT_DIR/.venv"
    echo "Set it up with: python3 -m venv $SCRIPT_DIR/.venv && $VENV_PYTHON -m pip install build123d ocp_vscode"
    exit 1
fi

# ── Ensure OCP CAD Viewer is running ──────────────────────────

if ! lsof -iTCP:"$OCP_PORT" -sTCP:LISTEN &>/dev/null; then
    echo "Starting OCP CAD Viewer on port $OCP_PORT..."
    "$VENV_PYTHON" -m ocp_vscode &>/dev/null &
    OCP_PID=$!

    for i in {1..20}; do
        if lsof -iTCP:"$OCP_PORT" -sTCP:LISTEN &>/dev/null; then
            echo "OCP CAD Viewer ready (pid $OCP_PID)"
            break
        fi
        sleep 0.5
    done

    if ! lsof -iTCP:"$OCP_PORT" -sTCP:LISTEN &>/dev/null; then
        echo "Warning: OCP CAD Viewer may not have started. Continuing anyway..."
    fi
else
    echo "OCP CAD Viewer already running on port $OCP_PORT"
fi

# ── Collect all project folders containing .py files ──────────
# Walks the full models/ tree. Any directory with at least one .py
# file is a selectable project. Paths are shown relative to models/.

projects=()
project_paths=()

while IFS= read -r dir; do
    rel="${dir#"$MODELS_DIR"/}"
    projects+=("$rel")
    project_paths+=("$dir")
done < <(
    find "$MODELS_DIR" -name '*.py' -not -path '*/__pycache__/*' \
        -exec dirname {} \; | sort -u
)

if [[ ${#projects[@]} -eq 0 ]]; then
    echo "No folders with .py files found under $MODELS_DIR"
    exit 1
fi

# ── Select project ────────────────────────────────────────────

if [[ ${#projects[@]} -eq 1 ]]; then
    chosen_idx=0
    echo "Project: ${projects[0]}"
else
    echo ""
    echo "Select a project:"
    select proj in "${projects[@]}"; do
        if [[ -n "$proj" ]]; then
            for i in "${!projects[@]}"; do
                [[ "${projects[$i]}" == "$proj" ]] && chosen_idx=$i && break
            done
            break
        fi
        echo "Invalid selection, try again."
    done
fi

chosen_dir="${project_paths[$chosen_idx]}"

# ── Collect .py scripts in the chosen folder ──────────────────

scripts=()
for f in "$chosen_dir"/*.py; do
    [[ -f "$f" ]] && scripts+=("$(basename "$f")")
done

if [[ ${#scripts[@]} -eq 0 ]]; then
    echo "No Python files found in $chosen_dir"
    exit 1
fi

# ── Select script ─────────────────────────────────────────────

if [[ ${#scripts[@]} -eq 1 ]]; then
    script="${scripts[0]}"
    echo "Model: $script"
else
    echo ""
    echo "Select a model to view:"
    select script in "${scripts[@]}"; do
        [[ -n "$script" ]] && break
        echo "Invalid selection, try again."
    done
fi

# ── Run ───────────────────────────────────────────────────────

target="$chosen_dir/$script"
echo ""
echo "Running: $target"
echo "---"
exec "$VENV_PYTHON" "$target"
