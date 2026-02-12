# Interrupt Detection Analysis Checklist

> **Purpose**: Track investigation and documentation tasks for understanding and improving our interrupt-based direction detection.
> 
> **Context**: Our sensor assemblies (rigid+flex hybrid design) combine two VCNL4040 INT lines via BAT54S diodes into a single wire. The flex PCB angles sensors ~2° apart to increase detection window, but ambiguity still exists when both sensors trigger within milliseconds of each other.

---

## 1. Circuit Documentation

- [ ] **Natural Language Netlist**
  - Create human-readable description of the INT circuit
  - Combine structured data (JSON/YAML) with prose explanations
  - Cover: Main PCB INT routing (GPIOs 11, 12, 13 → J4, J5, J6)
  - Cover: Sensor PCB wiring (J1 Pin 5 → R5 pull-up → BAT54S → VCNL4040 INT pins)
  - Explain the wired-OR diode configuration purpose

- [ ] **Component Reference**
  - BAT54S Schottky diode function in this circuit
  - R5 (8.2kΩ) pull-up resistor role
  - PCA9546A I2C mux (doesn't pass INT, only I2C)
  - VCNL4040 INT behavior (open-drain, active LOW)

---

## 2. Event Flow Diagrams

- [ ] **Scenario A: Single Sensor Interrupt**
  - Diagram showing GPIO goes LOW → ISR fires → I2C read → flag check → timestamp
  - Show timing at each step

- [ ] **Scenario B: Two Sensors, 2ms Apart (The Problem)**
  - Sensor 1 triggers at T=0
  - ISR fires, starts I2C communication
  - Sensor 2 triggers at T=2ms
  - By time we read flags, both are set
  - Show why we lose ordering information

- [ ] **Scenario C: Current Firmware Flow**
  - Document existing InterruptManager behavior
  - GPIO-to-board mapping
  - I2C polling to identify which sensor

---

## 3. Problem Analysis

- [ ] **Document the Core Issue**
  - Combined INT = can't distinguish which sensor triggered first
  - I2C flag read latency vs object transit time
  - Reading flags clears them (can't re-check)

- [ ] **Quantify the Timing**
  - How fast does an object traverse the sensor pair? (estimate)
  - How long does I2C flag read take? (~100-500µs?)
  - What's the window where ambiguity occurs?

---

## 4. Solution Options - Existing PCBs

- [ ] **Firmware Strategies**
  - Faster I2C polling after first interrupt
  - Hybrid: Use interrupt as wake, then rapid poll
  - Logic output mode (INT stays LOW while object present)

- [ ] **Hardware Workarounds (If Any)**
  - Can we use existing test points?
  - Any unused connections we could repurpose?

- [ ] **Accept Limitations**
  - Document what works with current design
  - Define use cases where combined INT is sufficient

---

## 5. Solution Options - Future PCB Redesign

- [ ] **Separate INT Lines Per Sensor**
  - New connector: 7-pin (add INT1, INT2 separately)
  - Main board changes: 2 GPIOs per sensor board (6 total instead of 3)
  - Pros: Immediate sensor identification, no I2C needed to know which
  - Cons: More wires, more GPIOs, connector change

- [ ] **Keep Combined + Add Secondary Signal**
  - Ideas for analog encoding (below)
  - Trade-offs vs separate lines

---

## 6. Analog Differentiation Ideas

- [ ] **Different Pull-Down Resistors**
  - Each sensor has different resistor after BAT54S
  - Creates different voltage levels when pulling LOW
  - Would need ADC instead of GPIO (T-Display has ADC pins?)

- [ ] **RC Timing Differences**
  - Add capacitor to one sensor's INT path
  - Creates detectable rise/fall time difference
  - Measure with timer capture

- [ ] **Pulse Encoding**
  - One-shot or 555 timer to create distinct pulse pattern
  - Adds complexity and parts

- [ ] **Feasibility Assessment**
  - Which ideas are practical for our constraints?
  - Power consumption implications
  - PCB space constraints

---

## 7. Decision & Next Steps

- [ ] **Decide on Approach**
  - For existing PCBs: What firmware changes to try?
  - For next PCB revision: Separate INT or analog encoding?

- [ ] **Update STATUS.md**
  - Document decisions made
  - Update implementation status

---

## Reference Files

| File | Description |
|------|-------------|
| `hardware/sensor-rigid/sensor-rigid.json` | Sensor rigid base PCB netlist (PCA9546A, INT combining) |
| `hardware/sensor-flex/sensor-flex.kicad_sch` | Sensor flex strip schematic (VCNL4040s) |
| `hardware/pcb-main/kicad/netlists/motion-play-main_5-1.json` | Main PCB netlist |
| `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md` | Hybrid rigid+flex design rationale |
| `docs/initiatives/interrupt-detection/DESIGN_PLAN.md` | Original interrupt mode design |
| `docs/initiatives/interrupt-detection/STATUS.md` | Current implementation status |
| `firmware/src/components/interrupt/InterruptManager.h` | Firmware interrupt handling |

---

*Created: December 15, 2025*

