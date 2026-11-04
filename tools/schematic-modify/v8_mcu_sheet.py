#!/usr/bin/env python3
"""
v8_mcu_sheet.py - v8 debug board, MCU sheet edits (Phase 8, task 2).

Initiative: docs/initiatives/v8-debug-board. Design intent:
hardware/pcb-main-v8/CONTEXT.md -> GPIO allocation, Jumper matrix rows a, e, g,
Parts (Jumper headers, Footprints, IC1 swap).

Edits (all label-style, through modify.py helpers):
  esp32_s3.kicad_sch
    - U3 pin 37 (IO43) and 36 (IO44) leave the bus: their labels become U3_IO43 / U3_IO44.
    - U3 pin 9 (IO16) leaves LED_DATA: label becomes U3_IO16.
    - U3 pin 8 (IO15) and 11 (IO18): no-connect replaced by labels U3_IO15 / U3_IO18.
    - Row a: JP1 (SDA) and JP2 (SCL), 1x4 shunt headers:
        pin 1 U3_IO16/15, pin 2 I2C_SDA/SCL (bus), pin 3 U3_IO43/44, pin 4 UART0_TX/RX.
        v8 = shunts 1-2 + 3-4; v7 = one shunt on 2-3.
    - Row e: J10 external-master 1x4 header (GND, EXT_SDA, EXT_SCL, +3.3V_BUS) and
      JP3/JP4, open SJ2s from EXT_SDA/EXT_SCL to I2C_SDA/I2C_SCL.
      New hierarchical label +3.3V_BUS (input) for J10 pin 4.
    - Row g: JP5, SJ3 Bridged12: pad 1 U3_IO18 (default), pad 2 LED_DATA, pad 3 U3_IO16 (v7).
  motion-play-main-v8.kicad_sch (root)
    - ESP32_S3 sheet symbol gets a +3.3V_BUS pin, with a stub and a +3.3V_BUS label
      (the Phase 10 power sheet joins it by the same label).
  led_controller.kicad_sch
    - IC1 SN74AHCT125PWR (quad, TSSOP-14) -> SN74AHCT1G125DBVR (SOT-23-5), C7484.
      The old pin positions get labels (GND, DATA_IN, DATA_TO_LEDS, +5V_TO_LEDS) so the
      existing wires stay connected; the new IC1 carries the same labels.

Not done here (other phases): UART0 header (Phase 11; UART0_TX/RX nets exist on JP1/JP2
pin 4 only), test points for U3_IO* / LED_DATA (Phase 11), ai_* annotation (Phase 11),
+3.3V -> +3.3V_MCU rename and the power sheet (Phase 10).

Usage:
  python3 tools/schematic-modify/v8_mcu_sheet.py            # dry run: print the plan
  python3 tools/schematic-modify/v8_mcu_sheet.py --apply    # edit (refuses if JP1 exists)
  python3 tools/schematic-modify/v8_mcu_sheet.py --check    # netlist check vs GPIO allocation
                                                            # and v7 positions vs v7 @ c2acffc
KiCad must be closed while --apply runs.
"""

from __future__ import annotations

import argparse
import copy
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modify  # noqa: E402
from kiutils.items.common import Effects, Font, Position  # noqa: E402
from kiutils.items.schitems import HierarchicalPin  # noqa: E402
from kiutils.symbol import SymbolLib  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
KICAD = REPO / "hardware/pcb-main-v8/kicad"
ROOT = KICAD / "motion-play-main-v8.kicad_sch"
PROJECT = "motion-play-main-v8"
MCU = "esp32_s3.kicad_sch"
LEDC = "led_controller.kicad_sch"
STOCK = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols")
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
V7_COMMIT = "c2acffc"

HDR_1X4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
SJ2_OPEN = "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm"
SJ3_B12 = "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm_NumberLabels"

# U3 pin -> new label net (GPIO allocation table).
U3_PINS = [
    ("37", "U3_IO43"),  # was I2C_SDA
    ("36", "U3_IO44"),  # was I2C_SCL
    ("9", "U3_IO16"),   # was LED_DATA
    ("8", "U3_IO15"),   # was no-connect
    ("11", "U3_IO18"),  # was no-connect
]

