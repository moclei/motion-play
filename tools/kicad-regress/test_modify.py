"""test_modify.py - differential test of tools/schematic-modify/modify.py (kicad10-tooling Phase 6b).
Runs in tools/.venv.

usage: test_modify.py OUTDIR --pre-tools DIR [--kicad-cli9 CLI] [--kicad-cli10 CLI | --no-k10] [--ops a,b]
Normally run through `regress.py modtest OUTDIR`, which puts a fresh `git archive` of v8 (at
v8-schematic-freeze, with hardware/pcb-main/resources) under OUTDIR/src/0 and a worktree of the oracle
tag kicad10-preport at OUTDIR/wt-pre (removed afterwards); --pre-tools is that worktree's tools/.
Everything is written under OUTDIR, never under the repository.

Method (PLAN "Oracle", write tools; the Phase 5 prototype comparison, SESSION Worker #5 Notes task 2).
Each OP is one fresh process per side (`--apply`): copy the base project, load it with that side's
modify.load_project, run the OP through that side's public modify API, save (ProjectDocs.save_all).
uuid.uuid4 is seeded in that process, so both sides mint the same UUIDs in the same order and the
netlists compare with tstamps included. The ops' return values are logged and must be equal.
Then, read by kicad-cli 9 (KiCad 9 stage):
  netlist   structurally identical (components with every field and tstamp; nets by node set)
  erc       ERC counts by (severity, type) identical
  plot      plotted strings identical on every sheet
  returns   the OP's logged return values identical
  census    the token census change of each edited sheet, port output against the unedited base,
            equals the change preport's edit made against preport's own no-op save (the same load
            and save with no OP), apart from the kinds in CENSUS_KIUTILS (tokens kiutils 1.4.8 never
            writes on a new item; each such difference is printed). So the port's file changes by
            exactly the edit, and by nothing else.
KiCad 10 stage (K10_OPS: the ops that write properties, sheets and sheet pins): the base copy is
converted by kicad-cli 10 (`sch upgrade` on every sheet); the port edits the converted copy; preport's
KiCad 9 output and its no-op save are copied and converted the same way. kicad-cli 10 reads both: the
same netlist/erc/plot/returns checks. The port's census change against the converted base is printed
(only the edit). The census check compares like with like and has no exceptions: the conversion writes
preport's new items in KiCad 10's full form (it adds the defaults body_style, in_pos_files, a
Description property, a sheet's in_bom/on_board/dnp/exclude_from_sim), so the port's output is
re-saved the same way (`sch upgrade --force`, a copy) and its change against the converted base must
equal preport's converted change against its converted no-op save exactly; the sheet node likewise.
The add_sheet_reference OP (`sheet`) also compares the new sheet node itself, port against preport
(numbers as numbers): SHEET_E2_DIFFS lists the only differences allowed (PLAN "Accepted differences
from preport", E2).
"""
import argparse
import collections
import itertools
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(HERE))
import kcompare  # noqa: E402
from sexp import Q, load  # noqa: E402

K9_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
K10_CLI = "/Applications/KiCad10/KiCad.app/Contents/MacOS/kicad-cli"
REL = "hardware/pcb-main-v8/kicad"
ROOT = "motion-play-main-v8.kicad_sch"
TCA = "tca9548A_subsystem.kicad_sch"
LED = "led_controller.kicad_sch"
PROJ = "motion-play-main-v8"
NEW_SHEET = "p6_new.kicad_sch"

OPS = ["reads", "add_comp", "remove_comp", "wires", "labels", "nc", "hlabels", "sheet", "power", "props",
       "pin_net", "annotate"]
# annotate is not run on KiCad 10: annotate_components only calls annotate.py, which is kiutils until
# Phase 9 and on a KiCad 10 file unhides every property-level-hidden field (Phase 12 validates it on 10).
K10_OPS = ["add_comp", "remove_comp", "hlabels", "sheet", "power", "props", "pin_net"]

