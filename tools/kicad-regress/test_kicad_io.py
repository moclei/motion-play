"""test_kicad_io.py - the I/O module's committed test (kicad10-tooling Phase 6a). Runs in tools/.venv.

usage: test_kicad_io.py OUTDIR [--kicad-cli9 CLI] [--kicad-cli10 CLI | --no-k10]
Normally run through `regress.py iotest OUTDIR`, which first puts fresh `git archive` copies under
OUTDIR/src: 0 = v8 (hardware/pcb-main-v8/kicad at v8-schematic-freeze), 1 = v7 (hardware/pcb-main/kicad
at c2acffc), 2 = the power-supply, sensor-rigid and sensor-flex projects and the project symbol
libraries at HEAD; each with hardware/pcb-main/resources. Everything else is written under OUTDIR,
never under the repository (kicad-cli 10 writes a .kicad_prl even when it only reads).

Stages (each check prints PASS or FAIL; exit 1 if any FAIL):
  1 round trip   every .kicad_sch / .kicad_pcb in src (the `regress.py roundtrip` set) and every
                 .kicad_sym in src plus the KiCad 9.0.4 and 10.0.8 stock symbol libraries: load + save
                 through kicad_io is byte-identical to the input (so tree-identical, version kept);
                 the one allowed byte difference is the final newline save adds when an input has none
                 (the easyeda2kicad libraries), and each such file is listed.
                 kicad-cli 9 then reads each saved project: netlist of every root sheet, DRC of v7's
                 board, counts equal to the unsaved input's.
  2 edits, KiCad 9   one Value edit on a KiCad-format sheet (v8 TCA, R92), one on the kiutils-format
                 LED sheet (R105) and one footprint move on v7's board (EDIT_FP): the splice save is
                 tree-identical to a plain kicad-tools save of the same edit, and every changed line
                 of the git diff is inside the edited item (line counts printed). kicad-cli 9 reads
                 the result: netlist/DRC counts equal to the unedited input's.
  3 edits, KiCad 10  the same on copies converted by kicad-cli 10 (`sch/pcb upgrade`); kicad-cli 10
                 reads the result (netlist/DRC counts equal to the unedited converted copy's).
  4 refusals     lock guard (~*.kicad_sch.lck, ~*.kicad_pcb.lck, save and save_project), format check
                 (made-up newer version), pin check (different version), save of a tree whose version
                 token was changed; a refused save writes nothing.
  4b embed check  a library symbol loaded from a newer KiCad's library is refused in an older sheet
                 (KiCad 10 stock into a KiCad 9 sheet: check_embed, save and save_project refuse, the
                 file is byte-unchanged, the message names the symbol and both formats; the same tree
                 written past the guard loses components in kicad-cli 9). KiCad 9 stock into 9 and 10,
                 KiCad 10 stock into 10, and a project-library symbol (20211014) into 9 and 10 save,
                 and kicad-cli of the sheet's version reads each with the input's netlist counts.
  5 atoms, hide  set_num keeps every digit of a float; hide and make_property write KiCad 9's form on
                 a 9 file and KiCad 10's on a 10 file; hiding an already-hidden property (each of the
                 three forms) changes nothing.
  6 cli 9 reads  kicad-cli 9 netlists the v8 copies stages 4 and 5 saved; counts equal to the input's.
"""
import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "kicad-io"))
import kcompare  # noqa: E402
import kicad_io as kio  # noqa: E402
from kicad_tools.core import sexp_file as kt  # noqa: E402  (the plain save the splice save is checked against)
from kicad_tools.sexp import SExp  # noqa: E402

K9_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
K10_CLI = "/Applications/KiCad10/KiCad.app/Contents/MacOS/kicad-cli"
V8 = "0/hardware/pcb-main-v8/kicad"
V7 = "1/hardware/pcb-main/kicad"
EDIT_VALUE = "IO-EDIT"
EDIT_FP, EDIT_DX = "TPIO44", "0.5"   # a move that changes no DRC count on v7 (C9 adds 8)
EDITS = [  # (label, project dir under a src root, file, reference)
    ("TCA sheet, KiCad format", V8, "tca9548A_subsystem.kicad_sch", "R92"),
    ("LED sheet, kiutils format", V8, "led_controller.kicad_sch", "R105"),
    ("v7 board, footprint move", V7, "motion-play-main.kicad_pcb", EDIT_FP),
]

