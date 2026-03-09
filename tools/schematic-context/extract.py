#!/usr/bin/env python3
"""
extract.py — Schematic context extraction pipeline.

Runs kicad-cli to export an XML netlist from a KiCad schematic,
parses the XML for component/pin/net data, and produces a
circuit-context.json file for AI-assisted hardware design sessions.

Usage:
    python extract.py <root.kicad_sch>
    python extract.py <root.kicad_sch> --output path/to/circuit-context.json
    python extract.py <root.kicad_sch> --previous path/to/old-circuit-context.json

Environment:
    KICAD_CLI   Override path to the kicad-cli binary.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

KICAD_CLI_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    "kicad-cli",
]


def find_kicad_cli() -> Optional[str]:
    """Locate the kicad-cli binary.

    Resolution order:
      1. KICAD_CLI environment variable (if set and executable)
      2. macOS default KiCad.app path
      3. System PATH lookup
    """
    env_path = os.environ.get("KICAD_CLI")
    if env_path:
        resolved = shutil.which(env_path)
        if resolved:
            return resolved
        if os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path
        print(
            f"Warning: KICAD_CLI={env_path} is not a valid executable, "
            "falling back to default search...",
            file=sys.stderr,
        )

    for candidate in KICAD_CLI_CANDIDATES:
        if os.path.isabs(candidate):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found

    return None


def export_netlist_xml(kicad_cli: str, schematic_path: Path) -> Path:
    """Run kicad-cli to export an XML netlist from the given root schematic.

    Creates a temporary file for the XML output. The caller is responsible
    for cleaning it up (or passing it to the parsing stage).

    Returns the Path to the exported XML file.

    Raises:
        FileNotFoundError: If the schematic file doesn't exist.
        subprocess.CalledProcessError: If kicad-cli exits non-zero.
        RuntimeError: If the output file is missing or empty after export.
    """
    if not schematic_path.exists():
        raise FileNotFoundError(f"Schematic not found: {schematic_path}")

    fd, xml_path = tempfile.mkstemp(suffix=".xml", prefix="kicad_netlist_")
    os.close(fd)

    try:
        cmd = [
            kicad_cli,
            "sch", "export", "netlist",
            "--format", "kicadxml",
            "--output", xml_path,
            str(schematic_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            stderr_lines = _filter_benign_warnings(result.stderr)
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr="\n".join(stderr_lines),
            )

        if not os.path.isfile(xml_path) or os.path.getsize(xml_path) == 0:
            raise RuntimeError(
                "kicad-cli exited successfully but produced no output"
            )

        return Path(xml_path)

    except BaseException:
        if os.path.exists(xml_path):
            os.unlink(xml_path)
        raise


def _filter_benign_warnings(stderr: str) -> List[str]:
    """Remove known-harmless kicad-cli stderr noise (e.g. Fontconfig warnings)."""
    if not stderr:
        return []
    return [
        line
        for line in stderr.strip().splitlines()
        if "Fontconfig" not in line and line.strip()
    ]


def resolve_schematic(raw_path: str) -> Path:
    """Resolve and validate the schematic path.

    Raises SystemExit with a descriptive message on failure.
    """
    schematic = Path(raw_path).resolve()

    if not schematic.exists():
        print(f"Error: schematic not found: {schematic}", file=sys.stderr)
        sys.exit(1)

    if not schematic.is_file():
        print(f"Error: not a file: {schematic}", file=sys.stderr)
        sys.exit(1)

    if schematic.suffix != ".kicad_sch":
        print(
            f"Error: expected a .kicad_sch file, got: {schematic.name}",
            file=sys.stderr,
        )
        sys.exit(1)

    return schematic


def resolve_output_path(schematic: Path, explicit_output: Optional[str]) -> Path:
    """Determine the output path for circuit-context.json.

    Default: circuit-context.json in the schematic's parent directory.
    """
    if explicit_output:
        return Path(explicit_output).resolve()
    return schematic.parent / "circuit-context.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract circuit context from a KiCad schematic.",
    )
    parser.add_argument(
        "schematic",
        help="Path to the root .kicad_sch file",
    )
    parser.add_argument(
        "--output", "-o",
        help=(
            "Output path for circuit-context.json "
            "(default: circuit-context.json next to the schematic)"
        ),
    )
    parser.add_argument(
        "--previous",
        help="Path to a previous circuit-context.json to merge annotations from",
    )
    args = parser.parse_args()

    schematic = resolve_schematic(args.schematic)
    output_path = resolve_output_path(schematic, args.output)

    kicad_cli = find_kicad_cli()
    if not kicad_cli:
        print(
            "Error: kicad-cli not found.\n"
            "  Install KiCad 9, or set the KICAD_CLI environment variable.\n"
            "  macOS default: /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Step 1: Export XML netlist via kicad-cli ---
    xml_path = None  # type: Optional[Path]
    try:
        print(f"Exporting XML netlist from {schematic.name}...", file=sys.stderr)
        xml_path = export_netlist_xml(kicad_cli, schematic)
        xml_size = xml_path.stat().st_size
        print(f"  OK — {xml_size:,} bytes", file=sys.stderr)

        # --- Step 2: Parse XML into data structures ---
        # TODO(Phase 1a task 3): parse_netlist_xml(xml_path)

        # --- Step 3: Read kiutils data ---
        # TODO(Phase 1b): kiutils integration

        # --- Step 4: Merge with previous context ---
        # TODO(Phase 1b): merge_previous_context(args.previous)

        # --- Step 5: Write circuit-context.json ---
        # TODO(Phase 1a task 4): write_context_json(output_path)

        print(
            f"XML export complete. Output will be written to {output_path}",
            file=sys.stderr,
        )
        print(
            "(Parsing and context file generation not yet implemented.)",
            file=sys.stderr,
        )

    except subprocess.CalledProcessError as e:
        print(f"Error: kicad-cli failed (exit {e.returncode}):", file=sys.stderr)
        if e.stderr:
            for line in e.stderr.strip().splitlines():
                print(f"  {line}", file=sys.stderr)
        sys.exit(1)

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if xml_path and xml_path.exists():
            xml_path.unlink()


if __name__ == "__main__":
    main()
