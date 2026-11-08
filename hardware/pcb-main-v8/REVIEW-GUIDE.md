# v8 Main Board: Schematic Review Guide (W3)

A plain-language tour of the v8 schematic, for the W3 review. It explains how to read the drawing, then goes sheet by sheet: where each block is, what it does, why it is there, and what a mistake would look like on screen. It ends with the W3 checklist.

- **Project:** `hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_pro` (KiCad 9). Close KiCad before any script runs on the schematic.
- **Design decisions:** `hardware/pcb-main-v8/CONTEXT.md` (cited below as "CONTEXT → section"). Jumper rows a–l are in CONTEXT → Jumper matrix. CL-IDs are from `docs/research/v7-retry/v6-v7-changelist.md`.
- **Checked against:** `hardware/pcb-main-v8/kicad/circuit-context.json`, extracted 2026-11-05 from the schematic as of `cf61cb2` (FRESH by `tools/lab/check_state.py --fresh`). Every ref and net named here was checked by script to exist in that file (Phase 11e, SESSION.md Worker #16).
- Net names are written in `code`, exactly as they appear on screen. KiCad's netlist adds a sheet prefix (`/Power Management/VSYS`); this guide leaves it off.

---

## 1. Primer: reading this schematic

**Symbol.** The drawing of one part. Each has a **reference** (a unique name such as R44 or U5) and a **value** (what it is: `10kΩ`, `BQ24195RGER`). Both are shown on screen; every other field (part number, footprint, AI notes) is hidden. Hover a part, or press E on it, to see the hidden fields.

| Prefix | Part | Prefix | Part |
|---|---|---|---|
| R | resistor | U, IC | chip |
| C | capacitor | J | connector or pin header that goes off the board |
| L | inductor (coil) | JP | jumper: a pin header with a removable shunt, or a solder jumper |
| D | diode or LED | SW | switch |
| Q | transistor (here: MOSFET switches) | F | fuse |
| TH | thermistor (temperature-sensing resistor) | TP, TPIO | test point (a bare copper pad to probe) |

**Pins.** The short lines at a symbol's edge. Each has a number (the physical pad) and often a name (`VIN`, `SDA`). A chip's datasheet pin number must match the symbol's.

**Net.** A set of pins that are electrically joined. Every net has a name. Two things put pins in the same net:
- a **wire** (a green line) drawn between them. A dot (**junction**) where wires meet means joined; wires that cross without a dot are not joined.
- a **net label**: text attached to a wire end. Every label with the same text on the same sheet is the same net, with no wire between them. This board is drawn mostly with labels, so you follow a circuit by reading names, not lines. Labels are exact and case-sensitive: `VBAT` and `V_BAT` are two different nets.

**Power symbols.** Small symbols such as `GND` (the ground bar), `+5V`, `+5V_CORE`, `+3.3V_MCU`, `+3.3V_BUS`. They work like a label that reaches every sheet: every `+3.3V_BUS` symbol anywhere on the board is one net. A `PWR_FLAG` is not a part: it only tells KiCad's electrical rules check (ERC) that a rail is driven.

**Hierarchical sheets.** The design is split into sheets. The **root sheet** (the one that opens first) shows each child sheet as a box. Double-click a box to go inside; the hierarchy navigator (View menu) or the "leave sheet" toolbar button goes back.
- A **sheet pin** on the box's edge connects to a **hierarchical label** (a flag-shaped label) of the same name inside the child sheet. On the root, a wire or label on the sheet pin carries the signal to the other sheets.
- The sheet pin's name only has to match the label inside its own sheet. So the TCA sheet's `I2C_SDA_IN` pin is the root's `I2C_SDA` net (a v7 name, kept; kicad-happy item 13 in SESSION.md Worker #15).
- This board's sheets: **ESP32_S3**, **TCA9548A_Subsystem**, **Power Management**, **LED Controller**.

**No-connect.** A small X on a pin means "deliberately unconnected".

**Tools that help.** Click a wire or label and press the backtick key (`` ` ``) to highlight its whole net on the sheet. The Net Navigator panel (View menu) lists every net and its pins. Cmd+F finds a reference or a label.

### How this board draws its debug features

**"Positions".** Most jumpers have a **v8 position** (the default, the fixed design) and a **v7 position** (puts back v7's exact connections, so a fault can be A/B/A-tested against v7). Each jumper belongs to a lettered **row** (a–l) of CONTEXT → Jumper matrix; the jumper's value says which, e.g. JP31 "row i".

**Pin-header jumpers** (rows a, b, c, d upstream, f). Drawn as a connector symbol (Conn_01x02, 01x03, 01x04, 02x03) with a net on each pin. The push-on **shunt** that bridges two pins is not drawn: a schematic can't show it. Where it ships fitted is in CONTEXT and in the part's description field. So for headers, check the pin → net order, not a drawn default.

**Solder jumpers** (rows d downstream, e, g, i, j, k, l, and the LED load jumpers). Drawn as two or three pads.
- **SJ2** (2 pads). "Open" = not joined until you add a solder blob. "Bridged" = joined by a thin copper bridge from the factory; cut it to open. The symbol draws the bridge.
- **SJ3** (3 pads, the middle one shared). The symbol draws a bridge between pads 1 and 2. **Rule on this board: pad 2 = the shared centre, pad 1 = the default (v8) position, pad 3 = the other position** (CONTEXT → Parts → Footprints).

**Current-measure links** (row h). A low-value resistor in a rail (R63, R64, R65 are 0 Ω; R66 is 10 mΩ), with an unfitted 2-pin header beside it (J30–J33, value "(DNP)" = do not populate). Lift the resistor and plug an ammeter into the header.

**Test points and ground points.** A signal test point is a round pad (TestPoint_Pad_D1.5mm, or D1.0mm for the strap pads); its value is the net it sits on. Every signal test point has its own **ground point**, a square GND pad placed beside it on the board (CONTEXT → Test points → Ground points). The partner is named in the ground point's description: "Ground point for TP10". Numbering:

| Sheet | Signal points | Their ground points |
|---|---|---|
| Power Management, LED Controller | TPn (TP10–TP37; there is no TP11, TP14 or TP16, because v7's TP3, TP1 and TP2 already cover those rails) | TP(n+40): TP10 → TP50 … TP37 → TP77 |
| Power Management, v7's points | TP1 `VSYS`, TP2 `VBAT`, TP3 `Protected_VBUS` | TP54, TP56, TP51 (TP4 is v7's own GND pad) |
| TCA9548A_Subsystem | TP80–TP91 (channels), TP114/TP115 | TP92–TP103, TP142/TP143 |
| ESP32_S3 | TPIO0, TPIO3, TPIO11–13, TPIO15/16, TPIO43–46, TP113 | TP130–TP141 |
| Root | TP110–TP112, TPIO10, TPIO21 | TP144–TP148 |

All 59 signal test points have their partner (script check, Phase 11e). **`TPIO<n>` always means GPIO n's own pad** (CONTEXT → Test points → As built).

**Rail LEDs.** A small LED and resistor on a rail, through a bridged SJ2, so the LED shows the rail is up and its ≈ 1 mA can be cut away for a v7 comparison.

**How labels sit.** After the Phase 11c tidy, labels are horizontal and their text runs away from the wire end they sit on. A few texts still touch their neighbours (45 small overlaps across the board, accepted at W3a); they don't change any connection.

### What a mistake looks like, in general

- **A label spelt differently from its partner.** It quietly makes a new net with only some of the pins. Highlight the net (backtick) and see whether every part you expect lights up.
- **An LED or diode backwards.** The triangle points the way current flows; the bar is the cathode (K, pin 1 on this board's LEDs). For a rail LED, the bar side goes towards `GND`.
- **A polarised capacitor backwards.** The electrolytic symbols (C22, C29, C30) mark "+" on pin 1; it must be on the higher-voltage net, never on `GND`.
- **A jumper's default wrong.** For an SJ3, the drawn bridge (pads 1–2) must join the centre to the v8 net in the tables below.
- **A test point without its ground point**, or a ground point whose description names the wrong TP.
- **A pin left dangling.** A pin end with no wire, label or X; ERC reports it.

---

## 2. Root sheet

**Where.** The sheet that opens first: the four sheet boxes; connectors J3, J4, J5, J6; test points TP110, TP111, TP112, TPIO10, TPIO21 with ground points TP144–TP148.

**What.**
- The boxes are wired to each other by the board-wide signals: `I2C_SDA`, `I2C_SCL` (the I²C bus), `LED_DATA`, `TCA_RESET`, `CHRG_INT`, `USB_DP`/`USB_DN`, and `BQ_SDA`/`BQ_SCL` (the charger's own I²C pins, which reach the bus on the TCA sheet through row f).
- **J4, J5, J6** are the three sensor-module cables (4-pin JST SH, CL-16): pin 1 `+3.3V_BUS`, pin 2 `GND`, pin 3 `CHn_SDA_CONN`, pin 4 `CHn_SCL_CONN` (n = 0, 1, 2).
- **J3** is the LED strip: pin 1 `+5V_TO_LEDS`, pin 2 `DATA_TO_LEDS` (from R105 on the LED sheet), pin 3 `GND`.
- **TP110/TP111** sit on `I2C_SDA`/`I2C_SCL` (the bus side of row a). **TP112** is on `LED_DATA` (row g's centre). TPIO10 is on `TCA_RESET`, TPIO21 on `CHRG_INT`.

**Why.** v7's TPIO43/44/16 sat on these nets. On v8 the bus is no longer GPIO43/44's own net, so they were renamed TP110–TP112, and the new TPIO43/44/16 sit on the GPIO pads themselves (CONTEXT → Test points → As built).

**Mistakes to look for.**
- A sensor connector with SDA and SCL swapped (pin 3 must be SDA, pin 4 SCL; the sensor boards expect it).
- A wire on a sheet pin that ends on nothing, or a sheet pin with no wire.
- The TCA box has a pin `VCC_3V3` from v7. It is the TCA's supply: on the root it is wired to a `+3.3V_BUS` power symbol (#PWR015), and inside the TCA sheet its label sits on U4 pin 24 with C9 and C10. `circuit-context.json` shows no net on it, which is an extractor quirk, not a missing wire (checklist item 10, corrected in Phase 11f).

---

## 3. ESP32_S3 sheet (A3)

The v7 module drawing is at the top; everything v8 added is in a grid below it, joined by labels.

### 3.1 The module (U3) and its support parts

**Where.** U3 (ESP32-S3-WROOM-1-N16R8), decoupling C51–C55, reset R50/C50/SW2 (`EN`), boot R51/SW3 (`GPIO0_BOOT`), USB series resistors R52/R53.

**What.** U3 is the processor. `EN` is its reset line (SW2 RESET pulls it low). `GPIO0_BOOT` low at reset enters the bootloader (SW3 BOOT). The USB pair arrives from the Power sheet as `USB_DP`/`USB_DN` and reaches U3 pins 14/13 through 22 Ω (R53/R52) as `USB_DP_MCU`/`USB_DN_MCU` (native USB, CL-07).

**Why.** Unchanged from v7, except the pins the GPIO allocation moved (CONTEXT → GPIO allocation).

**Mistakes to look for.**
- Anything on U3 pins 28–30 (GPIO35–37). They belong to the module's internal PSRAM and must stay unconnected; the symbol has no pins there.
- Anything that could pull **GPIO45 or GPIO46 high** at reset (strapping pins: a high level changes the flash voltage or boot mode). Their nets `U3_IO45`/`U3_IO46` must hold only U3 and the strap test pad (they do: 2 pins each).

### 3.2 Row a: which pins drive the I²C bus (JP1, JP2, J11)

**Where.** JP1 (SDA) and JP2 (SCL), 1 × 4 headers. J11, the UART0 header. Test points TPIO16, TPIO15, TPIO43, TPIO44 (pads), with TP132, TP133, TP130, TP131.

**What.** JP1 pins in order: 1 `U3_IO16`, 2 `I2C_SDA`, 3 `U3_IO43`, 4 `UART0_TX`. JP2: 1 `U3_IO15`, 2 `I2C_SCL`, 3 `U3_IO44`, 4 `UART0_RX`.
- **v8 (default):** shunts on 1–2 and 3–4. The bus runs on GPIO16/15, and GPIO43/44 go to J11 as a serial port (the chip's boot log).
- **v7:** one shunt on 2–3. The bus is back on GPIO43/44, as on v7. The single shunt physically blocks the other two positions.
- **No shunt** on 1–2 or 2–3: U3 is off the bus (used with row e).
- J11 pins: 1 `GND`, 2 `UART0_TX`, 3 `UART0_RX`, 4 no-connect. TX is the ESP's output, so it goes to a USB-serial adapter's RX.

**Why.** On v7 the ROM prints its boot log on GPIO43 = SDA at every boot (CL-02). GPIO16 is the one pad measured to give a normal I²C low on a v7 (card V7R-019). CONTEXT → Jumper matrix row a; GPIO allocation.

**Mistakes to look for.** Pins 1 and 3 swapped (then the v8 shunt would put GPIO43 on the bus). `UART0_TX` on the SCL header or `UART0_RX` on the SDA header.

### 3.3 Row e: external master header (J10, JP3, JP4)

**What.** J10 pins: 1 `GND`, 2 `EXT_SDA`, 3 `EXT_SCL`, 4 `+3.3V_BUS` (sense only). JP3 joins `EXT_SDA` to `I2C_SDA`, JP4 joins `EXT_SCL` to `I2C_SCL`. Both are **open** SJ2s.

**Why.** Lets an outside board (the Nano ESP32 used on the bench, V7R-004) drive the bus with U3 disconnected. No second master footprint (OQ-2). CONTEXT → Jumper matrix row e.

**Mistakes to look for.** JP3/JP4 drawn as bridged (they must be open: closing them puts the header's wires on the bus).

### 3.4 Row g: where `LED_DATA` comes from (JP5) and D5

**Where.** JP5 (SJ3); D5 (the on-board RGB LED, WS2812B-MINI).

**What.** JP5 centre (pad 2) is `LED_DATA`. Pad 1 (default, bridged) = `U3_IO18`; pad 3 = `U3_IO16` (v7). `LED_DATA` goes to D5's DIN (pin 1), to IC1 on the LED sheet, and to TP112. D5 runs from `+5V_CORE`.

**Why.** v7 drove the LEDs from GPIO16; v8 frees GPIO16 for the bus (CONTEXT → Jumper matrix row g; CL-06). D5's 3.3 V data into a 5 V LED is kept as v7 (CONTEXT → Kept v7 parts → Considered, not changed).

**Mistakes to look for.** The bridge drawn on pads 2–3 (that would make GPIO16 the default and put the LED loads on SDA). D5's DIN on `DATA_TO_LEDS` instead of `LED_DATA`.

### 3.5 Debug LEDs DBG1/DBG2 (D14, D15)

**What.** GPIO47 (`DBG1`) → R103 470 Ω → D14 blue → `GND`. GPIO48 (`DBG2`) → R104 → D15 white → `GND`. Firmware turns them on by driving the pin high.

**Why.** Spare pins for firmware status (CONTEXT → GPIO allocation, Test points → Debug LEDs).

**Mistakes to look for.** An LED with its bar towards the resistor (it would never light).

### 3.6 Test points, straps and the spare-GPIO header (J12)

**What.**
- TPIO0 `GPIO0_BOOT`, TP113 `EN`, TPIO13/12/11 on `INT1`/`INT2`/`INT3` (GPIO13/12/11, reserved for a future second bus or sensor interrupts, CL-05), each with its ground point.
- **Strap pads** TPIO3, TPIO45, TPIO46: tiny bare pads (value "STRAP …"), nothing else on the net. Each also has a ground point (TP139–TP141).
- **J12**, 2 × 15: odd pins = `U3_IO1`, `U3_IO2`, `U3_IO4`–`U3_IO9`, `U3_IO14`, `U3_IO17`, `U3_IO38`–`U3_IO42`; every even pin = `GND`, so each signal has a ground beside it.

**Why.** Probe access to every spare pin (CONTEXT → Test points → MCU and control; Headers).

**Mistakes to look for.** A J12 odd pin on `GND`, or an even pin on a signal. Two J12 pins on the same GPIO.

---

## 4. TCA9548A_Subsystem sheet

The TCA (U4) is at the top left with the upstream pull-ups; the channel test points form a grid at the top right; then one row of parts per channel; the row d/f selectors are at the bottom.

**Terms.** I²C is a two-wire bus: **SDA** (data) and **SCL** (clock). Chips only ever pull a line **low**; a **pull-up** resistor brings it back high, and its value sets how fast the line rises. **Upstream** = the processor's side of the TCA; **downstream** = a channel's side, towards a sensor cable. The TCA9548A is a **multiplexer**: it connects the upstream bus to one channel at a time.

### 4.1 The TCA (U4)

**What.** U4 pin 23 `I2C_SDA`, pin 22 `I2C_SCL` (upstream); pins 4–9 = `CH0_SDA`, `CH0_SCL`, `CH1_SDA`, `CH1_SCL`, `CH2_SDA`, `CH2_SCL`; pin 3 `TCA_RESET` (R6 10 k pull-up); pin 24 `+3.3V_BUS`; address pins 1, 2, 21 and pin 12 on `GND`. C9/C10 decouple it.

**Why.** As v7 (CONTEXT → Kept v7 parts: U4). R6 now on the bus rail (CONTEXT → Power path → As built).

**Mistakes to look for.** A channel's SDA and SCL swapped at U4 (pin 4 SDA, pin 5 SCL for CH0, and so on).

### 4.2 Row d upstream: pull-up selector (JP19, JP20)

**What.** JP19 (2 × 3) for SDA: pins 1, 3, 5 = `I2C_SDA`; pin 2 = `PU_SDA_2K2` (R28 2.2 k), pin 4 = `PU_SDA_4K7` (R86 4.7 k), pin 6 = `PU_SDA_10K` (R87 10 k); each resistor's other end on `+3.3V_BUS`. JP20 is the same for SCL (R29, R88, R89). A shunt across one column picks one value; 1–2 (2.2 k, as v7) ships fitted.

**Why.** Lets the bench vary pull-up strength without soldering (CONTEXT → Jumper matrix row d; Parts → Rise time). `I2C_PU_RAIL` in older notes is `+3.3V_BUS`.

**Mistakes to look for.** A resistor's free end on `I2C_SDA` itself (it would always be connected). Values in the wrong column (pin 2 must be the 2.2 k).

### 4.3 Row f: the charger on the bus (JP27, JP28)

**What.** JP27 joins `I2C_SDA` to `BQ_SDA`; JP28 joins `I2C_SCL` to `BQ_SCL`. Shunts fitted (v8 = v7). TP114/TP115 sit on `BQ_SDA`/`BQ_SCL`.

**Why.** Pulling a shunt takes the charger (U5) off the bus to see whether it is the device holding the bus low (CONTEXT → Jumper matrix row f).

**Mistakes to look for.** `BQ_SDA` and `BQ_SCL` crossed between the two headers.

### 4.4 One row per channel: series resistor, row b, TVS, row d downstream

For channel 0 (channels 1 and 2 repeat with the next numbers):
- **Series resistor** R80 (SDA) and R81 (SCL), 47 Ω, between the TCA side `CH0_SDA`/`CH0_SCL` and the connector side `CH0_SDA_CONN`/`CH0_SCL_CONN`.
- **Row b bypass** JP10/JP11, 1 × 2 headers across R80/R81. Shunt off = v8 (resistor in line); shunt on = v7 (resistor shorted).
- **TVS** U11 (TPD2E2U06): a static-zap clamp on the connector side, pin 3 `CH0_SDA_CONN`, pin 5 `CH0_SCL_CONN`, pin 4 its ground leg `CH0_TVS_GND`. **Row b GND leg** JP16 joins `CH0_TVS_GND` to `GND`: shunt on = v8 (protection active), off = v7.
- **Row d downstream** JP21/JP22, open SJ2s, each in series with a 4.7 k (R90/R91) to `+3.3V_BUS`. Open by default.
- Test points TP80–TP83 on the four channel-0 nets.

| Channel | Series R | Bypass | TVS / GND leg | Downstream PU | Test points |
|---|---|---|---|---|---|
| 0 | R80, R81 | JP10, JP11 | U11 / JP16 | JP21, JP22; R90, R91 | TP80–TP83 |
| 1 | R82, R83 | JP12, JP13 | U12 / JP17 | JP23, JP24; R92, R93 | TP84–TP87 |
| 2 | R84, R85 | JP14, JP15 | U13 / JP18 | JP25, JP26; R94, R95 | TP88–TP91 |

**Why.** The sensor cables are the board's most exposed wires. The resistor limits how much of a zap reaches the TCA; the TVS takes the rest (CONTEXT → Parts → Cable-facing protection; Jumper matrix rows b and d). The sensor boards already carry their own 4.7 k pull-ups, which is why the on-board downstream ones ship open.

**Mistakes to look for.**
- A TVS on the TCA side (`CHn_SDA`) instead of the connector side (`CHn_SDA_CONN`).
- A bypass header across the wrong resistor (JP10 must sit on R80's two nets).
- A downstream SJ2 drawn bridged.
- One channel's `_CONN` label touching the TVS's `GND` label (A7/A8/B7/B8): known text overlaps, not connections.

---

## 5. Power Management sheet (A3)

The busiest sheet. The v7 circuit (USB-C, charger, boost, regulators) is drawn as a circuit across the top. Everything v8 added is placed in rows below and to the right and joined **by net labels**, so follow it by name. The sheet was left as is at W3a (OQ-10).

**Terms.** A **rail** is a supply net (`+5V`, `VSYS`). A **regulator** turns one voltage into another, steady one; a **boost** converter raises it, an **LDO** (linear regulator) lowers it. A **fuse** opens on overcurrent. A **MOSFET** (Q) here is used as an on/off switch; its **gate** (G) controls the switch between **drain** (D) and **source** (S), and every MOSFET has a built-in **body diode** from drain to source (for these P-type parts, it conducts from drain to source).

### 5.1 The power tree in one picture

```
USB-C J7 ─ VBUS_RAW ─ F2 ─ Protected_VBUS ─┐
                                           U5 charger ─ VSYS ─ R44 ─ VSYS_SENSE ─ U6 boost ─ +5V
Cell J8 ─ BAT_CONN ─ F3 ─ BAT_FUSED ─ Q20 ─ BAT_COMMON ─ Q21 ─ VBAT ─┘
+5V ─ R65 (h3) ─ +5V_CORE ─┬ U8 ─ +3.3V_MCU_REG ─ R63 (h1) ─ +3.3V_MCU
                           └ U10 ─ +3.3V_BUS_REG ─ JP30 (row c) ─ +3.3V_BUS_HDR ─ R64 (h2) ─ +3.3V_BUS
+5V ─ F1 ─ +5V_LED_F ─ R66 (h4) ─ +5V_LED_H4 ─ R27 ─ +5V_TO_LEDS   (LED Controller sheet)
```
CONTEXT → Power path → v8 power tree.

### 5.2 USB input (J7, F2, U9, R30/R31)

**What.** J7's VBUS pins (A4B9, B4A9) are `VBUS_RAW` (TP10). F2 (3 A resettable fuse) → `Protected_VBUS` (TP3), decoupled by C20, C21, C22. U9 (USBLC6) clamps static on `USB_DP`/`USB_DN` and has its supply pin on `Protected_VBUS`. R30/R31 (5.1 k on `CC1`/`CC2`) tell a USB-C source "I am a device". J7's shell pin (0) is on `GND`.

**Why.** As v7, except the shell: v7's PCB footprint left the shell legs unnumbered, so they had no net; v8's footprint numbers them "0" (CONTEXT → Power path → Phase 10 checks, J7 shell).

**Mistakes to look for.** C22 (electrolytic) with "+" on `GND`. `USB_DP` and `USB_DN` swapped between J7 and U9 (U9 pins 1/6 = `USB_DP`, 3/4 = `USB_DN`).

### 5.3 The charger U5 (BQ24195) and rows j, k, l

**Terms.** U5 is a **charger with power path**: it takes USB power, makes `VSYS` for the board, charges the cell, and, with no USB, connects the cell to `VSYS` through an internal switch (the BATFET).

**Where.** U5 and its parts: L1 (`BQ_SW` → `VSYS`), C23 (`BQ_BTST`), C24 (`BQ_REGN`), PMID bank C25, C26, C63, C64, C69, C70 (`BQ_PMID`), `VSYS` caps C27, C28, C29, R32 (`BQ_ILIM`), R35, R36, R37, R38, TH1; jumpers JP32, JP33, JP34, JP35; J9.

**What, pin by pin.** Pins 1/24 `Protected_VBUS` (in); 13/14 `VBAT` (cell); 15/16 `VSYS` (out); 23 `BQ_PMID`; 22 `BQ_REGN` (its own small internal supply, alive only with USB in); 5/6 `BQ_SCL`/`BQ_SDA`; 7 `CHRG_INT` (R38 pull-up to `+3.3V_MCU`); 9 CE on `GND` (charging enabled); 10 `BQ_ILIM` (R32 330 Ω sets the input-current ceiling, 1.32–1.61 A); 11/12 `BQ_TS` (temperature sense, both pins joined as the datasheet requires).

**Why: the "needs an I²C command" fault.** On v7, with D+ and D− grounded, the charger decides it is on a PC port and limits itself to 100 mA until firmware raises it, so the board browns out on USB alone (CONTEXT → Inherited v7 faults → BQ24195, root cause 1–5). v8 fixes it with two solder jumpers:
- **Row j** (JP32 SJ3 + JP33 SJ2). JP32 centre (pad 2) = `BQ_DM`; pad 1 (default) = `BQ_DP`; pad 3 = `GND`. JP33 joins `BQ_DP` to `GND`, **open** in v8. Default: D+ shorted to D−, which reads as a charger port: 1.5 A from plug-in, no firmware needed. v7: JP32 to pad 3 and JP33 closed (both pins grounded).
- **Row k** (JP34 SJ3). Centre = `OTG_PU`, R35's top end; R35's other end is `OTG_BIAS`, U5 pin 8 (TP32). Pad 1 (default) = `BQ_REGN`; pad 3 = `+3.3V_MCU` (v7). REGN exists before the board's 3.3 V does, so the OTG pin is high from the start, which raises the fallback limit to 500 mA.
- **Row l** (JP35 SJ3). Centre = `BQ_TS` via the divider R36 (from `BQ_REGN`) / R37 (to `GND`). Pad 1 (default, = v7) = `TS_BOARD`, TH1 on the board; pad 3 = `TS_CELL`, J9 (a thermistor taped to the cell). With nothing plugged into J9 in the pad-3 position, charging is suspended and the STAT LED blinks (CONTEXT → Power path → Cell temperature).

**STAT LED (D10, R62).** `VSYS` → R62 2.2 k → `STAT_LED_A` → D10 (orange, anode) → D10 cathode on `BQ_STAT` (U5 pin 4, TP35). U5 pulls STAT low while charging, which lights it. CONTEXT → Other v7 deviations fixed, STAT LED rail.

**Mistakes to look for.**
- JP32 or JP34 drawn with the bridge on pads 2–3 (the v7 default would bring back the 100 mA fault).
- JP33 drawn bridged (with JP32 at pad 1 it would ground both D+ and D−: the v7 fault again).
- D10 with its bar on `STAT_LED_A` (backwards: never lights).
- U5 pins 11 and 12 on different nets.
- PMID capacitors on `Protected_VBUS` instead of `BQ_PMID` (the datasheet asks ≥ 60 µF on PMID; there are 6 × 22 µF).

### 5.4 The battery path, by net name (J8, F3, Q20, Q21, SW4)

This is the block that protects against the "battery cooked the board" faults (CONTEXT → Inherited v7 faults → Battery connection, mechanisms B1–B3). It sits as a column on the right of the sheet. Follow it with the net highlight:

1. **`BAT_CONN`**: J8 pin 2 (XT30 connector, "+"), F3 pin 1, TP37 (ground point TP77). J8 pin 1 is `GND`. The XT30 housing is keyed, so the cell can't go in backwards (B1).
2. **`BAT_FUSED`**: F3 pin 2 (7 A fuse, the first part after the connector), Q20 pins 1–3 (drain), TP17.
3. **`BAT_COMMON`**: Q20 pin 5 (source) and Q21 pin 5 (source) joined; R60 and C60 to the gate; TP18. This is the "back-to-back" joint.
4. **`VBAT`**: Q21 pins 1–3 (drain), C30 (47 µF, "+" here), C62 (10 µF), C61, U5 pins 13/14, TP2.
5. **`BAT_GATE`**: both gates (Q20 pin 4, Q21 pin 4); R60 1 M to `BAT_COMMON` (holds the switch off), C60 220 nF to `BAT_COMMON`, C61 22 nF to `VBAT` (sets the slow turn-on), R61 47 k to `BATT_SW_COM`; TP19.
6. **`BATT_SW_COM`**: SW4 ("BATT") common, pin 2. SW4 pin 1 = `GND` (ON: pulls the gate low, both FETs conduct). The OFF throw (pin 3) is unconnected: the gate floats up to `BAT_COMMON` through R60 and both FETs turn off.

**Why.**
- **Back-to-back P-FETs (Q20, Q21, CSD25402Q3A)** replace v7's single AO3401A. Their body diodes face each other, so a reversed cell is blocked (B1), and the cell is fully isolated when off.
- **Full gate drive.** Vgs ≈ −0.955 × cell voltage; v7's Q2 was under-driven (B2).
- **Slow turn-on.** R61/C61 ramp the gate, so plug-in inrush is ≈ 1 A instead of an uncontrolled spike (B3).
- **F3** catches a short anywhere downstream, including a failed FET; v7 had no battery-side fuse.
- **SW4** is the battery's own off switch, because the boost now runs whenever `VSYS` exists (row i). Cost: no charging with SW4 OFF.
- **No v7 position** for this block: accepted by the user 2026-11-03 (CONTEXT → Battery connection and protection).

**Mistakes to look for.**
- A drain (pins 1–3) on `BAT_COMMON`, or a source (pin 5) on `BAT_FUSED` or `VBAT`. Either way, one body diode would point the wrong way and reverse protection would be lost. If the symbol draws the body diodes, both should point towards `BAT_COMMON`.
- F3 after Q20 instead of before it (`BAT_FUSED` must be on Q20's drain).
- C30's "+" on `GND`, or C30 on `BAT_FUSED`/`BAT_CONN` (it belongs behind the protection, on `VBAT`).
- SW4's common on `GND` and a throw on `BATT_SW_COM` (swapped pins: the switch would do nothing).
- A label `VBAT` spelt `V_BAT` or `VBATT` on one of the five `VBAT` connections.

### 5.5 VSYS, the INA219 and the boost (U7, R44, U6, row i)

**What.**
- `VSYS` (TP1) → R44 (10 mΩ) → `VSYS_SENSE` (TP15). **U7** (INA219, a current/voltage monitor on the I²C bus) reads the drop across R44: pin 1 `VSYS`, pin 2 `VSYS_SENSE`, pin 4 `+3.3V_BUS`, pins 5/6 `I2C_SCL`/`I2C_SDA`.
- **U6** (TPS61088 boost): pin 9 VIN on `VSYS_SENSE` via L2 (pins 4–7 `BOOST_SW`); output pins 14–16 = `+5V` (TP20), with C34, C35, C36, C42. Feedback R39 180 k / R40 56 k on `BOOST_FB` (TP31) sets 5.07 V. R42 sets its current limit, R41 its frequency, C37 its soft start. `BOOST_VCC` (TP30) is its internal supply.
- **Row i** (JP31 SJ3): centre = `BOOST_EN` (U6 pin 2, TP29; R2 100 k pull-down). Pad 1 (default) = `VSYS_SENSE`: the boost is always on. Pad 3 = `SW1_COM`, SW1's common (v7: SW1 is the boost's on/off switch). SW1 is wired exactly as v7: pin 1 `VSYS_SENSE`, pin 3 `GND`.

**Why.** On v7, SW1 at its GND throw left the boost off even on USB: +5V sat at ≈ 3.8 V, the 3.3 V regulator dropped out, and the Mac found no ESP32. That looked like a dead board (cards PWR-001, PWR-002; CL-11). v8 ties EN on by default; SW4 is the off switch instead. The boost's parts are v7's, so +5V behaves as on v7 (CONTEXT → Boost and enable).

**Mistakes to look for.**
- JP31's bridge on pads 2–3 (that brings back "SW1 off = dead on USB" as the default).
- R39 and R40 swapped (the output would be ≈ 1.6 V instead of 5.07 V).
- U7's pins 1 and 2 swapped (the current reads negative).
- C29 (220 µF electrolytic on `VSYS`) with "+" on `GND`.

### 5.6 Regulators and current-measure links (U8, U10, rows c and h)

**What.**
- `+5V` → **R65 (h3)**, 0 Ω 2512, header J32 beside it → `+5V_CORE` (TP21). Feeds U8, U10 and D5.
- **U8** (AMS1117, LDO): pin 3 VIN `+5V_CORE`, pins 2/4 VOUT `+3.3V_MCU_REG` (TP24), C40 and C43 (tantalum, "+" on `+3.3V_MCU_REG`). → **R63 (h1)**, J30 → `+3.3V_MCU` (TP25): the processor's rail.
- **U10** (AP2112K, LDO): pin 1 VIN `+5V_CORE`, pin 3 EN on `+3.3V_MCU`, pin 5 VOUT `+3.3V_BUS_REG` (TP26), C67.
- **Row c** (JP30, 1 × 3 header): pin 1 `+3.3V_BUS_REG`, pin 2 `+3.3V_BUS_HDR` (TP27), pin 3 `+3.3V_MCU_REG`. Shunt 1–2 (default) = separate bus regulator; 2–3 (v7) = U8 feeds everything; no shunt = bus rail off.
- `+3.3V_BUS_HDR` → **R64 (h2)**, J31 → `+3.3V_BUS` (TP28; C68): the I²C bus, pull-ups, TCA, INA219 and sensor cables.

**Why.**
- v6 had a separate bus regulator; v7 shared one (CL-03, CL-08). Row c lets you test both.
- U10's EN on `+3.3V_MCU` means the bus rail can't be up while U3 is unpowered, so the pull-ups can't feed U3 through its pins (CONTEXT → Regulators → Back-powering).
- Row h links let an ammeter go in each rail (CONTEXT → Current-measure links).

**Mistakes to look for.**
- JP30 pins 1 and 3 swapped (the default shunt would then share the rail).
- U10's EN on `+5V_CORE` or `+3.3V_BUS` (the back-power guard would be lost).
- A link header J30–J32 on different nets from its resistor (each must sit on exactly its link's two nets).

### 5.7 Rail LEDs (D1, D11, D12, D13)

**What.** Each: rail → bridged SJ2 → resistor → LED anode; cathode on `GND`.

| LED | Rail | Jumper | Resistor | Colour |
|---|---|---|---|---|
| D1 | `+3.3V_MCU` | JP40 | R1 1 k | green (v7's LED) |
| D11 | `+3.3V_BUS` | JP41 | R100 1 k | green "BUS" |
| D12 | `+5V` | JP42 | R101 3.3 k | yellow |
| D13 | `Protected_VBUS` | JP43 | R102 3.3 k | red |

**Why.** You can see at a glance which rails are up: the #0004 case (boost off) shows as no yellow. Cutting JP41–JP43 removes the LEDs v7 didn't have, for a faithful v7 load; JP40 stays closed in the v7 set (CONTEXT → Test points → Debug LEDs).

**Mistakes to look for.** An LED with its bar towards the resistor. A jumper drawn open (they ship bridged).

### 5.8 Rail and control test points

Rail points TP10–TP37 and v7's TP1–TP3, each with its TP(n+40) ground point (table in §1), in three rows at the bottom left. The control nodes have points too: `BOOST_EN`, `BOOST_VCC`, `BOOST_FB`, `BAT_GATE`, `OTG_BIAS`, `BQ_TS`, `BQ_ILIM`, `BQ_STAT`. The two switching nodes (`BQ_SW`, `BOOST_SW`) deliberately get no pad: probe at the inductor (CONTEXT → Test points → Power control nodes).

**Mistakes to look for.** A test point whose value (the net name text) differs from the label it actually sits on.

---

## 6. LED Controller sheet

**Where.** F1, R66, J33, R27, C7, C8, IC1, R105, TP22, TP36, TP23 (ground points TP62, TP76, TP63).

**What.**
- `+5V` → **F1** (3 A fuse) → `+5V_LED_F` (TP22) → **R66 (link h4)**, 10 mΩ shunt with header J33 → `+5V_LED_H4` (TP36, C7) → **R27** 0.1 Ω (v7's strip current sense) → `+5V_TO_LEDS` (TP23, C8) → J3 pin 1.
- **IC1** (SN74AHCT1G125): pin 2 input `LED_DATA` (3.3 V from U3) → pin 4 output `DATA_TO_LEDS_IC1` (5 V) → **R105** 33 Ω (row m, added at W3) → `DATA_TO_LEDS` → J3 pin 2. Pin 5 VCC `+5V_TO_LEDS`; pin 1 (output enable) on `GND`, so it is always on.

**Why.**
- IC1 changes the 3.3 V data to the 5 V the strip expects. It replaces v7's 4-gate chip with a single gate: v7's part is out of stock, and v7 used one gate anyway (CONTEXT → Kept v7 parts → Swaps).
- R66 lets you read the strip current as 10 mV/A across J33, or lift it for an ammeter; R27 stays as v7 (user decision 2026-11-04; CONTEXT → Power path → As built).

**Mistakes to look for.**
- IC1's pins 2 and 4 swapped (input and output reversed).
- R105 not in line: IC1 pin 4 and J3's `DATA_TO_LEDS` must be on opposite ends of R105.
- J33 not across R66 (its pins must be `+5V_LED_F` and `+5V_LED_H4`).
- The labels `+5V_LED_F` and `+5V_LED_H4` near F1 and R27 run into each other on screen (a known text overlap, zone B3/C3). Check by highlight which wire each belongs to.

---

## 7. W3 checklist

**Status: all 11 items resolved at W3 (user, 2026-11-07; applied in Phase 11f).** The user found no errors in the schematic or this guide. Items 1–8 approved as drawn. Items 9–11 below carry their outcome.

Work through the sheets with sections 2–6, then these items. Each needs your decision or a look; nothing here is a known error.

**Still open from the Phase 11 review (SESSION.md Worker #11).**
1. **Root:** do the names TP110/TP111/TP112 (renamed from v7's TPIO43/44/16) read as you want? The alternative is to keep v7's names, at the cost that "TPIO43" would then not be GPIO43's pad.
2. **ESP32_S3, row a and J11:** JP1/JP2 pin order (§3.2) and J11's order, GND/TX/RX/NC (TX goes to an adapter's RX).
3. **ESP32_S3, J12:** the spare-GPIO pin order (§3.6) suits how you'll plug things in.
4. **ESP32_S3, D14/D15:** DBG1 blue on GPIO47, DBG2 white on GPIO48 (§3.5).
5. **ESP32_S3, strap pads:** TPIO3/TPIO45/TPIO46 each have a ground point (TP139–TP141). Confirm a GND pad beside a strap pad is wanted (harmless: nothing connects them).
6. **TCA9548A_Subsystem:** the row b/d/f grid (§4.2–4.4) and TP114/TP115 at the bottom.
7. **Power Management:** the battery block (§5.4); rows c, h, i, j, k, l (§5.3, 5.5, 5.6); rail LEDs D11–D13 with JP41–JP43, and JP40 for D1 (§5.7).
8. **LED Controller:** IC1 in its SOT-23-5 package and the h4 chain R66/J33/R27 (§6). R66 is decided (kept); this is a look only.

*Items 1–8: resolved, approved as drawn (W3, 2026-11-07).*

**Open from the kicad-happy review (Phase 11d, SESSION.md Worker #15, item 23).**

9. **J3's LED data line has no protection.** IC1's output (pin 4, `DATA_TO_LEDS`) goes straight off the board to J3 pin 2, with no series resistor and no static clamp. v7 was the same. The strip cable is handled by hand, and a long cable makes the signal "ring". Common practice is a small resistor (33–100 Ω) in series at IC1, and sometimes a small clamp diode at J3. If you want it: fit the resistor (or a 0 Ω / solder-bridge footprint for v7 comparisons) on the LED sheet. Optional; nothing in the v7 debug track suspects the strip.
   *Resolved (W3): added.* R105, 33 Ω (C23140), at IC1 pin 4; IC1 pin 4 is now on `DATA_TO_LEDS_IC1`. It is jumper row m: v7 position = 0 Ω or the pads bridged. No clamp diode. The all-v7 netlist check still shows 0 nets differing from v7.

**Smaller items found while writing this guide.**

10. **TCA box pin `VCC_3V3`** (root sheet) is a v7 leftover with no net on it (§2). Harmless; delete it or leave it.
   *Resolved (W3, Phase 11f): kept, because this item was wrong.* The pin is how U4 gets power. With it deleted (tried on a scratch copy), U4 pin 24, C9 and C10 end up on a net of their own. `circuit-context.json` showed no net because of an extractor quirk (§2). `--check` now confirms that U4 pin 24 is on `+3.3V_BUS`.
11. **PMID capacitors:** CONTEXT → Phase 10 checks allows trimming the 6 × 22 µF bank (C25, C26, C63, C64, C69, C70) if the capacitor maker's DC-bias curve says fewer are enough. Default: keep all six.
   *Resolved (W3): all six kept.*

**Decide when convenient (not needed for W3).** Still open after W3: the user hasn't decided. OQ-9: whether kicad-happy becomes a standing step in the pre-order review. The Phase 11d recommendation is no, with an optional PCB-analyzer trial at Phase 18 (SESSION.md Worker #15).

**Already closed (for reference, no action).** R66 kept; BAT_CONN test point added (TP37/TP77); LED currents kept; Q20/Q21/U10 symbols updated from the library and the SW1 wire's stray tail trimmed (Phase 11c; the wire stays and carries SW1 pin 1 to `VSYS_SENSE`); the field and label tidy and GUI autoplace done (Phases 11a–11c); no re-layout of the power and TCA sheets (W3a).

**After any edit in KiCad.** Save, close KiCad (no `~*.lck` file left in `hardware/pcb-main-v8/kicad/`), then:
```
python3 tools/schematic-modify/v8_debug_sheet.py --check      # must end PHASE 11 CHECK PASSED (includes ERC and layout_check)
python3 tools/schematic-context/extract.py hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch --previous hardware/pcb-main-v8/kicad/circuit-context.json
python3 tools/lab/check_state.py --fresh hardware/pcb-main-v8/kicad/circuit-context.json
```
A KiCad save merges straight wires and adds empty Description fields; the checks allow for both (SESSION.md Worker #14).
