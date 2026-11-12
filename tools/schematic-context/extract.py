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
    python extract.py <root.kicad_sch> --check-sheet-pins [-v]

Sheet pins in `sheet_interfaces` are resolved to the net KiCad connects them
to (a probe netlist from a scratch copy; see probe_sheet_pins), not by name.
--check-sheet-pins exits 1 and lists each sheet pin that resolves to no net or
to a net with no component pins; alone it writes nothing.

Schematic files are read through tools/kicad-io/kicad_io.py (raw s-expression
layer; read only). Run with tools/.venv/bin/python.

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad-io"))
try:
    import kicad_io as kio  # noqa: E402
    from kicad_io import atom, child, kids  # noqa: E402
except ImportError:
    kio = None  # no kicad-tools (not tools/.venv): the netlist-only path below still works

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
    x: float = 0.0  # connection point on the parent sheet (mm)
    y: float = 0.0


@dataclass
class SheetInfo:
    filename: str
    display_name: str
    uuid: str = ""  # the sheet symbol's uuid on the root
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
# Schematic reads (kicad_io raw tree) — component properties and sheet hierarchy
# ---------------------------------------------------------------------------

AI_PROP_PREFIX = "ai_"
AI_PROP_FIELDS = ("function", "block", "role", "critical_specs")


def _load_tree(path: Path):
    """A schematic's raw tree (kicad_io; read only)."""
    return kio.load_schematic(path).tree


def _sheet_prop_value(sheet, keys: Tuple[str, ...]) -> str:
    """A sheet reference's property value by key (KiCad 7+ and KiCad 6 spellings), '' if absent."""
    for p in kids(sheet, "property"):
        if atom(p, 0) in keys:
            return str(atom(p, 1))
    return ""


def _xy(n) -> Tuple[float, float]:
    at = child(n, "at")
    return float(atom(at, 0)), float(atom(at, 1))


def read_schematic_properties(
    schematic: Path,
) -> Tuple[Dict[str, Dict[str, str]], List[SheetInfo]]:
    """Read component ai_ properties and sheet hierarchy from the raw tree.

    Discovers child sheets from the root schematic's sheet objects,
    then reads each .kicad_sch file for component properties.

    Returns (component_props, sheet_infos) where:
      - component_props: ref → {field: value} for ai_-prefixed properties
        (e.g., {"function": "voltage regulator", "block": "power"})
      - sheet_infos: list of SheetInfo with filename, display name, and
        hierarchical pin interfaces
    """
    if kio is None:
        print(
            "Warning: kicad-tools not installed (run with tools/.venv/bin/python) — "
            "skipping property extraction",
            file=sys.stderr,
        )
        return {}, []

    root_dir = schematic.parent
    sch = _load_tree(schematic)

    component_props = {}  # type: Dict[str, Dict[str, str]]
    sheet_infos = []  # type: List[SheetInfo]

    _collect_ai_properties(sch, component_props)

    for sheet in kids(sch, "sheet"):
        filename = _sheet_prop_value(sheet, ("Sheetfile", "Sheet file"))
        display_name = _sheet_prop_value(sheet, ("Sheetname", "Sheet name"))
        child_path = root_dir / filename

        pins = [
            SheetPin(name=str(atom(pin, 0)), direction=str(atom(pin, 1)),
                     x=_xy(pin)[0], y=_xy(pin)[1])
            for pin in kids(sheet, "pin")
        ]
        u = child(sheet, "uuid")
        sheet_infos.append(SheetInfo(
            filename=filename,
            display_name=display_name,
            uuid=str(atom(u)) if u is not None else "",
            pins=pins,
        ))

        if not child_path.exists():
            print(
                f"Warning: child sheet not found: {child_path}",
                file=sys.stderr,
            )
            continue

        _collect_ai_properties(_load_tree(child_path), component_props)

    return component_props, sheet_infos


def _collect_ai_properties(
    sch,
    out: Dict[str, Dict[str, str]],
) -> None:
    """Extract ai_-prefixed properties from all symbols in a schematic's raw tree."""
    for sym in kids(sch, "symbol"):
        props = [(str(atom(p, 0)), str(atom(p, 1))) for p in kids(sym, "property")]
        ref = ""
        for key, val in props:
            if key == "Reference":
                ref = val
                break

        if not ref or ref.startswith("#"):
            continue

        ai_props = {}  # type: Dict[str, str]
        for key, val in props:
            if key.startswith(AI_PROP_PREFIX):
                field_name = key[len(AI_PROP_PREFIX):]
                if field_name in AI_PROP_FIELDS and val:
                    ai_props[field_name] = val

        if ai_props:
            out[ref] = ai_props


