200# Interrupt Strategy Refactor — Exploration

**Date:** March 23, 2026
**Status:** Exploring

---

## Problem Statement

Our original interrupt design combined two VCNL4040 INT lines per sensor module into a single shared line using BAT54S Schottky diodes (wired-OR). This was intended to reduce cable wires (5-pin JST-SH) and ESP32 GPIO usage (3 GPIOs for 6 sensors). In testing, we discovered a fundamental flaw: when a ball transits the hoop, both sensors on a module trigger so close together that by the time the ESP32 reads the interrupt registers via I2C, both have already fired. The ordering information — which sensor triggered first — is lost.

We abandoned interrupts and switched to proximity polling (reading PS_DATA directly). Polling works for wave-shape characterization but provides limited direction-detection precision: the timestamp of a threshold crossing is only as accurate as the poll interval (±1-3ms at current rates).

With the board redesign underway, we want to evaluate whether interrupts are worth revisiting, and if so, what architecture gives us reliable direction ordering without adding cable wires.

## Background: Why the Original Design Failed

### The Shared INT Circuit

On each rigid sensor PCB:
- D2, D3 (BAT54S dual Schottky) combine INT_A and INT_B into one line
- R5 (8.2kΩ) pulls the combined line high
- The combined INT routes through the JST-SH cable to the ESP32

The VCNL4040 INT pin is open-drain active-low. When either sensor crosses its proximity threshold, the combined line goes low. The ESP32 sees the falling edge and enters the ISR.

### The Race Condition

To determine which sensor triggered, the ISR must read the VCNL4040's INT_Flag register (0x0B) on each sensor via the I2C mux chain:

1. Select PCA9546A channel 0 → read INT_Flag on sensor A (~170μs)
2. Select PCA9546A channel 1 → read INT_Flag on sensor B (~170μs)

Total: ~340μs minimum. But the two VCNL4040 sensors on the same module have independent internal oscillators running at ~100Hz (10ms period). For a ball crossing the detection zone at moderate speed, both sensors' measurements update within a few hundred microseconds to a few milliseconds of each other. By the time the ESP32 finishes reading sensor A's registers, sensor B has already triggered. Both INT_Flag registers show active — ordering is lost.

### Why Diodes Weren't the Problem

The BAT54S diodes were good engineering practice (preventing backfeed during interrupt clearing), but they weren't the cause. Even direct wiring of two open-drain outputs (valid for active-low open-drain signals) would produce the same result. **A shared signal line cannot encode temporal ordering.**

---

## Requirements for a Viable Interrupt Solution

1. **Reliable ordering**: must determine which sensor on a module triggered first, 100% of the time
2. **No additional cable wires** (strongly preferred): keep JST-SH at 4 pins (3.3V, GND, SDA, SCL)
3. **Minimal rigid board complexity**: prefer adding one IC over a multi-chip latch circuit
4. **Compatible with polling**: interrupts augment the existing polling data (wave shape), they don't replace it
5. **Self-resetting**: the system should re-arm automatically after each transit without firmware intervention on the sensor board

---

## Solution: MCP23008 I2C GPIO Expander as Priority Latch

### Key Insight

The MCP23008 (Microchip 8-bit I2C GPIO expander) has an **INTCAP register** that captures a snapshot of all GPIO pin states at the moment the *first* interrupt fires, and **holds that snapshot until read by the host**. Subsequent pin changes do not update INTCAP until it is read and cleared. This is exactly a hardware priority latch — the first event wins, and the second event's timing is irrelevant.

### Architecture

