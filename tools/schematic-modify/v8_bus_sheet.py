#!/usr/bin/env python3
"""
v8_bus_sheet.py - v8 debug board, TCA / bus / channel edits (Phase 9).

Initiative: docs/initiatives/v8-debug-board. Design intent:
hardware/pcb-main-v8/CONTEXT.md -> Jumper matrix rows b, d, f; Test points (channel side);
Parts (Cable-facing protection, Jumper headers, Pull-up option resistors, Footprints).

Edits (all label-style, through modify.py helpers; KiCad must be closed during --apply):
  tca9548A_subsystem.kicad_sch (paper A4 -> A3; new parts below and right of the v7 drawing)
    - Channel split (row b): U4 SDn/SCn pins leave the wire to the hierarchical label and get
      local labels CHn_SDA / CHn_SCL (TCA side). The six channel hierarchical labels become
      CHn_SDA_CONN / CHn_SCL_CONN (connector side, moved right to x 215.9 with a stub + label).
    - Row b per line: 47 R (R80-R85) CHn_x -> CHn_x_CONN, with a 1x2 bypass header across it
      (JP10-JP15; shunt off = v8, on = v7). Per connector: TPD2E2U06DRL (U11-U13), IO1 pin 3 =
      CHn_SDA_CONN, IO2 pin 5 = CHn_SCL_CONN, GND pin 4 = CHn_TVS_GND, pins 1/2 no-connect;
      1x2 header CHn_TVS_GND -> GND (JP16-JP18; shunt on = v8, off = v7).
    - Row d upstream: R28 / R29 (kept, 2.2 k; LCSC -> C4190 per Parts) leave the bus: their bus
      stub and junction are removed and pin 1 goes to PU_SDA_2K2 / PU_SCL_2K2. A 2x3 header per
      line (JP19 SDA, JP20 SCL): odd pins 1/3/5 = bus, even 2/4/6 = 2.2 k / 4.7 k / 10 k. New
      4.7 k (R86 SDA, R88 SCL) and 10 k (R87 SDA, R89 SCL) from PU_x_4K7 / PU_x_10K to I2C_PU_RAIL.
      The bus is reached on this sheet by labels I2C_SDA_IN / I2C_SCL_IN placed on the old
      junction points of the bus wires.
    - Row d downstream: per channel line an open SJ2 (JP21-JP26) CHn_x -> CHn_x_PU and a 4.7 k
      (R90-R95) CHn_x_PU -> I2C_PU_RAIL.
    - I2C_PU_RAIL: a local label on R28 pin 2's +3.3V power-symbol point, so it is +3.3V until
      Phase 10 moves the bus loads to +3.3V_BUS (CONTEXT Power path: I2C_PU_RAIL is on +3.3V_BUS).
    - Row f: 1x2 header per line (JP27 SDA, JP28 SCL): bus -> BQ_SDA / BQ_SCL, shunt on (v8 = v7).
      New hierarchical labels BQ_SDA / BQ_SCL.
    - Channel test points TP80-TP91 (TestPoint_Pad_D1.5mm) on CHn_x and CHn_x_CONN, each with
      its own ground point TP92-TP103 (TestPoint_Pad_2.5x2.5mm) on GND.
  power_management.kicad_sch
    - U5 pin 6 (SDA) / 5 (SCL): label I2C_SDA/SCL -> BQ_SDA/BQ_SCL; new hierarchical labels.
  motion-play-main-v8.kicad_sch (root)
    - TCA sheet pins CHn_x renamed CHn_x_CONN (J4-J6 stay wired to them).
    - BQ_SDA / BQ_SCL sheet pins on the TCA and power sheet symbols, joined by root labels.

Not here: +3.3V_BUS rail moves and row c (Phase 10); upstream/bus/BQ test points, I2C_PU_RAIL
test point (Phase 11); ai_* annotation (Phase 11).

Usage:
  python3 tools/schematic-modify/v8_bus_sheet.py            # dry run: print the plan
  python3 tools/schematic-modify/v8_bus_sheet.py --apply    # edit (refuses if R80 exists)
  python3 tools/schematic-modify/v8_bus_sheet.py --check    # pin -> net, each jumper's two
                                                            # positions, all-v7 vs v7 @ c2acffc
  python3 tools/schematic-modify/v8_bus_sheet.py --check --root <copy>/motion-play-main-v8.kicad_sch
                                                            # the same check on a scratch copy
  --root also works with the modes that write, on a scratch copy outside the repository (a replay).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modify  # noqa: E402
import v8_mcu_sheet as mcu  # noqa: E402
from modify import kio  # noqa: E402
from kicad_io import atom, child, kids  # noqa: E402

ROOT = mcu.ROOT
PROJECT = mcu.PROJECT
TCA = "tca9548A_subsystem.kicad_sch"
PWR = "power_management.kicad_sch"

HDR_1X2 = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
HDR_2X3 = "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical"
R0603 = "Resistor_SMD:R_0603_1608Metric"
SOT553 = "Package_TO_SOT_SMD:SOT-553"
TP_SIG = "TestPoint:TestPoint_Pad_D1.5mm"
TP_GND = "TestPoint:TestPoint_Pad_2.5x2.5mm"
L_R = "Device:R"
L_1X2 = "Connector_Generic:Conn_01x02"
L_2X3 = "Connector_Generic:Conn_02x03_Odd_Even"
L_SJ2 = "Jumper:SolderJumper_2_Open"
L_TVS = "Power_Protection:TPD2E2U06DRL"
L_TP = "Connector:TestPoint"

CH = [(0, "J4"), (1, "J5"), (2, "J6")]
LINES = ("SDA", "SCL")
# U4 channel pins (TCA9548A: SD0 4, SC0 5, SD1 6, SC1 7, SD2 8, SC2 9).
U4_PIN = {(0, "SDA"): "4", (0, "SCL"): "5", (1, "SDA"): "6", (1, "SCL"): "7",
          (2, "SDA"): "8", (2, "SCL"): "9"}
U4_PIN_X, HL_OLD_X, HL_NEW_X = 181.61, 190.5, 215.9
BUS = {"SDA": "I2C_SDA_IN", "SCL": "I2C_SCL_IN"}
# R28/R29 bus stubs: (resistor pin 1, junction on the bus wire).
PU_STUB = {"SDA": ("R28", (139.7, 69.85), (139.7, 73.66)),
           "SCL": ("R29", (128.27, 69.85), (128.27, 71.12))}
RAIL = "I2C_PU_RAIL"
RAIL_POINT = (139.7, 60.96)       # R28 pin 2 wire end on #PWR030 (+3.3V)
GND_POINT = (193.04, 50.8)        # junction on the TCA sheet's GND hierarchical-label wire
BQ_HL = {"SDA": (119.38, 83.82), "SCL": (119.38, 88.9)}       # TCA sheet, left side
BQ_HL_PWR = {"SDA": (195.58, 189.23), "SCL": (208.28, 189.23)}  # power sheet, by I2C hlabels


def ch(n, line, suffix=""):
    return "CH{}_{}{}".format(n, line, suffix)


def build_parts():
    """(sheet key, ref, lib_id, value, footprint, lcsc, position, pin_nets, no_connect_pins)."""
    parts = []
    # Lower grid on A3: 10 columns x 4 rows. Row j = channel j (row b + downstream), row 3 = d/f.
    col = lambda i: round(45.72 + 38.1 * i, 2)   # noqa: E731
    row = lambda j: round(157.48 + 25.4 * j, 2)  # noqa: E731
    k = 0
    for n, _ in CH:
        i = 0
        for line in LINES:
            r = "R{}".format(80 + k)
            jp = "JP{}".format(10 + k)
            parts.append((TCA, r, L_R, "47Ω", R0603, "C23182", (col(i), row(n)),
                          {"1": ch(n, line), "2": ch(n, line, "_CONN")}, ()))
            parts.append((TCA, jp, L_1X2, "row b {} bypass".format(ch(n, line)), HDR_1X2, "C492401",
                          (col(i + 1), row(n)), {"1": ch(n, line), "2": ch(n, line, "_CONN")}, ()))
            i += 2
            k += 1
        parts.append((TCA, "U{}".format(11 + n), L_TVS, "TPD2E2U06DRLR", SOT553, "C1972959", (col(4), row(n)),
                      {"3": ch(n, "SDA", "_CONN"), "5": ch(n, "SCL", "_CONN"), "4": "CH{}_TVS_GND".format(n)},
                      ("1", "2")))
        parts.append((TCA, "JP{}".format(16 + n), L_1X2, "row b CH{} TVS GND".format(n), HDR_1X2, "C492401",
                      (col(5), row(n)), {"1": "CH{}_TVS_GND".format(n), "2": "GND"}, ()))
        for li, line in enumerate(LINES):
            idx = 2 * n + li
            parts.append((TCA, "JP{}".format(21 + idx), L_SJ2, "row d {} PU".format(ch(n, line)), mcu.SJ2_OPEN, "",
                          (col(6 + 2 * li), row(n)), {"1": ch(n, line), "2": ch(n, line, "_PU")}, ()))
            parts.append((TCA, "R{}".format(90 + idx), L_R, "4.7kΩ", R0603, "C23162", (col(7 + 2 * li), row(n)),
                          {"1": ch(n, line, "_PU"), "2": RAIL}, ()))
    # Row d upstream and row f (grid row 3).
    for li, line in enumerate(LINES):
        b = 3 * li
        parts.append((TCA, "JP{}".format(19 + li), L_2X3, "row d {} upstream".format(line), HDR_2X3, "C56153599",
                      (col(b), row(3)),
                      {"1": BUS[line], "3": BUS[line], "5": BUS[line], "2": "PU_{}_2K2".format(line),
                       "4": "PU_{}_4K7".format(line), "6": "PU_{}_10K".format(line)}, ()))
        parts.append((TCA, "R{}".format(86 + 2 * li), L_R, "4.7kΩ", R0603, "C23162", (col(b + 1), row(3)),
                      {"1": "PU_{}_4K7".format(line), "2": RAIL}, ()))
        parts.append((TCA, "R{}".format(87 + 2 * li), L_R, "10kΩ", R0603, "C25804", (col(b + 2), row(3)),
                      {"1": "PU_{}_10K".format(line), "2": RAIL}, ()))
        parts.append((TCA, "JP{}".format(27 + li), L_1X2, "row f BQ {}".format(line), HDR_1X2, "C492401",
                      (col(6 + li), row(3)), {"1": BUS[line], "2": "BQ_{}".format(line)}, ()))
    # Channel test points + ground points (upper right on A3): 4 columns x 3 rows.
    tp_nets = []
    for n, _ in CH:
        tp_nets += [ch(n, "SDA"), ch(n, "SCL"), ch(n, "SDA", "_CONN"), ch(n, "SCL", "_CONN")]
    for t, net in enumerate(tp_nets):
        x = round(241.3 + 38.1 * (t % 4), 2)
        y = round(45.72 + 30.48 * (t // 4), 2)
        parts.append((TCA, "TP{}".format(80 + t), L_TP, net, TP_SIG, "", (x, y), {"1": net}, ()))
        parts.append((TCA, "TP{}".format(92 + t), L_TP, "GND", TP_GND, "", (round(x + 10.16, 2), y),
                      {"1": "GND"}, ()))
    return parts


PARTS = build_parts()
NEW_REFS = tuple(p[1] for p in PARTS)

# Jumper positions, as pairs of jumper pins joined by a shunt / solder bridge.
ROW_B_V8, ROW_B_V7, ROW_D_V8, ROW_D_V7, ROW_F_V8, ROW_F_V7 = [], [], [], [], [], []
for _n in range(3):
    ROW_B_V8.append(("JP{}.1".format(16 + _n), "JP{}.2".format(16 + _n)))       # TVS GND leg on
    ROW_B_V7 += [("JP{}.1".format(10 + 2 * _n), "JP{}.2".format(10 + 2 * _n)),  # bypass on
                 ("JP{}.1".format(11 + 2 * _n), "JP{}.2".format(11 + 2 * _n))]
ROW_D_V8 = [("JP19.1", "JP19.2"), ("JP20.1", "JP20.2")]   # 2.2 k (v8 = v7); downstream SJ2s open
ROW_D_V7 = list(ROW_D_V8)
ROW_F_V8 = [("JP27.1", "JP27.2"), ("JP28.1", "JP28.2")]   # BQ on the bus (v8 = v7)
ROW_F_V7 = list(ROW_F_V8)
V7_SHORTS = ROW_B_V7 + ROW_D_V7 + ROW_F_V7
V8_SHORTS = ROW_B_V8 + ROW_D_V8 + ROW_F_V8


def _check_free(doc, xy, half=(1.0, 1.0), what="", symbols=True):
    """Refuse to place where a wire, label or pin already sits (prevents accidental joins)."""
    x0, y0 = xy[0] - half[0], xy[1] - half[1]
    x1, y1 = xy[0] + half[0], xy[1] + half[1]
    s = doc.schematic
    for w in kids(s, "wire"):
        (ax, ay), (bx, by) = modify._wire_pts(w)
        if max(ax, bx) >= x0 and min(ax, bx) <= x1 and max(ay, by) >= y0 and min(ay, by) <= y1:
            raise ValueError("{}: wire near {} on {}".format(what, xy, doc.path.name))
    for l in kids(s, "label") + kids(s, "hierarchical_label") + kids(s, "global_label"):
        lx, ly = modify._xy(l)
        if x0 <= lx <= x1 and y0 <= ly <= y1:
            raise ValueError("{}: label {} near {} on {}".format(what, atom(l, 0), xy, doc.path.name))
    for sym in (kids(s, "symbol") if symbols else []):
        sx, sy = modify._xy(sym)
        if x0 - 5 <= sx <= x1 + 5 and y0 - 5 <= sy <= y1 + 5:
            raise ValueError("{}: symbol {} near {} on {}".format(what, modify._symbol_ref(sym), xy, doc.path.name))


def set_paper(doc, size):
    """Set the sheet's paper size (the `(paper "A4")` atom)."""
    kio.set_str(child(doc.schematic, "paper"), 0, size)


