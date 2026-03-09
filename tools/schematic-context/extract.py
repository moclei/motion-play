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
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from kiutils.schematic import Schematic
except ImportError:
    Schematic = None

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


@dataclass
class SheetPin:
    name: str
    direction: str


@dataclass
class SheetInfo:
    filename: str
    display_name: str
    pins: List[SheetPin] = field(default_factory=list)


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
) -> Tuple[Dict[str, Component], Dict[str, Net], Dict[str, str]]:
    """Parse a kicad-cli XML netlist into component and net data structures.

    Returns (components, nets, sheet_map) where:
      - components: dict keyed by ref designator
      - nets: dict keyed by net name (excludes unconnected-* stubs)
      - sheet_map: child sheet filename → display name

    Pin data on each component is populated from the <nets> section,
    which is the authoritative source for pin-level connectivity.
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    components = _parse_components(root)
    nets = _parse_nets(root, components)
    sheet_map = _parse_sheet_map(root)

    for comp in components.values():
        comp.pins.sort(key=lambda p: _pin_sort_key(p.number))

    return components, nets, sheet_map


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


def _parse_sheet_map(root: ET.Element) -> Dict[str, str]:
    """Build a child-sheet filename → display name mapping from <design>.

    The root sheet (name="/") is excluded.
    """
    sheet_map = {}  # type: Dict[str, str]

    design = root.find("design")
    if design is None:
        return sheet_map

    for sheet_elem in design.findall("sheet"):
        name = sheet_elem.get("name", "")
        if name == "/":
            continue

        title_block = sheet_elem.find("title_block")
        if title_block is None:
            continue
        source_elem = title_block.find("source")
        if source_elem is None or not source_elem.text:
            continue

        display_name = name.strip("/")
        sheet_map[source_elem.text] = display_name

    return sheet_map


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


# ---------------------------------------------------------------------------
# kiutils integration — component properties and sheet hierarchy
# ---------------------------------------------------------------------------

AI_PROP_PREFIX = "ai_"
AI_PROP_FIELDS = ("function", "block", "role", "critical_specs")


def read_kiutils_properties(
    schematic: Path,
) -> Tuple[Dict[str, Dict[str, str]], List[SheetInfo]]:
    """Read component ai_ properties and sheet hierarchy via kiutils.

    Discovers child sheets from the root schematic's sheet objects,
    then reads each .kicad_sch file for component properties.

    Returns (component_props, sheet_infos) where:
      - component_props: ref → {field: value} for ai_-prefixed properties
        (e.g., {"function": "voltage regulator", "block": "power"})
      - sheet_infos: list of SheetInfo with filename, display name, and
        hierarchical pin interfaces
    """
    if Schematic is None:
        print(
            "Warning: kiutils not installed — skipping property extraction",
            file=sys.stderr,
        )
        return {}, []

    root_dir = schematic.parent
    sch = Schematic.from_file(str(schematic))

    component_props = {}  # type: Dict[str, Dict[str, str]]
    sheet_infos = []  # type: List[SheetInfo]

    _collect_ai_properties(sch, component_props)

    for sheet in sch.sheets:
        filename = sheet.fileName.value
        display_name = sheet.sheetName.value
        child_path = root_dir / filename

        pins = [
            SheetPin(name=pin.name, direction=pin.connectionType)
            for pin in sheet.pins
        ]
        sheet_infos.append(SheetInfo(
            filename=filename,
            display_name=display_name,
            pins=pins,
        ))

        if not child_path.exists():
            print(
                f"Warning: child sheet not found: {child_path}",
                file=sys.stderr,
            )
            continue

        child_sch = Schematic.from_file(str(child_path))
        _collect_ai_properties(child_sch, component_props)

    return component_props, sheet_infos


def _collect_ai_properties(
    sch: "Schematic",
    out: Dict[str, Dict[str, str]],
) -> None:
    """Extract ai_-prefixed properties from all symbols in a schematic."""
    for sym in sch.schematicSymbols:
        ref = ""
        for prop in sym.properties:
            if prop.key == "Reference":
                ref = prop.value
                break

        if not ref or ref.startswith("#"):
            continue

        ai_props = {}  # type: Dict[str, str]
        for prop in sym.properties:
            if prop.key.startswith(AI_PROP_PREFIX):
                field_name = prop.key[len(AI_PROP_PREFIX):]
                if field_name in AI_PROP_FIELDS and prop.value:
                    ai_props[field_name] = prop.value

        if ai_props:
            out[ref] = ai_props


# ---------------------------------------------------------------------------
# Sheet interface resolution — match hierarchical pins to parent-side nets
# ---------------------------------------------------------------------------

def build_sheet_interfaces(
    sheet_infos: List[SheetInfo],
    nets: Dict[str, Net],
) -> dict:
    """Build the sheet_interfaces section from kiutils sheet data.

    For each hierarchical sheet pin, attempts to resolve which net it
    connects to on the parent side using name-based heuristics.
    """
    all_net_names = set(nets.keys())  # type: Set[str]
    interfaces = {}  # type: dict

    for info in sheet_infos:
        pins_out = []
        for pin in info.pins:
            net = _resolve_pin_net(pin.name, info.display_name, all_net_names)
            pins_out.append({
                "name": pin.name,
                "direction": pin.direction,
                "net": net,
            })

        pins_out.sort(key=lambda p: p["name"])
        interfaces[info.filename] = {
            "description": "",
            "pins": pins_out,
        }

    return interfaces


_POWER_NET_ALIASES = {
    "VCC_3V3": "+3.3V",
    "VCC_5V": "+5V",
    "VCC": "+3.3V",
    "V3V3": "+3.3V",
    "V5V": "+5V",
}


def _resolve_pin_net(
    pin_name: str,
    sheet_display_name: str,
    all_net_names: Set[str],
) -> str:
    """Try to resolve which parent-side net a hierarchical sheet pin connects to.

    Uses a series of name-matching heuristics since kiutils cannot trace
    net connectivity. Returns empty string if unresolved.
    """
    scoped = "/{}/{}".format(sheet_display_name, pin_name)
    if scoped in all_net_names:
        return scoped

    if pin_name in all_net_names:
        return pin_name

    rooted = "/{}".format(pin_name)
    if rooted in all_net_names:
        return rooted

    for suffix in ("_IN", "_OUT"):
        if pin_name.upper().endswith(suffix):
            base = pin_name[:-len(suffix)]
            if base in all_net_names:
                return base
            rooted_base = "/{}".format(base)
            if rooted_base in all_net_names:
                return rooted_base

    alias = _POWER_NET_ALIASES.get(pin_name.upper())
    if alias and alias in all_net_names:
        return alias

    return ""


# ---------------------------------------------------------------------------
# Previous-context merge — carry forward annotations across re-extractions
# ---------------------------------------------------------------------------

def merge_previous_context(
    previous_path: Optional[str],
    context: dict,
) -> dict:
    """Merge annotations from a previous circuit-context.json.

    Carries forward:
      - Block definitions (entire blocks section)
      - Net annotations (type, protocol, direction, description)
      - Top-level description
    Reports new/removed components and nets to stderr.
    """
    if not previous_path:
        return context

    prev_file = Path(previous_path)
    if not prev_file.exists():
        print(
            f"Warning: previous context not found: {prev_file}",
            file=sys.stderr,
        )
        return context

    with open(str(prev_file)) as f:
        prev = json.load(f)

    print("Merging annotations from previous context...", file=sys.stderr)

    if prev.get("description") and not context.get("description"):
        context["description"] = prev["description"]

    for block_id, block_def in prev.get("blocks", {}).items():
        if block_id not in context["blocks"]:
            context["blocks"][block_id] = block_def

    for net_name, prev_net in prev.get("nets", {}).items():
        if net_name in context["nets"]:
            for key in ("type", "protocol", "direction", "description"):
                prev_val = prev_net.get(key, "")
                if prev_val and not context["nets"][net_name].get(key):
                    context["nets"][net_name][key] = prev_val

    prev_refs = set(prev.get("components", {}).keys())
    curr_refs = set(context.get("components", {}).keys())
    new_refs = sorted(curr_refs - prev_refs)
    removed_refs = sorted(prev_refs - curr_refs)

    prev_nets = set(prev.get("nets", {}).keys())
    curr_nets = set(context.get("nets", {}).keys())
    new_nets = sorted(curr_nets - prev_nets)
    removed_nets = sorted(prev_nets - curr_nets)

    if new_refs:
        print(f"  New components: {new_refs}", file=sys.stderr)
    if removed_refs:
        print(f"  Removed components: {removed_refs}", file=sys.stderr)
    if new_nets:
        print(f"  New nets: {new_nets}", file=sys.stderr)
    if removed_nets:
        print(f"  Removed nets: {removed_nets}", file=sys.stderr)
    if not (new_refs or removed_refs or new_nets or removed_nets):
        print("  No structural changes", file=sys.stderr)

    return context


# ---------------------------------------------------------------------------
# Context file construction and output
# ---------------------------------------------------------------------------

def build_context(
    components: Dict[str, Component],
    nets: Dict[str, Net],
    sheet_map: Dict[str, str],
    schematic: Path,
    component_props: Optional[Dict[str, Dict[str, str]]] = None,
    sheet_infos: Optional[List[SheetInfo]] = None,
) -> dict:
    """Assemble the circuit-context.json structure from parsed data.

    Annotation fields for components are populated from kiutils ai_
    properties when available; otherwise emitted as empty strings
    (populated during the annotation pass in Phase 3).
    """
    if component_props is None:
        component_props = {}
    if sheet_infos is None:
        sheet_infos = []

    ref_list = sorted(components.keys())
    net_list = sorted(nets.keys())
    hash_input = json.dumps({"refs": ref_list, "nets": net_list}, sort_keys=True)
    source_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]

    context = {
        "schema_version": "1.0",
        "project": schematic.stem,
        "source": {
            "root": schematic.name,
            "sheets": sheet_map,
            "source_hash": source_hash,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        },
        "description": "",
        "blocks": {},
        "components": {},
        "nets": {},
        "sheet_interfaces": build_sheet_interfaces(sheet_infos, nets),
    }

    for ref in sorted(components.keys()):
        comp = components[ref]
        ai = component_props.get(ref, {})
        context["components"][ref] = {
            "part": comp.part,
            "value": comp.value,
            "footprint": comp.footprint,
            "lcsc": comp.lcsc,
            "sheet": comp.sheet,
            "block": ai.get("block", ""),
            "function": ai.get("function", ""),
            "role": ai.get("role", ""),
            "critical_specs": ai.get("critical_specs", ""),
            "pins": [
                {
                    "number": p.number,
                    "name": p.name,
                    "type": p.type,
                    "net": p.net,
                }
                for p in comp.pins
            ],
        }

    for net_name in sorted(nets.keys()):
        context["nets"][net_name] = {
            "type": "",
            "protocol": "",
            "direction": "",
            "description": "",
        }

    return context


def write_context_json(context: dict, output_path: Path) -> None:
    """Write the context dictionary to a JSON file."""
    with open(str(output_path), "w") as f:
        json.dump(context, f, indent=2)
        f.write("\n")


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
        components, nets, sheet_map = parse_netlist_xml(xml_path)
        total_pins = sum(len(c.pins) for c in components.values())
        print(
            f"  {len(components)} components, {len(nets)} nets, "
            f"{total_pins} pin assignments, "
            f"{len(sheet_map) + 1} sheets",
            file=sys.stderr,
        )

        # --- Step 3: Read kiutils data ---
        print("Reading schematic properties via kiutils...", file=sys.stderr)
        component_props, sheet_infos = read_kiutils_properties(schematic)
        annotated = sum(1 for v in component_props.values() if v)
        print(
            f"  {len(sheet_infos)} child sheets, "
            f"{annotated} components with ai_ properties",
            file=sys.stderr,
        )

        # --- Step 4: Build context and merge ---
        context = build_context(
            components, nets, sheet_map, schematic,
            component_props=component_props,
            sheet_infos=sheet_infos,
        )

        if args.previous:
            context = merge_previous_context(args.previous, context)

        # --- Step 5: Write circuit-context.json ---
        write_context_json(context, output_path)
        print(
            f"Wrote {output_path.name} "
            f"({output_path.stat().st_size:,} bytes)",
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