```
On the Rigid Sensor PCB:
                                          ┌──────────────────┐
                                          │    MCP23008       │
VCNL4040_A (INT, active low) ──────────── │ GPIO0      SDA ──│──┐
                                          │                   │  │
VCNL4040_B (INT, active low) ──────────── │ GPIO1      SCL ──│──│──┐
                                          │                   │  │  │
                              VCC ─── R ──│ RESET     INTA ──│  │  │ (optional, not routed to cable)
                                          │                   │  │  │
                              ┌───────────│ A0,A1,A2   VDD ──│  │  │
                              │  (addr)   │             GND ──│  │  │
                              │           └──────────────────┘  │  │
                              │                                 │  │
Existing PCA9546A ──────── SDA ─────────────────────────────────┘  │
                           SCL ────────────────────────────────────┘
                              │
                    To main board via 4-pin JST-SH
                    (3.3V, GND, SDA, SCL — unchanged)
```

The MCP23008 sits on the upstream I2C bus alongside the PCA9546A. Both are directly addressable by the ESP32 without mux switching. The VCNL4040 INT lines connect to MCP23008 GPIO inputs instead of being combined through diodes.

### How It Works

**Setup (one-time, during sensor initialization):**
- Configure MCP23008 GPIO0 and GPIO1 as inputs
- Set DEFVAL register = 0xFF (default pin state = high)
- Set INTCON register = 0x03 (compare against DEFVAL, not previous state)
- Set GPINTEN register = 0x03 (enable interrupt on GPIO0 and GPIO1)

**Configure VCNL4040s in logic output mode** (`PS_MS = 1` in register 0x04):
- INT goes low when proximity exceeds PS_THDH
- INT auto-returns high when proximity drops below PS_THDL
- No register clearing needed — INT tracks object presence in real time

**Sequence when ball passes through (Side A triggers first):**

```
Time ────────────────────────────────────────────────────────────►

VCNL4040_A INT: ──────┐                                   ┌──────
                      └───────────────────────────────────┘
                      ↑ A fires (threshold crossed)

VCNL4040_B INT: ───────────┐                          ┌──────────
                           └──────────────────────────┘
                           ↑ B fires (Δt later)

MCP23008 INTCAP:      ◄── captured here: GPIO0=0, GPIO1=1 ──────►
                      (A=active, B=not yet)
                      Holds until ESP32 reads INTCAP
```

**What the ESP32 reads during its next poll cycle:**

| Register | Value | Meaning |
|----------|-------|---------|
| INTF | 0x03 (both bits set) | Both sensors have triggered |
| INTCAP | 0x02 (bit 0 = 0, bit 1 = 1) | At time of first interrupt: GPIO0 (A) was active, GPIO1 (B) was not |
| **Conclusion** | | **Side A triggered first** |

Reading INTCAP clears the MCP23008's interrupt state. In logic output mode, the VCNL4040 INTs auto-reset when the ball leaves the detection zone. The system is fully re-armed for the next transit with no firmware intervention.

### Direction Detection Integration

The MCP23008 ordering data integrates with the existing polling pipeline as supplementary evidence:

- **Polling** provides: wave shape, peak amplitude, wave duration, adaptive baseline
- **MCP23008** provides: which side crossed threshold first (binary: A-first or B-first)

These are independent measurements of the same event. The MCP23008 ordering serves as high-confidence confirmation of the direction inferred from wave timing analysis. In cases where the wave shapes are ambiguous (fast transit, low SNR), the hardware ordering is definitive.

The firmware reads MCP23008 INTF + INTCAP as part of the regular poll cycle. When INTF is non-zero, the ordering data is extracted and attached to the current detection event. When INTF is zero, no detection is in progress — skip.

### I2C Overhead

| Operation | Time |
|-----------|------|
| Read INTF (1 register, 2 bytes) | ~120μs |
| Read INTCAP (1 register, 2 bytes) | ~120μs |
| Per MCP23008 | ~240μs |
| All 3 boards (worst case) | ~720μs |

Options for when to read:
- **Every poll cycle**: adds ~720μs to the ~1,800μs cycle → ~2,500μs, ~400Hz. Acceptable.
- **Conditional**: only read when proximity values are elevated (transit in progress). Zero idle overhead.
- **Periodic**: every Nth cycle. Detection events last 30-100ms, so reading every 5-10ms catches everything.

### VCNL4040 Interrupt Configuration

For the MCP23008 approach, the VCNL4040s need specific interrupt settings:

