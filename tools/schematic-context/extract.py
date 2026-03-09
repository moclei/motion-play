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
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

KICAD_CLI_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    "kicad-cli",
]


# ---------------------------------------------------------------------------
# Data structures — intermediate representation between XML and JSON output
# ---------------------------------------------------------------------------

@dataclass
class Pin:
    number: str
    name: str
    type: str
    net: str


@dataclass
class Component:
    ref: str
    part: str
    value: str
    footprint: str
    lcsc: str
    sheet: str
    pins: List[Pin] = field(default_factory=list)


@dataclass
class NetConnection:
    ref: str
    pin: str


@dataclass
class Net:
    name: str
    connections: List[NetConnection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# kicad-cli helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# XML netlist parsing
# ---------------------------------------------------------------------------

def parse_netlist_xml(
    xml_path: Path,
) -> Tuple[Dict[str, Component], Dict[str, Net]]:
    """Parse a kicad-cli XML netlist into component and net data structures.

    Returns (components, nets) where:
      - components: dict keyed by ref designator
      - nets: dict keyed by net name (excludes unconnected-* stubs)

    Pin data on each component is populated from the <nets> section,
    which is the authoritative source for pin-level connectivity.
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    components = _parse_components(root)
    nets = _parse_nets(root, components)

    for comp in components.values():
        comp.pins.sort(key=lambda p: _pin_sort_key(p.number))

    return components, nets


def _parse_components(root: ET.Element) -> Dict[str, Component]:
    """Extract components from the <components> section."""
    components = {}  # type: Dict[str, Component]

    comps_elem = root.find("components")
    if comps_elem is None:
        return components

    for comp_elem in comps_elem.findall("comp"):
        ref = comp_elem.get("ref", "")
        if not ref:
            continue

        value = _text_or_empty(comp_elem, "value")
        footprint = _text_or_empty(comp_elem, "footprint")

        libsource = comp_elem.find("libsource")
        part = libsource.get("part", "") if libsource is not None else ""

        lcsc = _find_field(comp_elem, "LCSC Part")
        sheet = _find_property(comp_elem, "Sheetfile")

        components[ref] = Component(
            ref=ref,
            part=part,
            value=value,
            footprint=footprint,
            lcsc=lcsc,
            sheet=sheet,
        )

    return components


def _parse_nets(
    root: ET.Element,
    components: Dict[str, Component],
) -> Dict[str, Net]:
    """Extract nets from the <nets> section and populate component pin lists.

    Each <node> in a net contributes both a NetConnection to the net and
    a Pin entry on the referenced component.
    """
    nets = {}  # type: Dict[str, Net]

    nets_elem = root.find("nets")
    if nets_elem is None:
        return nets

    for net_elem in nets_elem.findall("net"):
        net_name = net_elem.get("name", "")
        if not net_name or net_name.startswith("unconnected-"):
            continue

        net = Net(name=net_name)

        for node_elem in net_elem.findall("node"):
            ref = node_elem.get("ref", "")
            pin_number = node_elem.get("pin", "")
            pin_name = node_elem.get("pinfunction", "")
            pin_type = node_elem.get("pintype", "")

            if ref:
                net.connections.append(NetConnection(ref=ref, pin=pin_number))

            if ref in components:
                components[ref].pins.append(Pin(
                    number=pin_number,
                    name=pin_name,
                    type=pin_type,
                    net=net_name,
                ))

        if net.connections:
            nets[net_name] = net

    return nets


def _text_or_empty(parent: ET.Element, tag: str) -> str:
    """Get text content of a child element, or empty string if absent."""
    elem = parent.find(tag)
    return (elem.text or "") if elem is not None else ""


def _find_field(comp_elem: ET.Element, field_name: str) -> str:
    """Find a named <field> inside a <comp>'s <fields> section."""
    fields = comp_elem.find("fields")
    if fields is None:
        return ""
    for f in fields.findall("field"):
        if f.get("name") == field_name:
            return f.text or ""
    return ""


def _find_property(comp_elem: ET.Element, prop_name: str) -> str:
    """Find a named <property> on a <comp> element."""
    for prop in comp_elem.findall("property"):
        if prop.get("name") == prop_name:
            return prop.get("value", "")
    return ""


def _pin_sort_key(pin_number: str) -> Tuple[int, str]:
    """Sort key that orders numeric pins first, then alphabetical."""
    try:
        return (0, str(int(pin_number)).zfill(10))
    except (ValueError, TypeError):
        return (1, pin_number)


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
        print("Parsing XML netlist...", file=sys.stderr)
        components, nets = parse_netlist_xml(xml_path)
        total_pins = sum(len(c.pins) for c in components.values())
        sheets = sorted({c.sheet for c in components.values() if c.sheet})
        print(
            f"  {len(components)} components, {len(nets)} nets, "
            f"{total_pins} pin assignments, {len(sheets)} sheets",
            file=sys.stderr,
        )

        # --- Step 3: Read kiutils data ---
        # TODO(Phase 1b): kiutils integration

        # --- Step 4: Merge with previous context ---
        # TODO(Phase 1b): merge_previous_context(args.previous)

        # --- Step 5: Write circuit-context.json ---
        # TODO(Phase 1a task 4): write_context_json(components, nets, output_path)

        print(
            f"Extraction complete. Output will be written to {output_path}",
            file=sys.stderr,
        )
        print(
            "(Context file JSON output not yet implemented.)",
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
