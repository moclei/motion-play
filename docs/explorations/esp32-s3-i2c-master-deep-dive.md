# ESP32-S3 I2C peripheral configuration audit and experiment plan

> Date: 2026-05-01. Scope: **the ESP32-S3 I2C master peripheral only.** Hardware, PCB, BQ24195 input characteristics, bus topology, and v8 design are explicitly out of scope — see [v7-i2c-investigation.md](../debugging/v7-i2c-investigation.md) for everything else. The Phase 24 Arduino-as-master test confirmed Story F: the same wire that NACKs an ESP32-S3 master ACKs a SAMD21 (Nano 33 IoT) master. Mechanism is in the S3 master peripheral itself; this document audits every knob we can poke from firmware to find it.

## 0. State of play (one screen)

We are pinned to **arduino-esp32 v2.0.14**, which wraps **ESP-IDF v4.4.x** ([platformio.ini:23](../../platformio.ini#L23)). That means the project is on the **legacy `driver/i2c.h` API**, not the new `i2c_master_*` API introduced in IDF v5.2 / arduino-esp32 v3.2.0. A lot of the public Espressif documentation and community advice from 2025+ assumes the new driver — we have to translate. The legacy driver exposes individual timing knobs (`i2c_set_period`, `i2c_set_data_timing`, `i2c_filter_enable`, etc.) that the new driver hides behind `i2c_master_bus_config_t`.

Current init code, [SensorManager.cpp:629-648](../../firmware/src/components/sensor/SensorManager.cpp#L629-L648):

```cpp
Wire.begin(43, 44);
Wire.setClock(100000);
gpio_set_drive_capability(GPIO_NUM_43, GPIO_DRIVE_CAP_3);
gpio_set_drive_capability(GPIO_NUM_44, GPIO_DRIVE_CAP_3);
```

That's it. No filter calls, no internal-pullup-disable, no timing-register tweaks, no peripheral-instance choice (defaulting to I2C0 via the global `Wire` object).

## 1. Block-level architecture

### 1.1 Two controllers, both HP

ESP32-S3 has **two HP I2C controllers** — I2C0 and I2C1 — described by a single hardware spec in [TRM Chapter 27](https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf). They are **architecturally identical** per the TRM: same FIFO depth, same command-list structure, same timing registers, separate clock-enable and reset bits in the system register block (`SYSTEM_I2C_EXT0_CLK_EN` / `SYSTEM_I2C_EXT1_CLK_EN`). They share no documented difference in jitter or interrupt routing — but the TRM also doesn't *guarantee* bit-identical analog behaviour, only register-identical behaviour. That gap is small but non-zero, and is the basis for a ranked experiment below ("move to I2C1"). There's also an **RTC I2C** block (TRM §2.7) — a separate low-power instance driven by ULP instructions, not what `Wire` uses.

### 1.2 Clock domains and clock source

Two domains: **APB_CLK** (≤80 MHz, holds registers and RAM) and **I2C_SCLK** (drives the FSM and filters). Software writes timing registers through APB and must commit them by setting `I2C_CTR_REG.I2C_CONF_UPGATE` to cross the domain — easy to forget when poking registers directly.

**Clock source selection**: `I2C_CLK_CONF_REG.I2C_SCLK_SEL` chooses **XTAL_CLK (40 MHz, default)** or **RC_FAST_CLK (~17.5 MHz, less accurate)**. **Crucial difference from the original ESP32: APB_CLK is *not* a selectable I2C source on S3.** This is silently relevant — community advice from "set the I2C clock source to APB" doesn't apply. The fractional divider derives `I2C_SCLK = src / (DIV_NUM + 1 + A/B)`, and the TRM imposes `f_I2C_SCLK / f_SCL > 20` (TRM §27.4.7), so at 100 kHz SCL the module clock runs at ≥2 MHz.

### 1.3 FIFOs and command list

- TX RAM and RX RAM are each **32 bytes** (TRM §27.4.10; HAL constant `I2C_LL_FIFO_LEN = 32`). Same depth as original ESP32.
- **Command list is 8 slots** (`I2C_COMD0_REG`–`I2C_COMD7_REG`; HAL `I2C_LL_CMD_REG_NUM = 8`). **Original ESP32 had 16.** Each slot holds one of {RSTART, WRITE, READ, STOP, END}. `byte_num` is 8 bits per slot. A transaction must terminate in STOP or END within those 8 slots, with END→ISR-refill→`I2C_TRANS_START` chaining for longer sequences.
- Halving the command list relative to ESP32 means the S3 master needs more refill interrupts on long transfers. Our address-only probe is one slot, so this isn't directly our bug — but it's a behavioural divergence relevant to the broader "S3 touchier" pattern.

### 1.4 GPIO matrix only — no IOMUX direct path for I2C

This is the architectural fact that the failure investigation kept circling. TRM Table 6.11-1 lists peripheral signals 89–92 (`I2CEXT0_SDA_in/out`, `I2CEXT0_SCL_in/out`, and the I2C1 equivalents); **all four show "no" in both the "Direct Input via IO MUX" and "Direct Output via IO MUX" columns**. Every SDA/SCL edge on S3 traverses the GPIO matrix. There is no equivalent of the original ESP32's IOMUX-direct path on certain pin pairs.

What the matrix does to signals:

- **Inputs are 2-stage synchronized to APB_CLK** (TRM §6.4.2). With IDF defaults this is 2 APB cycles = 25 ns at 80 MHz. Configurable per-pin via `GPIO_PINn_REG.GPIO_PINn_SYNC1_BYPASS` and `..._SYNC2_BYPASS` — **the IDF I2C driver does not touch these.**
- **Outputs traverse a combinational mux** with no synchronizer. The TRM does not quote a propagation-delay number; it is implementation-defined. A one-APB-cycle skew between SDA and SCL output paths is not formally ruled out by the TRM — it's "not documented as a known issue" rather than "guaranteed bound to zero."

### 1.5 Open-drain emulation on a push-pull pad

S3 GPIO pads are push-pull CMOS. Open-drain is software-emulated: when the I2C controller wants to "release" the line, it de-asserts the pad's output-enable so the pad goes high-Z and the external pull-up does the work. When it wants to drive low, it asserts OE and the pad's NMOS pulls down (data is tied LOW internally; only OE toggles). Driven by `GPIO_PINn_REG.GPIO_PINn_PAD_DRIVER = 1` plus clearing `I2C_SCL_FORCE_OUT` and `I2C_SDA_FORCE_OUT`.

Crucially, **the TRM does not document any pad-level guarantee against a brief push-pull-while-transitioning glitch**. The OE signal is generated in the I2C_SCLK domain and reaches the pad through the GPIO matrix; the *data* signal also crosses the matrix. If those two signals skew on the output side by even half an APB cycle (6.25 ns at 80 MHz), the pad could momentarily drive HIGH during a release transition — a "1-bit-wide active-high pulse" that an analyzer integrator wouldn't see but that a slave's edge detector might. This is the closest the TRM-level architecture gets to predicting our exact symptom; it's not documented as a known issue, just not ruled out.

### 1.6 Drive capability on open-drain output

`IO_MUX_GPIOn_REG.IO_MUX_FUN_DRV[14:12]` selects `GPIO_DRIVE_CAP_0..3`. Default is 0x2 (~20 mA). Phase 23 of the investigation bumped to CAP_3 (~40 mA). In open-drain mode the high-side driver is disabled, so **drive cap controls only the pull-down sink strength** — fall slope of SCL/SDA. It does not affect rise time (which is purely R_pullup × C_bus). Drive cap is *not* a knob for high-side glitch suppression.

### 1.7 Schmitt trigger and pad input filter

- **Schmitt trigger on input is not documented for S3 GPIO pads.** No register, no API. Ignore as a knob.
- A separate **pad-level input filter** (`IO_MUX_GPIOn_REG.IO_MUX_FILTER_EN`, bit 15) does exist (TRM §6.4.3). It rejects input pulses shorter than 2 APB cycles (~25 ns at 80 MHz APB). This is **independent of the I2C controller's `I2C_FILTER_CFG_REG`**. The IDF I2C driver does *not* enable it. There is no public API; it requires direct register write or `gpio_iomux_*` helpers. This is one of the more interesting unflipped knobs.

## 2. Configurable knobs — full enumeration

| Knob | Register / API (legacy IDF 4.4) | Default | Range | What it changes |
|---|---|---|---|---|
| Clock source | `i2c_set_source_clk(I2C_NUM_0, I2C_SCLK_DEFAULT)` | XTAL (40 MHz) | XTAL or RC_FAST | Module clock. RC_FAST less accurate (~17.5 MHz, RC-trimmed). |
| SCL period (high+low) | `i2c_set_period(num, high, low)` (units: I2C_SCLK cycles) | derived from `Wire.setClock()` | 9 bits each | SCL clock period. Asymmetric duty cycle possible. |
| Bus timeout | `i2c_set_timeout(num, val)` | derived | exponent, max 2²² cycles | When SCL stuck triggers timeout interrupt. |
| Data setup/hold | `i2c_set_data_timing(num, sample_time, hold_time)` | derived | 9 bits each | SDA hold after SCL fall; SDA sample point relative to SCL rise. |
| START hold | `i2c_set_start_timing(num, setup_time, hold_time)` | derived | 9 bits each | t_HD;STA and t_SU;STA (repeated start). |
| STOP hold/setup | `i2c_set_stop_timing(num, setup_time, hold_time)` | derived | 9 bits each | t_SU;STO and t_BUF (bus-free time after STOP). |
| **Glitch filter (digital deglitcher)** | **`i2c_filter_enable(I2C_NUM_0, cyc_num)`** | **disabled by default in 4.4 wrapper** | **0–7 cycles** of I2C_SCLK | **Pulses shorter than `cyc_num` cycles ignored. Applied to both SDA and SCL together — they cannot be set independently from the public API. The new driver renames this to `glitch_ignore_cnt`, default 7.** |
| Peripheral instance | `Wire1.begin()` instead of `Wire.begin()`; in IDF: `I2C_NUM_1` | I2C0 | 0 or 1 | Switches to the other (architecturally identical) controller. |
| GPIO drive capability | `gpio_set_drive_capability(pin, GPIO_DRIVE_CAP_0..3)` | CAP_2 (~20 mA) | 4 levels | Pull-down sink strength (open-drain → no effect on rise). |
| GPIO internal pull-up | `gpio_pullup_en(pin)` / `gpio_pullup_dis(pin)` | unset (depends on pinMode) | on/off | ~45 kΩ to 3.3 V. We have 2.2 kΩ external; internals nominally negligible but explicit `gpio_pullup_dis()` is the only sure way to take them out (per arduino-esp32 #4887). |
| GPIO internal pull-down | `gpio_pulldown_en/dis()` | unset | on/off | Should always be off for I2C. Verify. |
| Pad open-drain | `gpio_set_direction(pin, GPIO_MODE_OUTPUT_OD)` | set by Wire.begin | on/off | Toggles `GPIO_PINn_PAD_DRIVER`. Must be on. |
| **Pad input filter** | **`REG_SET_BIT(IO_MUX_GPIO43_REG, FUN_FILTER_EN)`** (no public API) | **disabled** | on/off | **Independent 2-APB-cycle pulse filter at the pad input. Different from `i2c_filter_enable`. Not enabled by the I2C driver.** |
| GPIO sync bypass | `GPIO_PINn_REG` bits `SYNC1_BYPASS` / `SYNC2_BYPASS` (no public API) | 0 (no bypass) | 2 bits each | Input synchronizer stages. Not touched by I2C driver. Affects edge alignment by ±1 APB cycle. |
| `Wire.setClock()` | arduino-esp32 wrapper around `i2c_param_config` | 100 kHz / 400 kHz / etc. | up to ~800 kHz before quirks | Frontend for SCL period. Phase 22 already null-tested 50 kHz vs 100 kHz. |

**What's *not* exposed in the legacy driver:**

- `I2C_CTR_REG.I2C_SAMPLE_SCL_LEVEL` (sample SDA on rising vs falling SCL) — HAL only.
- `I2C_FIFO_CONF_REG.I2C_NONFIFO_EN` (direct RAM access) — HAL only.
- `I2C_CTR_REG.I2C_FSM_RST` — HAL only, and an [explicit comment in i2c_ll.h L33](https://github.com/espressif/esp-idf/blob/master/components/esp_hal_i2c/esp32s3/include/hal/i2c_ll.h#L33) says *"FSM_RST only resets the FSM, not using it"* — IDF deliberately doesn't use FSM-only reset for stuck-bus recovery. Recovery is via `i2c_ll_master_clr_bus()` (9 SCL pulses).

**ESP32-S3 errata search**: across all silicon revisions (v0.0, v0.1, v0.2) the [esp-chip-errata repo](https://github.com/espressif/esp-chip-errata/tree/master/docs/en/03-errata-description/esp32s3) lists eight errata: cache, RTC, analog power, LCD, USB-OTG, RMT, touch, ADC. **Zero are I2C-related, zero GPIO-matrix-related, zero pad-related.** Whatever is happening on a BQ24195 NACK is not a documented silicon bug.

## 3. Community-known issues

Mappability scale: **3** = directly predicts the symptom; **2** = adjacent; **1** = same neighbourhood, unlikely.

### 3.1 GitHub: ESP-IDF and arduino-esp32 (post-2024)

| Issue | Score | Summary | Mappable because… |
|---|---|---|---|
| [ESP-IDF #14343](https://github.com/espressif/esp-idf/issues/14343) | **3** | After NACK, S3 TX FIFO not flushed; *next* transaction emits stale byte instead of new address. Open. | Exactly "analyzer accepts the byte but it's not what we queued." Espressif rep `mythbuster5` engaged Jan 2025, no fix merged. |
| [ESP-IDF #17474](https://github.com/espressif/esp-idf/issues/17474) + [PR #17507](https://github.com/espressif/esp-idf/pull/17507) | **3** | Race between ISR-set `I2C_STATUS_ACK_ERROR` and non-atomic `i2c_master->event` — "state machine goes chaos" per Espressif. New driver only. PR atomicizes the event field. | Bursts of spurious NACK reports on S3 master. Doesn't cleanly map to our deterministic per-transaction NACK, but documents that the S3 master FSM has races at NACK boundaries. |
| [ESP-IDF #14030](https://github.com/espressif/esp-idf/issues/14030) | **3** | After one NACK, all subsequent transmits return `ESP_ERR_INVALID_STATE` — fixed by inserting `printf` into `i2c_master.c`. Confirmed independently. Open. | Sub-µs timing dependency where adding a delay masks the bug. Same family. |
| [ESP-IDF #15675](https://github.com/espressif/esp-idf/issues/15675) | **3** | S3 inserts ~30 µs idle (SCL high) inside `i2c_master_transmit_receive` between phases. Old driver was ~9 µs. Closed; Espressif provided in-line patch to `s_i2c_write_command`, not on a release branch. | Slaves with tight inter-phase tolerance can interpret the long stretch differently from cleaner masters like SAMD21. |
| [arduino-esp32 #11949](https://github.com/espressif/arduino-esp32/issues/11949) | 2 | `i2c_master_transmit()` fails synchronously on **identical S3-WROOM-1-N16R8 module** with v3.3.2. Open. | Same module SKU. Failure mode is queue-related, not address-NACK, but worth bookmarking. |
| [ESP-IDF #11605](https://github.com/espressif/esp-idf/issues/11605) | 2 | `i2c_master_write_to_device` ignores caller timeout on the address-NACK branch on S3. | Adjacent state-machine handling. |
| [ESP-IDF #14667](https://github.com/espressif/esp-idf/issues/14667) | 2 | Clock-stretching cap fixed at 20 ms on S3, fixed in IDF 5.3 commit `deb91c7a`. | BQ24195 doesn't stretch under normal flows; not direct. |
| [ESP-IDF #11397](https://github.com/espressif/esp-idf/issues/11397) | 2 | Generic "S3 vs ESP32 I2C instability" on same code/wire. Closed 2023 with no diagnosis. | Pattern match — "S3 less reliable on same wire" is the literature signature. |
| [ESP-IDF #8741](https://github.com/espressif/esp-idf/issues/8741) | 2 | "S3 I2C communication failures" — last comment 2025-01 from a user with the same WROOM-1-N16R8 module. Open. | Same SKU. Vague. |
| [arduino-esp32 #11351](https://github.com/espressif/arduino-esp32/issues/11351) / [#11496](https://github.com/espressif/arduino-esp32/issues/11496) | 1 | BMI160/ICM-20948 I2C broken in arduino-esp32 3.2.0 (which ships the new IDF v5.4 driver). | We're on 2.0.14 / IDF v4.4 / legacy driver — these don't apply unless we upgrade. |
| [arduino-esp32 #4887](https://github.com/espressif/arduino-esp32/issues/4887) | 1 | Internal pullups don't disable cleanly through `pinMode(INPUT)` alone; need explicit `gpio_pullup_dis()`. Closed 2021. | Bears mostly on the Arduino-as-master test bus-release path — already noted. |

**Audit of arduino-esp32 commits between v2.0.14 (Sep 2023) and v3.2.0 (Mar 2025) touching I2C** — gathered from `gh api .../compare/2.0.14...3.2.0` filtered for `i2c|wire`:

- `f0cf3b1a` 2025-01-21 — feat(i2c): add IDF v5.4 new I2C driver wrapper (#10858). **Crosses the new-driver boundary.**
- `2c4ce95e` 2024-09-10 — fix(i2c): ensure semaphore is given if init fails (#10313).
- `93a118c8` 2023-10-16 — fix `Wire.setClock()` causing assert (#8777).
- `db7b3495` 2023-11-29 — add lock to protect concurrent I2C transactions across tasks (#8127).
- `7966f4ae` 2024-01-31 — fix ambiguous `requestFrom()` overloads (#8817).
- `23c6779d` 2024-01-23 — fix(i2c): move I2C pins out of `CONFIG_DISABLE_HAL_LOCKS`.

Net effect of upgrading 2.0.14 → 3.2.0: gain Wire-init lock + setClock fix, but **inherit every open issue in the table above** (14343, 17474, 14030 all live on the new driver). Conservative read: upgrading is a coin flip, not a known fix.

**Glitch filter API across the version boundary:**

- Legacy (we're on this): **`i2c_filter_enable(i2c_port_t num, uint8_t cyc_num)`** — writes `I2C_FILTER_CFG_REG.scl_filter_thres` and `sda_filter_thres` together. Range 0–7 cycles. **Disabled by default in the arduino-esp32 v2.0.14 wrapper** — `i2c_param_config` does not call it. Not exposed via Wire; we'd add it manually after `Wire.begin()`.
- New driver (≥ IDF 5.2): renamed to `glitch_ignore_cnt`, set at bus creation time only via `i2c_master_bus_config_t.glitch_ignore_cnt = 7`. No runtime enable/disable. The new driver's default is 7; the legacy driver's default is 0.

So **on our current pinned version we are running with the digital deglitcher off**, on a chip whose I2C peripheral is documented as touchier than the original ESP32. This is the single largest unflipped knob.

### 3.2 Forums and external sources

- **Adafruit's official guidance** ([Troublesome Chips](https://learn.adafruit.com/i2c-addresses/troublesome-chips)): *"ESP32-S3 has problems with I2C devices that do clock stretching or have other unusual timing behavior when using ESP-IDF older than v5.3.2."* Fixed in CircuitPython 9.2.2+ and arduino-esp32 v3.2.0+ (which uses IDF 5.4.0). **We are below this watermark.**
- [PlatformIO thread #32320](https://community.platformio.org/t/esp32-s3-i2c-not-working-with-arduino-but-with-esp-idf/32320): same hardware, switching from arduino-esp32 `Wire` to native ESP-IDF `i2c_master` resolved an S3 NACK. Suggests the Wire shim is a contributing layer.
- [esp32.com #38167](https://www.esp32.com/viewtopic.php?t=38167) and [#38725](https://www.esp32.com/viewtopic.php?t=38725): scope captures of S3 holding SCL high "16 ms later, not during the command" — a late-SCL-release pattern that could break the *next* transaction's START framing. Resolved by Espressif backporting an IDF 5.3.x fix.
- [esp32.com #11679](https://esp32.com/viewtopic.php?t=11679): rounded SCL rising edges read as two pulses by the slave. Fix: lower pull-up resistance + enable hardware glitch filter (`glitch_ignore_cnt = 7`).
- [TI E2E #1582042](https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/1582042): TMP1075 NACKs every transaction from an ESP32-S3 DevKitC-1, address byte visible on logic analyzer. TI engineer's first response is to demand a scope shot — implying TI knows the analyzer-passes-but-silicon-rejects pattern. **Same family as our BQ symptom.**
- [TI E2E #1404063](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/1404063): TCA9548A returning NAK; TI flagged "slow rise time interpreted as malformed START." Aligns with our cable+pullup loading.
- [Arduino forum #1289555](https://forum.arduino.cc/t/i2c-issues-with-esp32-s3/1289555) and [#1281448](https://forum.arduino.cc/t/esp32-s3-i2c-not-working/1281448): repeated "Wire.setPins() to force IOMUX-direct routing" advice — but this is **bunk on S3 specifically**, since per the TRM no GPIO pair is IOMUX-direct for I2C. The advice is a folk remedy that worked on classic ESP32 and got cargo-culted to S3.

### 3.3 Synthesis from all sources

Three patterns recur:

1. **S3 master FSM has documented races and stale-FIFO behaviour around NACK.** ESP-IDF #14343 and #17474 are the high-confidence anchors.
2. **S3 START/SCL-release shape can be marginal.** Multiple esp32.com threads and the TI E2E TMP1075 thread describe TI parts (and others) NACKing where SAMD21 / classic ESP32 pass. Fixed for many users by IDF 5.3.2+ and/or by enabling `glitch_ignore_cnt = 7`.
3. **The `Wire` shim layer matters.** PlatformIO #32320 documents bare ESP-IDF working where Wire fails on the same hardware.

There is **no single smoking-gun issue** that exactly predicts our v7 fault. But the union of these three patterns makes the failure mode plausible.

## 4. Hypothesis mapping

For each suspect mechanism, a candidate fix and a discriminator (what would falsify it).

| Suspect mechanism | If it's the cause… | Discriminator (what would refute) |
|---|---|---|
| **Digital deglitcher off** — sub-µs glitches on SDA pass through, BQ's input rejects | `i2c_filter_enable(I2C_NUM_0, 7)` resolves. | Filter on, BQ still NACKs in failing config. |
| **Pad-level input filter off** — sub-25-ns glitches at the pad pass through (independent path from the I2C filter) | Setting `IO_MUX_FILTER_EN` on GPIO 43/44 resolves. | Filter on, BQ still NACKs. |
| **Late SCL release / inter-phase idle** (#15675-class) | Patching `s_i2c_write_command` or upgrading to IDF 5.3.2+ resolves. | Upgrade, still NACKs. |
| **TX FIFO not flushed after NACK** (#14343-class) | First-transaction-after-mux-open is special; subsequent ones differ. | Inspect log: each iteration's BQ NACK is identical and deterministic regardless of prior transaction history. Phase 4 already shows this — *deterministic per-iteration, independent of prior state* — which **weakens** this hypothesis but doesn't fully refute it (the channel-open could itself produce the stale state). |
| **Wire shim doing something wrong** | Bare `i2c_master_write_to_device()` succeeds where `Wire.endTransmission()` fails on the same hardware. | Both fail identically. |
| **GPIO matrix output skew between SDA and SCL** | Switching to I2C1 (different controller, same matrix path) won't help. Switching pins might. Bit-banged software I2C definitely will (no peripheral). | All three work / all three fail equivalently. |
| **Open-drain glitch — pad briefly drives HIGH on release** | Same as above: bit-banging from arduino-`pinMode(OUTPUT_OD)` would still hit it; but bit-banging from manual `digitalWrite(LOW)` + `pinMode(INPUT)` toggling would expose any difference vs the I2C peripheral's OE machinery. | Bit-bang fails identically. |
| **Internal pull-up on S3 still active despite externals** (#4887) | `gpio_pullup_dis(43); gpio_pullup_dis(44)` after `Wire.begin()` resolves. | No change. |
| **Setup/hold timing too aggressive at default** | Manually widening `i2c_set_data_timing` and `i2c_set_start_timing` resolves. | Widened, still NACKs. |
| **Drive cap interaction at falling edge** | Cap_3 already tested in Phase 23 — V_OL drop confirmed, BQ still NACKs. **Refuted as primary mechanism.** | (Already refuted.) |
| **I2C0-specific analog quirk** | `Wire1` on I2C1 ACKs where `Wire` on I2C0 NACKs. | Both behave identically. |
| **Pin pair 43/44 specific (UART0 default pins)** | Moving SDA/SCL to a different pin pair (e.g. 8/9, or any free pair on the v7 schematic that can be bodged) resolves. | No change. |

## 5. Ranked firmware experiments

Ordered by **predictive value × low cost**. Each entry: 1-line summary, predicted outcome, exact code, where it goes in [SensorManager.cpp:629](../../firmware/src/components/sensor/SensorManager.cpp#L629), test time, refutation criterion.

### Experiment 1 — Enable the I2C glitch filter (highest priority, lowest cost)

**Summary**: Turn on the legacy-driver digital deglitcher at maximum (7 I2C_SCLK cycles ≈ 350 ns at 20 MHz I2C_SCLK, ≈ 87.5 ns at 80 MHz). This is the new driver's default that we are missing.

**Predicted outcome**: if the failing-config bus is producing sub-µs glitches that the analyzer integrates over but BQ rejects, BQ ACKs.

**Code** — add include and a single line after `Wire.begin()`, before `gpio_set_drive_capability`:

```cpp
#include <driver/i2c.h>
// ...
Wire.begin(43, 44);
Wire.setClock(100000);
i2c_filter_enable(I2C_NUM_0, 7);   // EXPERIMENT 1
gpio_set_drive_capability(GPIO_NUM_43, GPIO_DRIVE_CAP_3);
gpio_set_drive_capability(GPIO_NUM_44, GPIO_DRIVE_CAP_3);
```

**Test time**: 5 min (build + flash + watch diagnostic loop).

**Refutation**: BQ still NACKs on TCA2 row. Refutes "digital deglitcher" as the missing knob. This is the cheapest experiment, do it first.

### Experiment 2 — Enable the pad-level input filter (second-cheapest)

**Summary**: Set `IO_MUX_FILTER_EN` on GPIO 43 and 44. This is a separate ~25 ns pulse filter at the pad input, independent of the I2C controller's filter. The IDF I2C driver does not enable it.

**Predicted outcome**: if there's a pad-level input glitch the I2C filter doesn't catch, this catches it.

**Code**:

```cpp
#include <soc/io_mux_reg.h>
#include <hal/gpio_ll.h>
// after Wire.begin():
REG_SET_BIT(GPIO_PIN_MUX_REG[43], FUN_FILTER_EN);
REG_SET_BIT(GPIO_PIN_MUX_REG[44], FUN_FILTER_EN);
```

**Test time**: 10 min.

**Refutation**: BQ still NACKs. Refutes pad-level input glitches as the missing-filter mechanism.

### Experiment 3 — Explicitly disable internal pull-ups and pull-downs

**Summary**: Per arduino-esp32 #4887, internal pulls don't reliably disable through `pinMode` alone. We have 2.2 kΩ external pulls. The internal ~45 kΩ pulls in parallel are nominally negligible but not guaranteed off.

**Predicted outcome**: low — Phase 5 already varied total bus pull-up by 10× (1.5 kΩ to 2.1 kΩ effective) with no behavioural change, so a hypothetical extra 45 kΩ in parallel is unlikely to be the gating factor. Still cheap to rule out.

**Code**:

```cpp
gpio_pullup_dis(GPIO_NUM_43);
gpio_pullup_dis(GPIO_NUM_44);
gpio_pulldown_dis(GPIO_NUM_43);
gpio_pulldown_dis(GPIO_NUM_44);
```

**Test time**: 5 min. Bundle with Experiment 1 to amortize.

**Refutation**: no change. Closes #4887 as the mechanism.

### Experiment 4 — Switch to I2C1 (Wire1 instead of Wire)

**Summary**: arduino-esp32 exposes `Wire1` mapped to `I2C_NUM_1`. Same pins, same routing through GPIO matrix, but a different controller instance. If the failure depends on any non-documented analog or transistor-level difference between the two instances, this discriminates.

**Predicted outcome**: low — TRM says they're identical. But this is a 10-minute test that closes a hypothesis we can't otherwise close.

**Code**: replace `Wire.begin()` and `Wire.setClock()` with `Wire1.begin(43, 44); Wire1.setClock(100000);`. Update the entire SensorManager and TCA library use to reference `Wire1` (TCA9548 library accepts a `&Wire1` pointer in its constructor — check). This is more invasive than a one-liner but still under an hour.

**Test time**: 30–45 min including library plumbing.

**Refutation**: same NACK on Wire1. Refutes per-instance analog quirk.

### Experiment 5 — Drop Wire entirely; use raw `i2c_master_write_to_device`

**Summary**: Bypass the arduino-esp32 Wire shim. Directly call legacy ESP-IDF `i2c_master_write_to_device(I2C_NUM_0, 0x6B, ...)`. This is the discriminator validated by [PlatformIO #32320](https://community.platformio.org/t/esp32-s3-i2c-not-working-with-arduino-but-with-esp-idf/32320).

**Predicted outcome**: medium — if Wire is doing something subtle (extra START retries, mis-set timing, leftover state from probing INA), going to bare IDF surfaces it.

**Code**: a small standalone `bq_probe_idf()` helper that calls `i2c_param_config()`, `i2c_driver_install()`, then `i2c_master_write_to_device()` directly. Wrap in a build flag so it can be toggled without disturbing the rest of the firmware.

```cpp
i2c_config_t conf = {
    .mode = I2C_MODE_MASTER,
    .sda_io_num = 43,
    .scl_io_num = 44,
    .sda_pullup_en = GPIO_PULLUP_DISABLE,
    .scl_pullup_en = GPIO_PULLUP_DISABLE,
    .master = { .clk_speed = 100000 },
    .clk_flags = 0,
};
i2c_param_config(I2C_NUM_0, &conf);
i2c_driver_install(I2C_NUM_0, conf.mode, 0, 0, 0);
i2c_filter_enable(I2C_NUM_0, 7);
uint8_t dummy = 0;
esp_err_t err = i2c_master_write_to_device(I2C_NUM_0, 0x6B, &dummy, 0, pdMS_TO_TICKS(50));
```

**Test time**: 60–90 min.

**Refutation**: same NACK. Refutes "Wire shim is the layer at fault."

### Experiment 6 — Software bit-banged I2C as an extreme test

**Summary**: Use a known-good bit-banged I2C library ([SoftWire](https://github.com/stevemarple/SoftWire), [BitBang_I2C](https://github.com/bitbank2/BitBang_I2C)) on GPIO 43/44. If this works where the peripheral fails, the peripheral is unambiguously the culprit and the mechanism is at the peripheral-output side of the chain.

**Predicted outcome**: high information value either way.
- Works → Story F is fully confirmed at the peripheral level (not just at the master-vs-master level Phase 24 showed).
- Fails → mechanism is in something common between bit-bang and peripheral output, e.g. the GPIO pad itself or matrix routing.

**Code**: pull in BitBang_I2C, replace `Wire` with the bit-bang instance, run the same probe. ~1–2 hours including library swap.

**Test time**: 90–120 min.

**Refutation**: bit-bang also NACKs. Pushes the suspect from "I2C peripheral logic" to "GPIO pad / matrix output."

### Experiment 7 — Manually widen START hold and data setup/hold

**Summary**: Override the auto-derived timing registers via legacy API. Predict: if BQ's input has a tighter setup/hold tolerance than the analyzer, widening these helps.

**Predicted outcome**: medium. Phase 22 (50 kHz null) already showed clock-rate-dependent dynamics aren't the gating factor — but the period scales the *whole* timing graph, while these knobs scale only the START / data-edge phases. Worth a separate test.

**Code**:

```cpp
// At 100 kHz with default 80 MHz APB / 40 MHz XTAL I2C_SCLK,
// 1 I2C_SCLK cycle ≈ 25 ns. Widen START hold from default ~30 cycles
// to 100 cycles, data hold from default ~30 to 100.
i2c_set_start_timing(I2C_NUM_0, /*setup*/ 100, /*hold*/ 100);
i2c_set_data_timing(I2C_NUM_0, /*sample*/ 100, /*hold*/ 100);
i2c_set_stop_timing(I2C_NUM_0, /*setup*/ 100, /*hold*/ 100);
```

**Test time**: 30 min including iterating values.

**Refutation**: no change across a sweep of 30→200 cycles. Refutes timing-edge tightness.

### Experiment 8 — Move SDA/SCL to a different pin pair

**Summary**: GPIO 43/44 are the default UART0 TX/RX pins, freed by `ARDUINO_USB_CDC_ON_BOOT=1`. They're in a specific physical row of the WROOM-1's pad ring; matrix routing path may depend on physical pad position. Move I2C to e.g. GPIO 8/9 (or any unused free pair on the v7 schematic).

**Predicted outcome**: low — TRM doesn't say physical pad row affects matrix latency, but it doesn't *guarantee* it doesn't. Bodge required if v7's PCB doesn't have free alt pins; otherwise just a config change.

**Test time**: 30 min if pins are already broken out; 1+ hours if a hardware bodge is needed.

**Refutation**: no change. Refutes pin-pair-specific routing.

### Experiment 9 — Upgrade arduino-esp32 to 3.1.3 (last pre-regression version) or 3.2.x

**Summary**: per Adafruit's "Troublesome Chips" guidance, IDF 5.3.2+ fixes a class of S3 I2C issues. arduino-esp32 3.2.0 ships IDF v5.4. **However**, 3.2.0 also introduced [#11351](https://github.com/espressif/arduino-esp32/issues/11351) and [#11496](https://github.com/espressif/arduino-esp32/issues/11496) regressions affecting other common sensors. Test 3.1.3 first (last pre-regression; ships an earlier IDF).

**Predicted outcome**: medium-low. Adafruit's framing is about clock-stretching and unusual timing — neither obviously matches our deterministic, no-stretch failure. But it's a published Espressif-blessed delta.

**Code**: change [platformio.ini:23](../../platformio.ini#L23):

```
framework-arduinoespressif32@https://github.com/espressif/arduino-esp32.git#3.1.3
```

**Test time**: 30–60 min including build-failure triage from API drift in our codebase (the new I2C driver model changes some headers).

**Refutation**: no change. Refutes "fixed by post-2.0.14 IDF improvements."

### Experiment 10 — `Wire.setPins()` before `Wire.begin()` (folk-remedy null test)

**Summary**: Multiple Arduino forum threads recommend explicit `Wire.setPins(SDA, SCL)` before `Wire.begin()` "to force IOMUX routing." **Per the TRM this is bunk on S3** — there is no IOMUX-direct path for I2C. But the *call* sets pins via a different code path internally and may flush some otherwise-stale config.

**Predicted outcome**: very low. Including for completeness; if it works for some folk-remedy reason we want to know.

**Code**: `Wire.setPins(43, 44); Wire.begin();` (note the order — setPins before begin).

**Test time**: 5 min.

**Refutation**: no change. Confirms it's bunk on S3.

## 6. What this document does not cover

By instruction, none of the following are addressed:

- Hardware fixes (R28/R29 changes, I2C buffer ICs, v8 redesign). See [investigation doc § Candidate fixes](../debugging/v7-i2c-investigation.md).
- BQ24195-side mechanisms (Story H — Schmitt deglitcher, START detector quirks). The Arduino-as-master result has already pushed weight onto Story F.
- TCA9548A pass-gate Vpass behaviour. Documented in investigation Phase 19.
- Bus topology, pull-up sizing, cable parasitics. Already characterized.

## 7. Recommended sequence

If only a subset of experiments will be run, do them in this order:

1. **Experiment 1** (`i2c_filter_enable`) — 5 min, free, addresses the largest unflipped knob.
2. **Experiment 3** (`gpio_pullup_dis`) — bundle with #1.
3. **Experiment 5** (raw IDF `i2c_master_write_to_device`) — discriminates Wire shim from peripheral.
4. **Experiment 6** (software bit-bang) — discriminates peripheral from pad/matrix.
5. **Experiment 7** (timing register widening) — closes timing-edge tightness.
6. **Experiment 4** (Wire1 / I2C1) — closes per-instance quirk.
7. **Experiments 8, 9, 10** — only if 1–6 all null.

If 1–6 all null, the failure is in a path that none of {filters, internal pulls, Wire, peripheral logic, peripheral instance, timing edges, pad position} affects. That would push the suspect onto the GPIO pad's open-drain glitch hypothesis (§1.5) — testable only with a sub-ns scope at the pad, which we don't have on bench. At that point the answer is the v8 buffer regardless of which open-drain story is right.

## Sources

- [ESP32-S3 Technical Reference Manual v1.8](https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf)
- [ESP32-S3 Series Datasheet v2.2](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
- [ESP-IDF master — components/esp_hal_i2c/esp32s3/include/hal/i2c_ll.h](https://github.com/espressif/esp-idf/blob/master/components/esp_hal_i2c/esp32s3/include/hal/i2c_ll.h)
- [ESP-IDF master — components/esp_driver_i2c/i2c_master.c](https://github.com/espressif/esp-idf/blob/master/components/esp_driver_i2c/i2c_master.c)
- [ESP-IDF master — components/driver/i2c (legacy driver)](https://github.com/espressif/esp-idf/tree/master/components/driver/i2c)
- [ESP-IDF v4.4 I2C API reference (legacy driver, applicable to arduino-esp32 2.0.14)](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/i2c.html)
- [ESP-IDF v5.4 I2C API reference (new driver)](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-reference/peripherals/i2c.html)
- [esp-chip-errata for ESP32-S3](https://github.com/espressif/esp-chip-errata/tree/master/docs/en/03-errata-description/esp32s3)
- [arduino-esp32 master — cores/esp32/esp32-hal-i2c.c](https://github.com/espressif/arduino-esp32/blob/master/cores/esp32/esp32-hal-i2c.c)
- [ESP-IDF #14343 — S3 TX FIFO not flushed after NACK](https://github.com/espressif/esp-idf/issues/14343)
- [ESP-IDF #17474 — S3 master FSM "goes chaos" race](https://github.com/espressif/esp-idf/issues/17474)
- [ESP-IDF PR #17507 — atomic event field fix](https://github.com/espressif/esp-idf/pull/17507)
- [ESP-IDF #14030 — NACK leaves driver in INVALID_STATE, "fixed" by adding printf](https://github.com/espressif/esp-idf/issues/14030)
- [ESP-IDF #15675 — 35 µs idle inside transmit_receive on S3](https://github.com/espressif/esp-idf/issues/15675)
- [ESP-IDF #11605 — write_to_device ignores caller timeout on NACK](https://github.com/espressif/esp-idf/issues/11605)
- [ESP-IDF #14667 — S3 clock-stretching cap fixed at 20 ms](https://github.com/espressif/esp-idf/issues/14667)
- [ESP-IDF #11397 — S3 vs ESP32 I2C instability](https://github.com/espressif/esp-idf/issues/11397)
- [ESP-IDF #8741 — S3 I2C communication failures (WROOM-1-N16R8 reporter)](https://github.com/espressif/esp-idf/issues/8741)
- [arduino-esp32 #11949 — i2c_master_transmit fails on S3-WROOM-1-N16R8 v3.3.2](https://github.com/espressif/arduino-esp32/issues/11949)
- [arduino-esp32 #11351 — BMI160/ICM-20948 broken in 3.2.0](https://github.com/espressif/arduino-esp32/issues/11351)
- [arduino-esp32 #11496 — I2C regression 3.1.3 → 3.2.0](https://github.com/espressif/arduino-esp32/issues/11496)
- [arduino-esp32 #4887 — internal pullups not cleanly disabled](https://github.com/espressif/arduino-esp32/issues/4887)
- [arduino-esp32 PR #10858 — IDF v5.4 new I2C driver wrapper](https://github.com/espressif/arduino-esp32/pull/10858)
- [Adafruit Learning System — Troublesome Chips](https://learn.adafruit.com/i2c-addresses/troublesome-chips)
- [PlatformIO Community — ESP32-S3 I2C not working with Arduino but with ESP-IDF](https://community.platformio.org/t/esp32-s3-i2c-not-working-with-arduino-but-with-esp-idf/32320)
- [esp32.com #38167 — ESP32-S3 I2C SCL release timing](https://www.esp32.com/viewtopic.php?t=38167)
- [esp32.com #38725 — ESP32-S3 I2C failure in ESP-IDF 5.2 (IDFGH-12268)](https://www.esp32.com/viewtopic.php?t=38725)
- [esp32.com #11679 — Rounded SCL edge / hardware filter](https://esp32.com/viewtopic.php?t=11679)
- [TI E2E #1582042 — TMP1075 NACK on ESP32-S3-DevKitC-1](https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/1582042/tmp1075-mp1075-on-esp32-s3-devkitc-1-i2c-nack-at-address-0x48-logic-analyzer-capture-attached)
- [TI E2E #1404063 — TCA9548A I2C returning NAK](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/1404063/tca9548a-i2c-returning-nak)
- [Arduino forum #1289555 — I2C issues with ESP32-S3](https://forum.arduino.cc/t/i2c-issues-with-esp32-s3/1289555)
- [Arduino forum #1281448 — ESP32 S3 I2C not working](https://forum.arduino.cc/t/esp32-s3-i2c-not-working/1281448)
