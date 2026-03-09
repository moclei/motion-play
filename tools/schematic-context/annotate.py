#!/usr/bin/env python3
"""
annotate.py — Write AI annotation properties to KiCad schematic components.

Writes ai_-prefixed custom properties (ai_function, ai_block, ai_role,
ai_critical_specs) to component symbols in .kicad_sch files via kiutils.
Properties are hidden in the schematic editor and survive schematic edits.

Usage:
    python annotate.py <root.kicad_sch> <ref> key=value [key=value ...]
    python annotate.py <root.kicad_sch> <ref> --clear
    python annotate.py <root.kicad_sch> <ref> <ref2> ... -- key=value [key=value ...]

Examples:
    python annotate.py main.kicad_sch U1 function="3.3V LDO regulator" block=power
    python annotate.py main.kicad_sch R28 R29 -- role=pull_up block=i2c_mux
    python annotate.py main.kicad_sch C1 --clear

Environment:
    Python 3.7+, kiutils >= 1.4.8
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from kiutils.schematic import Schematic
    from kiutils.items.common import Effects, Font, Property
except ImportError:
    print(
        "Error: kiutils is required. Install with: pip install kiutils>=1.4.8",
        file=sys.stderr,
    )
    sys.exit(1)


AI_PROP_PREFIX = "ai_"
VALID_FIELDS = ("function", "block", "role", "critical_specs")

FONT_SIZE = 1.27


def load_all_schematics(
    root_path: Path,
) -> Dict[str, Tuple[Path, "Schematic"]]:
    """Load root and all child schematics, keyed by resolved path string.

    Returns a dict mapping file path string → (Path, Schematic).
    Schematics are loaded once and reused for all operations.
    """
    loaded = {}  # type: Dict[str, Tuple[Path, Schematic]]
    root_sch = Schematic.from_file(str(root_path))
    loaded[str(root_path)] = (root_path, root_sch)

    root_dir = root_path.parent
    for sheet in root_sch.sheets:
        child_path = (root_dir / sheet.fileName.value).resolve()
        if not child_path.exists():
            print(
                "Warning: child sheet not found: {}".format(child_path),
                file=sys.stderr,
            )
            continue
        if str(child_path) not in loaded:
            child_sch = Schematic.from_file(str(child_path))
            loaded[str(child_path)] = (child_path, child_sch)

    return loaded


def find_symbol(
    schematics: Dict[str, Tuple[Path, "Schematic"]],
    ref: str,
) -> Tuple[Optional[Path], Optional["Schematic"], Optional[object]]:
    """Locate a symbol by reference designator across loaded schematics.

    Returns (schematic_path, schematic_object, symbol) or (None, None, None)
    if the component is not found.
    """
    for sch_path, sch in schematics.values():
        result = _find_symbol_in_schematic(sch, ref)
        if result is not None:
            return sch_path, sch, result

    return None, None, None


def _find_symbol_in_schematic(
    sch: "Schematic",
    ref: str,
) -> Optional[object]:
    """Find a symbol with the given Reference property value."""
    for sym in sch.schematicSymbols:
        for prop in sym.properties:
            if prop.key == "Reference" and prop.value == ref:
                return sym
    return None


def write_ai_properties(
    symbol: object,
    props: Dict[str, str],
) -> List[str]:
    """Write ai_-prefixed properties to a symbol.

    Updates existing properties or creates new ones as needed.
    Returns a list of actions taken (for logging).
    """
    actions = []  # type: List[str]

    for field_name, value in sorted(props.items()):
        full_key = AI_PROP_PREFIX + field_name

        existing = None
        for prop in symbol.properties:
            if prop.key == full_key:
                existing = prop
                break

        if existing is not None:
            if existing.value != value:
                old = existing.value
                existing.value = value
                actions.append(
                    "  updated {}: {!r} -> {!r}".format(full_key, old, value)
                )
            else:
                actions.append("  unchanged {}: {!r}".format(full_key, value))
        else:
            new_prop = Property(
                key=full_key,
                value=value,
                effects=Effects(
                    font=Font(height=FONT_SIZE, width=FONT_SIZE),
                    hide=True,
                ),
            )
            symbol.properties.append(new_prop)
            actions.append("  added {}: {!r}".format(full_key, value))

    return actions


def clear_ai_properties(symbol: object) -> List[str]:
    """Remove all ai_-prefixed properties from a symbol.

    Returns a list of actions taken (for logging).
    """
    actions = []  # type: List[str]
    remaining = []

    for prop in symbol.properties:
        if prop.key.startswith(AI_PROP_PREFIX):
            actions.append("  removed {}: {!r}".format(prop.key, prop.value))
        else:
            remaining.append(prop)

    if actions:
        symbol.properties = remaining
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
        sch_path, sch, symbol = find_symbol(schematics, ref)

        if symbol is None:
            print("Error: component {} not found in any sheet".format(ref), file=sys.stderr)
            errors += 1
            continue

        print("{}  (in {})".format(ref, sch_path.name))

        if parsed.clear:
            actions = clear_ai_properties(symbol)
        else:
            actions = write_ai_properties(symbol, props)

        for action in actions:
            print(action)

        modified_keys.add(str(sch_path))

    if errors and not modified_keys:
        sys.exit(1)

    for file_key in sorted(modified_keys):
        sch_path, sch = schematics[file_key]
        sch.to_file(str(sch_path))
        print("\nSaved {}".format(sch_path.name))

    if errors:
        print(
            "\nWarning: {} ref(s) not found".format(errors),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