# Census kinds where kiutils 1.4.8 (through kiutils_k9) writes a new item's token in another form than
# KiCad 9 and the port. Only these may differ between the two census changes on KiCad 9; the kinds that
# carry the meaning (F:hide, L:fields_autoplaced, L:property, L:uuid, ...) must still match.
#   A:uuid/<id>         kiutils writes a new item's uuid bare, KiCad quotes it (L:uuid still counted)
#   L:id                kiutils writes (id N) on every new property; KiCad 9 doesn't
#   L:hide              kiutils writes a hidden field's flag as a bare `hide`, KiCad 9 as (hide yes)
#                       (both count as F:hide, which must match)
#   F:fields_autoplaced kiutils writes (fields_autoplaced), KiCad 9 (fields_autoplaced yes)
#   L:/N:/F:exclude_from_sim  kiutils drops (exclude_from_sim no); the port writes it, as KiCad does
#   L:/N:embedded_fonts kiutils drops (embedded_fonts no) from a library symbol it embeds; the port copies
#                       the library's symbol whole, as KiCad's own embedded symbols on v8 carry it
CENSUS_KIUTILS = {"L:id", "L:hide", "F:fields_autoplaced", "L:exclude_from_sim", "N:exclude_from_sim",
                  "F:exclude_from_sim", "L:embedded_fonts", "N:embedded_fonts", "A:uuid/*"}


def allowed(key, allow):
    return key in allow or any(a.endswith("*") and key.startswith(a[:-1]) for a in allow)

# The only differences allowed between preport's new sheet node and the port's, per stage: the E2 fix
# (PLAN "Accepted differences from preport"): the instance project is the root schematic's stem, and the
# keys are KiCad 7+'s Sheetname/Sheetfile. On KiCad 10 there are none: kicad-cli 10's conversion of
# preport's output already rewrites both (and the port's re-save is compared there).
SHEET_E2_DIFFS = {
    "KiCad 9": [("/sheet[3]/instances[1]/project[1]", "motion-play-main", "motion-play-main-v8"),
                ("/sheet[7]/property[1]", "Sheet file", "Sheetfile"),
                ("/sheet[8]/property[1]", "Sheet name", "Sheetname")],
    "KiCad 10": [],
}

RESULTS = collections.Counter()


def check(ok, what, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print("{} {}{}".format("PASS" if ok else "FAIL", what, "  " + detail if detail else ""))
    sys.stdout.flush()
    return ok


def info(msg):
    print("     " + msg)
    sys.stdout.flush()


def run(argv, **kw):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, **kw)


# ---------------------------------------------------------------------------
# --apply: one OP through one side's modify.py, in its own process
# ---------------------------------------------------------------------------