# New parts on the MCU sheet: (ref, lib_id, value, footprint, lcsc, position, pin_nets)
MCU_PARTS = [
    ("JP1", "Connector_Generic:Conn_01x04", "row a SDA", HDR_1X4, "C2691448", (220.98, 50.8),
     {"1": "U3_IO16", "2": "I2C_SDA", "3": "U3_IO43", "4": "UART0_TX"}),
    ("JP2", "Connector_Generic:Conn_01x04", "row a SCL", HDR_1X4, "C2691448", (220.98, 71.12),
     {"1": "U3_IO15", "2": "I2C_SCL", "3": "U3_IO44", "4": "UART0_RX"}),
    ("JP5", "Jumper:SolderJumper_3_Bridged12", "row g", SJ3_B12, "", (251.46, 63.5),
     {"1": "U3_IO18", "2": "LED_DATA", "3": "U3_IO16"}),
    ("J10", "Connector_Generic:Conn_01x04", "EXT_MASTER (row e)", HDR_1X4, "C2691448", (220.98, 99.06),
     {"1": "GND", "2": "EXT_SDA", "3": "EXT_SCL", "4": "+3.3V_BUS"}),
    ("JP3", "Jumper:SolderJumper_2_Open", "row e SDA", SJ2_OPEN, "", (251.46, 96.52),
     {"1": "EXT_SDA", "2": "I2C_SDA"}),
    ("JP4", "Jumper:SolderJumper_2_Open", "row e SCL", SJ2_OPEN, "", (251.46, 109.22),
     {"1": "EXT_SCL", "2": "I2C_SCL"}),
]
BUS_HLABEL = ("+3.3V_BUS", (15.24, 104.14))       # esp32 sheet, under the +5V hlabel
ROOT_PIN_Y = 55.88                               # left edge of the ESP32_S3 sheet symbol

# IC1 swap (led_controller sheet).
IC1_OLD_PIN_LABELS = {"1": "GND", "2": "DATA_IN", "3": "DATA_TO_LEDS", "7": "GND", "14": "+5V_TO_LEDS"}
IC1_NEW = ("IC1", "74xGxx:74AHCT1G125", "SN74AHCT1G125DBVR", "Package_TO_SOT_SMD:SOT-23-5",
           "C7484", (215.9, 120.65),
           {"1": "GND", "2": "DATA_IN", "3": "GND", "4": "DATA_TO_LEDS", "5": "+5V_TO_LEDS"})
IC1_PIN_MAP_V7_TO_V8 = {"1": "1", "2": "2", "3": "4", "7": "3", "14": "5"}


def stock_symbol(lib_id: str):
    """Load a stock KiCad symbol, flattening one level of `extends`."""
    lib, name = lib_id.split(":")
    sl = SymbolLib.from_file(str(STOCK / (lib + ".kicad_sym")))
    by = {s.libId: s for s in sl.symbols}
    sym = by[name]
    if sym.extends:
        parent = copy.deepcopy(by[sym.extends])
        parent.properties = copy.deepcopy(sym.properties)
        parent.extends = None
        parent.libId = name
        for unit in parent.units:
            unit.entryName = name
        sym = parent
    else:
        sym = copy.deepcopy(sym)
    sym.libId = lib_id
    return sym