def set_at(n, x, y, angle):
    """Replace an item's `(at ...)` with `(at x y angle)`."""
    at = child(n, "at")
    at.children[:] = kio.node("(at {} {} {})".format(kio.num(x), kio.num(y), kio.num(angle))).children


def _sheet_pin_with_label(root, file_name, name):
    modify.add_pin_to_sheet_ref(root, file_name, name, "bidirectional")
    pin = [p for p in kids(modify.find_sheet_ref(root, file_name), "pin") if atom(p, 0) == name][0]
    kio.set_num(child(pin, "at"), 2, 180)
    x, y = modify._xy(pin)
    end = (round(x - modify.WIRE_STUB_LEN, 2), y)
    _check_free(root, end, (0.6, 0.6), "root label " + name, symbols=False)
    modify.add_wire(root, (x, y), end)
    modify.add_local_label(root, name, end, 180)
    return (x, y), end


def apply() -> int:
    docs = modify.load_project(ROOT)
    tca, pwr, root = docs.sheet(TCA), docs.sheet(PWR), docs.sheet("root")
    if modify.find_component(tca, "R80") is not None:
        print("Refusing: R80 already on {} (already applied)".format(TCA))
        return 1
    set_paper(tca, "A3")
    print("{}: paper A4 -> A3".format(TCA))

    print("Channel split (row b)")
    for (n, line), pin in sorted(U4_PIN.items()):
        xy, _, _ = modify.pin_position(tca, "U4", pin)
        y = xy[1]
        if not modify.remove_wire_between(tca, (U4_PIN_X, y), (HL_OLD_X, y), tolerance=0.05):
            raise RuntimeError("U4.{}: wire to the hierarchical label not found".format(pin))
        print("  " + modify.set_pin_net(tca, "U4", pin, ch(n, line)))
        old, new = ch(n, line), ch(n, line, "_CONN")
        hls = [h for h in kids(tca.schematic, "hierarchical_label") if atom(h, 0) == old]
        if len(hls) != 1 or abs(modify._xy(hls[0])[1] - y) > 0.05:
            raise RuntimeError("hierarchical label {} not at y {}".format(old, y))
        _check_free(tca, (HL_NEW_X - 1.27, y), (1.4, 0.6), "hlabel " + new)
        kio.set_str(hls[0], 0, new)
        set_at(hls[0], HL_NEW_X, y, 0)
        end = (round(HL_NEW_X - modify.WIRE_STUB_LEN, 2), y)
        modify.add_wire(tca, (HL_NEW_X, y), end)
        modify.add_local_label(tca, new, end, 180)
        if not modify.rename_sheet_pin(root, TCA, old, new):
            raise RuntimeError("root sheet pin {} not found".format(old))
        print("  hlabel + sheet pin {} -> {} (hlabel at x {})".format(old, new, HL_NEW_X))

    print("Row d upstream: R28/R29 off the bus")
    for line, (ref, pin_xy, junction) in PU_STUB.items():
        if not modify.remove_wire_between(tca, pin_xy, junction, tolerance=0.05):
            raise RuntimeError("{}: bus stub not found".format(ref))
        if not modify.remove_junction_at(tca, junction):
            raise RuntimeError("{}: junction {} not found".format(ref, junction))
        modify.add_local_label(tca, BUS[line], junction, 0)
        print("  {} stub and junction {} removed; label {} on the bus wire".format(ref, junction, BUS[line]))
        print("  " + modify.set_pin_net(tca, ref, "1", "PU_{}_2K2".format(line)))
        sym = modify.find_component(tca, ref)
        for p in modify._props(sym):
            if atom(p, 0) in ("LCSC Part", "LCSC Part No"):
                kio.set_str(p, 1, "C4190")
        print("  {} LCSC -> C4190 (Parts: same value, basic)".format(ref))
    modify.add_local_label(tca, RAIL, RAIL_POINT, 0)
    modify.add_local_label(tca, "GND", GND_POINT, 0)
    print("  label {} at {} (R28.2 / +3.3V); label GND at {}".format(RAIL, RAIL_POINT, GND_POINT))

    print("Row f: BQ_SDA / BQ_SCL")
    for line in LINES:
        name = "BQ_{}".format(line)
        _check_free(tca, (BQ_HL[line][0] + 1.27, BQ_HL[line][1]), (1.6, 0.6), "hlabel " + name)
        modify.add_hierarchical_label(tca, name=name, shape="bidirectional", net=name,
                                      position=BQ_HL[line], angle=180)
        _check_free(pwr, (BQ_HL_PWR[line][0] + 1.27, BQ_HL_PWR[line][1]), (1.6, 0.6), "hlabel " + name)
        modify.add_hierarchical_label(pwr, name=name, shape="bidirectional", net=name,
                                      position=BQ_HL_PWR[line], angle=180)
        print("  " + modify.set_pin_net(pwr, "U5", "6" if line == "SDA" else "5", name))
        for f in (TCA, PWR):
            pin, end = _sheet_pin_with_label(root, f, name)
            print("  root: sheet pin {} on {} at {}, label at {}".format(name, f, pin, end))

    print("New parts ({})".format(TCA))
    lib_cache = {}
    for sheet, ref, lib_id, value, fp, lcsc, pos, nets, ncs in PARTS:
        doc = docs.sheet(sheet)
        _check_free(doc, pos, (3.0, 3.0), ref)
        if lib_id not in lib_cache:
            lib_cache[lib_id] = mcu.stock_symbol(lib_id)
        modify.add_component(doc, lib_symbol=lib_cache[lib_id], lib_id=lib_id, ref=ref, value=value,
                             footprint=fp, lcsc_part=lcsc, position=pos, pin_nets=nets, project_name=PROJECT)
        for p in ncs:
            modify.add_no_connect(doc, modify.pin_position(doc, ref, p)[0])
        print("  {:5s} {:24s} {}: {}{}".format(ref, value, pos, nets, " NC " + ",".join(ncs) if ncs else ""))

    docs.save_all()
    print("Saved.")
    return check()


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