def apply_op(impl, op, base, out, pre_tools):
    counter = itertools.count(1)
    uuid.uuid4 = lambda: uuid.UUID(int=(0x6EED << 96) + next(counter), version=4)
    tools = Path(pre_tools) if impl == "pre" else TOOLS
    sys.path.insert(0, str(tools / "schematic-modify"))
    import modify as m

    if out.exists():
        shutil.rmtree(str(out))
    shutil.copytree(str(base), str(out))
    k = out / REL
    root_path = k / ROOT
    stock = Path(m.STOCK_SYMBOLS)
    docs = m.load_project(root_path)
    tca, led, root = docs.sheet(TCA), docs.sheet(LED), docs.sheet("root")
    log = []

    if op == "noop":
        pass
    elif op == "reads":
        log.append(("project", docs.project_name, docs.root_uuid, sorted(docs.by_key)))
        log.append(("instance_paths", sorted((key, d.instance_path) for key, d in docs.by_key.items())))
        for key in sorted(docs.by_key):
            log.append(("refs", key, sorted(m._all_ref_set(docs.by_key[key].schematic))))
        for ref, pin in [("R92", "1"), ("R92", "2"), ("U4", "10"), ("TP99", "1")]:
            log.append(("pin_position", ref, pin, m.pin_position(tca, ref, pin)))
        for ref, pin in [("R105", "1"), ("R105", "2")]:
            log.append(("pin_position", ref, pin, m.pin_position(led, ref, pin)))
        # every pin of every unmirrored symbol on the MCU sheet (0/90/180/270-degree parts)
        mcu = docs.sheet("esp32_s3.kicad_sch")
        n = 0
        for ref in sorted(m._all_ref_set(mcu.schematic)):
            try:
                pins = [r[0] for r in m._pin_records(m.get_lib_symbol_for(mcu, _lib_id(m, m.find_component(mcu, ref))))]
                for pin in pins:
                    log.append(("pin_position", ref, pin, m.pin_position(mcu, ref, pin)))
                    n += 1
            except ValueError as e:
                log.append(("pin_position", ref, "ValueError", str(e)))
        log.append(("mcu pins", n))
        log.append(("find_sheet_ref", m._symbol_ref(m.find_component(tca, "R92")),
                    _sheet_file(m, m.find_sheet_ref(root, TCA))))
        for args in [((10.0, 20.0, 90, 2.54, -1.27)), ((10.0, 20.0, 270, 3.81, 0)), ((5.08, 5.08, 180, 1.27, 2.54))]:
            log.append(("geom", m._compute_pin_position(*args)))
        for args in [(10.0, 20.0, 0, 0), (10.0, 20.0, 90, 90), (10.0, 20.0, 270, 0, 2.54)]:
            log.append(("stub", m._compute_stub_endpoint(*args)))
        log.append(("lib_symbol Device:C", _lib_id_sym(m, m.extract_lib_symbol("Device:C", stock / "Device.kicad_sym"))))
        log.append(("lib_symbol Device:R", _lib_id_sym(m, m.extract_lib_symbol("Device:R", k / LED))))
    elif op == "add_comp":
        cap = m.extract_lib_symbol("Device:C", stock / "Device.kicad_sym")
        m.add_component(tca, lib_symbol=cap, lib_id="Device:C", ref="C900", value="100nF",
                        footprint="Capacitor_SMD:C_0402_1005Metric", lcsc_part="C1525", position=(60.96, 254.0),
                        angle=0, pin_nets={"1": "P6_NEW_A", "2": "GND"}, project_name=PROJ)
        res = m.extract_lib_symbol("Device:R", stock / "Device.kicad_sym")
        m.add_component(tca, lib_symbol=res, lib_id="Device:R", ref="R900", value="1k",
                        footprint="Resistor_SMD:R_0603_1608Metric", lcsc_part="", position=(81.28, 254.0),
                        angle=90, pin_nets={"1": "P6_NEW_A", "2": "P6_NEW_B"}, project_name=PROJ, stub_len=2.54)
        led_r = m.extract_lib_symbol("Device:R", k / LED)
        m.add_component(led, lib_symbol=led_r, lib_id="Device:R", ref="R901", value="2k",
                        footprint="Resistor_SMD:R_0603_1608Metric", lcsc_part="C0", position=(30.48, 30.48),
                        angle=180, pin_nets={"2": "P6_NEW_C"}, project_name=PROJ)
        # 270 degrees and a pin on a non-grid offset; default project_name
        m.add_component(tca, lib_symbol=res, lib_id="Device:R", ref="R902", value="4k7",
                        footprint="Resistor_SMD:R_0603_1608Metric", lcsc_part="C23162", position=(101.6, 254.0),
                        angle=270, pin_nets={"1": "P6_NEW_D", "2": "P6_NEW_B"})
        try:
            m.add_component(tca, lib_symbol=res, lib_id="Device:R", ref="R92", value="x", footprint="",
                            lcsc_part="", position=(0, 0))
        except ValueError as e:
            log.append(("dup ref", str(e)))
    elif op == "remove_comp":
        log.append(m.remove_component(tca, "R92"))
        log.append(m.remove_component(tca, "R_NOT_THERE"))
        log.append(m.remove_component_with_stubs(tca, "TP99"))
    elif op == "wires":
        m.add_wire(tca, (20.32, 20.32), (30.48, 20.32))
        log.append(m.remove_wire_between(tca, (278.13, 208.28), (280.67, 208.28)))
        log.append(m.remove_wire_between(tca, (1.0, 1.0), (2.0, 2.0)))
        log.append(m.remove_junction_at(tca, (146.05, 119.38)))
        log.append(m.remove_junction_at(tca, (1.0, 1.0)))
    elif op == "labels":
        m.add_local_label(tca, "P6_LBL_0", (30.48, 20.32), 0)
        m.add_local_label(tca, "P6_LBL_180", (20.32, 20.32), 180)
        m.add_local_label(tca, "P6_LBL_90", (20.32, 30.48), 90)
        m.add_local_label(tca, "P6_LBL_270", (20.32, 10.16), 270)
        m.add_wire(tca, (20.32, 20.32), (30.48, 20.32))
        m.add_wire(tca, (20.32, 10.16), (20.32, 30.48))
        log.append(m.remove_local_label_near(tca, "CH2_SDA_CONN", (45.72, 214.63)))
        log.append(m.remove_local_label_near(tca, "CH2_SDA_CONN", (1.0, 1.0)))
    elif op == "nc":
        log.append(m.remove_no_connect_at(tca, (181.61, 116.84)))
        log.append(m.remove_no_connect_at(tca, (1.0, 1.0)))
        m.add_no_connect(tca, (101.6, 101.6))
    elif op == "hlabels":
        m.add_hierarchical_label(tca, name="P6_H_NEW", shape="input", net="P6_H_NET", position=(25.4, 40.64))
        m.add_hierarchical_label(tca, name="P6_H_NEW0", shape="output", net="P6_H_NET0", position=(25.4, 50.8),
                                 angle=0)
        m.add_pin_to_sheet_ref(root, TCA, "P6_H_NEW", "input")
        m.add_pin_to_sheet_ref(root, TCA, "P6_H_NEW0", "output")
        log.append(m.change_hlabel_shape(tca, "TCA_RESET", "bidirectional"))
        log.append(m.change_hlabel_shape(tca, "NOT_THERE", "bidirectional"))
        log.append(m.change_sheet_pin_direction(root, TCA, "TCA_RESET", "bidirectional"))
        log.append(m.change_sheet_pin_direction(root, TCA, "NOT_THERE", "bidirectional"))
        log.append(m.rename_hlabel(tca, "I2C_SDA_IN", "I2C_SDA_IN_P6"))
        log.append(m.rename_sheet_pin(root, TCA, "I2C_SDA_IN", "I2C_SDA_IN_P6"))
        log.append(m.rename_sheet_pin(root, TCA, "NOT_THERE", "X"))
        for i in range(12):   # right-side pins until the sheet grows
            m.add_pin_to_sheet_ref(root, TCA, "P6_OUT_%d" % i, "output")
        try:
            m.add_pin_to_sheet_ref(root, TCA, "P6_OUT_0", "output")
        except ValueError as e:
            log.append(("dup pin", str(e)))
    elif op == "sheet":
        (k / NEW_SHEET).write_text(
            '(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") '
            '(uuid "00000000-0000-4000-8000-0000000000aa") (paper "A4") (lib_symbols) '
            '(hierarchical_label "IN_A" (shape input) (at 50.8 50.8 180) (effects (font (size 1.27 1.27)) '
            '(justify right)) (uuid "00000000-0000-4000-8000-0000000000ab")) '
            '(hierarchical_label "IO_C" (shape bidirectional) (at 50.8 55.88 180) (effects (font (size 1.27 1.27)) '
            '(justify right)) (uuid "00000000-0000-4000-8000-0000000000ac")) '
            '(hierarchical_label "OUT_B" (shape output) (at 101.6 50.8 0) (effects (font (size 1.27 1.27)) '
            '(justify left)) (uuid "00000000-0000-4000-8000-0000000000ad")) (embedded_fonts no))\n')
        log.append(m.add_sheet_reference(root, sheet_name="P6 New", file_name=NEW_SHEET,
                                         position=(254.0, 50.8), size=(25.4, 20.32),
                                         pins=[{"name": "IN_A", "direction": "input"},
                                               {"name": "OUT_B", "direction": "output"},
                                               {"name": "IO_C"}]))
        try:
            m.add_sheet_reference(root, sheet_name="dup", file_name=TCA, position=(0, 0), size=(1, 1), pins=[])
        except ValueError as e:
            log.append(("dup sheet", str(e)))
    elif op == "power":
        gnd = m.extract_lib_symbol("power:GND", stock / "power.kicad_sym")
        m.add_power_symbol(tca, gnd, "power:GND", "#PWR0900", "GND", (30.48, 20.32), PROJ)
        m.add_wire(tca, (20.32, 20.32), (30.48, 20.32))
        flg = m.extract_lib_symbol("power:PWR_FLAG", stock / "power.kicad_sym")
        m.add_power_symbol(tca, flg, "power:PWR_FLAG", "#FLG0900", "PWR_FLAG", (20.32, 20.32), PROJ)
    elif op == "props":
        log.append(m.set_property(tca, "R92", "Value", "10kΩ"))
        log.append(m.set_property(tca, "R92", "MPN", "RC0603FR-0710KL"))
        log.append(m.set_property(led, "R105", "LCSC Part", "C22775"))
        log.append(m.set_property(led, "R105", "Note \"q\"", "a \\ b"))
    elif op == "pin_net":
        log.append(m.set_pin_net(tca, "R92", "1", "P6_RENAMED"))
        log.append(m.set_pin_net(tca, "U4", "10", "P6_FROM_NC"))
        log.append(m.set_pin_net(tca, "U4", "11", "P6_FROM_NC2", stub_len=2.54))
        for ref, pin in [("U4", "1")]:
            try:
                m.set_pin_net(tca, ref, pin, "X")
            except ValueError as e:
                log.append(("refused", str(e)))
    elif op == "annotate":
        script = (Path(pre_tools) / "schematic-context/annotate.py") if impl == "pre" else None
        m.annotate_components(root_path, ["R92", "R105", "TP99"],
                              {"block": "p6_block", "role": "p6_role", "function": "new"}, annotate_script=script)
    else:
        raise SystemExit("unknown op " + op)

    if op != "annotate":
        docs.save_all()
    (out / "log.json").write_text(json.dumps(_plain(log), indent=1, ensure_ascii=False))