# ---------------------------------------------------------------------------
# Sheet interface resolution — the net KiCad connects each sheet pin to
# ---------------------------------------------------------------------------
#
# A sheet pin's net is read from KiCad itself, not guessed from its name. In a
# scratch copy of the project, a one-pin probe symbol is placed on the parent
# sheet with its pin exactly on each sheet pin's connection point, and
# kicad-cli exports a netlist. A probe's net holds everything KiCad joins to
# that sheet pin on both sides: the parent-side wires/labels/power symbols and
# the child's hierarchical label. The probe's fellow members are then looked up
# in the real netlist (no probes), so the name reported is the real net's name
# even when KiCad would have named the probed net after the probe. A probe is
# accepted only if its members equal one real net's full member set, so a probe
# that changed connectivity is caught and retried at another point.
#
# No name-matching fallback: the old `_POWER_NET_ALIASES` table (`VCC_3V3` ->
# `+3.3V`) is gone (v8-debug-board Phase 12a); it gave empty or wrong nets on
# boards that name their rails differently.

PROBE_PREFIX = "PRB_SHEETPIN"
PROBE_LIB_ID = "sheetpin_probe:PROBE"
PROBE_LIB_SYMBOL = (
    '\t\t(symbol "{lib}"\n'
    '\t\t\t(pin_names (offset 0) (hide yes))\n'
    '\t\t\t(exclude_from_sim yes) (in_bom yes) (on_board yes)\n'
    '\t\t\t(property "Reference" "{pfx}" (at 0 0 0) (effects (font (size 1.27 1.27))))\n'
    '\t\t\t(property "Value" "PROBE" (at 0 0 0) (effects (font (size 1.27 1.27))))\n'
    '\t\t\t(symbol "PROBE_1_1"\n'
    '\t\t\t\t(pin passive line (at 0 0 0) (length 1.27)\n'
    '\t\t\t\t\t(name "~" (effects (font (size 1.27 1.27))))\n'
    '\t\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))\n'
    '\t\t\t\t)\n'
    '\t\t\t)\n'
    '\t\t)\n'
)
PROBE_INSTANCE = (
    '\t(symbol (lib_id "{lib}") (at {x} {y} 0) (unit 1)\n'
    '\t\t(exclude_from_sim yes) (in_bom yes) (on_board yes) (dnp no)\n'
    '\t\t(uuid "{uuid}")\n'
    '\t\t(property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
    '\t\t(property "Value" "PROBE" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
    '\t\t(property "Footprint" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
    '\t\t(pin "1" (uuid "{pin_uuid}"))\n'
    '\t\t(instances (project "{project}" (path "{path}" (reference "{ref}") (unit 1))))\n'
    '\t)\n'
)


@dataclass
class PinResolution:
    """What KiCad connects one sheet pin to."""
    net: str                       # real net name, "" if none
    members: List[Tuple[str, str]]  # (ref, pin) of component pins on it
    problem: str = ""              # "" when the pin resolves to a net with component pins


def _sexpr_block_end(text: str, start: int) -> int:
    """Index just past the s-expression that opens at text[start] == '('."""
    depth = 0
    i = start
    in_str = False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise RuntimeError("unbalanced s-expression")


def _fmt(v: float) -> str:
    return ("%.4f" % v).rstrip("0").rstrip(".")


def _insert_probes(text: str, project: str, path: str,
                   probes: List[Tuple[str, float, float]]) -> str:
    """Return a sheet's text with the probe lib symbol and one instance per probe.

    `path` is the sheet instance path the probe references are written under
    ("/<root uuid>" on the root, "/<root uuid>/<sheet uuid>" in a child).
    """
    import uuid as uuidlib

    lib_start = text.find("(lib_symbols")
    if lib_start < 0:
        raise RuntimeError("sheet has no lib_symbols block")
    lib_end = _sexpr_block_end(text, lib_start)
    lib_sym = PROBE_LIB_SYMBOL.format(lib=PROBE_LIB_ID, pfx=PROBE_PREFIX)
    instances = "".join(
        PROBE_INSTANCE.format(
            lib=PROBE_LIB_ID, x=_fmt(x), y=_fmt(y), uuid=uuidlib.uuid4(),
            pin_uuid=uuidlib.uuid4(), ref=ref, project=project, path=path)
        for ref, x, y in probes
    )
    close = lib_end - 1  # the ')' closing lib_symbols
    return (text[:close] + lib_sym + "\t" + text[close:lib_end] + "\n"
            + instances + text[lib_end:])


