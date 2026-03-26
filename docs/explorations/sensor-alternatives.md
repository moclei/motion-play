# Sensor Alternatives Research

**Date:** March 23, 2026
**Status:** Shelved — ICU-10201 identified as top candidate for future investigation
**Related:** `docs/references/vcnl4040/CONFIGURATION_GUIDE.md`, `docs/explorations/multi-bus/multi-bus-architecture.md`

---

## Problem Statement

The VCNL4040 limits the system in two coupled ways:

1. **Detection range** (~200mm at 2T/x8, ~250mm stretched) forces us to use 2T integration time for center-of-hoop (250mm) detection, capping the measurement rate at 100Hz.
2. **Measurement rate** (200Hz max at 1T/1/40) yields only 3–4 unique readings per sensor during a 30mph ball transit (~35ms window). With 2T forced by range, we get 100Hz → 3–4 readings.

The forcing function is **range**. If a sensor can detect at 250mm with a faster integration time (or uses a fundamentally different measurement principle), we get more transit samples.

### Requirements

| Priority | Requirement | VCNL4040 Baseline |
|----------|------------|-------------------|
| **#1** | Detection range >300mm for reflective objects | ~200–250mm |
| **#2** | Measurement rate >200Hz | 200Hz max (1T), 100Hz typical (2T) |
| **#3** | Any interface (I2C, SPI, analog) | I2C only |
| **#4** | Configurable I2C address (if I2C) — eliminate muxes | Fixed 0x60 |
| **#5** | Small package — fit on flex PCB (~25mm × 8mm sensor area) | 4.0 × 2.0 × 0.8mm |

### Physical Constraints