def _plain(x):
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, float):
        return round(x, 9)
    return x


def _lib_id(m, sym):
    """A placed symbol's lib id on either side (kiutils object or raw node)."""
    if hasattr(sym, "libId"):
        return sym.libId
    return str(m.atom(m.child(sym, "lib_id")))


def _lib_id_sym(m, sym):
    if hasattr(sym, "libId"):
        return [sym.libId, sorted(r[0] for r in m._pin_records(sym))]
    return [str(m.atom(sym, 0)), sorted(r[0] for r in m._pin_records(sym))]


def _sheet_file(m, sheet):
    if hasattr(sheet, "fileName"):
        return sheet.fileName.value
    return m.sheet_file_name(sheet)


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------

def outputs(cli, tree):
    o = tree / "out"
    if o.exists():
        return o
    o.mkdir()
    k = tree / REL
    run([cli, "sch", "export", "netlist", "-o", str(o / "net.net"), str(k / ROOT)])
    run([cli, "sch", "erc", "--severity-all", "--format", "json", "-o", str(o / "erc.json"), str(k / ROOT)])
    run([cli, "sch", "export", "svg", "-o", str(o / "svg"), str(k / ROOT)])
    return o


def census_delta(after, before):
    a, b = kcompare.census(str(after)), kcompare.census(str(before))
    return {key: a[key] - b[key] for key in set(a) | set(b) if a[key] != b[key]}