def _root_uuid(text: str) -> str:
    import re
    m = re.search(r'^\t\(uuid "([^"]+)"\)', text, re.M)
    if not m:
        raise RuntimeError("root sheet has no top-level uuid")
    return m.group(1)


def _netlist_nets_raw(xml_path: Path) -> List[Tuple[str, List[Tuple[str, str]]]]:
    """Every net in a kicad-cli XML netlist, unconnected-* stubs included."""
    out = []
    root = ET.parse(str(xml_path)).getroot()
    nets_elem = root.find("nets")
    for net_elem in (nets_elem.findall("net") if nets_elem is not None else []):
        nodes = [(n.get("ref", ""), n.get("pin", "")) for n in net_elem.findall("node")]
        out.append((net_elem.get("name", ""), nodes))
    return out


def _on_segment(p: Tuple[float, float], a: Tuple[float, float],
                b: Tuple[float, float], tol: float = 0.01) -> bool:
    (px, py), (ax, ay), (bx, by) = p, a, b
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if abs(cross) > tol * max(1.0, abs(bx - ax) + abs(by - ay)):
        return False
    return (min(ax, bx) - tol <= px <= max(ax, bx) + tol
            and min(ay, by) - tol <= py <= max(ay, by) + tol)


def _probe_candidates(
    schematic: Path,
    sheet_infos: List[SheetInfo],
) -> Dict[Tuple[str, str], List[Tuple[str, float, float]]]:
    """Probe points to try for each sheet pin, in order: (sheet file, x, y).

    1. The sheet pin itself, on the root.
    2. The ends of each root wire that runs through or ends at the sheet pin.
       KiCad joins a sheet pin lying inside a wire to that wire, but a probe
       pin dropped on the same point splits it off (seen on the
       power-supply board), so a wire end is the next place to probe.
    3. The child's hierarchical label(s) of the same name (single-use
       child sheets only).
    A sheet file of "" means the root.
    """
    out = {}  # type: Dict[Tuple[str, str], List[Tuple[str, float, float]]]
    root_sch = _load_tree(schematic)
    wires = []
    for item in kids(root_sch, "wire"):
        pts_node = child(item, "pts")
        pts = [(float(atom(xy, 0)), float(atom(xy, 1)))
               for xy in (kids(pts_node, "xy") if pts_node is not None else [])]
        if len(pts) >= 2:
            wires.extend(zip(pts, pts[1:]))
    uses = {}  # type: Dict[str, int]
    for info in sheet_infos:
        uses[info.filename] = uses.get(info.filename, 0) + 1
    child_labels = {}  # type: Dict[str, List[Tuple[str, float, float]]]
    for fname in uses:
        path = schematic.parent / fname
        if uses[fname] != 1 or not path.exists():
            continue
        child_labels[fname] = [
            (str(atom(hl, 0)),) + _xy(hl) for hl in kids(_load_tree(path), "hierarchical_label")]

    for info in sheet_infos:
        for pin in info.pins:
            p = (pin.x, pin.y)
            cands = [("", pin.x, pin.y)]
            for a, b in wires:
                if _on_segment(p, a, b):
                    for e in (a, b):
                        c = ("", e[0], e[1])
                        if c not in cands:
                            cands.append(c)
            for text, x, y in child_labels.get(info.filename, []):
                if text == pin.name:
                    cands.append((info.filename, x, y))
            out[(info.filename, pin.name)] = cands
    return out


