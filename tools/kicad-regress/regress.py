#!/usr/bin/env python3
"""
regress.py - regression harness for the KiCad tools (kicad10-tooling, PLAN "Regression harness").

Runs a fixed set of tool commands on fresh `git archive` copies of v8 and v7 and hashes or compares
the outputs. It is how a tool change (the kiutils -> kicad-tools port, a dependency upgrade, a new
KiCad) is shown to change nothing: run the same set with the old and the new tools and compare.

Every run works only on scratch copies under the run root; it never touches the working tree's
hardware/ (kicad-cli 10 writes a .kicad_prl even on read-only commands: .context/HAZARDS.md).

Subcommands
  run RUNROOT [--python PY] [--kicad-cli CLI] [--tools REF] [--v8-ref REF] [--v7-ref REF]
      Fresh copies: RUNROOT/v8src = v8 project at --v8-ref (default v8-schematic-freeze), RUNROOT/v7src
      = v7 at --v7-ref (default c2acffc), each with hardware/pcb-main/resources beside it (the lib
      tables point there). Then the reference set (REFSET below) with PY (default tools/.venv/bin/python)
      and KICAD_CLI=CLI (default 9.0.4). --tools REF runs the tools from a temporary git worktree at REF
      (for example the oracle tag kicad10-preport); without it they run from this working tree.
      Writes RUNROOT/run.json (settings, exit codes) and RUNROOT/HASHES.txt.
      RUNROOT's last path component must be 6 characters long, and two runs are comparable only if
      their run roots have the same full length: extract.py prints the netlist's byte count, and the
      netlist carries the source path. Pick roots like <dir>/run-a1, <dir>/run-b1.
  hash RUNROOT [--against FILE]
      Recompute RUNROOT/HASHES.txt; with --against, diff it with a reference list (only the entries
      the reference has). reference-k9.txt here is the KiCad 9.0.4 / kiutils reference.
  compare RUNA RUNB [--tol 1e-9]
      Every output file of RUNA against RUNB: identical after replacing each run root, else JSON leaf by
      leaf (numbers within --tol, _provenance ignored), netlists structurally, Markdown without front
      matter. Also the exit codes. Exit 1 if anything differs.
  netlist A.net B.net [--strip-a] [--strip-b]   structural netlist compare (--strip-*: drop kicad-cli
                                                10's '_<pin>' pinfunction suffix on that side)
  erc REPORT.json PROJECT_DIR                   ERC/DRC counts, library items split setup/real
  plot SCH OUTDIR [--kicad-cli CLI]             kicad-cli SVG plot of a scratch schematic
  svg DIR_A DIR_B                               plotted strings per sheet
  tokens A [B]                                  token census of A, or the kinds whose count differs
  treeeq A B                                    exact tree equality (whitespace ignored)

Hashes: sha256 (first 16 hex) after normalizing: netlists drop the source/date/tool lines; JSON drops
the top-level _provenance; Markdown drops its front matter; the run root becomes <ROOT>. The check
outputs that Phase 1 recorded on the working tree (WT_OUTPUTS) also have the scratch prefix
<ROOT>/v8src/ removed, so their paths read repo-relative as they did there.

Python: stdlib only (runs on the global python3 or tools/.venv); the tools run on --python.
"""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kcompare  # noqa: E402

REPO = HERE.parents[1]
K9_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
DEFAULT_PY = REPO / "tools/.venv/bin/python"
V8_SCH = "v8src/hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch"
V7_PCB = "v7src/hardware/pcb-main/kicad/motion-play-main.kicad_pcb"
V8_SHEETS = ["motion-play-main-v8.kicad_sch", "esp32_s3.kicad_sch", "led_controller.kicad_sch",
             "power_management.kicad_sch", "tca9548A_subsystem.kicad_sch"]
ROOT_NAME_LEN = 6

