#!/usr/bin/env python3
"""
v8_debug_sheet.py - v8 debug board, debug features (Phase 11).

Initiative: docs/initiatives/v8-debug-board. Design intent: hardware/pcb-main-v8/CONTEXT.md ->
Test points (I2C master side, MCU and control, Headers, Debug LEDs), GPIO allocation, Parts
(Debug LEDs, Headers, Footprints).

Edits (all label-style, through modify.py helpers; KiCad must be closed during --apply):
  motion-play-main-v8.kicad_sch (root)
    - The v7 test points TPIO43 / TPIO44 / TPIO16 sit on I2C_SDA / I2C_SCL / LED_DATA, which on
      v8 are no longer GPIO43/44/16's own nets. They are renamed TP110 / TP111 / TP112 (value =
      net name), so that on v8 "TPIO<n>" always means GPIO n's own pad. The new TPIO43/44/16 sit
      on U3_IO43/44/16 (ESP32 sheet). The v7 comparison maps v7 TPIO43/44/16 to TP110/111/112.
    - Ground points for TP110-TP112, TPIO10, TPIO21.
  esp32_s3.kicad_sch (paper A4 -> A3; new parts in a grid below the v7 drawing)
    - U3 pins to new label nets: spare GPIOs 1, 2, 4-9, 14, 17, 38-42 (U3_IO<n>) to the spare
      GPIO header J12 (2x15, odd = signal, even = GND); strap pads GPIO3/45/46 (U3_IO3/45/46,
      TestPoint_Pad_D1.0mm only); GPIO47/48 -> DBG1/DBG2 debug LEDs (470 R, blue D14 / white D15).
    - Test points TPIO43, TPIO44, TPIO16, TPIO15 (U3 pad side of row a), TPIO0 (GPIO0_BOOT),
      TP113 (EN), TPIO13/12/11 (INT1-3), TPIO3/45/46 (strap pads), each with its own GND point.
    - UART0 header J11 (1x4: GND, UART0_TX, UART0_RX, NC). Clears the two dangling-label ERC errors.
  tca9548A_subsystem.kicad_sch
    - Test points TP114 / TP115 on BQ_SDA / BQ_SCL (U5 side of row f), each with a GND point.
  power_management.kicad_sch
    - D1 (+3.3V_MCU LED, kept): R1 pin 2 -> LED_D1_SJ, with JP40 (SJ2, factory-bridged) to +3.3V_MCU.
    - Rail LEDs, each rail -> SJ2 (bridged) -> R -> LED -> GND: D11 green "BUS" on +3.3V_BUS
      (JP41, R100 1k), D12 yellow on +5V (JP42, R101 3.3k), D13 red on Protected_VBUS (JP43, R102 3.3k).

Jumper positions: the LED SJ2s are closed by default (v8). v7 position: JP40 closed (v7 had D1),
JP41-JP43 cut (v7 had no such LEDs).

Usage:
  python3 tools/schematic-modify/v8_debug_sheet.py            # dry run: print the plan
  python3 tools/schematic-modify/v8_debug_sheet.py --apply    # edit (refuses if J11 exists)
  python3 tools/schematic-modify/v8_debug_sheet.py --check    # Phase 8-10 checks + Phase 11 pins,
                                                              # BOM audit, ERC summary
  python3 tools/schematic-modify/v8_debug_sheet.py --annotate # ai_* properties on the v8 parts
                                                              # (Phases 8-11), via annotate.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modify  # noqa: E402
import v8_mcu_sheet as mcu  # noqa: E402

REPO = mcu.REPO
ROOT = mcu.ROOT
PROJECT = mcu.PROJECT
MCU = mcu.MCU
TCA = "tca9548A_subsystem.kicad_sch"
PWR = "power_management.kicad_sch"

TP_SIG = "TestPoint:TestPoint_Pad_D1.5mm"
TP_GND = "TestPoint:TestPoint_Pad_2.5x2.5mm"
TP_STRAP = "TestPoint:TestPoint_Pad_D1.0mm"
SJ2_BRIDGED = "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"
R0603 = "Resistor_SMD:R_0603_1608Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
HDR_1X4 = mcu.HDR_1X4
HDR_2X15 = "Connector_PinHeader_2.54mm:PinHeader_2x15_P2.54mm_Vertical"
L_TP = "Connector:TestPoint"
L_R = "Device:R"
L_LED = "Device:LED"
L_SJ2B = "Jumper:SolderJumper_2_Bridged"
L_1X4 = "Connector_Generic:Conn_01x04"
L_2X15 = "Connector_Generic:Conn_02x15_Odd_Even"

# Root test points renamed (v7 ref -> v8 ref, value).
RENAMES = {"TPIO43": ("TP110", "I2C_SDA"), "TPIO44": ("TP111", "I2C_SCL"), "TPIO16": ("TP112", "LED_DATA")}
V7_REF_RENAME = {old: new for old, (new, _) in RENAMES.items()}

# GPIO allocation: spare GPIO -> U3 module pin (WROOM-1 pinout, U3 symbol pin names checked).
SPARE = [(1, "39"), (2, "38"), (4, "4"), (5, "5"), (6, "6"), (7, "7"), (8, "12"), (9, "17"),
         (14, "22"), (17, "10"), (38, "31"), (39, "32"), (40, "33"), (41, "34"), (42, "35")]
STRAP = [(3, "15"), (45, "26"), (46, "16")]
DBG = [("DBG1", "24", "R103", "D14", "blue DBG1", "C2288"), ("DBG2", "25", "R104", "D15", "white DBG2", "C2290")]
U3_PIN_NETS = ([(pin, "U3_IO{}".format(g)) for g, pin in SPARE + STRAP] + [(d[1], d[0]) for d in DBG])
U3_PINS_USED = tuple(p for p, _ in U3_PIN_NETS)   # v8_mcu_sheet's U3_UNUSED check skips these

# Signal test points: (sheet, ref, net, footprint).
SIG_TPS = [
    (MCU, "TPIO43", "U3_IO43", TP_SIG), (MCU, "TPIO44", "U3_IO44", TP_SIG),
    (MCU, "TPIO16", "U3_IO16", TP_SIG), (MCU, "TPIO15", "U3_IO15", TP_SIG),
    (MCU, "TPIO0", "GPIO0_BOOT", TP_SIG), (MCU, "TP113", "EN", TP_SIG),
    (MCU, "TPIO13", "INT1", TP_SIG), (MCU, "TPIO12", "INT2", TP_SIG), (MCU, "TPIO11", "INT3", TP_SIG),
    (MCU, "TPIO3", "U3_IO3", TP_STRAP), (MCU, "TPIO45", "U3_IO45", TP_STRAP),
    (MCU, "TPIO46", "U3_IO46", TP_STRAP),
    (TCA, "TP114", "BQ_SDA", TP_SIG), (TCA, "TP115", "BQ_SCL", TP_SIG),
]
# Signal test points that get only a ground point here (they already exist): root sheet.
ROOT_TPS = ["TP110", "TP111", "TP112", "TPIO10", "TPIO21"]

# Rail LEDs (power sheet): (rail, SJ ref, R ref, R value, R lcsc, LED ref, LED value, LED lcsc, mid nets)
RAIL_LEDS = [
    ("+3.3V_BUS", "JP41", "R100", "1k", "C21190", "D11", "green BUS", "C19171301"),
    ("+5V", "JP42", "R101", "3.3k", "C22978", "D12", "yellow +5V", "C2287"),
    ("Protected_VBUS", "JP43", "R102", "3.3k", "C22978", "D13", "red VBUS", "C2286"),
]
D1_SJ = ("JP40", "+3.3V_MCU", "LED_D1_SJ")   # R1 pin 2 moves to LED_D1_SJ


def build_parts():
    """(sheet, ref, lib_id, value, footprint, lcsc, position, pin_nets, no_connect_pins)."""
    parts = []
    gnd_n = 130
    pair = {}
    # ESP32 sheet (A3): row 1 = test points + GND points, rows 2-3 = LEDs, headers.
    mcu_tps = [t for t in SIG_TPS if t[0] == MCU]
    for i, (sheet, ref, net, fp) in enumerate(mcu_tps):
        x = round(25.4 + 25.4 * (i % 12), 2)
        y = round(172.72 + 22.86 * (i // 12), 2)
        value = "STRAP " + net if fp == TP_STRAP else net
        parts.append((sheet, ref, L_TP, value, fp, "", (x, y), {"1": net}, ()))
        g = "TP{}".format(gnd_n)
        parts.append((sheet, g, L_TP, "GND", TP_GND, "", (round(x + 10.16, 2), y), {"1": "GND"}, ()))
        pair[g] = ref
        gnd_n += 1
    for k, (net, _, r, d, dval, dlcsc) in enumerate(DBG):
        x0 = round(25.4 + 50.8 * k, 2)
        parts.append((MCU, r, L_R, "470", R0603, "C23179", (x0, 220.98), {"1": net, "2": net + "_A"}, ()))
        parts.append((MCU, d, L_LED, dval, LED0603, dlcsc, (round(x0 + 20.32, 2), 220.98),
                      {"2": net + "_A", "1": "GND"}, ()))
    parts.append((MCU, "J11", L_1X4, "UART0", HDR_1X4, "C2691448", (139.7, 220.98),
                  {"1": "GND", "2": "UART0_TX", "3": "UART0_RX"}, ("4",)))
    j12 = {}
    for i, (g, _) in enumerate(SPARE):
        j12[str(2 * i + 1)] = "U3_IO{}".format(g)
        j12[str(2 * i + 2)] = "GND"
    parts.append((MCU, "J12", L_2X15, "SPARE GPIO", HDR_2X15, "C22465939", (215.9, 233.68), j12, ()))
    # TCA sheet: BQ_SDA / BQ_SCL test points.
    for i, (sheet, ref, net, fp) in enumerate(t for t in SIG_TPS if t[0] == TCA):
        x = round(45.72 + 25.4 * i, 2)
        parts.append((sheet, ref, L_TP, net, fp, "", (x, 259.08), {"1": net}, ()))
        g = "TP{}".format(gnd_n)
        parts.append((sheet, g, L_TP, "GND", TP_GND, "", (round(x + 10.16, 2), 259.08), {"1": "GND"}, ()))
        pair[g] = ref
        gnd_n += 1
    # Root sheet: GND points for the existing test points.
    for i, ref in enumerate(ROOT_TPS):
        g = "TP{}".format(gnd_n)
        parts.append(("root", g, L_TP, "GND", TP_GND, "", (round(40.64 + 20.32 * i, 2), 144.78), {"1": "GND"}, ()))
        pair[g] = ref
        gnd_n += 1
    # Power sheet: rail LEDs and D1's SJ2.
    for k, (rail, sj, r, rval, rlcsc, d, dval, dlcsc) in enumerate(RAIL_LEDS):
        y = round(233.68 + 17.78 * k, 2)
        tag = "LED_{}".format(d)
        parts.append((PWR, sj, L_SJ2B, "LED load {}".format(d), SJ2_BRIDGED, "", (289.56, y),
                      {"1": rail, "2": tag + "_SJ"}, ()))
        parts.append((PWR, r, L_R, rval, R0603, rlcsc, (309.88, y), {"1": tag + "_SJ", "2": tag + "_A"}, ()))
        parts.append((PWR, d, L_LED, dval, LED0603, dlcsc, (330.2, y), {"2": tag + "_A", "1": "GND"}, ()))
    sj, rail, mid = D1_SJ
    parts.append((PWR, sj, L_SJ2B, "LED load D1", SJ2_BRIDGED, "", (355.6, 233.68), {"1": rail, "2": mid}, ()))
    return parts, pair


PARTS, GND_PAIR = build_parts()
NEW_REFS = tuple(p[1] for p in PARTS)
V8_SHORTS = [("{}.1".format(p[1]), "{}.2".format(p[1])) for p in PARTS if p[2] == L_SJ2B]
V7_SHORTS = [("JP40.1", "JP40.2")]


def rename_ref(doc, old, new, value):
    sym = modify.find_component(doc, old)
    if sym is None:
        raise ValueError("{} not on {}".format(old, doc.path.name))
    for p in sym.properties:
        if p.key == "Reference":
            p.value = new
        elif p.key == "Value":
            p.value = value
    for inst in sym.instances:
        for path in inst.paths:
            if path.reference == old:
                path.reference = new


def apply() -> int:
    import v8_bus_sheet as bus
    docs = modify.load_project(ROOT)
    mcu_doc, root = docs.sheet(MCU), docs.sheet("root")
    if modify.find_component(mcu_doc, "J11") is not None:
        print("Refusing: J11 already on {} (already applied)".format(MCU))
        return 1
    all_refs = set()
    for d in docs.by_key.values():
        all_refs |= modify._all_ref_set(d.schematic)
    after_rename = (all_refs - set(RENAMES)) | {v[0] for v in RENAMES.values()}
    taken = [r for r in NEW_REFS if r in after_rename]
    if taken:
        raise RuntimeError("references already used: {}".format(taken))

    print("Root: rename test points")
    for old, (new, value) in RENAMES.items():
        rename_ref(root, old, new, value)
        print("  {} -> {} ({})".format(old, new, value))

    mcu_doc.schematic.paper.paperSize = "A3"
    print("{}: paper A4 -> A3".format(MCU))
    for pin, net in U3_PIN_NETS:
        print("  " + modify.set_pin_net(mcu_doc, "U3", pin, net))

    print("{}: D1 load jumper".format(PWR))
    print("  " + modify.set_pin_net(docs.sheet(PWR), "R1", "2", D1_SJ[2]))

    print("New parts")
    cache = {}
    for sheet, ref, lib_id, value, fp, lcsc, pos, nets, nc in PARTS:
        doc = docs.sheet(sheet)
        bus._check_free(doc, pos, (7.0, 7.0) if lib_id != L_2X15 else (10.0, 21.0), ref, symbols=False)
        bus._check_free(doc, pos, (2.0, 2.0) if lib_id != L_2X15 else (5.0, 18.0), ref)
        if lib_id not in cache:
            cache[lib_id] = mcu.stock_symbol(lib_id)
        modify.add_component(doc, lib_symbol=cache[lib_id], lib_id=lib_id, ref=ref, value=value, footprint=fp,
                             lcsc_part=lcsc, position=pos, pin_nets=nets, project_name=PROJECT)
        for p in nc:
            modify.add_no_connect(doc, modify.pin_position(doc, ref, p)[0])
        print("  {:6s} {:6s} {:16s} {}: {}".format(sheet[:6], ref, value, pos, nets if len(nets) < 5 else
                                                   "{} pins".format(len(nets))))
    docs.save_all()
    print("Saved.")
    return check()


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

def expected():
    exp = {}
    for sheet, ref, lib_id, value, fp, lcsc, pos, nets, nc in PARTS:
        for pin, net in nets.items():
            exp["{}.{}".format(ref, pin)] = net
    for pin, net in U3_PIN_NETS:
        exp["U3.{}".format(pin)] = net
    exp.update({"TP110.1": "I2C_SDA", "TP111.1": "I2C_SCL", "TP112.1": "LED_DATA",
                "TPIO10.1": "TCA_RESET", "TPIO21.1": "CHRG_INT", "R1.2": "LED_D1_SJ", "D1.2": "Net-(D1-A)",
                "JP1.4": "UART0_TX", "JP2.4": "UART0_RX"})
    return exp


COPPER_ONLY = ("TestPoint:", "Jumper:SolderJumper")


def bom_audit(comps_xml):
    """Every placed part: footprint, and an LCSC number unless it is copper only (test point,
    solder jumper). Returns the list of problems."""
    root = comps_xml
    bad = []
    for c in root.find("components"):
        ref = c.get("ref")
        fp = c.findtext("footprint") or ""
        fields = {f.get("name"): (f.text or "") for f in (c.find("fields") or [])}
        lcsc = fields.get("LCSC Part") or fields.get("LCSC") or ""
        if not fp:
            bad.append("{}: no footprint".format(ref))
        elif not lcsc and not fp.startswith(COPPER_ONLY):
            bad.append("{}: no LCSC ({})".format(ref, fp))
    return bad


def erc_summary():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "erc.json"
        subprocess.run([mcu.KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", str(out),
                        str(ROOT)], capture_output=True, text=True)
        data = json.loads(out.read_text())
    counts = {}
    items = []
    for sheet in data.get("sheets", []):
        for v in sheet.get("violations", []):
            key = (v.get("severity"), v.get("type"))
            counts[key] = counts.get(key, 0) + 1
            items.append((sheet.get("path"), v))
    return counts, items


def check() -> int:
    import xml.etree.ElementTree as ET
    import v8_bus_sheet as bus
    import v8_power_sheet as pwr
    fails = pwr.check() != 0
    print("=== Phase 11 check (test points, ground points, debug LEDs, UART0 and spare headers) ===")
    with tempfile.TemporaryDirectory() as td:
        pin_net, nets, comps = mcu.netlist(ROOT, Path(td) / "v8.xml")
        xml_root = ET.parse(str(Path(td) / "v8.xml")).getroot()
    bad = 0
    exp = expected()
    for key, want in sorted(exp.items()):
        got = bus._short(pin_net.get(key))
        if got != want:
            bad += 1
            print("  BAD {:9s} {}  (want {})".format(key, pin_net.get(key), want))
    got = pin_net.get("J11.4")
    if got is not None and not got.startswith("unconnected-"):
        bad += 1
        print("  BAD J11.4 should be no-connect, is {}".format(got))
    for old in RENAMES:
        if any(k.startswith(old + ".") and pin_net[k] in ("/I2C_SDA", "/I2C_SCL", "/LED_DATA") for k in pin_net):
            bad += 1
            print("  BAD {} still on a bus/LED net".format(old))
    print("Pin -> net: {} pins checked, {} wrong".format(len(exp), bad))
    fails += bad

    base = mcu.V8_SHORTS + bus.V8_SHORTS + pwr.V8_SHORTS + V8_SHORTS
    g = lambda shorts: bus._groups(nets, pin_net, shorts)   # noqa: E731
    of = bus._group_of
    v8 = g(base)
    no_jp41 = g([s for s in base if s != ("JP41.1", "JP41.2")])
    facts = [
        ("D1 load on +3.3V_MCU via JP40 (closed)", "R1.2" in of(v8, "U3.2")),
        ("JP40 cut: D1 off +3.3V_MCU", "R1.2" not in of(g([s for s in base if s != ("JP40.1", "JP40.2")]), "U3.2")),
        ("BUS LED on +3.3V_BUS via JP41", "R100.1" in of(v8, "U4.24")),
        ("JP41 cut: BUS LED off +3.3V_BUS", "R100.1" not in of(no_jp41, "U4.24")),
        ("+5V LED on the boost output", "R101.1" in of(v8, "U6.14")),
        ("VBUS LED on Protected_VBUS", "R102.1" in of(v8, "TP3.1")),
        ("v8 default (row a 3-4): UART0 header TX/RX on U3 pins 37/36",
         "U3.37" in of(v8, "J11.2") and "U3.36" in of(v8, "J11.3")),
        ("v7 row a (2-3): J11 TX off U3 and off the bus",
         not ({"U3.37", "U4.23"} & of(g([s for s in base if s not in mcu.V8_SHORTS[:4]] + mcu.V7_SHORTS[:2]),
                                       "J11.2"))),
        ("TPIO43 on U3 pad 37 net; TP110 on the bus", "TPIO43.1" in of(v8, "U3.37") and "TP110.1" in of(v8, "U4.23")),
        ("DBG1 LED on U3 pin 24 (GPIO47), DBG2 on pin 25 (GPIO48)",
         "R103.1" in of(v8, "U3.24") and "R104.1" in of(v8, "U3.25")),
    ]
    gnd = of(v8, "U3.1")
    missing_gnd = [p for p in GND_PAIR if "{}.1".format(p) not in gnd]
    facts.append(("{} new ground points on GND".format(len(GND_PAIR)), not missing_gnd))
    for text, ok in facts:
        fails += not ok
        print("  {} {}".format("ok " if ok else "BAD", text))

    probs = bom_audit(xml_root)
    print("BOM audit ({} parts): {}".format(len(comps), "every part has a footprint, and an LCSC number unless "
                                            "copper only" if not probs else "{} problems".format(len(probs))))
    for p in probs:
        print("  BAD " + p)
    fails += len(probs)

    counts, _ = erc_summary()
    print("ERC (all severities):")
    for (sev, typ), n in sorted(counts.items()):
        print("  {:8s} {:28s} {}".format(sev, typ, n))
    errors = sum(n for (sev, _), n in counts.items() if sev == "error")
    print("  errors: {}".format(errors))
    fails += errors
    print("PHASE 11 CHECK {}".format("PASSED" if fails == 0 else "FAILED ({} problems)".format(fails)))
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# Annotation (ai_* properties) for the parts Phases 8-11 added or changed
# ---------------------------------------------------------------------------

def annotations():
    """ref -> {function, block, role, critical_specs}."""
    import v8_bus_sheet as bus
    import v8_power_sheet as pwr
    ann = {}

    def tp(ref, net, block="test_points", pair=None):
        ann[ref] = {"function": "Test point on {}".format(net), "block": block, "role": "test_point",
                    "critical_specs": "own GND point {}; gap 1.0-3.0 mm copper edge to edge".format(pair)
                    if pair else "own GND point beside it; gap 1.0-3.0 mm copper edge to edge"}

    def gp(ref, of_ref, block="test_points"):
        ann[ref] = {"function": "Ground point for {}".format(of_ref), "block": block, "role": "ground_point",
                    "critical_specs": "2.5x2.5 mm pad, 1.0-3.0 mm edge to edge from {}".format(of_ref)}

    # Phase 8 (MCU sheet)
    for r, line in (("JP1", "SDA"), ("JP2", "SCL")):
        ann[r] = {"function": "Row a {} master selector: 1-2 = GPIO{} (v8), 2-3 = GPIO{} (v7), 3-4 = UART0".format(
            line, "16" if line == "SDA" else "15", "43" if line == "SDA" else "44"),
            "block": "i2c_master_select", "role": "jumper_header",
            "critical_specs": "1x4 2.54 mm; v8 shunts 1-2 + 3-4, v7 one shunt 2-3"}
    ann["J10"] = {"function": "External I2C master header (row e): GND, EXT_SDA, EXT_SCL, +3.3V_BUS sense",
                  "block": "i2c_master_select", "role": "connector", "critical_specs": "1x4 2.54 mm"}
    for r, line in (("JP3", "SDA"), ("JP4", "SCL")):
        ann[r] = {"function": "Row e: joins EXT_{0} to I2C_{0} (open by default)".format(line),
                  "block": "i2c_master_select", "role": "solder_jumper", "critical_specs": "SJ2, open"}
    ann["JP5"] = {"function": "Row g LED_DATA source: pad 1 GPIO18 (v8 default), pad 3 GPIO16 (v7)",
                  "block": "led_data_select", "role": "solder_jumper", "critical_specs": "SJ3, pads 1-2 bridged"}
    ann["IC1"] = {"function": "LED data level shifter 3.3 V -> 5 V (single AHCT gate, replaces v7 quad)",
                  "block": "led_controller", "role": "level_shifter",
                  "critical_specs": "SN74AHCT1G125, VCC +5V_TO_LEDS, OE to GND"}
    # Phase 9 (TCA sheet)
    for _, ref, lib_id, value, fp, lcsc, pos, nets, nc in bus.PARTS:
        if ref.startswith("TP"):
            continue
        if ref.startswith("R8") and int(ref[1:]) <= 85:
            a = ("Row b series resistor {} -> {}".format(nets["1"], nets["2"]), "i2c_channels", "series_resistor",
                 "47 R 0603, between the TCA pin and the connector")
        elif ref.startswith("U1"):
            a = ("Cable-facing TVS on {} / {}".format(nets["3"], nets["5"]), "i2c_channels", "esd_protection",
                 "TPD2E2U06, GND leg via row b header; place at the connector")
        elif ref.startswith("JP") and 10 <= int(ref[2:]) <= 15:
            a = ("Row b bypass across the series R (shunt on = v7)", "i2c_channels", "jumper_header", "1x2 2.54 mm")
        elif ref.startswith("JP") and 16 <= int(ref[2:]) <= 18:
            a = ("Row b TVS GND leg (shunt on = v8)", "i2c_channels", "jumper_header",
                 "1x2 2.54 mm; GND pin on a via at the TVS pad")
        elif ref in ("JP19", "JP20"):
            a = ("Row d upstream pull-up selector: 1-2 2.2k, 3-4 4.7k, 5-6 10k", "i2c_pullups", "jumper_header",
                 "2x3 2.54 mm, odd pins = bus")
        elif ref in ("R86", "R87", "R88", "R89"):
            a = ("Row d upstream pull-up option {}".format(value), "i2c_pullups", "pull_up", "0603 1%")
        elif ref.startswith("JP") and 21 <= int(ref[2:]) <= 26:
            a = ("Row d downstream pull-up enable on {}".format(nets["1"]), "i2c_channels", "solder_jumper",
                 "SJ2, open")
        elif ref.startswith("R9"):
            a = ("Row d downstream 4.7k pull-up on {}".format(nets["1"].replace("_PU", "")), "i2c_channels",
                 "pull_up", "0603 1%")
        elif ref in ("JP27", "JP28"):
            a = ("Row f: BQ24195 on the I2C bus (shunt on, v8 = v7)", "i2c_bus", "jumper_header", "1x2 2.54 mm")
        else:
            continue
        ann[ref] = dict(zip(("function", "block", "role", "critical_specs"), a))
    for t in range(12):
        net = [p for p in bus.PARTS if p[1] == "TP{}".format(80 + t)][0][7]["1"]
        tp("TP{}".format(80 + t), net, "i2c_channels", "TP{}".format(92 + t))
        gp("TP{}".format(92 + t), "TP{}".format(80 + t), "i2c_channels")
    for r in ("R28", "R29"):
        ann[r] = {"function": "Row d upstream 2.2k pull-up (v7 value) via JP19/JP20 1-2", "block": "i2c_pullups",
                  "role": "pull_up", "critical_specs": "2.2k 0603 1%, rail +3.3V_BUS"}
    # Phase 10 (power spec parts; changed v7 parts)
    for c in pwr.load_spec():
        ref = c["ref"]
        if c.get("v7_ref") and not c.get("_phase10") and ref not in dict(pwr.PROPS):
            continue
        if ref.startswith("TP"):
            if c["value"] == "GND":
                gp(ref, c.get("pair_of", "its rail test point"), c["block"])
            else:
                tp(ref, c["pins"]["1"], c["block"], None)
            continue
        ann[ref] = {"function": "{} ({})".format(c.get("note") or c["value"], c["value"]), "block": c["block"],
                    "role": c["lib_id"].split(":")[1].lower(),
                    "critical_specs": "{}, LCSC {}".format(c["value"], c.get("lcsc") or "-")}
    # Phase 11
    pair_of = {v: k for k, v in GND_PAIR.items()}
    for sheet, ref, lib_id, value, fp, lcsc, pos, nets, nc in PARTS:
        if lib_id == L_TP and value != "GND":
            tp(ref, nets["1"], "test_points", pair_of.get(ref))
        elif lib_id == L_TP:
            gp(ref, GND_PAIR[ref])
        elif lib_id == L_SJ2B:
            ann[ref] = {"function": "Rail LED load jumper ({}): cut to remove the LED's ~1 mA".format(value),
                        "block": "debug_leds", "role": "solder_jumper", "critical_specs": "SJ2, factory-bridged"}
        elif lib_id == L_LED:
            ann[ref] = {"function": "Debug LED {}".format(value), "block": "debug_leds", "role": "indicator",
                        "critical_specs": "0603, ~1 mA"}
        elif lib_id == L_R:
            ann[ref] = {"function": "Debug LED series resistor ({})".format(nets["1"]), "block": "debug_leds",
                        "role": "current_limit", "critical_specs": "{} 0603".format(value)}
        elif ref == "J11":
            ann[ref] = {"function": "UART0 header (boot log when the bus is off GPIO43/44): GND, TX, RX, NC",
                        "block": "debug_headers", "role": "connector", "critical_specs": "1x4 2.54 mm, 3.3 V logic"}
        elif ref == "J12":
            ann[ref] = {"function": "Spare GPIO header: odd pins GPIO1,2,4-9,14,17,38-42, even pins GND",
                        "block": "debug_headers", "role": "connector", "critical_specs": "2x15 2.54 mm"}
    for ref in ROOT_TPS:
        net = {"TP110": "I2C_SDA", "TP111": "I2C_SCL", "TP112": "LED_DATA (row g centre)",
               "TPIO10": "TCA_RESET (GPIO10)", "TPIO21": "CHRG_INT (GPIO21)"}[ref]
        tp(ref, net, "test_points", pair_of.get(ref))
    return ann


def annotate() -> int:
    sys.path.insert(0, str(REPO / "tools/schematic-context"))
    import annotate as ann_tool
    docs = modify.load_project(ROOT)
    ann = annotations()
    done = set()
    for key, d in docs.by_key.items():
        for sym in d.schematic.schematicSymbols:
            ref = modify._symbol_ref(sym)
            if ref in ann:
                ann_tool.write_ai_properties(sym, ann[ref])
                done.add(ref)
    missing = sorted(set(ann) - done)
    docs.save_all()
    print("Annotated {} parts{}".format(len(done), "; not found: {}".format(missing) if missing else ""))
    return 1 if missing else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--annotate", action="store_true")
    args = ap.parse_args()
    if args.apply:
        return apply()
    if args.annotate:
        return annotate()
    if args.check:
        return check()
    print(__doc__)
    for sheet, ref, lib_id, value, fp, lcsc, pos, nets, nc in PARTS:
        print("{:6s} {:6s} {:16s} {} {}".format(sheet[:6], ref, value, pos, nets if len(nets) < 5 else
                                                 "{} pins".format(len(nets))))
    print("U3 pins:", U3_PIN_NETS)
    print("Renames:", RENAMES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
