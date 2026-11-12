#!/usr/bin/env python3
"""
v8_project_setup.py - Create the v8 debug-board KiCad project from the v7 project.

Initiative: docs/initiatives/v8-debug-board (Phase 8, task 1).

What it does (all through git + tools/kicad-io/kicad_io.py; no .kicad_sch/.kicad_pcb text is edited
by hand):
  1. Copies the v7 project files from a git commit (default c2acffc) into
     hardware/pcb-main-v8/kicad/, renaming motion-play-main.* to motion-play-main-v8.*.
     Copied: .kicad_pro, the five .kicad_sch sheets, .kicad_dru, sym-lib-table,
     fp-lib-table, libraries/. Not copied: the v7 board, reports, production,
     netlists, generated context JSON, STEP.
  2. Rewrites the lib tables so ${KIPRJMOD}/../resources points at the v7 resources
     folder (hardware/pcb-main/resources), which stays the single copy.
  3. Renames every symbol and sheet instance's project to motion-play-main-v8 and sets
     the title blocks to v8 (raw-tree edit, splice save; checked netlist-identical to v7).
  4. Writes a fresh .kicad_pcb from the v7 board: setup (stackup, design settings),
     layers, paper and title block only. No footprints, nets, tracks, zones, graphics
     or outline.
  5. Verifies with kicad-cli: ERC on the root schematic, netlist export compared with
     the v7 netlist at the same commit (components and net membership must match),
     and a DRC run on the empty board (proves it opens).

Usage:
  python3 tools/schematic-modify/v8_project_setup.py            # dry run: verify only if present
  python3 tools/schematic-modify/v8_project_setup.py --apply    # create (refuses if dest exists)
  python3 tools/schematic-modify/v8_project_setup.py --verify   # re-run the checks on dest
  python3 tools/schematic-modify/v8_project_setup.py --verify --root <copy>/motion-play-main-v8.kicad_sch
                                                                 # the checks on another copy of the
                                                                 # v8 project (a scratch copy); DRC
                                                                 # runs there, not on the working tree
  python3 tools/schematic-modify/v8_project_setup.py --apply --root <scratch>/hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch
                                                                 # create the project in a scratch folder
                                                                 # outside the repository (a replay); the
                                                                 # lib tables expect hardware/pcb-main/resources
                                                                 # two levels up, as in the repository
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad-io"))
import kicad_io as kio  # noqa: E402
from kicad_io import atom, child, kids, node  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
V7_DIR = "hardware/pcb-main/kicad"
DEST = REPO / "hardware/pcb-main-v8/kicad"
OLD = "motion-play-main"
NEW = "motion-play-main-v8"
KICAD_CLI = os.environ.get("KICAD_CLI") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
SHEETS = [
    "esp32_s3.kicad_sch",
    "led_controller.kicad_sch",
    "power_management.kicad_sch",
    "tca9548A_subsystem.kicad_sch",
]
TITLE = "Motion Play Main Board v8 (debug board)"
REVISION = "8.0"


def inside_repo(path: Path) -> bool:
    try:
        Path(path).resolve().relative_to(REPO.resolve())
        return True
    except ValueError:
        return False


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO)] + list(args), check=True,
                          capture_output=True).stdout


def git_files(commit: str, prefix: str):
    out = git("ls-tree", "-r", "--name-only", commit, prefix).decode()
    return [l for l in out.splitlines() if l]


def copy_from_git(commit: str, src: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(git("show", "{}:{}".format(commit, src)))


def copy_project(commit: str) -> None:
    mapping = {
        "{}/{}.kicad_sch".format(V7_DIR, OLD): "{}.kicad_sch".format(NEW),
        "{}/{}.kicad_pro".format(V7_DIR, OLD): "{}.kicad_pro".format(NEW),
        "{}/{}.kicad_dru".format(V7_DIR, OLD): "{}.kicad_dru".format(NEW),
        "{}/sym-lib-table".format(V7_DIR): "sym-lib-table",
        "{}/fp-lib-table".format(V7_DIR): "fp-lib-table",
    }
    for s in SHEETS:
        mapping["{}/{}".format(V7_DIR, s)] = s
    for f in git_files(commit, V7_DIR + "/libraries"):
        mapping[f] = f[len(V7_DIR) + 1:]
    for src, rel in sorted(mapping.items()):
        copy_from_git(commit, src, DEST / rel)
        print("  copied {} -> {}".format(src, rel))

    # Project file: JSON, update the meta filename only.
    pro = DEST / "{}.kicad_pro".format(NEW)
    data = json.loads(pro.read_text())
    data["meta"]["filename"] = pro.name
    data.get("pcbnew", {}).get("last_paths", {})["step"] = ""
    pro.write_text(json.dumps(data, indent=2) + "\n")

    # Lib tables: v7's resources folder stays the single copy.
    for name in ("sym-lib-table", "fp-lib-table"):
        p = DEST / name
        text = p.read_text()
        text = text.replace("${KIPRJMOD}/../resources/", "${KIPRJMOD}/../../pcb-main/resources/")
        p.write_text(text)


# title_block children in KiCad's order; a missing one is inserted at its place.
TITLE_BLOCK_ORDER = ("title", "date", "rev", "company", "comment")


def _set_title_field(tb, key: str, value: str) -> None:
    n = child(tb, key)
    if n is not None:
        kio.set_str(n, 0, value)
        return
    rank = TITLE_BLOCK_ORDER.index(key)
    idx = len(tb.children)
    for i, c in enumerate(tb.children):
        if c.name in TITLE_BLOCK_ORDER and TITLE_BLOCK_ORDER.index(c.name) > rank:
            idx = i
            break
    tb.children.insert(idx, node("({} {})".format(key, kio.q(value))))


def rename_instances() -> None:
    today = datetime.date.today().isoformat()
    for f in [DEST / "{}.kicad_sch".format(NEW)] + [DEST / s for s in SHEETS]:
        doc = kio.load_schematic(f)
        n = 0
        for item in kids(doc.tree, "symbol") + kids(doc.tree, "sheet"):
            inst = child(item, "instances")
            for proj in (kids(inst, "project") if inst is not None else []):
                kio.set_str(proj, 0, NEW)
                n += 1
        tb = child(doc.tree, "title_block")
        if tb is not None:
            _set_title_field(tb, "title", TITLE)
            _set_title_field(tb, "rev", REVISION)
            _set_title_field(tb, "date", today)
        kio.save(doc)
        print("  {}: {} instances renamed".format(f.name, n))


# Top-level board items the fresh board drops (everything but setup, layers, paper, title block and
# the like); nets are reduced to net 0.
BOARD_DROP = {"footprint", "segment", "arc", "via", "zone", "dimension", "target", "group", "property",
              "gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly", "gr_curve", "gr_text", "gr_text_box",
              "gr_bbox"}


def _val(n):
    """An atom's value as kiutils read it (numbers int/float), or None."""
    return kio.to_lists(n) if n is not None else None