# (output, kind, argv). kind: "cli" runs kicad-cli, "py" runs a tool script with --python,
# "erc" counts an ERC report in-process. {V8}/{V7}/{R} are the v8 root sheet, the v7 board and
# the run root. stdout+stderr of "py" commands is the output file.
REFSET = [
    ("v8/netlist.net", "cli", ["sch", "export", "netlist", "-o", "{R}/v8/netlist.net", "{V8}"]),
    ("v8/netlist.xml", "cli", ["sch", "export", "netlist", "--format", "kicadxml", "-o", "{R}/v8/netlist.xml", "{V8}"]),
    ("v8/erc.json", "cli", ["sch", "erc", "--format", "json", "--severity-all", "-o", "{R}/v8/erc.json", "{V8}"]),
    ("v8/erc_counts.txt", "erc", ["{R}/v8/erc.json"]),
    ("v8/extract_sheetpins.txt", "py", ["tools/schematic-context/extract.py", "{V8}", "--check-sheet-pins"]),
    ("v8/layout_check.txt", "py", ["tools/schematic-modify/layout_check.py", "--root", "{V8}"]),
    ("v8/tidy_fields.txt", "py", ["tools/schematic-modify/tidy_fields.py", "--check", "--root", "{V8}"]),
    ("v8/tidy_labels.txt", "py", ["tools/schematic-modify/tidy_labels.py", "--check", "--root", "{V8}"]),
    ("v8/v8_debug_sheet_check.txt", "py", ["tools/schematic-modify/v8_debug_sheet.py", "--check", "--root", "{V8}"]),
    ("checks/v8_mcu_sheet.txt", "py", ["tools/schematic-modify/v8_mcu_sheet.py", "--check", "--root", "{V8}"]),
    ("checks/v8_bus_sheet.txt", "py", ["tools/schematic-modify/v8_bus_sheet.py", "--check", "--root", "{V8}"]),
    ("checks/v8_power_sheet.txt", "py", ["tools/schematic-modify/v8_power_sheet.py", "--check", "--root", "{V8}"]),
    ("checks/v8_project_setup_verify.txt", "py",
     ["tools/schematic-modify/v8_project_setup.py", "--verify", "--no-v7-compare", "--root", "{V8}"]),
    ("v7/board_model.txt", "py", ["tools/pcb-context/board_model.py", "{V7}", "-o", "{R}/v7/board-model.json",
                                  "--source-ref", "{V7REF}"]),
    ("v7/net_report.txt", "py", ["tools/pcb-context/net_report.py", "{R}/v7/board-model.json"]),
    ("v7/plane_report.txt", "py", ["tools/pcb-context/plane_report.py", "{R}/v7/board-model.json"]),
    ("v7/pads_U5_C21_C9.txt", "py", ["tools/lab/probe_points/probe_points.py", "pads", "--board", "{V7}",
                                     "U5", "C21", "C9"]),
]
# Hashed outputs (besides the source files). Console logs of the board tools are left out: they
# carry paths and timings; their JSON/Markdown outputs are hashed instead.
HASHED = ["v8/netlist.net", "v8/netlist.xml", "v8/erc_counts.txt", "v8/extract_sheetpins.txt",
          "v8/layout_check.txt", "v8/tidy_fields.txt", "v8/tidy_labels.txt", "v8/v8_debug_sheet_check.txt",
          "checks/v8_mcu_sheet.txt", "checks/v8_bus_sheet.txt", "checks/v8_power_sheet.txt",
          "checks/v8_project_setup_verify.txt",
          "v7/board-model.json", "v7/net-report.json", "v7/net-report.md", "v7/plane-report.json",
          "v7/plane-report.md", "v7/pads_U5_C21_C9.txt",
          "v7src/hardware/pcb-main/kicad/motion-play-main.kicad_pcb"] + \
         ["v8src/hardware/pcb-main-v8/kicad/" + s for s in sorted(V8_SHEETS)]
# Outputs Phase 1 recorded on the working tree: on a scratch root, strip the scratch prefix.
WT_OUTPUTS = {"v8/layout_check.txt", "v8/v8_debug_sheet_check.txt", "checks/v8_mcu_sheet.txt",
              "checks/v8_bus_sheet.txt", "checks/v8_power_sheet.txt", "checks/v8_project_setup_verify.txt"}
SKIP_COMPARE = ("v8src/", "v7src/", "wt/")


def die(msg):
    print("regress.py: " + msg, file=sys.stderr)
    sys.exit(2)


def inside_repo(p):
    try:
        Path(p).resolve().relative_to(REPO)
        return True
    except ValueError:
        return False


