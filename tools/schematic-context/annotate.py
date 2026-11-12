#!/usr/bin/env python3
"""
annotate.py — Write AI annotation properties to KiCad schematic components.

Writes ai_-prefixed custom properties (ai_function, ai_block, ai_role,
ai_critical_specs) to component symbols in .kicad_sch files. Files are loaded
and saved through tools/kicad-io/kicad_io.py (raw s-expression layer, splice
save). Properties are hidden in the schematic editor, in the file's own hide
form (KiCad 9 or 10), and survive schematic edits.

Usage:
    python annotate.py <root.kicad_sch> <ref> key=value [key=value ...]
    python annotate.py <root.kicad_sch> <ref> --clear
    python annotate.py <root.kicad_sch> <ref> <ref2> ... -- key=value [key=value ...]

Examples:
    python annotate.py main.kicad_sch U1 function="3.3V LDO regulator" block=power
    python annotate.py main.kicad_sch R28 R29 -- role=pull_up block=i2c_mux
    python annotate.py main.kicad_sch C1 --clear

Environment:
    tools/.venv/bin/python (kicad-tools pinned in tools/requirements.txt)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad-io"))
import kicad_io as kio  # noqa: E402
from kicad_io import atom, atom_text, child, kids, node  # noqa: E402


AI_PROP_PREFIX = "ai_"
VALID_FIELDS = ("function", "block", "role", "critical_specs")

FONT_SIZE = 1.27


def _sheet_file(sheet) -> str:
    """A sheet reference's file name (KiCad 7+ ``Sheetfile``, KiCad 6 ``Sheet file``)."""
    for p in kids(sheet, "property"):
        if atom(p, 0) in ("Sheetfile", "Sheet file"):
            return str(atom(p, 1))
    return ""


def load_all_schematics(
    root_path: Path,
) -> Dict[str, Tuple[Path, "kio.Doc"]]:
    """Load root and all child schematics, keyed by resolved path string.

    Returns a dict mapping file path string -> (Path, kicad_io Doc).
    Schematics are loaded once and reused for all operations.
    """
    loaded = {}  # type: Dict[str, Tuple[Path, kio.Doc]]
    root_doc = kio.load_schematic(root_path)
    loaded[str(root_path)] = (root_path, root_doc)

    root_dir = root_path.parent
    for sheet in kids(root_doc.tree, "sheet"):
        child_path = (root_dir / _sheet_file(sheet)).resolve()
        if not child_path.exists():
            print(
                "Warning: child sheet not found: {}".format(child_path),
                file=sys.stderr,
            )
            continue
        if str(child_path) not in loaded:
            loaded[str(child_path)] = (child_path, kio.load_schematic(child_path))

    return loaded


def find_symbol(
    schematics: Dict[str, Tuple[Path, "kio.Doc"]],
    ref: str,
) -> Tuple[Optional[Path], Optional["kio.Doc"], Optional[object]]:
    """Locate a symbol by reference designator across loaded schematics.

    Returns (schematic_path, doc, raw symbol node) or (None, None, None)
    if the component is not found.
    """
    for sch_path, doc in schematics.values():
        result = _find_symbol_in_schematic(doc, ref)
        if result is not None:
            return sch_path, doc, result

    return None, None, None


def _find_symbol_in_schematic(
    doc: "kio.Doc",
    ref: str,
) -> Optional[object]:
    """Find a symbol with the given Reference property value."""
    for sym in kids(doc.tree, "symbol"):
        for prop in kids(sym, "property"):
            if atom(prop, 0) == "Reference" and atom(prop, 1) == ref:
                return sym
    return None


def _prop(symbol, key: str):
    for p in kids(symbol, "property"):
        if atom(p, 0) == key:
            return p
    return None


def _append_prop(symbol, prop) -> None:
    """After the symbol's last property (properties come before pins and instances)."""
    idx = max((i for i, c in enumerate(symbol.children) if c.name == "property"), default=None)
    if idx is None:
        idx = max(i for i, c in enumerate(symbol.children) if c.name in ("uuid", "at", "lib_id"))
    symbol.children.insert(idx + 1, prop)


def _home_hidden(doc: "kio.Doc", prop, sx: str, sy: str) -> bool:
    """Hide an ai_* property and put it at its symbol's origin (``sx``, ``sy``: the symbol's
    ``at`` text).

    A hidden field still has a position: KiCad uses it for the sheet's
    bounding box and "zoom to fit", so a field left at (0, 0) drags the view
    off the sheet (readability section 1.2). The hide flag is written in the
    file's own form (kicad_io.hide). Returns True if anything changed.
    """
    changed = False
    if child(prop, "effects") is None:
        prop.children.append(node(kio.effects_text(size=FONT_SIZE)))
        changed = True
    changed |= kio.hide(doc, prop)
    at = child(prop, "at")
    if at is None or float(atom(at, 0)) != float(sx) or float(atom(at, 1)) != float(sy):
        new_at = node("(at {} {} 0)".format(sx, sy))
        if at is None:
            prop.children.insert(2, new_at)
        else:
            prop.children[prop.children.index(at)] = new_at
        changed = True
    return changed