def sheet_node(path, sheet_uuid):
    for c in load(path):
        if isinstance(c, list) and c and c[0] == "sheet":
            for d in c:
                if isinstance(d, list) and d and d[0] == "uuid" and d[1] == sheet_uuid:
                    return c
    return None


def _norm(n, parent=None):
    """A tree compared for meaning, not form: numbers as floats; a uuid quoted or bare alike; kiutils'
    (id N) on properties dropped (KiCad 9 doesn't write it); in each list the head and its atoms keep
    their order, and the sub-lists are sorted (kiutils writes a sheet pin's effects before its uuid,
    KiCad after)."""
    if isinstance(n, list):
        lead = [_norm(c, n[0] if n else None) for c in n if not isinstance(c, list)]
        subs = sorted((_norm(c) for c in n if isinstance(c, list) and not (c and c[0] == "id")), key=repr)
        return tuple(lead + subs)
    if parent == "uuid":
        return str(n)
    if not isinstance(n, Q):
        try:
            return ("num", float(n))
        except ValueError:
            pass
    return ("Q", str(n)) if isinstance(n, Q) else str(n)


def tree_diffs(a, b, path="", out=None):
    out = [] if out is None else out
    if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b) and not (a and a[0] in ("num", "Q")):
        for i, (x, y) in enumerate(zip(a, b)):
            tree_diffs(x, y, "{}/{}[{}]".format(path, a[0] if a and isinstance(a[0], str) else "?", i), out)
    elif a != b:
        out.append((path, _show(a), _show(b)))
    return out


def _show(x):
    if isinstance(x, tuple) and len(x) == 2 and x[0] in ("num", "Q"):
        return x[1]
    return str(x)[:160]