def _short(net):
    return None if net is None else net.rsplit("/", 1)[-1]


def expected_short_names():
    """Pin -> last path component of the netlist net name."""
    alias = {"I2C_SDA_IN": "I2C_SDA", "I2C_SCL_IN": "I2C_SCL", RAIL: "+3.3V_BUS"}
    exp = {}
    for _, ref, _, _, _, _, _, nets, _ in PARTS:
        for pin, net in nets.items():
            exp["{}.{}".format(ref, pin)] = alias.get(net, net)
    for (n, line), pin in U4_PIN.items():
        exp["U4.{}".format(pin)] = ch(n, line)
    for n, j in CH:
        exp["{}.3".format(j)] = ch(n, "SDA", "_CONN")
        exp["{}.4".format(j)] = ch(n, "SCL", "_CONN")
    exp.update({"R28.1": "PU_SDA_2K2", "R29.1": "PU_SCL_2K2", "R28.2": "+3.3V_BUS", "R29.2": "+3.3V_BUS",
                "U4.23": "I2C_SDA", "U4.22": "I2C_SCL", "U5.6": "BQ_SDA", "U5.5": "BQ_SCL",
                "U7.6": "I2C_SDA", "U7.5": "I2C_SCL"})
    return exp


def _groups(nets, pin_net, shorts):
    parent = {n: n for n in nets}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in shorts:
        parent[find(pin_net[a])] = find(pin_net[b])
    groups = {}
    for n, members in nets.items():
        groups.setdefault(find(n), set()).update(members)
    return list(groups.values())