```
PS_MS register (0x04 high byte):
  PS_MS = 1          (logic output mode — INT follows proximity state)
  LED_I = 0x07       (200mA, unchanged)

PS_CONF2 register (0x03 high byte):
  PS_INT = 0x01      (trigger when close — INT pulls low above PS_THDH)
  PS_HD = 1          (16-bit, unchanged)

PS_CONF1 register (0x03 low byte):
  PS_PERS = 1        (single measurement above threshold fires interrupt)
  PS_Duty, PS_IT     (unchanged from current config)

PS_THDH register (0x07):
  Set to detection threshold (calibrated per-sensor during initialization)

PS_THDL register (0x06):
  Set below PS_THDH for hysteresis (e.g., PS_THDH - 20% of signal range)
```

The threshold values (PS_THDH / PS_THDL) define when the VCNL4040 asserts its INT line. These must be calibrated to distinguish a ball at center-of-hoop from baseline noise. The existing adaptive baseline system in DirectionDetector can inform initial threshold values, which are then written to the sensor registers at boot.

---

## Alternative Approaches Considered

### Option A: Dedicated INT Lines (6-pin JST-SH)

Add a second INT wire to each cable, giving each VCNL4040 its own GPIO on the ESP32.

| Aspect | Assessment |
|--------|-----------|
| Direction precision | Excellent — ISR timestamps (μs) or MCPWM capture (ns) |
| Cable wires | 6 (vs current 4-pin plan) |
| ESP32 GPIOs | 6 dedicated to INT |
| Rigid board changes | Remove D2/D3/R5, route INT lines to cable |
| Firmware | ISR management + poll loop |
| Bonus: transit speed | Threshold-crossing timestamps enable speed calculation |

**Trade-off**: Simplest hardware, best precision, but adds 2 wires per cable. The ESP32-S3's MCPWM capture channels (6 available) could give ~12.5ns hardware timestamps — far beyond what's needed for direction detection, but potentially useful for transit speed estimation.

**When to prefer this**: If cable wire count is not a constraint, or if precise threshold-crossing timestamps (not just ordering) become valuable for transit speed measurement or other features.

### Option B: PCA9545A Swap (Replace PCA9546A)

The PCA9545A is pin-compatible with the PCA9546A (same TSSOP-20 footprint) but adds per-channel interrupt inputs and a status register.

| Aspect | Assessment |
|--------|-----------|
| Interrupt status | Reads which channels have active INTs without switching |
| Priority detection | **No** — shows current state, not ordering |
| Drop-in replacement | Yes, same footprint and function |
| Cost | $0.71-0.90 (potentially cheaper than PCA9546A) |
| Cable wires | 4 (unchanged) or 5 (if upstream INT output routed to cable) |

**Problem**: The PCA9545A's interrupt register reflects the *current* state of each channel's INT input. If both sensors have already triggered when the register is read, you see both active — same ambiguity as the original design. It helps in the subset of cases where you happen to read between the two triggers, but this is probabilistic, not deterministic.

**Verdict**: Nice-to-have upgrade (free interrupt visibility, same footprint, possibly cheaper), but does not solve the ordering problem alone. Could be combined with the MCP23008 approach for belt-and-suspenders monitoring, but not required.

### Option C: Discrete Priority Latch (Flip-Flops + GPIO Expander)

Build a hardware priority detector from discrete logic (SN74LVC2G74 dual D flip-flop) and read the result via a simple I2C GPIO expander (PCA9536).

| Aspect | Assessment |
|--------|-----------|
| Ordering detection | Deterministic |
| Components | 2 ICs (flip-flop + GPIO expander) + passives |
| Address conflicts | PCA9536 has fixed address 0x41 — can't use 3 boards |
| Board complexity | Higher than MCP23008 (more routing, more components) |

**Verdict**: Works in principle, but more components and the PCA9536 address conflict is a blocker (would need a different configurable-address GPIO expander). The MCP23008 replaces both the flip-flop and the GPIO expander in a single IC with configurable addresses.