def apply() -> int:
    docs = modify.load_project(ROOT)
    mcu = docs.sheet(MCU)
    ledc = docs.sheet(LEDC)
    root = docs.sheet("root")
    if modify.find_component(mcu, "JP1") is not None:
        print("Refusing: JP1 already on {} (already applied)".format(MCU))
        return 1

    print("U3 pins ({})".format(MCU))
    for pin, net in U3_PINS:
        print("  " + modify.set_pin_net(mcu, "U3", pin, net))

    print("New parts ({})".format(MCU))
    for ref, lib_id, value, fp, lcsc, pos, nets in MCU_PARTS:
        modify.add_component(mcu, lib_symbol=stock_symbol(lib_id), lib_id=lib_id, ref=ref, value=value,
                             footprint=fp, lcsc_part=lcsc, position=pos, pin_nets=nets,
                             project_name=PROJECT)
        print("  {} {} at {}: {}".format(ref, value, pos, nets))

    name, pos = BUS_HLABEL
    modify.add_hierarchical_label(mcu, name=name, shape="input", net=name, position=pos, angle=180)
    print("  hierarchical label {} at {}".format(name, pos))

    sheet = modify.find_sheet_ref(root, MCU)
    x = round(sheet.position.X, 2)
    sheet.pins.append(HierarchicalPin(
        name=name, connectionType="input", position=Position(X=x, Y=ROOT_PIN_Y, angle=180),
        effects=Effects(font=Font(height=modify.FONT_SIZE, width=modify.FONT_SIZE)),
        uuid=modify.new_uuid()))
    stub = (round(x - modify.WIRE_STUB_LEN, 2), ROOT_PIN_Y)
    root.schematic.graphicalItems.append(modify._make_wire((x, ROOT_PIN_Y), stub))
    root.schematic.labels.append(modify._make_local_label(name, stub[0], stub[1], 180))
    print("Root: sheet pin {} on ESP32_S3 at ({}, {}), label at {}".format(name, x, ROOT_PIN_Y, stub))

    print("IC1 swap ({})".format(LEDC))
    old_pins = {}
    for pin in IC1_OLD_PIN_LABELS:
        old_pins[pin] = modify.pin_position(ledc, "IC1", pin)[0]
    all_old = [modify.pin_position(ledc, "IC1", str(n))[0] for n in range(1, 15)]
    old_lib = modify.find_component(ledc, "IC1").libId
    removed_nc = sum(modify.remove_no_connect_at(ledc, p) for p in all_old)
    modify.remove_component(ledc, "IC1")
    if not any(s.libId == old_lib for s in ledc.schematic.schematicSymbols):
        ledc.schematic.libSymbols = [l for l in ledc.schematic.libSymbols if l.libId != old_lib]
    for pin, net in IC1_OLD_PIN_LABELS.items():
        p = old_pins[pin]
        angle = 180 if pin == "14" else 0
        ledc.schematic.labels.append(modify._make_local_label(net, p[0], p[1], angle))
    print("  removed old IC1 ({}), {} no-connects; labels at old pins: {}".format(
        old_lib, removed_nc, IC1_OLD_PIN_LABELS))
    ref, lib_id, value, fp, lcsc, pos, nets = IC1_NEW
    modify.add_component(ledc, lib_symbol=stock_symbol(lib_id), lib_id=lib_id, ref=ref, value=value,
                         footprint=fp, lcsc_part=lcsc, position=pos, pin_nets=nets, project_name=PROJECT)
    print("  new IC1 {} at {}: {}".format(value, pos, nets))

    docs.save_all()
    print("Saved.")
    return check()


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

def netlist(sch: Path, out: Path):
    r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                        str(sch)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    root = ET.parse(str(out)).getroot()
    pin_net = {}
    nets = {}
    for n in root.find("nets"):
        members = set()
        for node in n.findall("node"):
            key = "{}.{}".format(node.get("ref"), node.get("pin"))
            pin_net[key] = n.get("name")
            members.add(key)
        nets[n.get("name")] = members
    comps = {c.get("ref"): (c.findtext("value"), c.findtext("footprint")) for c in root.find("components")}
    return pin_net, nets, comps


EXPECTED = {
    # GPIO allocation: U3 module pin -> net
    "U3.37": "/ESP32_S3/U3_IO43", "U3.36": "/ESP32_S3/U3_IO44",
    "U3.9": "/ESP32_S3/U3_IO16", "U3.8": "/ESP32_S3/U3_IO15", "U3.11": "/ESP32_S3/U3_IO18",
    "U3.18": "/TCA_RESET", "U3.23": "/CHRG_INT",
    "U3.21": "/ESP32_S3/INT1", "U3.20": "/ESP32_S3/INT2", "U3.19": "/ESP32_S3/INT3",
    "U3.27": "/ESP32_S3/GPIO0_BOOT", "U3.3": "/ESP32_S3/EN",
    "U3.13": "/ESP32_S3/USB_DN_MCU", "U3.14": "/ESP32_S3/USB_DP_MCU",
    # Row a
    "JP1.1": "/ESP32_S3/U3_IO16", "JP1.2": "/I2C_SDA", "JP1.3": "/ESP32_S3/U3_IO43", "JP1.4": "/ESP32_S3/UART0_TX",
    "JP2.1": "/ESP32_S3/U3_IO15", "JP2.2": "/I2C_SCL", "JP2.3": "/ESP32_S3/U3_IO44", "JP2.4": "/ESP32_S3/UART0_RX",
    # Row e
    "J10.1": "GND", "J10.2": "/ESP32_S3/EXT_SDA", "J10.3": "/ESP32_S3/EXT_SCL", "J10.4": "+3.3V_BUS",
    "JP3.1": "/ESP32_S3/EXT_SDA", "JP3.2": "/I2C_SDA", "JP4.1": "/ESP32_S3/EXT_SCL", "JP4.2": "/I2C_SCL",
    # Row g
    "JP5.1": "/ESP32_S3/U3_IO18", "JP5.2": "/LED_DATA", "JP5.3": "/ESP32_S3/U3_IO16", "D5.1": "/LED_DATA",
    # IC1 swap
    "IC1.1": "GND", "IC1.2": "/LED_DATA", "IC1.3": "GND",
    "IC1.4": "/LED Controller/DATA_TO_LEDS", "IC1.5": "/LED Controller/+5V_TO_LEDS",
}
# U3 module pins that must stay unconnected (no net or an unconnected-* net).
U3_UNUSED = ["4", "5", "6", "7", "10", "12", "15", "16", "17", "22", "24", "25", "26",
             "28", "29", "30", "31", "32", "33", "34", "35", "38", "39"]