RESULTS = collections.Counter()


def check(ok, what, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print("{} {}{}".format("PASS" if ok else "FAIL", what, "  " + detail if detail else ""))
    sys.stdout.flush()
    return ok


def info(msg):
    print("     " + msg)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# kicad-cli
# ---------------------------------------------------------------------------

def run(argv):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)


def netlist(cli, sch, out):
    r = run([cli, "sch", "export", "netlist", "-o", str(out), str(sch)])
    if r.returncode or not Path(out).exists():
        return None
    comps, nets, _, _ = kcompare.read_netlist(str(out))
    return comps, nets


def drc_counts(cli, pcb, out):
    r = run([cli, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "-o", str(out), str(pcb)])
    if not Path(out).exists():
        return None
    rep = json.loads(Path(out).read_text())
    c = collections.Counter((v.get("severity"), v.get("type")) for v in rep.get("violations", []))
    c[("-", "unconnected_items")] = len(rep.get("unconnected_items", []))
    c[("-", "schematic_parity")] = len(rep.get("schematic_parity", []))
    return dict(sorted(("{} {}".format(*k), v) for k, v in c.items()))


def roots(folder):
    """Root sheets: <stem>.kicad_sch beside each <stem>.kicad_pro."""
    return sorted(p.with_suffix(".kicad_sch") for p in Path(folder).rglob("*.kicad_pro")
                  if p.with_suffix(".kicad_sch").exists())


def same_counts(label, a, b):
    """a, b: (components, nets) of two netlists; the counts must be equal."""
    if a is None or b is None:
        return check(False, label, "kicad-cli did not write a netlist")
    ca, cb = (len(a[0]), len(a[1])), (len(b[0]), len(b[1]))
    return check(ca == cb, label, "components/nets input {} saved {}".format(ca, cb))


# ---------------------------------------------------------------------------
# Finding things in a raw tree
# ---------------------------------------------------------------------------

def prop(n, key):
    return next((p for p in kio.kids(n, "property") if kio.atom(p, 0) == key), None)


def find_ref(doc, ref):
    """The top-level symbol (schematic) or footprint (board) whose Reference is ref."""
    tag = "footprint" if doc.kind == kio.PCB else "symbol"
    for c in kio.kids(doc.tree, tag):
        p = prop(c, "Reference")
        if p is not None and kio.atom(p, 1) == ref:
            return c
    raise KeyError("{} not found in {}".format(ref, doc.path))


def edit(doc, ref):
    """The test's one edit: a Value on a sheet, a +EDIT_DX mm move in x on a board."""
    n = find_ref(doc, ref)
    if doc.kind == kio.PCB:
        at = kio.child(n, "at")
        x = kio.atom_text(at, 0)
        kio.set_num(at, 0, "{:.6f}".format(float(x) + float(EDIT_DX)).rstrip("0").rstrip("."))
    else:
        kio.set_str(prop(n, "Value"), 1, EDIT_VALUE)
    return doc.tree.children.index(n)


def hide_flags(p):
    """Every hide flag on a property: property level, in effects; (hide x) and bare hide."""
    out = []
    for where, holder in (("property", p), ("effects", kio.child(p, "effects"))):
        if holder is None:
            continue
        for c in holder.children:
            if c.name == "hide":
                out.append("{}:(hide {})".format(where, kio.atom(c)))
            elif c.is_atom and c.value == "hide":
                out.append("{}:bare".format(where))
    return out


# ---------------------------------------------------------------------------
# Diffs
# ---------------------------------------------------------------------------

def line_range(text, span):
    """1-based first and last line of span (start, end) in text."""
    return text.count("\n", 0, span[0]) + 1, text.count("\n", 0, span[1]) + 1