def _stackup_layers(board):
    setup = child(board, "setup")
    st = child(setup, "stackup") if setup is not None else None
    return kids(st, "layer") if st is not None else None


def fresh_board(commit: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "v7.kicad_pcb"
        src.write_bytes(git("show", "{}:{}/{}.kicad_pcb".format(commit, V7_DIR, OLD)))
        doc = kio.load_board(src)
    board = doc.tree
    drop = [c for c in board.children if c.name in BOARD_DROP]
    drop += [c for c in kids(board, "net") if atom(c, 0) != 0]
    kio.remove_items(board, drop)
    if not kids(board, "net"):
        kio.insert_item(board, node('(net 0 "")'))
    tb = child(board, "title_block")
    if tb is not None:
        _set_title_field(tb, "title", TITLE)
        _set_title_field(tb, "rev", REVISION)
    out = DEST / "{}.kicad_pcb".format(NEW)
    kio.save(doc, out)
    st = _stackup_layers(board)
    general = child(board, "general")
    th = child(general, "thickness") if general is not None else None
    print("  board: {} layers, stackup {} entries, thickness {}".format(
        len([c for c in child(board, "layers").children if not c.is_atom]), len(st) if st else 0,
        _val(kio.atoms(th)[0]) if th is not None else None))


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([KICAD_CLI] + list(args), capture_output=True, text=True)


def load_netlist(path: Path):
    root = ET.parse(str(path)).getroot()
    comps = {}
    for c in root.find("components"):
        fields = {x.get("name"): (x.text or "") for x in (c.find("fields") if c.find("fields") is not None else [])}
        comps[c.get("ref")] = (c.findtext("value"), c.findtext("footprint"),
                               tuple(sorted(fields.items())))
    nets = {}
    for n in root.find("nets"):
        nets[n.get("name")] = frozenset(
            "{}.{}".format(x.get("ref"), x.get("pin")) for x in n.findall("node"))
    return comps, nets


def erc_summary(path: Path):
    data = json.loads(path.read_text())
    counts = {}
    for sheet in data["sheets"]:
        for v in sheet["violations"]:
            key = (v["severity"], v["type"])
            counts[key] = counts.get(key, 0) + 1
    return counts


def verify(commit: str, compare_v7: bool) -> int:
    root = DEST / "{}.kicad_sch".format(NEW)
    pcb = DEST / "{}.kicad_pcb".format(NEW)
    fails = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = run_cli("sch", "erc", "--format", "json", "-o", str(td / "erc.json"), str(root))
        if r.returncode != 0 or not (td / "erc.json").exists():
            print("ERC failed to run:\n" + r.stdout + r.stderr)
            return 1
        counts = erc_summary(td / "erc.json")
        errors = sum(n for (sev, _), n in counts.items() if sev == "error")
        print("ERC: {} violations ({} errors)".format(sum(counts.values()), errors))
        for (sev, typ), n in sorted(counts.items()):
            print("  {:8s} {:28s} {}".format(sev, typ, n))

        r = run_cli("sch", "export", "netlist", "--format", "kicadxml", "-o",
                    str(td / "v8.xml"), str(root))
        if r.returncode != 0:
            print("netlist export failed:\n" + r.stdout + r.stderr)
            return 1
        if compare_v7:
            v7 = td / "v7"
            v7.mkdir()
            for f in [OLD + ".kicad_sch", OLD + ".kicad_pro", "sym-lib-table", "fp-lib-table"] + SHEETS:
                copy_from_git(commit, "{}/{}".format(V7_DIR, f), v7 / f)
            for f in git_files(commit, V7_DIR + "/libraries"):
                copy_from_git(commit, f, v7 / f[len(V7_DIR) + 1:])
            # v7's lib tables point at ../resources: point them at the repo copy.
            for name in ("sym-lib-table", "fp-lib-table"):
                p = v7 / name
                p.write_text(p.read_text().replace(
                    "${KIPRJMOD}/../resources/", str(REPO / "hardware/pcb-main/resources") + "/"))
            r = run_cli("sch", "export", "netlist", "--format", "kicadxml", "-o",
                        str(td / "v7.xml"), str(v7 / (OLD + ".kicad_sch")))
            if r.returncode != 0:
                print("v7 netlist export failed:\n" + r.stdout + r.stderr)
                return 1
            c7, n7 = load_netlist(td / "v7.xml")
            c8, n8 = load_netlist(td / "v8.xml")
            comp_diff = [k for k in set(c7) | set(c8) if c7.get(k) != c8.get(k)]
            m7 = {v: k for k, v in n7.items()}
            m8 = {v: k for k, v in n8.items()}
            net_diff = [(k, m8.get(v)) for v, k in m7.items() if m8.get(v) != k]
            net_diff += [(None, k) for v, k in m8.items() if v not in m7]
            print("netlist vs v7 @ {}: {} components, {} nets; {} component diffs, {} net diffs".format(
                commit, len(c8), len(n8), len(comp_diff), len(net_diff)))
            for d in sorted(comp_diff)[:20]:
                print("  comp", d)
            for d in net_diff[:20]:
                print("  net", d)
            fails += bool(comp_diff or net_diff)

        r = run_cli("pcb", "drc", "--format", "json", "-o", str(td / "drc.json"), str(pcb))
        if r.returncode != 0 or not (td / "drc.json").exists():
            print("DRC on the empty board failed to run:\n" + r.stdout + r.stderr)
            return 1
        drc = json.loads((td / "drc.json").read_text())
        print("empty board opens: DRC ran, {} violations, {} unconnected, {} footprint errors".format(
            len(drc.get("violations", [])), len(drc.get("unconnected_items", [])),
            len(drc.get("schematic_parity", []))))
        for v in drc.get("violations", [])[:5]:
            print("  ", v.get("type"), "-", v.get("description"))
    board = kio.load_board(pcb).tree
    layers = []
    for l in _stackup_layers(board) or []:
        typ, th = child(l, "type"), child(l, "thickness")
        if typ is not None and atom(typ, 0) in ("copper", "core", "prepreg"):
            layers.append("{}({})".format(atom(l, 0), _val(kio.atoms(th)[0]) if th is not None else None))
    print("board stackup: " + ", ".join(layers))
    print("board items: footprints {}, tracks {}, zones {}, graphics {}, nets {}".format(
        len(kids(board, "footprint")), sum(len(kids(board, k)) for k in ("segment", "arc", "via")),
        len(kids(board, "zone")), sum(len(kids(board, k)) for k in sorted(BOARD_DROP) if k.startswith("gr_")),
        len(kids(board, "net"))))
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", default="c2acffc", help="v7 source commit (default c2acffc)")
    ap.add_argument("--apply", action="store_true", help="create the v8 project")
    ap.add_argument("--verify", action="store_true", help="run the checks on the v8 project")
    ap.add_argument("--no-v7-compare", action="store_true",
                    help="skip the netlist comparison with v7 (use once the v8 schematic is edited)")
    ap.add_argument("--root", type=Path, help="root .kicad_sch of another copy of the v8 project "
                    "(a scratch copy); with --apply, the file to create, outside this repository")
    args = ap.parse_args()
    if args.root is not None:
        global DEST
        root = args.root.resolve()
        if root.name != "{}.kicad_sch".format(NEW):
            ap.error("--root must name {}.kicad_sch".format(NEW))
        if args.apply:
            if inside_repo(root):
                ap.error("--root with --apply must be a scratch copy outside the repository")
        elif not root.is_file():
            ap.error("--root must be an existing {}.kicad_sch".format(NEW))
        DEST = root.parent

    if args.apply:
        if DEST.exists() and any(DEST.iterdir()):
            print("Refusing: {} is not empty".format(DEST))
            return 1
        print("Copying v7 project @ {} -> {}".format(
            args.commit, DEST.relative_to(REPO) if inside_repo(DEST) else DEST))
        copy_project(args.commit)
        print("Renaming project instances and title blocks")
        rename_instances()
        print("Writing the empty board")
        fresh_board(args.commit)
    if args.apply or args.verify:
        return verify(args.commit, compare_v7=not args.no_v7_compare)
    print("Nothing to do: pass --apply or --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