def compare(op, pre, port, base_pre, base_port, cli, stage, census_allow, census_port=None):
    tag = "[{}] {}".format(stage, op)
    oa, ob = outputs(cli, pre), outputs(cli, port)
    lines, eq = kcompare.netlist_diff(str(oa / "net.net"), str(ob / "net.net"))
    check(eq, tag + " netlist", lines[0])
    if not eq:
        info("\n     ".join(lines[1:]))
    ea = kcompare.erc_counts(json.load(open(str(oa / "erc.json"))))
    eb = kcompare.erc_counts(json.load(open(str(ob / "erc.json"))))
    ca = [l for l in ea if not l.startswith("   ")]
    cb = [l for l in eb if not l.startswith("   ")]
    check(ca == cb, tag + " erc", "; ".join(cb))
    if ca != cb:
        info("preport only: {}; port only: {}".format([l for l in ca if l not in cb], [l for l in cb if l not in ca]))
    sl, seq = kcompare.svg_strings(str(oa / "svg"), str(ob / "svg"))
    check(seq, tag + " plot", "{} sheets".format(len(sl)))
    if not seq:
        info("\n     ".join(l for l in sl if l.startswith("DIFF")))
    if op == "annotate":
        # annotate_components runs annotate.py (kiutils until Phase 9) in both: the files must be equal
        same = [f.name for f in sorted((port / REL).glob("*.kicad_sch"))
                if f.read_bytes() == (pre / REL / f.name).read_bytes()]
        n = len(list((port / REL).glob("*.kicad_sch")))
        check(len(same) == n, tag + " files", "{}/{} sheets byte-identical to preport's (the same annotate.py "
              "writes both)".format(len(same), n))
        return pre, port
    la, lb = json.loads((pre / "log.json").read_text()), json.loads((port / "log.json").read_text())
    check(la == lb, tag + " returns", "{} values".format(len(lb)))
    if la != lb:
        for x, y in zip(la, lb):
            if x != y:
                info("preport {}\n     port    {}".format(str(x)[:300], str(y)[:300]))
    # census: port vs base == preport vs its own no-op save
    ok, touched = True, []
    if census_port is not None:
        info("port census change against the base: " + " | ".join(
            "{} {}".format(sh.name, _fmt_delta(census_delta(sh, base_port / REL / sh.name)))
            for sh in sorted((port / REL).glob("*.kicad_sch"))
            if (base_port / REL / sh.name).exists() and census_delta(sh, base_port / REL / sh.name)))
        port = census_port
    for sh in sorted((port / REL).glob("*.kicad_sch")):
        if not (base_port / REL / sh.name).exists():
            touched.append(sh.name + " (new file)")
            continue
        dp = census_delta(sh, base_port / REL / sh.name)
        dr = census_delta(pre / REL / sh.name, base_pre / REL / sh.name)
        if not dp and not dr:
            continue
        touched.append("{} {}".format(sh.name, _fmt_delta(dp)))
        diff = {key: (dr.get(key, 0), dp.get(key, 0)) for key in set(dp) | set(dr) if dp.get(key, 0) != dr.get(key, 0)}
        bad = {key: v for key, v in diff.items() if not allowed(key, census_allow)}
        if diff:
            uu = sum(1 for key in diff if key.startswith("A:uuid/"))
            shown = sorted((key, v) for key, v in diff.items() if not key.startswith("A:uuid/"))
            info("{}: census change preport/port differs in {}{}{}".format(
                sh.name, ", ".join("{} {:+d}/{:+d}".format(key, *v) for key, v in shown),
                ", {} bare uuids".format(uu) if uu else "", "" if bad else " (all CENSUS_KIUTILS)"))
        ok &= not bad
    check(ok, tag + " census", "only the edit; " + " | ".join(touched))
    return pre, port


def _fmt_delta(d):
    return ", ".join("{} {:+d}".format(key, v) for key, v in sorted(d.items()))


def sheet_check(pre, port, stage):
    sid = json.loads((port / "log.json").read_text())[0]
    a, b = sheet_node(pre / REL / ROOT, sid), sheet_node(port / REL / ROOT, sid)
    if a is None or b is None:
        return check(False, "[{}] sheet node".format(stage), "new sheet {} missing (preport {}, port {})".format(
            sid, a is not None, b is not None))
    d = tree_diffs(_norm(a), _norm(b))
    expected = [tuple(x) for x in SHEET_E2_DIFFS[stage]]
    ok = check(sorted(d) == sorted(expected), "[{}] sheet node, port against preport".format(stage),
               "{} differences{}".format(len(d), " (E2)" if d and d == expected else ""))
    for x in d:
        info("{}: preport {!r} port {!r}".format(*x))
    return ok


