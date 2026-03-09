#!/usr/bin/env python3
"""
show.py — Display AI annotation status for KiCad schematic components.

Reads all component symbols from a root schematic and its child sheets,
checks for ai_-prefixed properties, and displays annotation coverage.
Useful for guiding interactive annotation sessions.

Usage:
    python show.py <root.kicad_sch>
    python show.py <root.kicad_sch> --unannotated
    python show.py <root.kicad_sch> --sheet led_controller.kicad_sch

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
except ImportError:
    print(
        "Error: kiutils is required. Install with: pip install kiutils>=1.4.8",
        file=sys.stderr,
    )
    sys.exit(1)


AI_PROP_PREFIX = "ai_"
AI_PROP_FIELDS = ("function", "block", "role", "critical_specs")


def collect_components(
    root_path: Path,
) -> List[Dict[str, str]]:
    """Collect all components with their annotation status from all sheets.

    Returns a list of dicts with keys: ref, part, value, sheet, and each
    ai_ field (empty string if not set).
    """
    root_sch = Schematic.from_file(str(root_path))
    root_dir = root_path.parent

    components = []  # type: List[Dict[str, str]]

    _collect_from_schematic(root_sch, root_path.name, components)

    for sheet in root_sch.sheets:
        child_path = root_dir / sheet.fileName.value
        if not child_path.exists():
            print(
                "Warning: child sheet not found: {}".format(child_path),
                file=sys.stderr,
            )
            continue
        child_sch = Schematic.from_file(str(child_path))
        _collect_from_schematic(child_sch, sheet.fileName.value, components)

    components.sort(key=lambda c: _ref_sort_key(c["ref"]))
    return components


def _collect_from_schematic(
    sch: "Schematic",
    sheet_name: str,
    out: List[Dict[str, str]],
) -> None:
    """Extract component info and ai_ properties from one schematic file."""
    for sym in sch.schematicSymbols:
        ref = ""
        part = ""
        value = ""

        for prop in sym.properties:
            if prop.key == "Reference":
                ref = prop.value
            elif prop.key == "Value":
                value = prop.value
            elif prop.key == "Description":
                part = prop.value

        if not ref or ref.startswith("#"):
            continue

        comp = {
            "ref": ref,
            "part": part,
            "value": value,
            "sheet": sheet_name,
        }  # type: Dict[str, str]

        for field in AI_PROP_FIELDS:
            comp[field] = ""

        for prop in sym.properties:
            if prop.key.startswith(AI_PROP_PREFIX):
                field_name = prop.key[len(AI_PROP_PREFIX):]
                if field_name in AI_PROP_FIELDS and prop.value:
                    comp[field_name] = prop.value

        out.append(comp)


def _ref_sort_key(ref: str) -> Tuple[str, int, str]:
    """Sort refs by letter prefix then numeric suffix (C1 < C2 < C10)."""
    prefix = ""
    num_str = ""
    for i, ch in enumerate(ref):
        if ch.isdigit():
            prefix = ref[:i]
            num_str = ref[i:]
            break
    else:
        prefix = ref
        num_str = ""

    try:
        num = int(num_str)
    except ValueError:
        num = 0

    return (prefix, num, ref)


def is_annotated(comp: Dict[str, str]) -> bool:
    """A component counts as annotated if it has at least ai_function set."""
    return bool(comp.get("function"))


def format_sheet(name: str) -> str:
    """Shorten root sheet name for display."""
    if name.endswith(".kicad_sch"):
        name = name[:-len(".kicad_sch")]
    return name


def display_components(
    components: List[Dict[str, str]],
    show_only_unannotated: bool,
    sheet_filter: Optional[str],
) -> None:
    """Display components with annotation status."""
    if sheet_filter:
        components = [c for c in components if sheet_filter in c["sheet"]]

    annotated = [c for c in components if is_annotated(c)]
    unannotated = [c for c in components if not is_annotated(c)]

    total = len(components)
    n_annotated = len(annotated)
    n_unannotated = len(unannotated)

    print("Annotation Status: {}/{} components annotated".format(
        n_annotated, total,
    ))

    if n_annotated > 0:
        pct = 100.0 * n_annotated / total
        bar_width = 30
        filled = int(bar_width * n_annotated / total)
        bar = "#" * filled + "-" * (bar_width - filled)
        print("  [{}] {:.0f}%".format(bar, pct))

    print()

    if not show_only_unannotated and annotated:
        print("--- Annotated ({}) ---".format(n_annotated))
        for comp in annotated:
            _print_component(comp, show_props=True)
        print()

    if unannotated:
        print("--- Unannotated ({}) ---".format(n_unannotated))
        for comp in unannotated:
            _print_component(comp, show_props=False)
        print()

    if not unannotated:
        print("All components are annotated!")

    by_sheet = {}  # type: Dict[str, Tuple[int, int]]
    for comp in components:
        sheet = format_sheet(comp["sheet"])
        ann, tot = by_sheet.get(sheet, (0, 0))
        tot += 1
        if is_annotated(comp):
            ann += 1
        by_sheet[sheet] = (ann, tot)

    if len(by_sheet) > 1:
        print("--- By Sheet ---")
        for sheet in sorted(by_sheet.keys()):
            ann, tot = by_sheet[sheet]
            print("  {:30s}  {}/{}".format(sheet, ann, tot))


def _print_component(comp: Dict[str, str], show_props: bool) -> None:
    """Print a single component line."""
    label = comp["value"] or comp["part"] or "?"
    sheet = format_sheet(comp["sheet"])
    print("  {:12s} {:30s}  [{}]".format(comp["ref"], label, sheet))

    if show_props:
        for field in AI_PROP_FIELDS:
            val = comp.get(field, "")
            if val:
                print("    {:20s} {}".format(AI_PROP_PREFIX + field + ":", val))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display AI annotation status for KiCad schematic components.",
    )
    parser.add_argument(
        "schematic",
        help="Path to the root .kicad_sch file",
    )
    parser.add_argument(
        "--unannotated", "-u",
        action="store_true",
        help="Show only unannotated components",
    )
    parser.add_argument(
        "--sheet", "-s",
        help="Filter to components on a specific sheet (substring match)",
    )
    args = parser.parse_args()

    schematic = Path(args.schematic).resolve()
    if not schematic.exists() or not schematic.is_file():
        print("Error: schematic not found: {}".format(schematic), file=sys.stderr)
        sys.exit(1)

    components = collect_components(schematic)
    display_components(components, args.unannotated, args.sheet)


if __name__ == "__main__":
    main()