- Sensors are coverless — mounted on flex PCB, facing inward through the hoop opening (no tube or lens covering)
- Hoop is 500mm diameter transparent polypropylene tubing (19mm tube diameter)
- Must detect objects up to 250mm away (center of hoop)
- Cable runs up to 825mm (Module 3 at 3 o'clock position)
- Flex PCB area per sensor: ~25mm × 8mm with stiffener

---

## Candidate Summary

| Sensor | Mfr | Type | Range | Max Rate | Interface | Package (mm) | I2C Addr | Price (LCSC) | Verdict |
|--------|-----|------|-------|----------|-----------|-------------|----------|-------------|---------|
| **ICU-10201** | TDK | Ultrasonic ToF | **1200mm** | **250Hz** @0.3m | SPI (13MHz) | 3.5×3.5×1.26 | N/A (SPI) | ~$3–5 | **Top candidate** — needs eval |
| **VL53L4CD** | ST | ToF (SPAD) | **1200mm** | **100Hz** | I2C (1MHz) | 4.4×2.4×1.0 | Software-configurable | ~$2.38 @30 | Range win, no rate win |
| **OPT3101** | TI | ToF AFE | **1000–1500mm** | **4000Hz** | I2C | 5.0×4.0 (IC only) | N/A | ~$1.83 @30 | Best perf, needs ext. optics |
| **VCNL4200** | Vishay | Reflective prox | **1500mm** | 62Hz | I2C | 8.0×3.0×1.8 | Fixed 0x51 | ~$1.85 @30 | More range, worse rate |
| **VL53L1X** | ST | ToF (SPAD) | **4000mm** | 50Hz | I2C | 4.9×2.5×1.56 | Software-configurable | ~$3+ | Slower than VL53L4CD |
| **VCNL4030X01** | Vishay | Reflective prox | **300mm** | ~200Hz (est.) | I2C | 4.0×2.36×0.75 | Fixed | ~$1+ | Incremental, not transformative |
| **VCNL4040** | Vishay | Reflective prox | 200–250mm | 200Hz | I2C | 4.0×2.0×0.8 | Fixed 0x60 | ~$0.86 @30 | Current sensor (baseline) |
| APDS-9960 | Broadcom | Reflective prox | ~100mm | Fast | I2C | 3.94×2.36×1.35 | Fixed 0x39 | ~$2 | Range too short |
| Si1153 | SiLabs | Reflective prox | ~500mm (claimed) | Unknown | I2C | 2.0×2.0×0.6 | Configurable | ~$3+ | Poorly documented, sourcing unclear |
| TMF8820 | ams-OSRAM | ToF (SPAD) | 5000mm | 30Hz | I2C | Large | Fixed | ~$5+ | Too slow |
| Sharp GP2Y | Sharp | Triangulation | 80–150mm | 26Hz | Analog | ~30×13×14 | N/A | ~$5+ | Too slow, too large |
| VCNL36826S | Vishay | VCSEL prox | 200mm | ~100Hz | I2C | 2.55×2.05×1.0 | Fixed | ~$2 | Range too short |

---

## Detailed Analysis

### Tier 1: Strong Candidates

#### ICU-10201 (TDK/InvenSense) — Top Candidate

**What it is:** A fully self-contained ultrasonic Time-of-Flight sensor using a PMUT (Piezoelectric Micromachined Ultrasonic Transducer). Emits 175kHz ultrasonic pulses, measures time of flight. Works in any lighting condition.

| Parameter | Value | vs. VCNL4040 |
|-----------|-------|---------------|
| Detection range | 100–1200mm | **5× better** |
| Measurement rate | **250Hz @0.3m**, 130Hz @1m | **2.5× faster** (at 0.3m) |
| Interface | **SPI at 13MHz** | Faster readout, no bus contention |
| Package | 3.5 × 3.5 × 1.26mm | Slightly larger, fits flex |
| Supply | 1.8V or 3.3V | Compatible |
| FoV | Up to 180° (customizable) | Much wider |
| Data output | Distance (mm) | Richer than proximity counts |
| Availability | Mouser ~1,987 units; eval boards ~$20–30 | Available |

**Why it's the top candidate:**

The ICU-10201 is the only sensor found that delivers improvements on **both** primary requirements simultaneously:

1. **Genuinely faster measurement rate.** 250Hz at 0.3m max range gives **~8–9 unique readings per sensor** during a 30mph transit (~35ms) — 2–2.5× more than the VCNL4040. The rate is physically limited by speed of sound (round trip to 0.3m takes ~1.75ms), not by a firmware ceiling.

2. **Ample detection range.** At 0.3m max range setting, center-of-hoop (250mm) detection is well within operating range. Longer range settings (up to 1.2m) available at reduced rate.

3. **SPI interface eliminates I2C contention.** No muxes needed. No bus sharing with power management ICs. Each sensor gets a dedicated SPI chip-select line. The ESP32-S3 SPI controller can run at MHz speeds — readout is effectively instantaneous compared to measurement time.

4. **Self-contained.** No external optics, emitters, or photodiodes. Single IC in a 3.5×3.5mm package. Simpler BOM than the VCNL4040 (no LED anode caps, no filter resistors).

5. **Wide FoV (customizable up to 180°).** Better coverage of off-center ball transits than narrow-beam laser ToF sensors.

6. **Lighting-independent.** Ultrasonic sensing is unaffected by ambient IR, sunlight, or LED strip light. Removes an entire class of potential interference.

7. **Below-minimum-range detection.** The datasheet states "detection of moving objects closer than 10cm" — meaning objects in the <100mm blind zone are still detected for presence/motion, just without accurate distance. For direction detection (which only needs to know something passed), this is sufficient.

**Unknowns and concerns (to evaluate with prototyping):**

- **Multi-sensor acoustic crosstalk.** Six sensors at 175kHz operating simultaneously around the same hoop. Could produce interference, multipath echoes, or false triggers. Mitigation options: time-division multiplexing (read sensors sequentially, not simultaneously), or relying on the narrow round-trip time window to reject stray echoes. The 40MHz on-chip DSP may handle some of this. Needs bench testing.
- **Ball acoustic reflectivity.** Soccer balls (smooth synthetic or leather surface, ~190mm spherical) should reflect 175kHz ultrasonic well, but real-world testing is needed across ball types and conditions (wet, dirty, spinning).
- **Hoop structure reflections.** The polypropylene tube, cable harness, and enclosures are all potential acoustic reflectors. Calibration / background subtraction should handle static reflections, but dynamic changes (e.g., hoop flexing) are unknown.
- **LCSC/JLCPCB availability.** The IC is available on Mouser/DigiKey/Farnell. Eval boards (EV_MOD_ICU-10201-00) exist at ~$20–30. Not yet confirmed on LCSC for JLCPCB assembly — may need to source separately and hand-solder for prototypes.
- **Acoustic housing.** The eval board includes an "acoustic housing." The bare IC may need a small acoustic cavity or horn to control the beam pattern. Need to understand whether the PMUT works well in a bare flex-PCB mount or needs mechanical accommodation.

**Next steps (when this investigation resumes):**

1. Order 2–3 eval boards (EV_MOD_ICU-10201-00, ~$20 each from Symmetry Electronics)
2. Bench test: detect a soccer ball at 100–300mm, measure rate and signal quality
3. Multi-sensor test: two sensors facing each other across a ~500mm gap, check for crosstalk
4. Mount test: attach to hoop tubing, verify no acoustic issues from hoop structure
5. If eval passes: design a new flex PCB with ICU-10201 footprint + SPI routing

---

#### VL53L4CD (STMicroelectronics) — Range Win, No Rate Win

**What it is:** A laser Time-of-Flight sensor (SPAD + VCSEL, 940nm). Returns absolute distance in millimeters.

| Parameter | Value | vs. VCNL4040 |
|-----------|-------|---------------|
| Detection range | 0–1200mm | **5× better** |
| Ranging rate | Up to 100Hz (10ms min timing budget) | Same as 2T config |
| FoV | 18° diagonal (22° at 100mm) | Narrower |
| I2C address | Software-configurable (default 0x52) | Could eliminate muxes |
| Package | 4.4 × 2.4 × 1.0mm (LGA-12) | Fits flex PCB |
| Supply | 2.6–3.5V | Compatible (3.3V system) |
| Unit price | ~$2.38 @30qty (LCSC/JLCPCB) | Available |

**Key insight: 100Hz is a hard ceiling.** The VL53L4CD's minimum timing budget is 10ms, giving a maximum ranging frequency of 100Hz. This is the same unique-reading rate as the current VCNL4040 at 2T/1/40 — **transit sample count does not improve.** The original thesis ("more range → use faster integration time → more samples") doesn't apply here because the VL53L4CD's rate limit is a firmware/hardware processing constraint, not a range/sensitivity trade-off.

The VCNL4040 at 1T/x8/1/40 (200Hz) is actually **faster** than the VL53L4CD. Whether 1T/x8 has enough range at 250mm remains untested.

**Still valuable for:** guaranteed detection reliability at 250mm (massive range margin), true distance data (mm not counts), software-configurable I2C addresses, and simpler configuration. If transit sample count is acceptable at 3–4 per sensor, this is a solid upgrade.

---

#### OPT3101 (Texas Instruments) — Highest Performance, Most Complex

**What it is:** A ToF analog front end (AFE) driving external emitters + photodiode. Phase-based continuous-wave measurement.

| Parameter | Value |
|-----------|-------|
| Sample rate | **Up to 4000Hz** |
| Detection range | 1–1.5m (no lens) |
| Interface | I2C |
| Package | 5.0 × 4.0mm VQFN-28 (IC only) |

4kHz = **140 samples per transit** at 30mph. Transformative, but requires custom optical system design (external emitters, photodiode, beam shaping, PCB analog routing). Not practical on the current flex strip — future "Gen 2" rigid sensor board candidate.

---

### Tier 2: Partial Fits

#### VCNL4200 (Vishay) — More Range, Less Speed

The VCNL4200 is Vishay's "long distance" variant. Same register-based architecture as VCNL4040 but with larger optics and higher drive current capability.

| Parameter | Value | vs. VCNL4040 |
|-----------|-------|---------------|
| Detection range | Up to 1500mm | **6× better** |
| Max rate | ~62Hz (1T at 1/160 duty) | **3× worse** |
| Duty cycle options | 1/160, 1/320, 1/640, 1/1280 | No 1/40 or 1/80 |
| LED current | Up to 800mA (external MOSFET) | 4× more |
| PS resolution | 12-bit or 16-bit | 16-bit option |
| Interface | I2C, fixed 0x51 | Different fixed address |
| Package | **8.0 × 3.0 × 1.8mm** | **4× larger footprint** |
| Requires | External PMOS FET + RLED for high current | More components |

**Why it doesn't fit:**

The VCNL4200's minimum duty cycle is **1/160** — the VCNL4040's minimum is 1/40. This means the VCNL4200's fastest possible measurement rate at 1T is ~62Hz, versus the VCNL4040's 200Hz. The VCNL4200 trades speed for range by design.

The package at 8.0 × 3.0mm is too large for the current flex PCB sensor area.

The external MOSFET circuit adds board complexity and power supply requirements (needs separate VIRED supply at 3.8–5.5V).

**Verdict:** Wrong trade-off direction. We need more range AND more speed, not more range at the expense of speed.

---

#### VCNL4030X01 (Vishay) — Incremental Improvement

The recommended replacement for the older VCNL4020. Same general architecture as VCNL4040 with slightly better range.

| Parameter | Value | vs. VCNL4040 |
|-----------|-------|---------------|
| Detection range | Up to 300mm | ~50% better |
| Max rate | ~200Hz (estimated, similar architecture) | Same |
| Interface | I2C, fixed address | Same |
| Package | 4.0 × 2.36 × 0.75mm | Nearly identical |
| Temperature | -40 to +105°C (AEC-Q101) | Automotive qualified |

**Verdict:** A modest range improvement (~300mm vs ~200mm). Not enough to change the fundamental problem. The extra 50–100mm of range doesn't eliminate the need for 2T integration time at center-of-hoop distance.

---

#### VL53L1X (STMicroelectronics) — Longer Range, Slower

The VL53L1X is the predecessor/sibling of the VL53L4CD with longer range but slower rate.

| Parameter | Value | vs. VL53L4CD |
|-----------|-------|---------------|
| Detection range | Up to 4000mm | 3× more range |
| Max rate | ~50Hz (20ms timing budget) | **2× slower** |
| Package | 4.9 × 2.5 × 1.56mm | Slightly larger |
| Interface | I2C, software-configurable address | Same |

**Verdict:** More range than needed (4m vs 1.2m for the hoop), but half the rate. The VL53L4CD is better optimized for our use case — shorter range but faster, and more compact.

---

### Tier 3: Not Suitable

| Sensor | Why Not |
|--------|---------|
| **APDS-9960** (Broadcom) | Max range ~100mm. Designed for phone gesture/proximity, not long-distance detection. |
| **TMF8820/8828** (ams-OSRAM) | 15–30Hz rate. Designed for multi-zone depth mapping (robotics, AR). Massive overkill and too slow. |
| **Sharp GP2Y series** | 26Hz rate, through-hole module (~30×13×14mm), needs 5V. Completely wrong form factor. |
| **VCNL36826S** (Vishay) | Max range 200mm. VCSEL with ±3° beam — too narrow and too short range. Designed for force feedback. |
| **TMD2672/TMD2755** (ams-OSRAM) | Phone proximity sensors. Range is <100mm. Wrong application class. |
| **Si1153** (Silicon Labs) | Claims 500mm range but poorly documented measurement rate. Hard to source. Discontinued risk. |

---

## The Physics: Why This Trade-off Exists

For reflective proximity sensors (VCNL4040, VCNL4200, APDS-99xx, etc.), the detection range is governed by:

```
Signal ∝ (LED power × integration time × reflectivity) / distance⁴
```

The 1/distance⁴ law (inverse-square for emission AND collection) means doubling the range requires 16× more signal. You can get more signal by:
- Longer integration time (reduces rate)
- More LED current (limited by IC, adds heat)
- Multi-pulse accumulation (may reduce rate)
- Bigger optics (bigger package)

**There is no reflective proximity sensor IC that offers both >300mm range AND >200Hz rate.** The physics don't allow it in a small package.

**Time-of-Flight sensors break this trade-off** by measuring photon flight time rather than reflected intensity. ToF range depends on timing resolution and laser power, not integration time in the same way. A ToF sensor can measure 1m distance at 100Hz because it's measuring a ~6.7ns time delay, not accumulating photons over milliseconds.

---

## Recommendation

### Primary: ICU-10201 (Ultrasonic ToF)

The ICU-10201 is the only sensor found that improves **both** range and measurement rate simultaneously:

- **250Hz** at 0.3m max range → **~8–9 unique readings per transit** (vs 3–4 with VCNL4040)
- **SPI interface** eliminates I2C bus contention and mux complexity
- **Self-contained** — no external optics
- **Wide FoV** — better coverage than narrow-beam alternatives

The main risk is acoustic unknowns (multi-sensor crosstalk, hoop structure reflections, ball reflectivity). These can only be resolved with physical prototyping using eval boards.

### Backup: VL53L4CD (Laser ToF)

If the ICU-10201 doesn't work out acoustically, the VL53L4CD is a solid fallback. It doesn't improve transit sample count (100Hz = same as VCNL4040 at 2T), but it massively improves detection reliability at 250mm (1200mm range vs 250mm edge-of-range) and returns true distance data in millimeters.

### Long-term: OPT3101 (Custom Optical System)

For a future "Gen 2" rigid sensor board with custom optics: 4kHz rate = 140+ samples per transit. Requires optical engineering expertise.

### Status

This exploration is **shelved**. The current VCNL4040 sensors are adequate for the near-term milestone (field-testable prototype). Sensor upgrade is a future initiative to revisit when the detection algorithm and data pipeline are more mature. When resumed, start by ordering ICU-10201 eval boards.

---

## Appendix: Data Sources

| Sensor | Datasheet/Source |
|--------|-----------------|
| VCNL4040 | Vishay doc #84274, design guide, project testing |
| VCNL4200 | Vishay doc #84430 (Rev 1.8, Mar 2025), app note #84327 |
| VL53L4CD | ST datasheet, Pololu/Adafruit product pages |
| VL53L1X | ST datasheet, user manual DM00474730 |
| OPT3101 | TI datasheet SBAS825, app notes SBAU305/SBAA303 |
| ICU-10201 | TDK InvenSense DS-000480 v1.6 |
| VCNL4030X01 | Vishay doc #84424 |
| APDS-9960 | Broadcom/Avago datasheet |
| Si1153 | Silicon Labs si115x datasheet |
| TMF8820 | ams-OSRAM datasheet |
| Sharp GP2Y | Sharp datasheets via Pololu |

---

*Last Updated: March 23, 2026*