def _probe_round(
    kicad_cli: str,
    schematic: Path,
    sheet_infos: List[SheetInfo],
    placements: Dict[Tuple[str, str], Tuple[str, float, float]],
) -> Dict[Tuple[str, str], List[Tuple[str, str]]]:
    """One probe netlist: (sheet, pin) -> component pins on the probe's net.

    A pin missing from the result had its probe on no net at all.
    """
    sheet_uuid = {i.filename: i.uuid for i in sheet_infos}
    by_file = {}  # type: Dict[str, List[Tuple[str, float, float]]]
    owner = {}  # type: Dict[str, Tuple[str, str]]
    for n, (key, (fname, x, y)) in enumerate(sorted(placements.items()), 1):
        ref = "{}{}".format(PROBE_PREFIX, n)
        owner[ref] = key
        by_file.setdefault(fname, []).append((ref, x, y))

    with tempfile.TemporaryDirectory(prefix="sheetpin_probe_") as tmp:
        tmp_dir = Path(tmp)
        for f in schematic.parent.iterdir():
            if f.is_file() and (f.suffix in (".kicad_sch", ".kicad_pro")
                                or f.name in ("sym-lib-table", "fp-lib-table")):
                shutil.copy2(str(f), str(tmp_dir / f.name))
        root_uuid = _root_uuid(schematic.read_text())
        for fname, probes in by_file.items():
            if fname:
                src = schematic.parent / fname
                path = "/{}/{}".format(root_uuid, sheet_uuid[fname])
            else:
                src = schematic
                path = "/" + root_uuid
            (tmp_dir / src.name).write_text(
                _insert_probes(src.read_text(), schematic.stem, path, probes))

        xml_path = export_netlist_xml(kicad_cli, tmp_dir / schematic.name)
        try:
            raw = _netlist_nets_raw(xml_path)
        finally:
            xml_path.unlink()

    found = {}  # type: Dict[Tuple[str, str], List[Tuple[str, str]]]
    for _name, nodes in raw:
        members = sorted(((r, p) for r, p in nodes if not r.startswith(PROBE_PREFIX)),
                         key=lambda m: (m[0], _pin_sort_key(m[1])))
        for r, _p in nodes:
            if r in owner:
                found[owner[r]] = members
    return found


def probe_sheet_pins(
    kicad_cli: str,
    schematic: Path,
    sheet_infos: List[SheetInfo],
    nets: Dict[str, Net],
) -> Dict[Tuple[str, str], PinResolution]:
    """Resolve every root-level sheet pin to the net KiCad connects it to.

    Returns (sheet filename, pin name) -> PinResolution. Works on scratch
    copies of the project folder; the real files are only read.

    A probe is accepted only when its fellow members are exactly one real
    net's full member set: the probe must not have changed connectivity.
    A pin whose probe fails that (or lands on no component pins) is probed
    again at its next candidate point (_probe_candidates), one kicad-cli
    export per round. A pin still unresolved after its last candidate is
    reported with the reason.
    """
    if kio is None:
        raise RuntimeError("kicad-tools is required to resolve sheet pins (run with tools/.venv/bin/python)")
    cands = _probe_candidates(schematic, sheet_infos)
    if not cands:
        return {}

    real_by_member = {}  # type: Dict[Tuple[str, str], str]
    real_members = {}  # type: Dict[str, Set[Tuple[str, str]]]
    for net in nets.values():
        real_members[net.name] = set()
        for c in net.connections:
            real_by_member[(c.ref, c.pin)] = net.name
            real_members[net.name].add((c.ref, c.pin))

    result = {}  # type: Dict[Tuple[str, str], PinResolution]
    pending = {key: 0 for key in cands}  # key -> index of the candidate to try
    while pending:
        placements = {key: cands[key][i] for key, i in pending.items()}
        found = _probe_round(kicad_cli, schematic, sheet_infos, placements)
        retry = {}
        for key, i in pending.items():
            members = found.get(key)
            if members is None:
                res = PinResolution("", [], "probe on no net")
            elif not members:
                res = PinResolution("", [], "no component pins on its net")
            else:
                names = sorted({real_by_member.get(m, "") for m in members})
                if len(names) != 1 or not names[0]:
                    res = PinResolution("", members, "probe members span real nets {}".format(names))
                elif set(members) != real_members[names[0]]:
                    res = PinResolution("", members, "probe split net {} (got {} of its {} pins)".format(
                        names[0], len(members), len(real_members[names[0]])))
                else:
                    res = PinResolution(names[0], members)
            if res.problem and i + 1 < len(cands[key]):
                retry[key] = i + 1
            else:
                result[key] = res
        pending = retry
    return result


def build_sheet_interfaces(
    sheet_infos: List[SheetInfo],
    resolved: Dict[Tuple[str, str], PinResolution],
) -> dict:
    """Build the sheet_interfaces section: each sheet pin and its real net."""
    interfaces = {}  # type: dict
    for info in sheet_infos:
        pins_out = []
        for pin in info.pins:
            res = resolved.get((info.filename, pin.name))
            pins_out.append({
                "name": pin.name,
                "direction": pin.direction,
                "net": res.net if res else "",
            })
        pins_out.sort(key=lambda p: p["name"])
        interfaces[info.filename] = {
            "description": "",
            "pins": pins_out,
        }
    return interfaces