def write_ai_properties(
    doc: "kio.Doc",
    symbol,
    props: Dict[str, str],
) -> List[str]:
    """Write ai_-prefixed properties to a symbol (a raw node in ``doc``).

    Updates existing properties or creates new ones as needed. Every ai_*
    property written (new or existing) is hidden (in the file's own form) and
    placed at the symbol's position, angle 0; a new one goes after the
    symbol's last property. Returns a list of actions taken (for logging).
    """
    actions = []  # type: List[str]
    at = child(symbol, "at")
    sx, sy = atom_text(at, 0), atom_text(at, 1)

    for field_name, value in sorted(props.items()):
        full_key = AI_PROP_PREFIX + field_name
        existing = _prop(symbol, full_key)

        if existing is not None:
            if _home_hidden(doc, existing, sx, sy):
                actions.append("  re-homed {} (hidden, at symbol)".format(full_key))
            old = str(atom(existing, 1))
            if old != value:
                kio.set_str(existing, 1, value)
                actions.append(
                    "  updated {}: {!r} -> {!r}".format(full_key, old, value)
                )
            else:
                actions.append("  unchanged {}: {!r}".format(full_key, value))
        else:
            _append_prop(symbol, kio.make_property(doc, full_key, value, sx, sy, 0, hide=True))
            actions.append("  added {}: {!r}".format(full_key, value))

    return actions


def clear_ai_properties(symbol) -> List[str]:
    """Remove all ai_-prefixed properties from a symbol (a raw node).

    Returns a list of actions taken (for logging).
    """
    actions = []  # type: List[str]
    drop = []

    for prop in kids(symbol, "property"):
        key = str(atom(prop, 0))
        if key.startswith(AI_PROP_PREFIX):
            actions.append("  removed {}: {!r}".format(key, str(atom(prop, 1))))
            drop.append(prop)

    if actions:
        kio.remove_items(symbol, drop)
    else:
        actions.append("  no ai_ properties to clear")

    return actions


def parse_key_value_pairs(args: List[str]) -> Dict[str, str]:
    """Parse key=value arguments into a dict, validating field names."""
    props = {}  # type: Dict[str, str]
    for arg in args:
        if "=" not in arg:
            print(
                "Error: expected key=value, got: {!r}\n"
                "  Valid keys: {}".format(arg, ", ".join(VALID_FIELDS)),
                file=sys.stderr,
            )
            sys.exit(1)

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key not in VALID_FIELDS:
            print(
                "Error: unknown field {!r}\n"
                "  Valid fields: {}".format(key, ", ".join(VALID_FIELDS)),
                file=sys.stderr,
            )
            sys.exit(1)

        if not value:
            print(
                "Error: empty value for field {!r}".format(key),
                file=sys.stderr,
            )
            sys.exit(1)

        props[key] = value

    return props


def split_refs_and_props(args: List[str]) -> Tuple[List[str], List[str]]:
    """Split positional args into refs and key=value pairs.

    Supports two forms:
      1. Single ref followed by key=value pairs:  U1 function=... block=...
      2. Multiple refs separated by -- from props: U1 U2 -- function=... block=...
    """
    if "--" in args:
        idx = args.index("--")
        return args[:idx], args[idx + 1:]

    refs = []  # type: List[str]
    kv_args = []  # type: List[str]
    for arg in args:
        if "=" in arg:
            kv_args.append(arg)
        else:
            refs.append(arg)

    return refs, kv_args


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write AI annotation properties to KiCad schematic components.",
        epilog="Valid fields: " + ", ".join(VALID_FIELDS),
    )
    parser.add_argument(
        "schematic",
        help="Path to the root .kicad_sch file",
    )
    parser.add_argument(
        "args",
        nargs="+",
        help="Component ref(s) and key=value pairs (use -- to separate multiple refs from props)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Remove all ai_ properties from the specified component(s)",
    )

    parsed = parser.parse_args()

    schematic = Path(parsed.schematic).resolve()
    if not schematic.exists() or not schematic.is_file():
        print("Error: schematic not found: {}".format(schematic), file=sys.stderr)
        sys.exit(1)

    refs, kv_args = split_refs_and_props(parsed.args)

    if not refs:
        print("Error: no component reference(s) provided", file=sys.stderr)
        sys.exit(1)

    if not parsed.clear and not kv_args:
        print(
            "Error: no key=value pairs provided (or use --clear to remove annotations)",
            file=sys.stderr,
        )
        sys.exit(1)

    props = {}  # type: Dict[str, str]
    if not parsed.clear:
        props = parse_key_value_pairs(kv_args)

    schematics = load_all_schematics(schematic)
    modified_keys = set()  # type: set
    errors = 0

    for ref in refs:
        sch_path, doc, symbol = find_symbol(schematics, ref)

        if symbol is None:
            print("Error: component {} not found in any sheet".format(ref), file=sys.stderr)
            errors += 1
            continue

        print("{}  (in {})".format(ref, sch_path.name))

        if parsed.clear:
            actions = clear_ai_properties(symbol)
        else:
            actions = write_ai_properties(doc, symbol, props)

        for action in actions:
            print(action)

        modified_keys.add(str(sch_path))

    if errors and not modified_keys:
        sys.exit(1)

    # one lock check before any write, so a refusal writes nothing
    kio.save_project(schematics[k][1] for k in sorted(modified_keys))
    for file_key in sorted(modified_keys):
        sch_path, _doc = schematics[file_key]
        print("\nSaved {}".format(sch_path.name))

    if errors:
        print(
            "\nWarning: {} ref(s) not found".format(errors),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
