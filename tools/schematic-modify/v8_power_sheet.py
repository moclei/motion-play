#!/usr/bin/env python3
"""
v8_power_sheet.py - v8 debug board, power sheet edits (Phase 10).

Initiative: docs/initiatives/v8-debug-board. Design intent: hardware/pcb-main-v8/CONTEXT.md ->
Power path (approved 2026-11-03, W2), Jumper matrix rows c, h, i, j, k, l, Test points (rails).
Part list: tools/schematic-gen/power_v8_spec.json (Phase 7 spec, with the Phase 10 corrections
recorded in its `_note_phase10`). The v7-derived power sheet is modified in place (all
label-style), not regenerated: it keeps U9, D1/R1, TP1-TP4 and every v7 symbol and footprint.

Edits (KiCad must be closed during --apply):
  power_management.kicad_sch (paper A4 -> A3; new parts in a grid right of and below the v7 drawing)
    - Battery: BT1, Q2, R33, R34 removed with their stubs/labels. New J8 (XT30), F3, Q20/Q21
      back to back, gate network R60/C60/C61/R61, SW4 "BATT", J9 cell NTC. C30 moves to VBAT.
      No v7 position (user decision 2026-11-03): the check models both sides as conducting.
    - U5: pin 2 -> BQ_DP, 3 -> BQ_DM (row j: JP32 SJ3 + JP33 SJ2), 4 -> BQ_STAT (D10/R62 STAT LED
      from VSYS). R35 top -> OTG_PU (row k: JP34). TH1 -> TS_BOARD (row l: JP35, J9).
    - Row i: SW1 common -> SW1_COM; JP31 SJ3 (pad 1 VSYS_SENSE default, pad 3 SW1_COM).
    - Row c / h: U8 output -> +3.3V_MCU_REG, input -> +5V_CORE; U10 AP2112K (EN on +3.3V_MCU);
      JP30 1x3 header; links R63 (h1), R64 (h2), R65 (h3) with unfitted headers J30-J32.
      U7 (INA219) VS -> +3.3V_BUS. PMID 6 x 22 uF (C25, C26 re-valued + C63, C64, C69, C70).
    - Rail and control test points TP10-TP35, each with its own GND point TP50-TP75
      (TP11/14/16 not added: v7 TP3/TP1/TP2 cover those nets, TP51/54/56 are their GND points).
    - Value/LCSC/footprint fixes from Power path "Other v7 deviations" (C22, C25, C26, C29, C30,
      R44, C34-C36, C42), J7 footprint -> v8 copy with the shell legs on pin "0" (SH -> GND).
  led_controller.kicad_sch
    - Link h4: F1 out -> +5V_LED_F -> R66 (10 mOhm) / J33 -> +5V_LED_H4 (v7 C7, R27) -> R27 ->
      +5V_TO_LEDS. TP22/TP62, TP36/TP76, TP23/TP63. PWR_FLAG on +5V_TO_LEDS (IC1 VCC driven).
  Rails, all sheets: the global power net +3.3V becomes +3.3V_MCU (power symbols' Value, labels,
    hierarchical labels and sheet pins). The bus loads (TCA U4 via VCC_3V3, R6, R28/R29 and the
    I2C_PU_RAIL labels, J4-J6 pin 1) move to the global +3.3V_BUS, which the ESP32 sheet's J10
    and the power sheet's U7 / link h2 join. D5 (ESP32 sheet +5V) moves to +5V_CORE.

Usage:
  python3 tools/schematic-modify/v8_power_sheet.py            # dry run: print the plan
  python3 tools/schematic-modify/v8_power_sheet.py --apply    # edit (refuses if U10 exists)
  python3 tools/schematic-modify/v8_power_sheet.py --check    # Phase 8+9 checks, pin -> net for
                                                              # every power part, rows c/h/i/j/k/l
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modify  # noqa: E402
import v8_mcu_sheet as mcu  # noqa: E402

REPO = mcu.REPO
ROOT = mcu.ROOT
PROJECT = mcu.PROJECT
KICAD = mcu.KICAD
PWR = "power_management.kicad_sch"
LED = "led_controller.kicad_sch"
TCA = "tca9548A_subsystem.kicad_sch"
MCU = mcu.MCU
SPEC = REPO / "tools/schematic-gen/power_v8_spec.json"

# J7 footprint: v8 copy of the v7 footprint with the shell legs on the symbol's SH pin ("0").
J7_V7_FP = REPO / "hardware/pcb-main/resources/TYPE-C-31-M-12/TYPE-C-31-M-12.pretty/USB-C_SMD-TYPE-C-31-M-12_1.kicad_mod"
FP_LIB = "motion-play-v8"
FP_DIR = KICAD / "libraries/footprints/motion-play-v8.pretty"
J7_FP_NAME = "USB-C_SMD-TYPE-C-31-M-12_ShellGND"

V7_REMOVED = ("BT1", "Q2", "R33", "R34")

# Power-sheet pin moves (order matters: U7.4 before the +3.3V label rename).
PIN_MOVES = [
    ("C30", "1", "VBAT"), ("U5", "2", "BQ_DP"), ("U5", "3", "BQ_DM"), ("U5", "4", "BQ_STAT"),
    ("R35", "2", "OTG_PU"), ("TH1", "1", "TS_BOARD"), ("SW1", "2", "SW1_COM"),
    ("U8", "2", "+3.3V_MCU_REG"), ("U8", "4", "+3.3V_MCU_REG"), ("C40", "1", "+3.3V_MCU_REG"),
    ("C43", "1", "+3.3V_MCU_REG"), ("U8", "3", "+5V_CORE"), ("U7", "4", "+3.3V_BUS"),
]
CP_ELEC = "Capacitor_SMD:CP_Elec_6.3x5.4"
PROPS = [
    ("C22", {"Value": "47uF 35V", "Footprint": CP_ELEC, "LCSC Part": "C72522"}),
    ("C30", {"Value": "47uF 35V", "Footprint": CP_ELEC, "LCSC Part": "C72522"}),
    ("C25", {"Value": "22uF 25V", "Footprint": "Capacitor_SMD:C_1206_3216Metric", "LCSC Part": "C12891"}),
    ("C26", {"Value": "22uF 25V", "Footprint": "Capacitor_SMD:C_1206_3216Metric", "LCSC Part": "C12891"}),
    ("C29", {"Value": "220uF 16V"}),
    ("R44", {"Value": "10mR 1% 3W", "LCSC Part": "C2903468"}),
    ("C34", {"Value": "22uF 25V", "LCSC Part": "C45783"}),
    ("C35", {"Value": "22uF 25V", "LCSC Part": "C45783"}),
    ("C36", {"Value": "22uF 25V", "LCSC Part": "C45783"}),
    ("C42", {"Value": "22uF 25V", "LCSC Part": "C45783"}),
    ("SW1", {"Value": "BOOST (row i v7)"}),
    ("J7", {"Footprint": "{}:{}".format(FP_LIB, J7_FP_NAME)}),
]
# Power symbols retargeted from +3.3V to +3.3V_BUS (bus loads), and +5V -> +5V_CORE (D5).
TO_BUS = {(TCA, "#PWR014"): "R6", (TCA, "#PWR029"): "R29", (TCA, "#PWR030"): "R28 / I2C_PU_RAIL",
          ("root", "#PWR031"): "J4", ("root", "#PWR013"): "J6", ("root", "#PWR016"): "J5",
          ("root", "#PWR015"): "TCA VCC_3V3"}
TO_CORE = {("root", "#PWR02"): "ESP32 sheet +5V (D5)"}
# New power symbols / flags: (sheet, ref, lib_id, value, point)
NEW_POWER = [
    (PWR, "#PWR101", "power:+3.3V", "+3.3V_BUS", (21.59, 96.52)),     # U7.4 stub end
    (PWR, "#PWR102", "power:+5V", "+5V_CORE", (223.52, 52.07)),       # U8.3 stub end
    ("root", "#PWR103", "power:+3.3V", "+3.3V_BUS", (143.51, 55.88)),  # ESP32 sheet pin label (J10.4)
    (LED, "#FLG101", "power:PWR_FLAG", "PWR_FLAG", (182.88, 102.87)),   # +5V_TO_LEDS hlabel point
]
# ERC: +5V and +3.3V_MCU lost their root PWR_FLAGs to +5V_CORE / +3.3V_BUS (FLG01, FLG03), and the
# TCA sheet's I2C_PU_RAIL labels now sit on the +3.3V_BUS power net (multiple_net_names).
ERC_FLAGS = [
    (PWR, "#FLG102", "power:PWR_FLAG", "PWR_FLAG", (147.32, 124.46)),   # R39.1 stub end, +5V
    (PWR, "#FLG103", "power:PWR_FLAG", "PWR_FLAG", (105.41, 158.75)),   # R38.2 stub end, +3.3V_MCU
]
RAIL_LABEL = ("I2C_PU_RAIL", "+3.3V_BUS")
# LED sheet: F1 pin 2 wire to the C7/R27 junction.
F1_WIRE = ((140.97, 102.87), (147.32, 102.87))

# Jumper positions (pairs of pins joined by a shunt / bridge / closed link).
LINKS = [("R63.1", "R63.2"), ("R64.1", "R64.2"), ("R65.1", "R65.2"), ("R66.1", "R66.2")]
BATT_ON = [("F3.1", "F3.2"), ("Q20.1", "Q20.5"), ("Q21.1", "Q21.5")]   # SW4 ON, fuse intact
ROW = {
    "c": ([("JP30.1", "JP30.2")], [("JP30.2", "JP30.3")]),
    "h": (LINKS, LINKS),
    "i": ([("JP31.1", "JP31.2")], [("JP31.2", "JP31.3")]),
    "j": ([("JP32.1", "JP32.2")], [("JP32.2", "JP32.3"), ("JP33.1", "JP33.2")]),
    "k": ([("JP34.1", "JP34.2")], [("JP34.2", "JP34.3")]),
    "l": ([("JP35.1", "JP35.2")], [("JP35.1", "JP35.2")]),
}
V8_SHORTS = [s for r in ROW.values() for s in r[0]] + BATT_ON
V7_SHORTS = [s for r in ROW.values() for s in r[1]] + BATT_ON
# v7 side of the battery exception: BT1/Q2/R33/R34 dropped, Q2 conducting.
V7_SIDE_DROP = V7_REMOVED
V7_SIDE_SHORTS = [("Q2.2", "Q2.3")]


def load_spec():
    spec = json.loads(SPEC.read_text())
    return [c for c in spec["components"] if "ref" in c]


def new_parts():
    """Spec parts that are new in v8 (no v7_ref), with their sheet and a grid position."""
    parts = [c for c in load_spec() if not c.get("v7_ref")]
    pwr_main = [c for c in parts if c.get("sheet", PWR) == PWR and not c["ref"].startswith("TP")]
    pwr_tp = [c for c in parts if c.get("sheet", PWR) == PWR and c["ref"].startswith("TP")]
    led = [c for c in parts if c.get("sheet") == LED]
    out = []
    for i, c in enumerate(pwr_main):      # right of the v7 drawing: 5 columns x 9 rows
        out.append((PWR, c, (round(304.8 + 25.4 * (i // 9), 2), round(25.4 + 22.86 * (i % 9), 2))))
    for i, c in enumerate(pwr_tp):        # below it: signal + GND pairs, 20 per row
        out.append((PWR, c, (round(25.4 + 12.7 * (i % 20), 2), round(210.82 + 25.4 * (i // 20), 2))))
    for i, c in enumerate(led):           # LED sheet, below the v7 drawing
        out.append((LED, c, (round(127.0 + 15.24 * i, 2), 160.02)))
    if len(pwr_main) > 45 or len(pwr_tp) > 60:
        raise RuntimeError("grid too small")
    return out


NEW_REFS = tuple(c["ref"] for _, c, _ in new_parts())


def write_j7_footprint():
    text = J7_V7_FP.read_text()
    n = 0
    for pad in ("1", "2", "3", "4"):
        text, k = re.subn(r"\(pad {} thru_hole oval".format(pad), '(pad "0" thru_hole oval', text)
        n += k
    if n != 4:
        raise RuntimeError("J7 footprint: expected 4 shell pads, renamed {}".format(n))
    text = re.sub(r"\(footprint \"?[^\s\"]+\"?", '(footprint "{}"'.format(J7_FP_NAME), text, count=1)
    text = re.sub(r"\(module \"?[^\s\"]+\"?", '(module "{}"'.format(J7_FP_NAME), text, count=1)
    FP_DIR.mkdir(parents=True, exist_ok=True)
    (FP_DIR / (J7_FP_NAME + ".kicad_mod")).write_text(text)
    table = KICAD / "fp-lib-table"
    t = table.read_text()
    if '(name "{}")'.format(FP_LIB) not in t:
        row = ('  (lib (name "{}")(type "KiCad")(uri "${{KIPRJMOD}}/libraries/footprints/{}.pretty")'
               '(options "")(descr "v8-only footprints (Phase 10)"))\n').format(FP_LIB, FP_LIB)
        t = t.rstrip().rstrip(")") + row + ")\n"
        table.write_text(t)
    return n


def apply() -> int:
    docs = modify.load_project(ROOT)
    pwr, led, root = docs.sheet(PWR), docs.sheet(LED), docs.sheet("root")
    if modify.find_component(pwr, "U10") is not None:
        print("Refusing: U10 already on {} (already applied)".format(PWR))
        return 1
    all_refs = set()
    for d in docs.by_key.values():
        all_refs |= modify._all_ref_set(d.schematic)
    taken = [r for r in NEW_REFS + tuple(p[1] for p in NEW_POWER) if r in all_refs]
    if taken:
        raise RuntimeError("references already used: {}".format(taken))

    pwr.schematic.paper.paperSize = "A3"
    print("{}: paper A4 -> A3".format(PWR))
    for ref in V7_REMOVED:
        print("  removed {} (labels {})".format(ref, modify.remove_component_with_stubs(pwr, ref)))
    for ref, pin, net in PIN_MOVES:
        print("  " + modify.set_pin_net(pwr, ref, pin, net))
    for ref, props in PROPS:
        for k, v in props.items():
            print("  " + modify.set_property(pwr, ref, k, v))
    print("  J7 footprint: {} shell pads renumbered '0' in {}".format(write_j7_footprint(), FP_DIR.name))

    print("Rails")
    for key, d in docs.by_key.items():
        for sym in d.schematic.schematicSymbols:
            ref = modify._symbol_ref(sym)
            if not ref.startswith("#PWR"):
                continue
            val = [p for p in sym.properties if p.key == "Value"][0]
            if (key, ref) in TO_BUS:
                assert val.value == "+3.3V", (key, ref, val.value)
                val.value = "+3.3V_BUS"
                print("  {} {} +3.3V -> +3.3V_BUS ({})".format(key, ref, TO_BUS[(key, ref)]))
            elif (key, ref) in TO_CORE:
                assert val.value == "+5V", (key, ref, val.value)
                val.value = "+5V_CORE"
                print("  {} {} +5V -> +5V_CORE ({})".format(key, ref, TO_CORE[(key, ref)]))
            elif val.value == "+3.3V":
                val.value = "+3.3V_MCU"
                print("  {} {} +3.3V -> +3.3V_MCU".format(key, ref))
    for key, old, new in ((PWR, "+3.3V", "+3.3V_MCU"), (MCU, "+3.3V", "+3.3V_MCU"), (MCU, "+5V", "+5V_CORE")):
        s = docs.sheet(key).schematic
        n = 0
        for l in s.labels:
            if l.text == old:
                l.text = new
                n += 1
        h = modify.rename_hlabel(docs.sheet(key), old, new)
        ok = modify.rename_sheet_pin(root, key, old, new)
        print("  {}: {} labels, {} hlabels, sheet pin {} {} -> {}".format(key, n, h, "renamed" if ok else "MISSING",
                                                                            old, new))
    for sheet, ref, lib_id, value, pt in NEW_POWER:
        modify.add_power_symbol(docs.sheet(sheet), mcu.stock_symbol(lib_id), lib_id, ref, value, pt, PROJECT)
        print("  {} {} {} at {}".format(sheet, ref, value, pt))

    print("LED sheet: link h4 after F1")
    if not modify.remove_wire_between(led, *F1_WIRE, tolerance=0.05):
        raise RuntimeError("F1 pin 2 wire not found")
    modify.add_local_label(led, "+5V_LED_H4", F1_WIRE[1], 0)
    print("  " + modify.set_pin_net(led, "F1", "2", "+5V_LED_F"))
    print("  label +5V_LED_H4 at the C7/R27 junction {}".format(F1_WIRE[1]))

    print("New parts")
    cache = {}
    for sheet, c, pos in new_parts():
        doc = docs.sheet(sheet)
        lib_id = c["lib_id"]
        if lib_id not in cache:
            cache[lib_id] = mcu.stock_symbol(lib_id)
        modify.add_component(doc, lib_symbol=cache[lib_id], lib_id=lib_id, ref=c["ref"], value=c["value"],
                             footprint=c["footprint"], lcsc_part=c.get("lcsc", ""), position=pos,
                             pin_nets=c["pins"], project_name=PROJECT)
        for p in c.get("no_connect", []):
            modify.add_no_connect(doc, modify.pin_position(doc, c["ref"], p)[0])
        if c.get("dnp"):
            sym = modify.find_component(doc, c["ref"])
            sym.dnp = True
            sym.inBom = False
        print("  {:6s} {:5s} {:22s} {}: {}".format(sheet[:6], c["ref"], c["value"], pos, c["pins"]))
    erc_fixes(docs)
    docs.save_all()
    print("Saved.")
    return check()


def erc_fixes(docs) -> None:
    for sheet, ref, lib_id, value, pt in ERC_FLAGS:
        modify.add_power_symbol(docs.sheet(sheet), mcu.stock_symbol(lib_id), lib_id, ref, value, pt, PROJECT)
        print("  {} {} at {}".format(sheet, ref, pt))
    n = 0
    for l in docs.sheet(TCA).schematic.labels:
        if l.text == RAIL_LABEL[0]:
            l.text = RAIL_LABEL[1]
            n += 1
    print("  {}: {} labels {} -> {}".format(TCA, n, *RAIL_LABEL))


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

GLOBAL = {"GND", "+5V", "+5V_CORE", "+3.3V_MCU", "+3.3V_BUS"}


def expected():
    exp = {}
    for c in load_spec():
        for pin, net in c["pins"].items():
            exp["{}.{}".format(c["ref"], pin)] = net
    exp.update({
        "U3.2": "+3.3V_MCU", "R50.1": "+3.3V_MCU", "R51.1": "+3.3V_MCU",
        "U4.24": "+3.3V_BUS", "C9.2": "+3.3V_BUS", "C10.2": "+3.3V_BUS", "R6.2": "+3.3V_BUS",
        "J4.1": "+3.3V_BUS", "J5.1": "+3.3V_BUS", "J6.1": "+3.3V_BUS", "J10.4": "+3.3V_BUS",
        "R28.2": "+3.3V_BUS", "R29.2": "+3.3V_BUS", "R86.2": "+3.3V_BUS", "R90.2": "+3.3V_BUS",
        "D5.2": "+5V_CORE", "IC1.5": "+5V_TO_LEDS", "C8.2": "+5V_TO_LEDS", "J3.1": "+5V_TO_LEDS",
        "TP1.1": "VSYS", "TP2.1": "VBAT", "TP3.1": "Protected_VBUS", "TP4.1": "GND",
        "U9.5": "Protected_VBUS", "U9.1": "USB_DP", "U9.3": "USB_DN",
    })
    # R1.2 (D1's resistor) was on +3.3V_MCU here; Phase 11 puts it behind the D1 load jumper JP40
    # (v8_debug_sheet.py checks R1.2 = LED_D1_SJ and that JP40 closed joins it to +3.3V_MCU).
    return exp


def check() -> int:
    import v8_bus_sheet as bus
    fails = bus.check() != 0
    print("=== Phase 10 check (power sheet; rows c, h, i, j, k, l) ===")
    with tempfile.TemporaryDirectory() as td:
        pin_net, nets, comps = mcu.netlist(ROOT, Path(td) / "v8.xml")
    bad = 0
    exp = expected()
    for key, want in sorted(exp.items()):
        got = bus._short(pin_net.get(key))
        full = pin_net.get(key) or ""
        if got != want or (want in GLOBAL and full != want):
            bad += 1
            print("  BAD {:8s} {}  (want {})".format(key, full, want))
    for c in load_spec():
        for p in c.get("no_connect", []):
            got = pin_net.get("{}.{}".format(c["ref"], p))
            if got is not None and not got.startswith("unconnected-"):
                bad += 1
                print("  BAD {}.{} should be no-connect, is {}".format(c["ref"], p, got))
    for ref in V7_REMOVED:
        if any(k.startswith(ref + ".") for k in pin_net):
            bad += 1
            print("  BAD {} still in the netlist".format(ref))
    print("Pin -> net: {} pins checked, {} wrong".format(len(exp), bad))
    fails += bad

    base = mcu.V8_SHORTS + bus.V8_SHORTS + V8_SHORTS
    g = lambda shorts: bus._groups(nets, pin_net, shorts)   # noqa: E731
    of = bus._group_of

    def without(row):
        return [s for s in base if s not in ROW[row][0]]
    v8 = g(base)
    facts = [
        ("c v8 (JP30 1-2): bus rail from U10, not U8", "U10.5" in of(v8, "U4.24") and "U8.2" not in of(v8, "U4.24")),
        ("c v8: MCU rail from U8 via h1", "U8.2" in of(v8, "U3.2")),
        ("c v7 (JP30 2-3): U8 feeds U3 and the bus loads",
         {"U3.2", "U4.24", "R28.2", "U7.4", "J4.1"} <= of(g(without("c") + ROW["c"][1]), "U8.2")),
        ("c no shunt: no regulator on the bus rail",
         not ({"U8.2", "U10.5"} & of(g(without("c")), "U4.24"))),
        ("h1 lifted (R63 open): U3 off U8", "U3.2" not in of(g([s for s in base if s != ("R63.1", "R63.2")]), "U8.2")),
        ("h4 lifted (R66 open): J3 off F1", "F1.2" not in of(g([s for s in base if s != ("R66.1", "R66.2")]), "J3.1")),
        ("h3 closed: U8 input on boost +5V", "U6.14" in of(v8, "U8.3")),
        ("i v8 (JP31 1-2): BOOST_EN on VSYS_SENSE", "U6.9" in of(v8, "U6.2")),
        ("i v7 (JP31 2-3): BOOST_EN on SW1 common only",
         of(g(without("i") + ROW["i"][1]), "U6.2") >= {"SW1.2", "R2.1"}
         and "U6.9" not in of(g(without("i") + ROW["i"][1]), "U6.2")),
        ("j v8 (JP32 1-2): D+ shorted to D-, not GND", "U5.3" in of(v8, "U5.2") and "U3.1" not in of(v8, "U5.2")),
        ("j v7 (JP32 2-3, JP33 closed): D+ and D- on GND",
         {"U5.2", "U5.3", "U3.1"} <= of(g(without("j") + ROW["j"][1]), "U5.2")),
        ("k v8 (JP34 1-2): R35 pull-up from REGN", "U5.22" in of(v8, "R35.2")),
        ("k v7 (JP34 2-3): R35 pull-up from +3.3V_MCU", "U3.2" in of(g(without("k") + ROW["k"][1]), "R35.2")),
        ("l default (JP35 1-2): TS on TH1", "TH1.1" in of(v8, "U5.11") and "J9.1" not in of(v8, "U5.11")),
        ("l alternate (JP35 2-3): TS on J9", "J9.1" in of(g(without("l") + [("JP35.2", "JP35.3")]), "U5.11")),
        ("battery SW4 ON: J8 + reaches U5 BAT", "J8.2" in of(v8, "U5.13")),
        ("battery: SW4 throw 1 on GND, R61 to SW4 common", "U3.1" in of(v8, "SW4.1") and "R61.2" in of(v8, "SW4.2")),
        ("U10 EN on +3.3V_MCU (after h1)", "U3.2" in of(v8, "U10.3")),
    ]
    for text, ok in facts:
        fails += not ok
        print("  {} {}".format("ok " if ok else "BAD", text))
    print("Power nets (v8 default positions; jumper pins and test points omitted):")
    seen = set()
    for net in json.loads(SPEC.read_text())["nets"]:
        key = [k for k, v in exp.items() if v == net]
        if not key or net == "GND":
            continue
        grp = of(v8, key[0])
        fs = frozenset(grp)
        if fs in seen:
            continue
        seen.add(fs)
        names = sorted({bus._short(pin_net[m]) for m in grp})
        print("  {:34s} {}".format("/".join(names), sorted(m for m in grp if not m.startswith(("TP", "JP", "J3")))))
    print("PHASE 10 CHECK {}".format("PASSED" if fails == 0 else "FAILED ({} problems)".format(fails)))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--erc-fixes", action="store_true",
                    help="one-off: the ERC fixes on a sheet where --apply ran before they were added")
    args = ap.parse_args()
    if args.apply:
        return apply()
    if args.erc_fixes:
        docs = modify.load_project(ROOT)
        if modify.find_component(docs.sheet(PWR), "#FLG102") is not None:
            print("Refusing: ERC fixes already applied")
            return 1
        erc_fixes(docs)
        docs.save_all()
        return check()
    if args.check:
        return check()
    print(__doc__)
    for sheet, c, pos in new_parts():
        print("{:6s} {:5s} {:22s} {} {}".format(sheet[:6], c["ref"], c["value"], pos, c["pins"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