def sheet_pin_offenders(
    resolved: Dict[Tuple[str, str], PinResolution],
) -> List[str]:
    """One line per sheet pin that resolves to no net or a net with no component pins."""
    return [
        "{} : {} — {}".format(sheet, pin, res.problem)
        for (sheet, pin), res in sorted(resolved.items())
        if res.problem
    ]


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
    resolved_pins: Optional[Dict[Tuple[str, str], PinResolution]] = None,
) -> dict:
    """Assemble the circuit-context.json structure from parsed data.

    Annotation fields for components are populated from the schematic's ai_
    properties when available; otherwise emitted as empty strings
    (populated during the annotation pass in Phase 3).
    """
    if component_props is None:
        component_props = {}
    if sheet_infos is None:
        sheet_infos = []
    if resolved_pins is None:
        resolved_pins = {}

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
        "sheet_interfaces": build_sheet_interfaces(sheet_infos, resolved_pins),
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


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                              cwd=str(Path(__file__).resolve().parent)).stdout.strip()
    except OSError:
        return ""


def build_provenance(schematic: Path, sheet_files: List[str]) -> dict:
    """`_provenance` per tools/CONTEXT.md Source-Hash Rule. `source` is the root sheet; a
    hierarchical schematic's child sheets are hashed in `sources` (path -> sha256), which
    tools/lab/check_state.py --fresh also checks, so an edit to any sheet marks the file stale."""
    top = _git("rev-parse", "--show-toplevel")
    root = Path(top) if top else None

    def rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(root.resolve())) if root else str(p.resolve())
        except ValueError:
            return str(p.resolve())

    def sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    sources = {}
    for name in sorted(set(sheet_files)):
        child = (schematic.parent / name)
        if child.is_file() and child.resolve() != schematic.resolve():
            sources[rel(child)] = sha(child)
    commit = _git("rev-parse", "HEAD") or "unknown"
    if _git("status", "--porcelain", "--", str(Path(__file__).resolve())):
        commit += "-dirty"
    return {
        "source": rel(schematic),
        "source_sha256": sha(schematic),
        "sources": sources,
        "generator": "tools/schematic-context/extract.py",
        "generator_commit": commit,
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


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
    parser.add_argument(
        "--check-sheet-pins",
        action="store_true",
        help=(
            "Resolve every sheet pin and exit non-zero if any resolves to no net "
            "or to a net with no component pins (each offender is listed). "
            "Writes nothing unless --output is also given."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="With --check-sheet-pins: print every sheet pin, its net and members",
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

        # --- Step 3: Read the schematic files ---
        print("Reading schematic properties via kicad_io...", file=sys.stderr)
        component_props, sheet_infos = read_schematic_properties(schematic)
        annotated = sum(1 for v in component_props.values() if v)
        print(
            f"  {len(sheet_infos)} child sheets, "
            f"{annotated} components with ai_ properties",
            file=sys.stderr,
        )

        # --- Step 4: Resolve sheet pins to the nets KiCad connects them to ---
        print("Resolving sheet pins (probe netlist)...", file=sys.stderr)
        resolved_pins = probe_sheet_pins(kicad_cli, schematic, sheet_infos, nets)
        offenders = sheet_pin_offenders(resolved_pins)
        print(
            f"  {len(resolved_pins)} sheet pins, {len(offenders)} unresolved",
            file=sys.stderr,
        )

        if args.check_sheet_pins:
            if args.verbose:
                for (sheet, pin), res in sorted(resolved_pins.items()):
                    members = " ".join("{}.{}".format(r, p) for r, p in res.members)
                    print("{} : {} -> {} [{}]".format(
                        sheet, pin, res.net or "(none)", members))
            if offenders:
                print("SHEET-PIN CHECK FAILED: {} offender(s)".format(len(offenders)))
                for line in offenders:
                    print("  " + line)
            else:
                print("SHEET-PIN CHECK PASSED: {} sheet pins, each on a net with "
                      "component pins".format(len(resolved_pins)))
            if not args.output:
                sys.exit(1 if offenders else 0)

        # --- Step 5: Build context and merge ---
        context = build_context(
            components, nets, sheet_map, schematic,
            component_props=component_props,
            sheet_infos=sheet_infos,
            resolved_pins=resolved_pins,
        )

        if args.previous:
            context = merge_previous_context(args.previous, context)

        context = dict([("_provenance", build_provenance(
            schematic, [i.filename for i in sheet_infos] if sheet_infos else []))] + list(context.items()))

        # --- Step 6: Write circuit-context.json ---
        write_context_json(context, output_path)
        print(
            f"Wrote {output_path.name} "
            f"({output_path.stat().st_size:,} bytes)",
            file=sys.stderr,
        )
        if args.check_sheet_pins and offenders:
            sys.exit(1)

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