# v7 shunt positions: pairs of jumper pins that are joined (row a 2-3, row e open, row g pads 2-3).
V7_SHORTS = [("JP1.2", "JP1.3"), ("JP2.2", "JP2.3"), ("JP5.2", "JP5.3")]
V8_SHORTS = [("JP1.1", "JP1.2"), ("JP1.3", "JP1.4"), ("JP2.1", "JP2.2"), ("JP2.3", "JP2.4"),
             ("JP5.1", "JP5.2")]
NEW_REFS = ("JP1", "JP2", "JP3", "JP4", "JP5", "J10")


def later_phases():
    """Refs and jumper positions added by later phases' scripts (Phase 9: v8_bus_sheet.py,
    Phase 10: v8_power_sheet.py), so this check stays valid on the whole v8 schematic.
    Returns (new refs, v7 shorts, v8 shorts, v7-side drop refs, v7-side shorts). The v7-side
    pair models v7 parts that have no v7 position on v8 (Phase 10: the battery protection,
    user decision 2026-11-03): they are dropped from the v7 netlist with their conducting
    state applied as shorts, and the v8 replacement parts likewise."""
    refs, v7, v8, v7_drop, v7_side = [], [], [], [], []
    for name in ("v8_bus_sheet", "v8_power_sheet"):
        try:
            mod = __import__(name)
        except ImportError:
            continue
        refs += list(mod.NEW_REFS)
        v7 += list(mod.V7_SHORTS)
        v8 += list(mod.V8_SHORTS)
        v7_drop += list(getattr(mod, "V7_SIDE_DROP", ()))
        v7_side += list(getattr(mod, "V7_SIDE_SHORTS", ()))
    return refs, v7, v8, v7_drop, v7_side


def merged(nets, pin_net, shorts, drop_refs=NEW_REFS):
    """Net membership with jumper shorts applied, jumper/new-part pins dropped."""
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
    out = []
    for members in groups.values():
        kept = frozenset(m for m in members if m.split(".")[0] not in drop_refs)
        if kept:
            out.append(kept)
    return set(out)


