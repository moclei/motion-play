#!/usr/bin/env bash
#
# Interactive launcher for viewing enclosure models in OCP CAD Viewer.
# Run from the project root: ./mechanical/view.sh
#
# Requires the mechanical/.venv virtual environment with build123d and
# ocp_vscode installed, and the OCP CAD Viewer standalone server running
# on port 3939.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENCLOSURES_DIR="$SCRIPT_DIR/enclosures"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: virtual environment not found at $SCRIPT_DIR/.venv"
    echo "Set it up with: python3 -m venv $SCRIPT_DIR/.venv && $VENV_PYTHON -m pip install build123d ocp_vscode"
    exit 1
fi

# Collect enclosure folders (skip hidden dirs)
folders=()
for d in "$ENCLOSURES_DIR"/*/; do
    [[ -d "$d" ]] && folders+=("$(basename "$d")")
done

if [[ ${#folders[@]} -eq 0 ]]; then
    echo "No enclosure folders found in $ENCLOSURES_DIR"
    exit 1
fi

# Select folder (skip prompt if only one)
if [[ ${#folders[@]} -eq 1 ]]; then
    folder="${folders[0]}"
    echo "Enclosure: $folder"
else
    echo "Select an enclosure:"
    select folder in "${folders[@]}"; do
        [[ -n "$folder" ]] && break
        echo "Invalid selection, try again."
    done
fi

# Collect .py files in the chosen folder
scripts=()
for f in "$ENCLOSURES_DIR/$folder"/*.py; do
    [[ -f "$f" ]] && scripts+=("$(basename "$f")")
done

if [[ ${#scripts[@]} -eq 0 ]]; then
    echo "No Python files found in $ENCLOSURES_DIR/$folder"
    exit 1
fi

# Select script (skip prompt if only one)
if [[ ${#scripts[@]} -eq 1 ]]; then
    script="${scripts[0]}"
    echo "Model: $script"
else
    echo "Select a model to view:"
    select script in "${scripts[@]}"; do
        [[ -n "$script" ]] && break
        echo "Invalid selection, try again."
    done
fi

target="$ENCLOSURES_DIR/$folder/$script"
echo ""
echo "Running: $target"
echo "---"
exec "$VENV_PYTHON" "$target"