def git_diff(a, b):
    """(added, removed, [(old_start, old_len, new_start, new_len)]) of git diff --no-index -U0 a b."""
    r = run(["git", "diff", "--no-index", "-U0", "--no-color", str(a), str(b)])
    hunks = [tuple(int(x) if x else 1 for x in m) for m in
             re.findall(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", r.stdout, re.M)]
    lines = r.stdout.splitlines()
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    return added, removed, hunks


def confined(hunks, old_rng, new_rng):
    """Every hunk's old lines are inside old_rng and its new lines inside new_rng (a pure insertion
    or deletion may sit on the line just before the range)."""
    def inside(start, length, rng):
        if length == 0:
            return rng[0] - 1 <= start <= rng[1]
        return rng[0] <= start and start + length - 1 <= rng[1]
    return all(inside(o, ol, old_rng) and inside(n, nl, new_rng) for o, ol, n, nl in hunks)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

NO_FINAL_NEWLINE = []


def same_bytes(inp, saved):
    """Byte-identical, except that save adds the final newline an input may lack (PLAN "Save")."""
    a, b = Path(inp).read_bytes(), Path(saved).read_bytes()
    if a != b and not a.endswith(b"\n") and a + b"\n" == b:
        NO_FINAL_NEWLINE.append(str(inp))
        return True
    return a == b


def copytree(src, dst):
    if dst.exists():
        shutil.rmtree(str(dst))
    shutil.copytree(str(src), str(dst))
    return dst


def stage1(out, cli9, stock):
    print("== 1 round trip (load + save through kicad_io)")
    src, rt = out / "src", copytree(out / "src", out / "rt")
    files = sorted(p for p in rt.rglob("*") if p.suffix in (".kicad_sch", ".kicad_pcb"))
    syms = sorted(p for p in rt.rglob("*.kicad_sym"))
    versions = collections.Counter()
    sym_fail = 0
    for f in files + syms:
        rel = f.relative_to(rt)
        doc = kio.load(f)
        kio.save(doc)
        same = same_bytes(src / rel, f)
        eq, d = kcompare.tree_equal(str(src / rel), str(f))
        kept = kio.tree_version(kio.load(f).tree) == doc.version
        versions[(doc.kind, doc.version)] += 1
        detail = "byte-identical {}, tree-identical {}, version {} kept {}".format(same, eq, doc.version, kept)
        if f.suffix != ".kicad_sym":
            check(same and eq and kept, "round trip {}".format(rel), detail)
        elif not (same and eq and kept):
            sym_fail += 1
            info("symbol library {}: {}".format(rel, detail))
    check(syms and not sym_fail, "round trip of {} project symbol libraries".format(len(syms)),
          "{} failed".format(sym_fail))
    for label, d in stock:
        n, fails = 0, 0
        so = out / "rt-stock" / label
        so.mkdir(parents=True, exist_ok=True)
        for f in sorted(Path(d).glob("*.kicad_sym")):
            doc = kio.load_symbol_lib(f)
            kio.save(doc, so / f.name)
            n += 1
            versions[(doc.kind, doc.version)] += 1
            if not same_bytes(f, so / f.name):
                fails += 1
                info("not byte-identical: {}".format(f))
        check(n > 0 and not fails, "round trip of {} {} stock symbol libraries".format(n, label),
              "{} not byte-identical".format(fails))
    if NO_FINAL_NEWLINE:
        info("{} inputs had no final newline; the save added one and is otherwise byte-identical: {}".format(
            len(NO_FINAL_NEWLINE), ", ".join(sorted({Path(p).name for p in NO_FINAL_NEWLINE}))))
    info("format versions loaded: {}".format(", ".join("{} {} x{}".format(k[0], k[1], v)
                                                      for k, v in sorted(versions.items()))))
    print("== 1b kicad-cli 9 reads every saved KiCad 9 file (counts equal to the input's)")
    cl = out / "cli9-rt"
    cl.mkdir(exist_ok=True)
    for i, r in enumerate(roots(rt)):
        rel = r.relative_to(rt)
        a = netlist(cli9, src / rel, cl / "{}-in.net".format(i))
        b = netlist(cli9, r, cl / "{}-rt.net".format(i))
        if same_counts("kicad-cli 9 netlist {}".format(rel), a, b):
            check(a == b, "  netlists structurally identical {}".format(rel))
    a = drc_counts(cli9, src / V7 / "motion-play-main.kicad_pcb", cl / "v7-in-drc.json")
    b = drc_counts(cli9, rt / V7 / "motion-play-main.kicad_pcb", cl / "v7-rt-drc.json")
    check(a is not None and a == b, "kicad-cli 9 DRC v7 board", "input {} saved {}".format(a, b))


def edit_pair(base, work, label, proj, fname, ref):
    """Edit fname in two copies of base: the splice save (work/splice) and a plain kicad-tools save
    (work/plain). Returns (splice path, plain path, line counts)."""
    sp_root, pl_root = copytree(base, work / "splice"), copytree(base, work / "plain")
    src = base / proj / fname
    doc = kio.load(sp_root / proj / fname)
    idx = edit(doc, ref)
    old_rng = line_range(doc.text, doc.spans[idx])
    kio.save(doc)
    new_rng = line_range(doc.text, doc.spans[idx])
    pdoc = kio.load(pl_root / proj / fname)
    edit(pdoc, ref)
    (kt.save_pcb if pdoc.kind == kio.PCB else kt.save_schematic)(pdoc.tree, pl_root / proj / fname)
    sp, pl = sp_root / proj / fname, pl_root / proj / fname
    eq, d = kcompare.tree_equal(str(sp), str(pl))
    check(eq, "{}: splice save tree-identical to a plain kicad-tools save".format(label), "" if eq else str(d))
    added, removed, hunks = git_diff(src, sp)
    padded, premoved, _ = git_diff(src, pl)
    ok = confined(hunks, old_rng, new_rng) and hunks
    check(ok, "{}: diff only inside the edited item".format(label),
          "splice +{}/-{} in {} hunk(s), item lines {}-{} -> {}-{}; plain save +{}/-{}".format(
              added, removed, len(hunks), old_rng[0], old_rng[1], new_rng[0], new_rng[1], padded, premoved))
    check(kio.tree_version(kio.load(sp).tree) == doc.version, "{}: version {} kept".format(label, doc.version))
    return sp_root, sp


def stage_edits(out, base, cli, tag):
    work = out / "edits{}".format(tag)
    work.mkdir(exist_ok=True)
    for i, (label, proj, fname, ref) in enumerate(EDITS):
        label = "{} [KiCad {}]".format(label, tag)
        sp_root, sp = edit_pair(base, work / str(i), label, proj, fname, ref)
        cl = work / str(i) / "cli"
        cl.mkdir(exist_ok=True)
        if sp.suffix == ".kicad_sch":
            root = roots(sp_root / proj)[0]
            a = netlist(cli, base / root.relative_to(sp_root), cl / "in.net")
            b = netlist(cli, root, cl / "edited.net")
            if same_counts("{}: kicad-cli {} netlist".format(label, tag), a, b):
                changed = sorted(r for r in a[0] if a[0][r] != b[0].get(r))
                check(changed == [ref] and b[0][ref]["value"] == EDIT_VALUE and a[1] == b[1],
                      "{}: netlist changes only {}'s Value".format(label, ref), "changed {}".format(changed))
        else:
            a = drc_counts(cli, base / proj / fname, cl / "in-drc.json")
            b = drc_counts(cli, sp, cl / "edited-drc.json")
            check(a is not None and a == b, "{}: kicad-cli {} DRC counts".format(label, tag),
                  "input {} edited {}".format(a, b))


def convert10(out, cli10):
    """Copies of v8 and v7 converted by kicad-cli 10 (every sheet, the board), outside the repo."""
    base = out / "k10src"
    if base.exists():
        shutil.rmtree(str(base))
    for d in ("0", "1"):
        shutil.copytree(str(out / "src" / d), str(base / d))
    for f in sorted(base.rglob("*.kicad_sch")):
        r = run([cli10, "sch", "upgrade", str(f)])
        if r.returncode:
            check(False, "kicad-cli 10 sch upgrade {}".format(f.relative_to(base)), r.stdout.strip()[-200:])
    for f in sorted(base.rglob("*.kicad_pcb")):
        r = run([cli10, "pcb", "upgrade", str(f)])
        if r.returncode:
            check(False, "kicad-cli 10 pcb upgrade {}".format(f.relative_to(base)), r.stdout.strip()[-200:])
    vs = collections.Counter(kio.tree_version(kio.load(f).tree)
                             for f in base.rglob("*") if f.suffix in (".kicad_sch", ".kicad_pcb"))
    check(set(vs) == {20260306, 20260206}, "converted copies are in KiCad 10 format", str(dict(vs)))
    for f in sorted(p for p in base.rglob("*") if p.suffix in (".kicad_sch", ".kicad_pcb")):
        doc = kio.load(f)
        o = out / "rt10" / f.relative_to(base)
        o.parent.mkdir(parents=True, exist_ok=True)
        kio.save(doc, o)
        check(o.read_bytes() == f.read_bytes(), "round trip [KiCad 10] {}".format(f.relative_to(base)))
    return base


def expect_raise(exc, fn, what, unchanged=None):
    before = unchanged.read_bytes() if unchanged is not None else None
    try:
        fn()
    except exc as e:
        ok = unchanged is None or unchanged.read_bytes() == before
        return check(ok, what, "{}: {}".format(type(e).__name__, str(e)[:140]) + ("" if ok else "; FILE CHANGED"))
    return check(False, what, "no {} raised".format(exc.__name__))


def stage4(out):
    print("== 4 refusals")
    w = out / "refuse"
    v8 = copytree(out / "src" / V8, w / "v8")
    v7 = copytree(out / "src" / V7, w / "v7")
    sheet = v8 / "tca9548A_subsystem.kicad_sch"
    board = v7 / "motion-play-main.kicad_pcb"
    lock = v8 / "~motion-play-main-v8.kicad_sch.lck"
    lock.write_text("{}")
    doc = kio.load_schematic(sheet)
    edit(doc, "R92")
    expect_raise(kio.KiCadOpenError, lambda: kio.save(doc), "lock guard refuses save with ~*.kicad_sch.lck", sheet)
    expect_raise(kio.KiCadOpenError, lambda: kio.save_project([doc]), "lock guard refuses save_project", sheet)
    lock.unlink()
    plock = v7 / "~motion-play-main.kicad_pcb.lck"
    plock.write_text("{}")
    bdoc = kio.load_board(board)
    edit(bdoc, EDIT_FP)
    expect_raise(kio.KiCadOpenError, lambda: kio.save(bdoc), "lock guard refuses a board save with ~*.kicad_pcb.lck",
                 board)
    plock.unlink()
    kio.save(doc)
    check(kio.atom(prop(find_ref(kio.load(sheet), "R92"), "Value"), 1) == EDIT_VALUE,
          "save goes through once the lock file is gone")

    newer = w / "newer.kicad_sch"
    d2 = kio.load_schematic(out / "src" / V8 / "tca9548A_subsystem.kicad_sch")
    kio.set_num(kio.child(d2.tree, "version"), 0, 20990101)
    newer.write_text(kio.render(d2)[0])
    expect_raise(kio.KiCadIOFormatError, lambda: kio.load_schematic(newer),
                 "format check refuses a made-up newer version (20990101)")

    expect_raise(kio.KiCadIOVersionError, lambda: kio.check_pin("0.30.0"), "pin check refuses kicad-tools 0.30.0")
    check(kio.check_pin() == kio.PIN, "pin check passes the installed kicad-tools {}".format(kio.PIN))

    d3 = kio.load_schematic(sheet)
    kio.set_num(kio.child(d3.tree, "version"), 0, 20260306)
    expect_raise(kio.KiCadIOFormatError, lambda: kio.save(d3), "save refuses a tree whose version token changed", sheet)
    d4 = kio.load_board(board)
    kio.set_num(kio.child(d4.tree, "version"), 0, 20260206)
    other = kio.load_schematic(v8 / "led_controller.kicad_sch")
    edit(other, "R105")
    led = v8 / "led_controller.kicad_sch"
    expect_raise(kio.KiCadIOFormatError, lambda: kio.save(d4), "save refuses a board whose version token changed",
                 board)
    expect_raise(kio.KiCadIOFormatError, lambda: kio.save_project([other, d3]),
                 "save_project refuses (and writes none) when one tree's version changed", led)


EMBED_SHEET = "tca9548A_subsystem.kicad_sch"
EMBED_ROOT = "motion-play-main-v8.kicad_sch"
EMBED_STOCK = "Device:D_Schottky"                                        # not embedded in v8
EMBED_PROJECT = ("hardware/pcb-main/resources/INA219AIDCNR/INA219AIDCNR.kicad_sym", 20211014)


def lib_copy(lib_path, name, lib_id):
    """A library symbol as the tools take one: loaded through kicad_io, deep-copied, renamed."""
    import copy
    sym = next(s for s in kio.kids(kio.load_symbol_lib(lib_path).tree, "symbol") if kio.atom(s, 0) == name)
    sym = copy.deepcopy(sym)
    kio.set_str(sym, 0, lib_id)
    return sym


def stage4b(out, stock, k10base, cli9, cli10):
    """The embedded-symbol check (PLAN "One I/O module", Save): a library symbol from a newer KiCad's
    library can't go into an older sheet; every other combination saves and kicad-cli reads it."""
    print("== 4b embedded-symbol check (library format against the sheet's)")
    w = out / "embed"
    if w.exists():
        shutil.rmtree(str(w))
    stock = dict(stock)
    plib, pver = EMBED_PROJECT
    plib = out / "src" / "0" / plib
    check(kio.load_symbol_lib(plib).version == pver, "project library {} is format {}".format(plib.name, pver))
    sources = [("KiCad 9 stock", stock["KiCad 9"] / "Device.kicad_sym", "D_Schottky", EMBED_STOCK)]
    if "KiCad 10" in stock:
        sources.append(("KiCad 10 stock", stock["KiCad 10"] / "Device.kicad_sym", "D_Schottky", EMBED_STOCK))
    sources.append(("project library ({})".format(pver), plib, "INA219AIDCNR", "motion-play:INA219AIDCNR"))
    targets = [("9", out / "src" / V8, cli9)]
    if k10base is not None:
        targets.append(("10", k10base / V8, cli10))
    w.mkdir(parents=True)
    for ttag, tdir, cli in targets:
        n_in = netlist(cli, tdir / EMBED_ROOT, w / "in-{}.net".format(ttag))
        for i, (stag, lib, name, lib_id) in enumerate(sources):
            proj = copytree(tdir, w / "k{}-{}".format(ttag, i))
            sheet = proj / EMBED_SHEET
            doc = kio.load_schematic(sheet)
            sym = lib_copy(lib, name, lib_id)
            refuse = stag == "KiCad 10 stock" and ttag == "9"
            what = "{} {} into a KiCad {} sheet".format(stag, lib_id, ttag)
            if refuse:
                expect_raise(kio.KiCadIOFormatError, lambda: kio.check_embed(doc, sym),
                             "check_embed refuses " + what, sheet)
                kio.child(doc.tree, "lib_symbols").children.append(sym)    # past the embed check
                before = sheet.read_bytes()
                try:
                    kio.save(doc)
                    msg = None
                except kio.KiCadIOFormatError as e:
                    msg = str(e)
                named = msg is not None and all(s in msg for s in (lib_id, "20251024", "20250114"))
                check(msg is not None and sheet.read_bytes() == before and named,
                      "save refuses " + what + "; file byte-unchanged; message names symbol and both formats",
                      (msg or "no KiCadIOFormatError raised")[-170:])
                expect_raise(kio.KiCadIOFormatError, lambda: kio.save_project([doc]), "save_project refuses " + what,
                             sheet)
                # Why: the same tree written past the guard is a sheet kicad-cli 9 can't read.
                bad = copytree(tdir, w / "k9-unguarded")
                (bad / EMBED_SHEET).write_text(kio.render(doc)[0], encoding="utf-8")
                n_bad = netlist(cli, bad / EMBED_ROOT, w / "k9-unguarded.net")
                check(n_bad is None or len(n_bad[0]) < len(n_in[0]),
                      "  (the refused sheet, written past the guard, loses components in kicad-cli 9)",
                      "input {} unguarded {}".format(len(n_in[0]), "no netlist" if n_bad is None else len(n_bad[0])))
                continue
            kio.check_embed(doc, sym)
            kio.child(doc.tree, "lib_symbols").children.append(sym)
            kio.save(doc)
            back = kio.load_schematic(sheet)
            held = any(kio.atom(s, 0) == lib_id for s in kio.lib_symbol_nodes(back.tree))
            check(held and back.version == doc.version, "save passes " + what,
                  "embedded {}, version {} kept".format(held, back.version))
            same_counts("  kicad-cli {} reads it (netlist counts equal to the input's)".format(ttag), n_in,
                        netlist(cli, proj / EMBED_ROOT, w / "k{}-{}.net".format(ttag, i)))
    # a deep copy of a deep copy keeps its source; a node built in code has none
    s10 = [s for s in sources if s[0] == "KiCad 10 stock"]
    if s10:
        import copy
        twice = copy.deepcopy(lib_copy(*s10[0][1:]))
        check(kio.lib_symbol_source(twice) == (kio.SYM, 20251024, 10),
              "a copied copy keeps its source", str(kio.lib_symbol_source(twice)))
    check(kio.lib_symbol_source(kio.node('(symbol "X:Y")')) is None, "a node built in code has no source")


def stage5(out, k10base):
    print("== 5 atoms and hide flags")
    w = out / "atoms"
    v8 = copytree(out / "src" / V8, w / "v8")
    sheet = v8 / "tca9548A_subsystem.kicad_sch"
    doc = kio.load_schematic(sheet)
    at = kio.child(prop(find_ref(doc, "R92"), "Value"), "at")   # a field position: connectivity unchanged
    kio.set_num(at, 0, 181.6099)
    kio.set_num(at, 1, 63.123456789)
    kio.save(doc)
    got = [kio.atom_text(kio.child(prop(find_ref(kio.load_schematic(sheet), "R92"), "Value"), "at"), i)
           for i in (0, 1)]
    check(got == ["181.6099", "63.123456789"], "set_num keeps every digit", "file has {}".format(got))
    info("the trap set_num avoids: SExp(value=181.6099) writes {} and SExp(value=63.123456789) {}".format(
        SExp(value=181.6099).to_string(), SExp(value=63.123456789).to_string()))
    check(kio.num(-0.0) == "0" and kio.num(5.0) == "5" and kio.num(1e-7) == "0.0000001" and kio.num(2) == "2",
          "num(): -0.0 -> 0, 5.0 -> 5, 1e-7 -> 0.0000001, 2 -> 2")

    cases = [("9", sheet, "R92"), ("9 kiutils-format", v8 / "led_controller.kicad_sch", "R105")]
    if k10base is not None:
        cases.append(("10", k10base / V8 / "tca9548A_subsystem.kicad_sch", "R92"))
    for tag, path, ref in cases:
        p10 = tag == "10"
        d = kio.load_schematic(path)
        sym = find_ref(d, ref)
        # already hidden: the Footprint property, in this file's own form
        fp = prop(sym, "Footprint")
        before, compact = hide_flags(fp), fp.to_string(compact=True)
        changed = kio.hide(d, fp)
        check(kio.is_hidden(fp) and not changed and fp.to_string(compact=True) == compact and len(before) == 1,
              "[{}] hiding an already-hidden property adds nothing".format(tag), "flags {}".format(before))
        if tag.endswith("kiutils-format"):
            check(before == ["effects:bare"], "[{}] the hidden property is in the bare-hide form".format(tag))
            continue
        # a visible property: Value
        val = prop(sym, "Value")
        check(not kio.is_hidden(val), "[{}] Value is visible before".format(tag))
        kio.hide(d, val)
        want = ["property:(hide yes)"] if p10 else ["effects:(hide yes)"]
        check(hide_flags(val) == want and kio.is_hidden(val), "[KiCad {}] hide writes {}".format(tag, want),
              "got {}".format(hide_flags(val)))
        if p10:
            names = [c.name for c in val.children if not c.is_atom]
            check(names[:4] == ["at", "hide", "show_name", "do_not_autoplace"],
                  "[KiCad 10] the flag sits where KiCad 10 writes it (at, hide, show_name, ...)", str(names))
        again = kio.hide(d, val)
        check(not again and hide_flags(val) == want, "[KiCad {}] hiding it again adds no second flag".format(tag))
        np_ = kio.make_property(d, "MPN", "X-1", 10, 20.5, 0, hide=True)
        check(hide_flags(np_) == want, "[KiCad {}] make_property(hide=True) writes {}".format(tag, want),
              np_.to_string(compact=True))
        vis = kio.make_property(d, "Note", "n", 10, 20.5)
        check(not kio.is_hidden(vis) and hide_flags(vis) == [], "[KiCad {}] make_property() is visible".format(tag))
        if p10:
            check([c.name for c in np_.children if not c.is_atom][:4] == ["at", "hide", "show_name",
                                                                          "do_not_autoplace"],
                  "[KiCad 10] make_property has show_name and do_not_autoplace")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("--kicad-cli9", default=K9_CLI)
    ap.add_argument("--kicad-cli10", default=K10_CLI)
    ap.add_argument("--no-k10", action="store_true", help="skip stage 3 and the KiCad 10 hide cases")
    a = ap.parse_args()
    out = Path(a.outdir).resolve()
    if not (out / "src" / "0").is_dir():
        sys.exit("test_kicad_io.py: {}/src/0..2 missing (run it through regress.py iotest)".format(out))
    stock = [("KiCad 9", Path(a.kicad_cli9).resolve().parents[1] / "SharedSupport/symbols")]
    if not a.no_k10:
        stock.append(("KiCad 10", Path(a.kicad_cli10).resolve().parents[1] / "SharedSupport/symbols"))
    print("kicad_io pin {}; kicad-cli 9 {}; kicad-cli 10 {}".format(
        kio.PIN, run([a.kicad_cli9, "version"]).stdout.strip(),
        "skipped" if a.no_k10 else run([a.kicad_cli10, "version"]).stdout.strip()))
    stage1(out, a.kicad_cli9, stock)
    print("== 2 edits on KiCad 9 files")
    stage_edits(out, out / "src", a.kicad_cli9, "9")
    k10 = None
    if a.no_k10:
        print("== 3 SKIPPED (--no-k10)")
    else:
        print("== 3 edits on KiCad 10 copies (kicad-cli 10, scratch only)")
        k10 = convert10(out, a.kicad_cli10)
        stage_edits(out, k10, a.kicad_cli10, "10")
    stage4(out)
    stage4b(out, stock, k10, a.kicad_cli9, a.kicad_cli10)
    stage5(out, k10)
    print("== 6 kicad-cli 9 reads the KiCad 9 sheets stages 4 and 5 saved")
    n_in = netlist(a.kicad_cli9, out / "src" / V8 / "motion-play-main-v8.kicad_sch", out / "cli9-in6.net")
    for d in ("refuse", "atoms"):
        n_out = netlist(a.kicad_cli9, out / d / "v8" / "motion-play-main-v8.kicad_sch", out / "cli9-{}.net".format(d))
        same_counts("kicad-cli 9 netlist {}/v8".format(d), n_in, n_out)
    print("IOTEST {}: {} passed, {} failed".format("PASSED" if not RESULTS["FAIL"] else "FAILED",
                                                  RESULTS["PASS"], RESULTS["FAIL"]))
    return 1 if RESULTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