def check() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pin_net, nets, comps = netlist(ROOT, td / "v8.xml")

        print("Pin -> net vs GPIO allocation / jumper rows a, e, g:")
        for key, want in EXPECTED.items():
            got = pin_net.get(key)
            ok = got == want
            fails += not ok
            print("  {} {:7s} {:32s}{}".format("ok " if ok else "BAD", key, str(got),
                                                "" if ok else "  (want {})".format(want)))
        for p in U3_UNUSED:
            got = pin_net.get("U3." + p)
            ok = got is None or got.startswith("unconnected-")
            fails += not ok
            if not ok:
                print("  BAD U3.{} should be unconnected, is {}".format(p, got))
        print("  U3 unused pins ({}) unconnected: {}".format(len(U3_UNUSED), "ok" if fails == 0 else "see above"))
        ic1 = comps.get("IC1")
        print("  IC1: {}".format(ic1))

        # v7 positions vs v7 @ c2acffc
        v7dir = td / "v7"
        v7dir.mkdir()
        files = ["motion-play-main.kicad_sch", "motion-play-main.kicad_pro", "sym-lib-table", "fp-lib-table",
                 MCU, LEDC, "power_management.kicad_sch", "tca9548A_subsystem.kicad_sch"]
        for f in files:
            data = subprocess.run(["git", "-C", str(REPO), "show", "{}:hardware/pcb-main/kicad/{}".format(V7_COMMIT, f)],
                                  check=True, capture_output=True).stdout
            (v7dir / f).write_bytes(data)
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", V7_COMMIT,
                              "hardware/pcb-main/kicad/libraries"], check=True, capture_output=True, text=True).stdout
        for f in out.split():
            dest = v7dir / f[len("hardware/pcb-main/kicad/"):]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(subprocess.run(["git", "-C", str(REPO), "show", "{}:{}".format(V7_COMMIT, f)],
                                            check=True, capture_output=True).stdout)
        for name in ("sym-lib-table", "fp-lib-table"):
            p = v7dir / name
            p.write_text(p.read_text().replace("${KIPRJMOD}/../resources/",
                                               str(REPO / "hardware/pcb-main/resources") + "/"))
        v7_pin_net, v7_nets, _ = netlist(v7dir / "motion-play-main.kicad_sch", td / "v7.xml")
        later_refs, later_v7, later_v8, v7_drop, v7_side = later_phases()
        # Map v7 IC1 pin numbers onto the single-gate part; drop the quad's unused pins.
        mapped_nets = {}
        for name, members in v7_nets.items():
            mapped = set()
            for m in members:
                ref, pin = m.split(".")
                if ref == "IC1":
                    if pin not in IC1_PIN_MAP_V7_TO_V8:
                        continue
                    m = "IC1." + IC1_PIN_MAP_V7_TO_V8[pin]
                mapped.add(m)
            mapped_nets[name] = mapped
        v7_sets = merged(mapped_nets, v7_pin_net, v7_side, tuple(v7_drop))
        if v7_drop:
            print("v7 parts with no v7 position on v8, dropped from the v7 netlist (conducting): {}".format(
                ", ".join(v7_drop)))
        all_new = tuple(NEW_REFS) + tuple(later_refs)
        present = {k.split(".")[0] for k in pin_net}
        later_v7 = [s for s in later_v7 if s[0].split(".")[0] in present]
        later_v8 = [s for s in later_v8 if s[0].split(".")[0] in present]
        v8_sets = merged(nets, pin_net, V7_SHORTS + later_v7, all_new)
        # Single-pin unconnected nets are not interesting.
        v7_sets = {s for s in v7_sets if len(s) > 1}
        v8_sets = {s for s in v8_sets if len(s) > 1}
        only7 = v7_sets - v8_sets
        only8 = v8_sets - v7_sets
        print("All-v7 positions (JP1 2-3, JP2 2-3, JP5 pads 2-3, JP3/JP4 open{}) vs v7 @ {}: "
              "{} nets differ in v7, {} in v8".format(
                  "; later phases' v7 shorts: {}".format(len(later_v7)) if later_v7 else "",
                  V7_COMMIT, len(only7), len(only8)))
        for s in sorted(only7, key=sorted):
            print("  v7 only:", sorted(s))
        for s in sorted(only8, key=sorted):
            print("  v8 only:", sorted(s))
        fails += bool(only7 or only8)

        v8_default = merged(nets, pin_net, V8_SHORTS + later_v8, all_new)
        for bus in ("/I2C_SDA", "/I2C_SCL", "/LED_DATA"):
            seed = {m for m in nets[bus] if m.split(".")[0] not in all_new}
            for s in v8_default:
                if s & seed:
                    print("v8 default positions: {} members: {}".format(bus, sorted(s)))
    print("CHECK {}".format("PASSED" if fails == 0 else "FAILED ({} problems)".format(fails)))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.apply:
        return apply()
    if args.check:
        return check()
    print(__doc__)
    for pin, net in U3_PINS:
        print("U3.{} -> {}".format(pin, net))
    for part in MCU_PARTS:
        print("{} {} {} {}".format(part[0], part[2], part[5], part[6]))
    print("IC1 -> {} {}".format(IC1_NEW[2], IC1_NEW[6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