### Option D: Polling Only (Current Approach)

Keep the current polling-based direction detection. No interrupts.

| Aspect | Assessment |
|--------|-----------|
| Direction detection | Works, but limited by poll timing (±1-3ms) |
| Reliability | Good for slow/medium transits, marginal for fast |
| Cable wires | 4 (minimal) |
| Hardware changes | None |

**Verdict**: The baseline. Works well enough for many cases but provides no hardware-level ordering confirmation. The MCP23008 approach augments this with definitive ordering data at minimal cost.

---

## Component Selection

### MCP23008 (Priority Latch)

| Part Number | Package | LCSC ID | Stock | Price | Notes |
|---|---|---|---|---|---|
| **MCP23008T-E/SS** | SSOP-20 (6.5×5.3mm) | C629435 | 1,749 | $1.48 | **Recommended** — best stock, lowest price |
| MCP23008-E/ML | QFN-20 (4×4mm) | C144211 | 682 | $1.92 | Most compact option |
| MCP23008-E/SO | SOIC-18 (11.6×7.5mm) | C92253 | 362 | $2.22 | Hand-solderable, but large |

All are extended library parts on JLCPCB. LCSC stock numbers shown — verify JLCPCB assembly availability during checkout.

### PCA9545A (Optional PCA9546A Replacement)

| Part Number | Package | LCSC ID | Stock | Price |
|---|---|---|---|---|
| PCA9545APWR (TI) | TSSOP-20 | C2149504 | 82 | $0.71 |
| **PCA9545APW,118** (NXP) | TSSOP-20 | C515584 | 481 | $0.90 |

Pin-compatible with the PCA9546A. Not required for the MCP23008 approach but a potential free upgrade during the board redesign.

### I2C Address Map (No Conflicts)

| Device | Address | Bus Location |
|--------|---------|-------------|
| PCA9546A #1 | 0x70 | Sensor bus |
| PCA9546A #2 | 0x71 | Sensor bus |
| PCA9546A #3 | 0x72 | Sensor bus |
| MCP23008 #1 | 0x20 | Sensor bus |
| MCP23008 #2 | 0x21 | Sensor bus |
| MCP23008 #3 | 0x22 | Sensor bus |
| BQ24195 | 0x6B | Main bus |
| INA219 | 0x40 | Main bus |
| VCNL4040 (×6) | 0x60 | Behind PCA9546A (no conflict) |

MCP23008 addresses set via 3 hardware pins (A0-A2), same pattern as PCA9546A solder jumpers.

---

## Rigid Board Changes

### Components Removed
- D2, D3 (BAT54S dual Schottky) — interrupt combining no longer needed
- R5 (8.2kΩ INT pull-up) — shared INT line no longer exists

### Components Added
- U2: MCP23008T-E/SS (SSOP-20)
- C_new: 100nF bypass cap near MCP23008 VDD
- R_reset: 10kΩ pull-up on MCP23008 RESET pin (tie to VCC for normal operation)
- Address configuration: 3 solder jumpers or traces tied to VCC/GND (can share JP3/JP4 pattern)

### Wiring Changes
- VCNL4040_A INT → MCP23008 GPIO0 (was → D2 anode)
- VCNL4040_B INT → MCP23008 GPIO1 (was → D3 anode)
- MCP23008 SDA/SCL → upstream I2C bus (same bus as PCA9546A)
- MCP23008 INTA → unconnected (not needed; ESP32 reads via I2C polling)
- MCP23008 GPIO2-7 → unconnected (unused)
- Remove shared INT line from ZIF FPC connector routing

### Net Impact
- Remove 3 components (D2, D3, R5)
- Add 3 components (U2, C_new, R_reset)
- Component count unchanged; board gains interrupt priority detection
- JST-SH cable stays at 4 pins (3.3V, GND, SDA, SCL)

---

## Firmware Changes

### Initialization (per sensor module)