def _group_of(groups, member):
    for g in groups:
        if member in g:
            return g
    return set()


def check() -> int:
    fails = 0
    print("=== Phase 8 check (MCU sheet; all-v7 positions of rows a, e, g + b, d, f vs v7) ===")
    fails += mcu.check() != 0

    print("=== Phase 9 check (rows b, d, f) ===")
    with tempfile.TemporaryDirectory() as td:
        pin_net, nets, comps = mcu.netlist(ROOT, Path(td) / "v8.xml")
    print("Pin -> net:")
    bad = 0
    for key, want in sorted(expected_short_names().items()):
        got = _short(pin_net.get(key))
        if got != want:
            bad += 1
            print("  BAD {:8s} {}  (want {})".format(key, pin_net.get(key), want))
    print("  {} pins checked, {} wrong".format(len(expected_short_names()), bad))
    fails += bad
    for n in range(3):
        for p in ("1", "2"):
            got = pin_net.get("U{}.{}".format(11 + n, p))
            if got is not None and not got.startswith("unconnected-"):
                fails += 1
                print("  BAD U{}.{} should be no-connect, is {}".format(11 + n, p, got))

    # Each jumper row, both positions, starting from the v8 default of everything else.
    base_v8 = mcu.V8_SHORTS + V8_SHORTS
    rows = [
        ("b", ROW_B_V8, ROW_B_V7, ["U4.4", "J4.3", "U11.4", "U4.9", "J6.4", "U13.4"]),
        ("d", ROW_D_V8, ROW_D_V7, ["U4.23", "U4.22", "U4.4"]),
        ("f", ROW_F_V8, ROW_F_V7, ["U4.23", "U5.6", "U5.5"]),
    ]
    want = {
        ("b", "v8"): {"U4.4": {"U4.4", "R80.1", "JP10.1", "JP21.1", "TP80.1"},
                      "J4.3": {"J4.3", "R80.2", "JP10.2", "U11.3", "TP82.1"},
                      "U11.4": "GND", "U4.9": {"U4.9", "R85.1", "JP15.1", "JP26.1", "TP89.1"},
                      "J6.4": {"J6.4", "R85.2", "JP15.2", "U13.5", "TP91.1"}, "U13.4": "GND"},
        ("b", "v7"): {"U4.4": {"U4.4", "R80.1", "R80.2", "JP10.1", "JP10.2", "JP21.1", "TP80.1", "J4.3",
                               "U11.3", "TP82.1"},
                      "J4.3": "same as U4.4", "U11.4": {"U11.4", "JP16.1"},
                      "U4.9": {"U4.9", "R85.1", "R85.2", "JP15.1", "JP15.2", "JP26.1", "TP89.1", "J6.4",
                               "U13.5", "TP91.1"},
                      "J6.4": "same as U4.9", "U13.4": {"U13.4", "JP18.1"}},
    }
    for row, v8, v7, probes in rows:
        others = [s for s in base_v8 if s not in v8]
        for pos, shorts in (("v8", v8), ("v7", v7)):
            groups = _groups(nets, pin_net, others + shorts)
            print("Row {} {} position (others at v8 default):".format(row, pos))
            for m in probes:
                g = _group_of(groups, m)
                w = want.get((row, pos), {}).get(m)
                if w == "GND":
                    ok = "U3.1" in g
                    desc = "on GND" if ok else sorted(g)
                elif w == "same as U4.4":
                    ok = g == _group_of(groups, "U4.4")
                    desc = "joined to U4.4's net" if ok else sorted(g)
                elif w == "same as U4.9":
                    ok = g == _group_of(groups, "U4.9")
                    desc = "joined to U4.9's net" if ok else sorted(g)
                elif w is not None:
                    ok = g == w
                    desc = sorted(g)
                else:
                    ok = True
                    desc = sorted(x for x in g if not x.startswith(("TP", "TPIO")))
                fails += not ok
                print("  {} {:6s} {}".format("ok " if ok else "BAD", m, desc if len(str(desc)) < 400 else
                                             "{} members".format(len(g))))
    # Row d and f membership facts.
    groups = _groups(nets, pin_net, base_v8)
    sda = _group_of(groups, "U4.23")
    facts = [
        ("v8 default: R28.1 (2.2 k) on I2C_SDA via JP19 1-2", "R28.1" in sda),
        ("v8 default: R86/R87 (4.7 k/10 k) not on I2C_SDA", not ({"R86.1", "R87.1"} & sda)),
        ("v8 default: downstream 4.7 k not on CH0_SDA (JP21 open)", "R90.1" not in _group_of(groups, "U4.4")),
        ("v8 default: U5.6 (BQ SDA) on I2C_SDA via JP27", "U5.6" in sda),
        ("v8 default: U3.37 not on I2C_SDA (row a v8)", "U3.37" not in sda),
    ]
    g_f_open = _groups(nets, pin_net, [s for s in base_v8 if s not in ROW_F_V8])
    facts.append(("row f open: U5.6 off I2C_SDA", "U5.6" not in _group_of(g_f_open, "U4.23")))
    g_d_none = _groups(nets, pin_net, [s for s in base_v8 if s not in ROW_D_V8])
    facts.append(("row d no shunt: no pull-up on I2C_SDA",
                  not any(m.startswith(("R28", "R29", "R86", "R87", "R88", "R89")) for m in
                          _group_of(g_d_none, "U4.23"))))
    g_47 = _groups(nets, pin_net, [s for s in base_v8 if s not in ROW_D_V8] + [("JP19.3", "JP19.4")])
    bus47 = _group_of(g_47, "U4.23")
    facts.append(("row d SDA shunt 3-4: R86 (4.7 k) on I2C_SDA, R28/R87 off",
                  "R86.1" in bus47 and not ({"R28.1", "R87.1"} & bus47)))
    g_10 = _groups(nets, pin_net, [s for s in base_v8 if s not in ROW_D_V8] + [("JP20.5", "JP20.6")])
    bus10 = _group_of(g_10, "U4.22")
    facts.append(("row d SCL shunt 5-6: R89 (10 k) on I2C_SCL, R29/R88 off",
                  "R89.1" in bus10 and not ({"R29.1", "R88.1"} & bus10)))
    g_dn = _groups(nets, pin_net, base_v8 + [("JP21.1", "JP21.2")])
    facts.append(("row d downstream JP21 closed: R90 (4.7 k) on CH0_SDA, rail end on +3.3V_BUS",
                  "R90.1" in _group_of(g_dn, "U4.4") and _short(pin_net["R90.2"]) == "+3.3V_BUS"))
    for text, ok in facts:
        fails += not ok
        print("  {} {}".format("ok " if ok else "BAD", text))
    print("v8 default I2C_SDA members:", sorted(sda))
    print("PHASE 9 CHECK {}".format("PASSED" if fails == 0 else "FAILED ({} problems)".format(fails)))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    mcu.add_root_arg(ap)
    args = ap.parse_args()
    mcu.apply_root_arg(ap, args, ("apply",))
    if args.apply:
        return apply()
    if args.check:
        return check()
    print(__doc__)
    for p in PARTS:
        print("{:5s} {:22s} {:28s} {} {}".format(p[1], p[3], p[4].split(":")[-1], p[6], p[7]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