def upgrade(cli10, tree, force=False):
    for f in sorted((tree / REL).glob("*.kicad_sch")):
        r = run([cli10, "sch", "upgrade"] + (["--force"] if force else []) + [str(f)])
        if r.returncode:
            check(False, "kicad-cli 10 sch upgrade {}".format(f.name), r.stdout.strip()[-200:])


def apply(py, impl, op, base, out, pre_tools, cli):
    env = dict(os.environ, KICAD_CLI=cli)
    r = run([str(py), str(Path(__file__).resolve()), "--apply", impl, op, str(base), str(out),
             "--pre-tools", str(pre_tools)], env=env)
    if r.returncode:
        check(False, "{} {} applied".format(impl, op), r.stdout.strip()[-1500:])
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", nargs="?")
    ap.add_argument("--apply", nargs=4, metavar=("IMPL", "OP", "BASE", "OUT"))
    ap.add_argument("--pre-tools", required=True)
    ap.add_argument("--kicad-cli9", default=K9_CLI)
    ap.add_argument("--kicad-cli10", default=K10_CLI)
    ap.add_argument("--no-k10", action="store_true")
    ap.add_argument("--ops")
    a = ap.parse_args()
    if a.apply:
        impl, op, base, out = a.apply
        apply_op(impl, op, Path(base), Path(out), a.pre_tools)
        return 0

    out = Path(a.outdir).resolve()
    py = Path(sys.executable)
    pre_tools = Path(a.pre_tools).resolve()
    ops = a.ops.split(",") if a.ops else OPS
    src = out / "src/0"
    cli9, cli10 = a.kicad_cli9, a.kicad_cli10

    # KiCad 9
    k9 = out / "k9"
    print("== KiCad 9 ({}), base {}".format(cli9, src))
    base_pre = k9 / "noop/pre"
    apply(py, "pre", "noop", src, base_pre, pre_tools, cli9)
    for op in ops:
        pre, port = k9 / op / "pre", k9 / op / "port"
        if apply(py, "pre", op, src, pre, pre_tools, cli9) and apply(py, "port", op, src, port, pre_tools, cli9):
            compare(op, pre, port, base_pre, src, cli9, "KiCad 9", CENSUS_KIUTILS)
            if op == "sheet":
                sheet_check(pre, port, "KiCad 9")

    # KiCad 10
    if not a.no_k10:
        k10 = out / "k10"
        base10 = k10 / "base"
        shutil.copytree(str(src), str(base10))
        upgrade(cli10, base10)
        vs = collections.Counter(load(f)[1][1] for f in (base10 / REL).glob("*.kicad_sch"))
        check(set(vs) == {"20260306"}, "[KiCad 10] base converted", str(dict(vs)))
        print("== KiCad 10 ({}), base {}".format(cli10, base10))
        noop10 = k10 / "noop/pre"
        shutil.copytree(str(base_pre), str(noop10))
        shutil.rmtree(str(noop10 / "out"), ignore_errors=True)
        upgrade(cli10, noop10)
        for op in [o for o in ops if o in K10_OPS]:
            pre, port = k10 / op / "pre", k10 / op / "port"
            if not (k9 / op / "pre/log.json").exists():
                continue
            shutil.copytree(str(k9 / op / "pre"), str(pre))
            shutil.rmtree(str(pre / "out"), ignore_errors=True)
            upgrade(cli10, pre)
            if apply(py, "port", op, base10, port, pre_tools, cli10):
                resaved = k10 / op / "port-resaved"
                shutil.copytree(str(port), str(resaved))
                upgrade(cli10, resaved, force=True)
                compare(op, pre, port, noop10, base10, cli10, "KiCad 10", set(), census_port=resaved)
                if op == "sheet":
                    sheet_check(pre, resaved, "KiCad 10")

    print("MODTEST {}: {} passed, {} failed".format("PASSED" if not RESULTS["FAIL"] else "FAILED",
                                                    RESULTS["PASS"], RESULTS["FAIL"]))
    return 1 if RESULTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