```
1. Configure MCP23008 at address 0x20/0x21/0x22:
   - IODIR = 0x03 (GPIO0, GPIO1 as inputs; GPIO2-7 as outputs/don't care)
   - DEFVAL = 0x03 (default = both high)
   - INTCON = 0x03 (compare against DEFVAL)
   - GPINTEN = 0x03 (enable interrupt on GPIO0 and GPIO1)
   - GPPU = 0x03 (enable internal pull-ups on GPIO0/GPIO1, optional if external pull-ups exist)

2. Configure VCNL4040 interrupt (in addition to existing PS config):
   - PS_MS = 1 (logic output mode)
   - PS_INT = 0x01 (trigger when close)
   - PS_THDH = calibrated detection threshold
   - PS_THDL = PS_THDH × 0.8 (hysteresis)
```

### Poll Loop Integration

```
For each sensor module (during existing poll cycle):
  1. Read PS_DATA from both VCNL4040s (existing)
  2. Read MCP23008 INTF register
  3. If INTF != 0:
     a. Read MCP23008 INTCAP register
     b. Determine ordering:
        - INTCAP bit 0 = 0, bit 1 = 1 → Side A triggered first
        - INTCAP bit 0 = 1, bit 1 = 0 → Side B triggered first
        - INTCAP bit 0 = 0, bit 1 = 0 → both triggered simultaneously (rare)
     c. Attach ordering result to current detection event
     d. Reading INTCAP clears the interrupt — MCP23008 re-arms automatically
```

---

## Relationship to Other Explorations

- **Multi-Bus Architecture** (`docs/explorations/multi-bus/`): The MCP23008 approach is compatible with all bus architectures (current single-bus, dual-bus Option A, triple-bus Option B). The MCP23008 sits on the same bus segment as its PCA9546A regardless of topology.

- **VCNL4040 Optimization** (sensor range/speed investigation): The interrupt threshold (PS_THDH) needs to be set based on the expected signal at center-of-hoop. If 1T/x8 is adopted (lower signal, 200Hz), the threshold must be correspondingly lower. The MCP23008 ordering is independent of signal strength — it just needs the threshold to be crossed.

---

## Open Questions

1. **MCP23008 INTCAP timing resolution**: How fast does the MCP23008 sample its inputs internally? If both VCNL4040 INTs fire within the MCP23008's sampling window, INTCAP might capture both as simultaneous. The internal scan rate is not specified in the datasheet but is believed to be in the tens-of-microseconds range — fast enough for our application where sensor measurement periods are ~10ms.

2. **Threshold calibration strategy**: How should PS_THDH be set per-sensor? Options include:
   - Fixed value based on lab characterization
   - Dynamic: boot-time calibration using baseline + margin
   - Adaptive: periodically update thresholds based on ambient conditions

3. **JLCPCB assembly verification**: LCSC stock (1,749 units for MCP23008T-E/SS) is a proxy for JLCPCB assembly availability but not a guarantee. Verify during checkout.

4. **Logic output mode interaction with polling**: With PS_MS = 1 (logic output mode), does PS_DATA still update normally? Logic mode affects the INT pin behavior, not the data registers. PS_DATA should continue to reflect raw proximity counts regardless of PS_MS setting. Needs confirmation.

5. **MCP23008 re-arm timing**: After reading INTCAP (clearing the interrupt), how quickly can the MCP23008 capture a new event? Relevant if two transits occur in quick succession (unlikely in normal play but worth understanding).

---

## Recommendation

**Add an MCP23008T-E/SS to each rigid sensor board.** This provides deterministic direction ordering via I2C with zero additional cable wires, minimal board changes (net component count unchanged), and clean integration with the existing polling pipeline. The MCP23008's INTCAP register acts as a hardware priority latch that captures which sensor triggered first, readable at any time during the poll cycle.

The 6-pin dedicated INT approach (Option A) remains a viable alternative if transit speed measurement or precise threshold-crossing timestamps become important. It offers better absolute timing but at the cost of 2 extra cable wires per module.

---

*Last Updated: March 23, 2026*