def cli_version(cli):
    r = subprocess.run([cli, "version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def normalized(path, root, rel):
    t = Path(path).read_text(encoding="utf-8")
    suffix = Path(path).suffix
    if suffix in (".net", ".xml"):
        t = "\n".join(l for l in t.splitlines() if not re.match(r"\s*(\((source|date|tool) |<(source|date|tool)>)", l))
    elif suffix == ".json":
        d = json.loads(t)
        if isinstance(d, dict):
            d.pop("_provenance", None)
        t = json.dumps(d, sort_keys=True)
    elif suffix == ".md" and t.startswith("---"):
        t = t.split("\n---", 1)[1] if "\n---" in t[3:] else t
    if rel in WT_OUTPUTS:
        t = t.replace(root + "/v8src/", "")
    return t.replace(root, "<ROOT>")


def hash_run(run_root):
    root = str(Path(run_root).resolve())
    lines = []
    for rel in HASHED:
        p = Path(root) / rel
        if p.exists():
            h = hashlib.sha256(normalized(p, root, rel).encode("utf-8")).hexdigest()[:16]
            lines.append("{}  {}".format(h, rel))
        else:
            lines.append("{}  {}".format("MISSING".ljust(16), rel))
    (Path(root) / "HASHES.txt").write_text("\n".join(lines) + "\n")
    return lines


def read_hashes(path):
    out = {}
    for l in Path(path).read_text().splitlines():
        if l.strip() and not l.startswith("#"):
            h, rel = l.split(None, 1)
            out[rel.strip()] = h
    return out


def against(run_root, ref_file):
    got = read_hashes(Path(run_root) / "HASHES.txt")
    ref = read_hashes(ref_file)
    bad = 0
    for rel, h in ref.items():
        ok = got.get(rel) == h
        bad += not ok
        print("  {} {}  {}{}".format("ok " if ok else "BAD", h, rel, "" if ok else "  (run: {})".format(got.get(rel))))
    print("{} of {} reference hashes match ({})".format(len(ref) - bad, len(ref), ref_file))
    return bad


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def git(*args, **kw):
    return subprocess.run(["git", "-C", str(REPO)] + list(args), check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kw).stdout


def archive(ref, paths, dest):
    dest.mkdir(parents=True)
    data = git("archive", ref, *paths)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=data, check=True)


def tools_worktree(ref, wt):
    """A detached worktree at `ref` with only tools/ and hardware/pcb-main/resources checked out."""
    git("worktree", "add", "--no-checkout", "--detach", str(wt), ref)
    subprocess.run(["git", "-C", str(wt), "checkout", ref, "--", "tools", "hardware/pcb-main/resources"],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return wt


def cmd_run(a):
    root = Path(a.run_root).resolve()
    if len(root.name) != ROOT_NAME_LEN:
        die("run root name must be {} characters (got '{}'): see 'run' in the docstring".format(ROOT_NAME_LEN, root.name))
    if inside_repo(root):
        die("run root must be outside the repository")
    if root.exists() and any(root.iterdir()):
        die("run root exists and is not empty: {}".format(root))
    py = Path(a.python) if a.python else DEFAULT_PY
    if not py.exists():
        die("python not found: {} (build tools/.venv: tools/requirements.txt)".format(py))
    cli = a.kicad_cli or K9_CLI
    root.mkdir(parents=True, exist_ok=True)
    for d in ("v8", "v7", "checks"):
        (root / d).mkdir()
    archive(a.v8_ref, ["hardware/pcb-main-v8/kicad", "hardware/pcb-main/resources"], root / "v8src")
    archive(a.v7_ref, ["hardware/pcb-main/kicad", "hardware/pcb-main/resources"], root / "v7src")
    tools = tools_worktree(a.tools, root / "wt") if a.tools else REPO
    tools_commit = subprocess.run(["git", "-C", str(tools), "rev-parse", "HEAD"], stdout=subprocess.PIPE,
                                  universal_newlines=True).stdout.strip()
    dirty = "" if a.tools else subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "tools"],
                                              stdout=subprocess.PIPE, universal_newlines=True).stdout
    env = dict(os.environ, KICAD_CLI=cli)
    subst = {"{R}": str(root), "{V8}": str(root / V8_SCH), "{V7}": str(root / V7_PCB), "{V7REF}": a.v7_ref}
    meta = {"run_root": str(root), "run_root_len": len(str(root)), "python": str(py),
            "python_version": subprocess.run([str(py), "-c", "import sys; print(sys.version.split()[0])"],
                                             stdout=subprocess.PIPE, universal_newlines=True).stdout.strip(),
            "kicad_cli": cli, "kicad_cli_version": cli_version(cli), "tools": a.tools or "working tree",
            "tools_commit": tools_commit, "tools_dirty": bool(dirty.strip()), "v8_ref": a.v8_ref,
            "v7_ref": a.v7_ref, "exit": {}}
    try:
        for out, kind, argv in REFSET:
            argv = [subst.get(x, x) for x in argv]
            argv = [x.replace("{R}", str(root)) for x in argv]
            for x in argv:
                if x.startswith("/") and inside_repo(x) and not x.startswith(str(tools)):
                    die("refusing to pass a working-tree path to a tool: " + x)
            if kind == "cli":
                r = subprocess.run([cli] + argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
                code = r.returncode
            elif kind == "erc":
                lines = kcompare.erc_counts(json.loads(Path(argv[0]).read_text()))
                (root / out).write_text("\n".join(lines) + "\n")
                code = 0
            else:
                with open(str(root / out), "w") as f:
                    code = subprocess.run([str(py)] + argv, stdout=f, stderr=subprocess.STDOUT, cwd=str(tools),
                                          env=env).returncode
            meta["exit"][out] = code
            print("  {:3d}  {}".format(code, out))
    finally:
        if a.tools and not a.keep_worktree:
            git("worktree", "remove", "--force", str(root / "wt"))
        (root / "run.json").write_text(json.dumps(meta, indent=2) + "\n")
    hash_run(root)
    print("run root {} ({} chars); tools {} @ {}{}; python {}; kicad-cli {}".format(
        root, len(str(root)), meta["tools"], tools_commit[:9], " (dirty)" if meta["tools_dirty"] else "",
        meta["python_version"], meta["kicad_cli_version"]))
    bad = [k for k, v in meta["exit"].items() if v != 0]
    print("non-zero exits: {}".format(", ".join(bad) if bad else "none"))
    if a.against:
        return 1 if against(root, a.against) else 0
    return 0


def cmd_hash(a):
    for l in hash_run(a.run_root):
        print(l)
    if a.against:
        return 1 if against(a.run_root, a.against) else 0
    return 0


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------

def cmd_compare(a):
    A, B = Path(a.run_a).resolve(), Path(a.run_b).resolve()
    ma, mb = (json.loads((p / "run.json").read_text()) for p in (A, B))
    differ = 0
    if len(str(A)) != len(str(B)):
        print("WARNING: run roots differ in length ({} vs {}): extract.py's byte count will differ".format(
            len(str(A)), len(str(B))))
    for k in ("python_version", "kicad_cli_version", "tools", "tools_commit", "v8_ref", "v7_ref"):
        if ma.get(k) != mb.get(k):
            print("setting  {}: {} | {}".format(k, ma.get(k), mb.get(k)))
    for k in sorted(set(ma["exit"]) | set(mb["exit"])):
        if ma["exit"].get(k) != mb["exit"].get(k):
            differ += 1
            print("EXIT DIFF  {}: {} vs {}".format(k, ma["exit"].get(k), mb["exit"].get(k)))
    for fa in sorted(A.rglob("*")):
        rel = fa.relative_to(A).as_posix()
        if fa.is_dir() or rel.startswith(SKIP_COMPARE) or rel in ("run.json", "HASHES.txt"):
            continue
        fb = B / rel
        if not fb.exists():
            differ += 1
            print("MISSING    {} (only in A)".format(rel))
            continue
        ta = fa.read_text(encoding="utf-8").replace(str(A), "<ROOT>")
        tb = fb.read_text(encoding="utf-8").replace(str(B), "<ROOT>")
        if ta == tb:
            print("IDENTICAL  {}".format(rel))
            continue
        na, nb = normalized(fa, str(A), rel), normalized(fb, str(B), rel)
        if fa.suffix == ".json":
            out = kcompare.json_diff(json.loads(ta), json.loads(tb), a.tol)
            if not out:
                print("EQUAL      {} (JSON leaves within {}; _provenance ignored)".format(rel, a.tol))
                continue
            differ += 1
            print("JSON DIFF  {}: {} leaves".format(rel, len(out)))
            for p, d in out[:12]:
                print("     {} {}".format(p, d))
            continue
        if na == nb:
            print("EQUAL      {} (after normalizing header lines / front matter)".format(rel))
            continue
        if fa.suffix == ".net":
            lines, eq = kcompare.netlist_diff(str(fa), str(fb))
            print("{}  {} (structural)".format("EQUAL     " if eq else "NET DIFF  ", rel))
            for l in lines:
                print("     " + l)
            differ += not eq
            continue
        differ += 1
        import difflib
        dl = [l for l in difflib.unified_diff(na.splitlines(), nb.splitlines(), lineterm="", n=0)
              if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        print("TEXT DIFF  {}: {} lines".format(rel, len(dl)))
        for l in dl[:8]:
            print("     " + l[:200])
    for p in sorted(B.rglob("*")):
        rel = p.relative_to(B).as_posix()
        if p.is_file() and not rel.startswith(SKIP_COMPARE) and not (A / rel).exists():
            differ += 1
            print("MISSING    {} (only in B)".format(rel))
    print("COMPARE {}".format("SAME" if not differ else "DIFFERENT ({} items)".format(differ)))
    return 1 if differ else 0


# ---------------------------------------------------------------------------
# small subcommands
# ---------------------------------------------------------------------------

def cmd_netlist(a):
    lines, eq = kcompare.netlist_diff(a.a, a.b, a.strip_a, a.strip_b)
    print("\n".join(lines))
    print("NETLISTS " + ("EQUAL" if eq else "DIFFER"))
    return 0 if eq else 1


def cmd_erc(a):
    print("\n".join(kcompare.erc_split(json.loads(Path(a.report).read_text()), a.project_dir)))
    return 0


def cmd_plot(a):
    if inside_repo(a.sch) or inside_repo(a.outdir):
        die("plot works on scratch copies only")
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    r = subprocess.run([a.kicad_cli or K9_CLI, "sch", "export", "svg", "-o", a.outdir, a.sch],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    print(r.stdout.strip())
    return r.returncode


def cmd_svg(a):
    lines, eq = kcompare.svg_strings(a.dir_a, a.dir_b)
    print("\n".join(lines))
    print("PLOTTED STRINGS " + ("EQUAL" if eq else "DIFFER"))
    return 0 if eq else 1


def cmd_tokens(a):
    if a.b:
        lines = kcompare.census_diff(a.a, a.b)
        print("\n".join(lines) if lines else "CENSUS EQUAL")
        return 1 if lines else 0
    for k, v in sorted(kcompare.census(a.a).items()):
        print(v, k)
    return 0


def cmd_treeeq(a):
    eq, d = kcompare.tree_equal(a.a, a.b)
    print("EQUAL" if eq else "DIFFERENT {}".format(d))
    return 0 if eq else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run")
    p.add_argument("run_root")
    p.add_argument("--python")
    p.add_argument("--kicad-cli")
    p.add_argument("--tools", metavar="REF", help="run the tools from a worktree at REF (default: working tree)")
    p.add_argument("--keep-worktree", action="store_true")
    p.add_argument("--v8-ref", default="v8-schematic-freeze")
    p.add_argument("--v7-ref", default="c2acffc")
    p.add_argument("--against", help="reference hash list to check the run against")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("hash")
    p.add_argument("run_root")
    p.add_argument("--against")
    p.set_defaults(fn=cmd_hash)
    p = sub.add_parser("compare")
    p.add_argument("run_a")
    p.add_argument("run_b")
    p.add_argument("--tol", type=float, default=1e-9)
    p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("netlist")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--strip-a", action="store_true")
    p.add_argument("--strip-b", action="store_true")
    p.set_defaults(fn=cmd_netlist)
    p = sub.add_parser("erc")
    p.add_argument("report")
    p.add_argument("project_dir")
    p.set_defaults(fn=cmd_erc)
    p = sub.add_parser("plot")
    p.add_argument("sch")
    p.add_argument("outdir")
    p.add_argument("--kicad-cli")
    p.set_defaults(fn=cmd_plot)
    p = sub.add_parser("svg")
    p.add_argument("dir_a")
    p.add_argument("dir_b")
    p.set_defaults(fn=cmd_svg)
    p = sub.add_parser("tokens")
    p.add_argument("a")
    p.add_argument("b", nargs="?")
    p.set_defaults(fn=cmd_tokens)
    p = sub.add_parser("treeeq")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(fn=cmd_treeeq)
    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
