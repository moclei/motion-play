 # Multi-Bus I2C Architecture — Exploration

**Date:** March 22, 2026
**Status:** Exploring
**Branch:** `esp32-integration-schematic`

---

## Problem Statement

The current single-bus I2C architecture polls 6 VCNL4040 sensors through a TCA9548A → PCA9546A mux chain at a measured 357 Hz. With the sensor configured at 2T/x8/1/40 (100Hz measurement rate), only ~75 of ~268 polls per sensor per 0.75s window contain unique data. We want to explore whether splitting the I2C traffic across multiple buses can improve timing precision, reduce poll cycle time, and prepare for future sensor upgrades — without adding complexity.

## Constraints

- ESP32-S3 MCU (2 hardware I2C controllers, GPIO-flexible)
- Sensor pairs required for directionality (Side A / Side B per module)
- Sensor angular offset limited to ~3-4° max (further tilt compromises center-of-hoop detection range)
- Willing to redesign PCBs and rewrite firmware
- INT lines abandoned (simplifies JST-SH from 5-pin to 4-pin, removes D2/D3/R5 from rigid board)
- Three sensor modules at 120° positions: M1 (6 o'clock, ~305mm cable), M2 (9 o'clock, ~305mm), M3 (3 o'clock, ~825mm)

## Current Architecture (Baseline)

```
ESP32-S3 I2C0 (GPIO43 SDA, GPIO44 SCL, 400kHz)
  ├── BQ24195 (0x6B) — charger PMIC
  ├── INA219 (0x40) — power monitor
  └── TCA9548A (0x70) — 8-ch I2C switch
       ├── Ch 0 → [305mm cable] → PCA9546A #1 (addr set by JP3/JP4) → 2× VCNL4040
       ├── Ch 1 → [305mm cable] → PCA9546A #2 (addr set by JP3/JP4) → 2× VCNL4040
       └── Ch 2 → [825mm cable] → PCA9546A #3 (addr set by JP3/JP4) → 2× VCNL4040
```

### Measured Performance

| Metric | Value | Source |
|--------|-------|--------|
| Sensor config | 2T, x8 multi-pulse, 1/40 duty | Tested, landed config |
| Sensor measurement rate | ~100 Hz (unique readings) | Calculated from 2T/1/40 |
| Total polls in 0.75s session | 1,608 (all 6 sensors) | Measured from session data |
| Polls per sensor per session | 268 | 1608 / 6 |
| Poll rate | **357 Hz** | 268 / 0.75s |
| Unique readings per sensor per session | **~75** | 100Hz × 0.75s |
| Stale read ratio | ~72% | (268-75)/268 |
| Theoretical poll rate (prox only) | 549 Hz | From timing analysis |
| Poll rate gap | 357 vs 549 Hz | Likely: ALS reads, BQ/INA I2C, firmware overhead |

### Transit Detection at 30mph (13.4 m/s)

Ball: 190mm (size 3). Hoop: 500mm. Detection window: ~30-40ms.

| At 2T/x8/1/40 (100Hz) | Per sensor | All 6 sensors |
|---|---|---|
| Unique readings during transit | **3-4** | **18-24** |
| Poll samples during transit | ~11-14 | ~66-84 |

3-4 unique readings per sensor is tight for wave characterization and direction detection.

### Key Insight: TCA9548A Is Redundant

The three PCA9546A boards have **unique I2C addresses** (configured via solder jumper bridges JP3/JP4 on each rigid board). The PCA9546A isolates its downstream VCNL4040s when no channel is selected — this is its core function. With unique addresses, the ESP32 can address each PCA directly and only enable one channel at a time, ensuring only one VCNL4040 (0x60) is ever visible on the bus.

The TCA9548A provided an extra layer of isolation, but with addressable PCAs it is electrically unnecessary. Removing it saves:
- One TSSOP-24 IC (U4), two decoupling caps (C9, C10), one pull-up (R6)
- 3 TCA mux-select I2C transactions per read cycle (~150μs)
- The entire cleanup phase (~650μs): TCA channel selects, PCA disable sweeps, stabilization delays

**What we lose:** fault isolation (a bus-locked sensor board can't be isolated by software) and per-channel capacitance isolation (all cables load the bus simultaneously). Neither is a blocking concern at 400kHz with these cable lengths.

---

## Option A: Dual I2C Bus, No TCA (Recommended)

### Architecture

```
ESP32-S3 I2C0 (GPIO43 SDA, GPIO44 SCL, 400kHz)
  ├── BQ24195 (0x6B) — charger PMIC
  ├── INA219 (0x40) — power monitor
  ├── [305mm cable] → PCA9546A #1 (unique addr) → 2× VCNL4040 (M1)
  └── [305mm cable] → PCA9546A #2 (unique addr) → 2× VCNL4040 (M2)

ESP32-S3 I2C1 (GPIOxx SDA, GPIOyy SCL, 400kHz)
  └── [825mm cable] → PCA9546A #3 (unique addr) → 2× VCNL4040 (M3)
```

JST-SH connectors reduced to 4-pin: 3.3V, GND, SDA, SCL (INT removed).

### Bus Timing

**Bus 0 (M1 + M2, 4 sensors):**

| Operation | Time |
|-----------|------|
| PCA#2 select ch1 (sensor 3) | ~50 μs |
| Read 0x60 PS_DATA | ~120 μs |
| PCA#2 select ch0 (sensor 2) | ~50 μs |
| Read 0x60 PS_DATA | ~120 μs |
| PCA#2 disable | ~50 μs |
| PCA#1 select ch1 (sensor 1) | ~50 μs |
| Read 0x60 PS_DATA | ~120 μs |
| PCA#1 select ch0 (sensor 0) | ~50 μs |
| Read 0x60 PS_DATA | ~120 μs |
| PCA#1 disable | ~50 μs |
| **Subtotal (sensors)** | **~780 μs** |
| BQ24195/INA219 reads (estimate) | ~200-400 μs |
| **Total** | **~980-1,180 μs** |

**Bus 1 (M3, 2 sensors):**

| Operation | Time |
|-----------|------|
| PCA#3 select ch1 (sensor 5) | ~50 μs |
| Read 0x60 PS_DATA | ~120 μs |
| PCA#3 select ch0 (sensor 4) | ~50 μs |
| Read 0x60 PS_DATA | ~120 μs |
| PCA#3 disable | ~50 μs |
| **Total** | **~390 μs** |

**Synchronous mode:** Both buses start simultaneously. All 6 readings get the same cycle timestamp. Cycle time = slower bus.

### Projected Performance

| Metric | Current | Option A (sync) |
|--------|---------|-----------------|
| Cycle time (sensor reads only) | ~2,800 μs (measured) | ~980 μs |
| Cycle time (with BQ/INA) | ~2,800 μs | ~1,180 μs |
| Poll rate | 357 Hz | ~850-1,020 Hz |
| Oversampling (at 100Hz sensor) | 3.6× | 8.5-10.2× |
| Max timestamp jitter | 2.8 ms | ~1.0-1.2 ms |
| All sensors symmetric? | Yes | Yes |
| Unique reads per transit (30mph) | 3-4 | 3-4 (unchanged) |
| Firmware changes | — | Moderate (2nd I2C init, remove TCA driver, adjust read loop) |
| Hardware changes | — | Remove TCA + passives, assign 2 GPIOs for I2C1, route to J6 |

**Note:** Unique reads per transit don't change because the VCNL4040 sensor measurement rate (100Hz at 2T/1/40) is the bottleneck, not the bus. The improvement is in timing precision and headroom.

### Signal Integrity (825mm on Bus 1)

- Cable capacitance: ~62 pF
- Plus IC pins, connectors, traces: ~90-120 pF total
- Pull-ups: R28/R29 = 2.2kΩ on main board (or new dedicated pull-ups for Bus 1)
- Rise time: τ = 2.2kΩ × 120pF = 264ns → 20-80% rise ≈ 191ns
- I2C 400kHz spec: <300ns → **passes with ~100ns margin**

### Signal Integrity (Bus 0 with 2 cables)

- M1 cable (~23 pF) + M2 cable (~23 pF) + IC pins + traces: ~100-130 pF
- Pull-ups: R28 (2.2kΩ) || M1 R1 (4.7kΩ) || M2 R1 (4.7kΩ) ≈ 1.1kΩ effective
- Rise time: τ = 1.1kΩ × 130pF = 143ns → 20-80% ≈ 103ns → **well within spec**
- Sink current at logic low: 3.3V / 1.1kΩ = 3.0mA → within PCA9546A's 6mA capability
- Consideration: could depopulate R1/R2 on sensor boards if pull-up is too strong

---

## Option B: Triple I2C Bus (2 Native + 1 Additional)

### Architecture

```
ESP32-S3 I2C0 (400kHz)
  ├── BQ24195, INA219
  └── [305mm] → PCA#1 → 2× VCNL4040 (M1)

ESP32-S3 I2C1 (400kHz)
  └── [305mm] → PCA#2 → 2× VCNL4040 (M2)

3rd Bus (see variants below)
  └── [825mm] → PCA#3 → 2× VCNL4040 (M3)
```

### 3rd Bus Variants

| Variant | Method | Speed | Cycle time (M3) | Extra components | Reliability |
|---------|--------|-------|-----------------|-----------------|-------------|
| B1 | SPI-to-I2C bridge (e.g., SC18IS600) | 400kHz on I2C side | ~530 μs | 1 IC + passives | High |
| B2 | Software bitbang at 100kHz | 100kHz | ~1,560 μs | None | Medium |
| B3 | Software bitbang at 200kHz | 200kHz | ~780 μs | None | Medium-Low |

### Projected Performance (Synchronous)

| Metric | B1 (SPI bridge) | B2 (bitbang 100k) | B3 (bitbang 200k) |
|--------|-----------------|--------------------|--------------------|
| Cycle time (sync, slowest bus) | ~530 μs | ~1,560 μs | ~780 μs |
| Poll rate | ~1,890 Hz | ~640 Hz | ~1,280 Hz |
| Oversampling (at 100Hz) | 18.9× | 6.4× | 12.8× |
| All sensors symmetric? | Yes | Yes | Yes |
| Extra hardware? | Bridge IC | None | None |
| Firmware complexity | High (SPI-I2C driver) | Medium (bitbang lib) | Medium-High |
| Risk | Low | Low | Medium (timing jitter) |

### Trade-offs vs Option A

Each module gets its own dedicated bus — true 3-way symmetry, maximum fault isolation. But:

- BQ24195 and INA219 share Bus 0 with M1, adding ~200-400μs of non-sensor I2C traffic to that bus. In sync mode, this becomes the bottleneck unless those reads are moved out of the sensor cycle (e.g., read power devices less frequently or on a separate timer).
- The 3rd bus introduces either a new IC (bridge) or firmware fragility (bitbang).
- At 100Hz sensor rate, 10-19× oversampling provides diminishing returns over Option A's 8.5-10×.

---

## Comparison Summary

| | Current | Option A (2 bus, no TCA) | Option B1 (3 bus, bridge) |
|---|---|---|---|
| Components | TCA + 3 PCA | **3 PCA only** | Bridge + 3 PCA |
| Net component change | — | **-1 IC, -3 passives** | +1 IC (swap TCA for bridge) |
| Poll rate | 357 Hz | **850-1,020 Hz** | ~1,890 Hz |
| Oversampling (100Hz) | 3.6× | **8.5-10.2×** | 18.9× |
| Timestamp jitter | 2.8 ms | **~1.0-1.2 ms** | ~0.5 ms |
| Symmetric? | Yes | **Yes (sync)** | Yes (sync) |
| Fault isolation | Best (TCA) | Partial (per-bus) | Best (per-bus) |
| Firmware effort | Baseline | **Moderate** | High |
| Unique transit reads (30mph) | 3-4/sensor | 3-4/sensor | 3-4/sensor |

**The unique reading count is identical across all options** because the VCNL4040 sensor rate (100Hz at 2T/1/40) is the bottleneck. Bus speed improvements increase timestamp precision and oversampling ratio, not unique data density.

---

## Understanding Poll Rate vs Sensor Rate

These two rates are independent processes. Confusing them is easy, so this section clarifies.

### Process 1: Sensor Measurement (autonomous, parallel)

Each VCNL4040 has an internal clock. At 2T/1/40, it fires an IR pulse, measures the reflection, and writes the result to its `PS_DATA` register every ~10ms (100Hz). Then it does it again, forever, **independently of the I2C bus**. All 6 sensors do this **simultaneously in parallel** — no bus involvement.

### Process 2: ESP32 Polling (sequential, over I2C)

The ESP32 walks through each sensor one at a time: select PCA channel → read `PS_DATA` register → next sensor → ... → done → repeat. Each complete walk = one "poll cycle." The cycle time determines the poll rate.

### These Processes Are Decoupled

Reading a sensor's register is like glancing at a clock on a wall. Looking at it doesn't slow it down. Looking at it twice between ticks just shows the same time. The sensor updates its register at its own rate; the ESP32 reads it at a different rate.

### Timeline Visualization

A ~20ms window for one sensor. Sensor measurement ticks every 10ms. Poll ticks every 2.8ms (current) or ~1.0ms (dual bus):

**Current (single bus, 357 Hz poll rate):**

```
Time (ms):   0     2.8    5.6    8.4    10     12.8   15.6   18.4   20
Sensor:      ■──────────────────────────■──────────────────────────■───
             V1 (new measurement)       V2 (new measurement)       V3

ESP32 poll:  ●      ●      ●      ●      ●      ●      ●      ●
Value read:  V1     V1     V1     V1     V2     V2     V2     V2
             new!   stale  stale  stale  new!   stale  stale  stale
             └─── caught within 2.8ms ──┘
```

**Dual bus (no TCA, ~1,000 Hz poll rate):**

```
Time (ms):   0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20
Sensor:      ■─────────────────────────────■──────────────────────────────■
             V1                            V2                             V3

ESP32 poll:  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●
Value read:  V1 V1 V1 V1 V1 V1 V1 V1 V1 V1 V2 V2 V2 V2 V2 V2 V2 V2 V2 V2
             new!                          new!
             └─── caught within 1.0ms ─────┘
```

**Same 2 unique readings (V1, V2) in both cases.** But the dual bus catches each one within ~1ms of it appearing, vs ~2.8ms. More polls = more stale reads, but each new reading is timestamped more precisely.

### What Each Rate Controls

| | Sensor rate (100Hz) | Poll rate (357→1000 Hz) |
|---|---|---|
| Determined by | VCNL4040 internal config (IT, duty cycle) | I2C bus speed, mux overhead, firmware |
| Controls | How many **unique** readings per second | How **quickly** each new reading is captured |
| For a 30mph transit | 3-4 unique data points per sensor | Doesn't change data point count |
| Improvement lever | Change sensor IC, or switch 2T→1T | Add I2C buses, remove TCA, optimize firmware |
| Analogy | How fast the clock ticks | How often you glance at the clock |

### Why the Dual Bus Still Matters

Even though it doesn't increase unique readings, faster polling improves:

1. **Timestamp precision**: Each unique reading is captured within ~1ms of its actual measurement, vs ~2.8ms. For direction detection (A vs B peak timing), this 3× improvement directly helps.
2. **Zero missed readings**: At 10× oversampling, it's impossible to miss a sensor update. At 3.6× oversampling, unlucky clock alignment could occasionally skip one.
3. **Firmware headroom**: Shorter cycles mean more CPU time for processing, ML inference, or future sensor upgrades with higher measurement rates.

---

## The Sensor Rate Bottleneck

This is the fundamental limit. Some paths to more unique readings per transit:

| Approach | Unique reads/sensor at 30mph | Effort | Notes |
|----------|------------------------------|--------|-------|
| Current (2T/x8/1/40, 100Hz) | 3-4 | — | Baseline |
| Switch to 1T/x8/1/40 (200Hz) | 6-7 | Firmware config | Trades signal strength for rate; needs testing |
| Sub-sample interpolation | 3-4 raw, but ~0.5ms peak timing | Firmware algorithm | "Free" timing improvement on existing data |
| Different sensor IC (>200Hz) | Depends on sensor | New sensor boards | No I2C prox sensor >200Hz found on market |
| Analog IR sensing (LED+photodiode) | 50+ (at 1-5kHz ADC) | Major sensor redesign | Eliminates I2C bottleneck entirely |
| Local MCU per sensor board | 50+ (at kHz local ADC) | Major redesign | "Dream" architecture, digital over cables |

### 1T vs 2T Trade-off (Needs Investigation)

At 2T/x8/1/40 the sensor produces ~100Hz unique data. At 1T/x8/1/40 it would produce ~200Hz, doubling transit samples from 3-4 to 6-7. The user observed "1T→2T didn't affect sample rate" — this is the poll rate staying constant, not the unique data rate. The unique data rate did halve, but without deduplication in the firmware the change is invisible in raw counts.

**Question to test:** At 1T/x8/1/40, does the reduced signal strength (half of 2T) still provide adequate detection range at the hoop center (~250mm)? If yes, 1T doubles effective transit samples. The x8 multi-pulse provides 8× signal boost which may compensate for the shorter integration time.

---

## Other Changes Bundled with This Architecture Shift

### JST-SH 5-pin → 4-pin

With INT lines abandoned, connector becomes: 1=3.3V, 2=GND, 3=SDA, 4=SCL. Saves one wire per cable, removes D2/D3/R5 from rigid board, frees up 3 ESP32 GPIO pins (INT1/INT2/INT3).

### PCA Address Selection on Rigid Board

Current: solder bridge jumper pads (JP3/JP4). User wants a small switch for easier reconfiguration. Options:
- 2-position DIP switch (e.g., CTS 219-2): ~2.5mm height, LCSC available
- SMD slide switch per address bit: more board area but lower profile
- Keep solder jumpers but add silkscreen truth table for clarity

With the TCA removed, correct PCA addressing becomes critical (shared bus = address collision = bus failure). A switch makes field changes safer than jumper bridges.

---

## Open Questions

1. **What causes the 357 Hz vs 549 Hz poll rate gap?** Profile the firmware sensor loop to identify: ALS reads? BQ24195/INA219 reads? Task switching overhead? This affects projected performance of all options.
2. **Can BQ24195/INA219 be read outside the sensor loop?** Moving them to a separate, slower timer (e.g., 10Hz) would free ~200-400μs from the sensor cycle.
3. **1T vs 2T at center-of-hoop distance?** Test 1T/x8/1/40 for center detection range. If adequate, 2× improvement in unique transit samples.
4. **GPIO availability for I2C1?** Need to identify 2 free GPIOs for the second I2C bus that don't conflict with existing assignments (USB, boot strapping, etc.).
5. **PCA9546A address truth table?** Confirm the actual 7-bit addresses for each JP3/JP4 configuration to verify no conflicts with BQ24195 (0x6B) or INA219 (0x40) on Bus 0.

## Recommendation

**Option A (Dual I2C, No TCA)** is the clear winner for the next board revision:

- Removes a component instead of adding one
- 2.4-2.9× faster poll rate with better timestamp precision
- Zero sensor asymmetry in synchronous mode
- Moderate firmware effort (well-understood I2C APIs)
- Leaves the door open for a 3rd bus later if needed

Option B (Triple Bus) is a reasonable future step but offers diminishing returns at the current 100Hz sensor rate. Worth revisiting if sensor technology changes.

---

*Last Updated: March 22, 2026*
