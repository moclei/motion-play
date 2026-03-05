# Motion Play Project Context

> **Quick Reference**: See [manifest.yaml](./manifest.yaml) for structured metadata. See [IDEAS.md](./IDEAS.md) for feature backlog. See [WORKFLOW.md](./WORKFLOW.md) for instructions on managing features and initiatives.

## Overview

Motion Play is an ESP32-based sensor system for detecting and tracking fast-moving objects through a detection plane. The system determines movement direction and provides visual feedback through LED lights. Multiple units can be networked via Bluetooth, and the system supports WiFi connectivity for mobile device integration. Designed for games and sports performance training applications.

## Vision & Goals

Motion Play is primarily an engineering project — the goal is to design and build a complete sensor-based sports training system from scratch, learning across every discipline (electronics, firmware, cloud, ML, mechanical design). Creating something commercially viable is part of that learning journey, not the sole objective.

**Near-term milestone:** A portable, battery-powered system robust enough for real playtesting — surviving balls kicked at up to 20mph, transportable by car to remote locations away from the workstation, and capable of gathering training sessions and testing play modes in the field.

**Medium-term:** Iterate through enclosure and hardware designs toward a self-contained device (hoop + main PCB + sensors + LED strip + battery) that is well-tested, durable, and approaching production quality.

**Long-term:** A Motion Play device that could potentially be manufactured at scale and sold — though the path there is through engineering depth, not shortcuts to market.

## Current Project Status

**Hardware:** ✅ Custom PCBs operational with dual-MUX architecture (TCA→PCA→Sensors)
**Firmware:** ✅ Full data collection pipeline (1000 Hz, PSRAM buffering, MQTT transmission)
**Backend:** ✅ AWS IoT Core + Lambda + DynamoDB + API Gateway
**Frontend:** ✅ React web interface with real-time visualization and device control
**ML Detection:** 🔄 Initial proof-of-concept working — TFLite Micro 1D CNN running on-device. See `docs/initiatives/ml-direction-detection/`
**Current Phase:** Phase 4 - Integration & Polish (77% complete overall)

## Distributed Context System

This project uses a distributed documentation system for AI chat context. Instead of putting all details in this file, each major aspect of the project maintains its own `CONTEXT.md` with domain-specific details.

**How it works:**
- **This file** (`PROJECT.md`) provides the high-level project overview, cross-cutting terminology, and a map of what lives where. It should be read first.
- **Aspect CONTEXT.md files** (e.g., `firmware/CONTEXT.md`) contain the detailed architecture, constraints, and design decisions specific to that domain. Read the relevant one when working in that area.
- **README.md files** in some folders provide developer-oriented documentation (build steps, API reference, debugging). These complement the CONTEXT.md files.
- **Initiative docs** in `docs/initiatives/` follow the BRIEF/PLAN/TASKS structure defined in [WORKFLOW.md](./WORKFLOW.md).

**When starting a new conversation about a specific area**, point the AI at both this file and the relevant aspect's `CONTEXT.md`. When working across aspects, include multiple CONTEXT.md files as needed.

**When creating a new aspect or major folder**, add a `CONTEXT.md` to it following the same pattern: what it is, how it's structured, key design decisions, and relationships to other aspects.

## Project Structure

```
motion-play/
├── .context/              # AI documentation (this file, manifest, workflow, ideas)
├── firmware/              # ESP32-S3 firmware (C++/Arduino)  ← has CONTEXT.md
├── frontend/              # React web interface (TypeScript)  ← has CONTEXT.md
├── hardware/              # KiCad schematics and PCB designs  ← has CONTEXT.md
├── infrastructure/        # AWS setup docs and config  ← has CONTEXT.md
├── lambda/                # AWS Lambda function source (Node.js)
├── mechanical/            # Physical enclosures, 3D-printed parts (build123d)
├── docs/                  # Project documentation
│   ├── explorations/      # Problem-space analyses (pre-initiative)
│   ├── initiatives/       # Feature docs (BRIEF/PLAN/TASKS per feature)
│   └── references/        # Hardware datasheets and component docs
├── tools/                 # Diagnostic and ML tools
│   ├── ml-training/       # Python ML pipeline (download, preprocess, train, export TFLite)
│   ├── serial-studio/     # Serial Studio dashboard files
│   └── transit-calculator.py
├── scripts/               # Utility shell scripts
├── session_data/          # Labeled training data
├── platformio.ini         # PlatformIO configuration
└── README.md              # GitHub-facing project summary
```

### Aspect Context Files

| Aspect | CONTEXT.md | Covers |
|--------|------------|--------|
| **Firmware** | `firmware/CONTEXT.md` | Dual-core architecture, pin config, power management, Serial Studio, build config, data collection flow |
| **Hardware** | `hardware/CONTEXT.md` | PCB designs (main + sensor rigid + flex), physical architecture, I2C mux chain, annotated netlist spec, component nicknames |
| **Infrastructure** | `infrastructure/CONTEXT.md` | AWS architecture, IoT Core, Lambda functions, DynamoDB schema (composite key!), API endpoints, MQTT message formats, data flow |
| **Frontend** | `frontend/CONTEXT.md` | React app architecture, tech stack, what it does, relationship to cloud infrastructure |
| **Mechanical** | `mechanical/CONTEXT.md` | Enclosure design process, build123d tooling, coordinate conventions, folder structure, FDM design rules |

### Folders Without CONTEXT.md

These folders have README.md files or are self-explanatory:

- **`lambda/`** — Lambda function source code. Has its own `README.md` with deployment guides. Closely related to `infrastructure/`.
- **`mechanical/`** — Enclosure designs using build123d (Python CAD). Has `CONTEXT.md` covering design process, tooling, and constraints. See `specs/assembly-v0.1.yaml` for dimensions.
- **`docs/`** — Organized per [WORKFLOW.md](./WORKFLOW.md). Explorations are single-file analyses; initiatives follow BRIEF/PLAN/TASKS.
- **`tools/`** — `ml-training/` has its own README. `serial-studio/` dashboard files are documented in `firmware/CONTEXT.md`.
- **`scripts/`** — Utility scripts with `README.md`.
- **`session_data/`** — Labeled sensor data for ML training.

## Terminology

Standard terms used across code, docs, and conversation.

### Hardware

| Term | Definition | Code / Notation |
|------|-----------|-----------------|
| **Sensor Module** | Complete assembly: rigid base + flex strip + enclosure. Three per system, spaced 120° around the hoop. | Module 1 (M1) at 6 o'clock, M2 at 9 o'clock, M3 at 3 o'clock |
| **Rigid Base** | FR4 PCB with PCA9546A I2C mux and connectors. | `hardware/sensor-rigid/` |
| **Flex Strip** | Polyimide flex PCB with both VCNL4040 sensors. Bends to angle sensors ~2° outward. | `hardware/sensor-flex/` |
| **Sensor** | Individual VCNL4040 proximity/ambient light sensor. | Identified by module + side: M1-A, M1-B, etc. In code: `position` (0–5), `pcb_id` (1–3), `side` (1–2) |
| **Side A / Side B** | Two sensors on a module. A (side 1) faces back (-2°). B (side 2) faces front (+2°). | P1S1 = Module 1 Side A, P1S2 = Module 1 Side B |

### Data Pipeline

| Term | Definition | Code Reference |
|------|-----------|---------------|
| **Reading** | Single proximity + ambient value from one sensor at one timestamp. The atomic unit. | `SensorReading` struct |
| **Cycle** | One complete read of all active sensors at the same timestamp. | `SessionSummary.total_cycles` |
| **Wave** | Continuous period where a side's smoothed signal exceeds its adaptive threshold. | `WaveTracker`, `WaveState` |
| **Detection** | Algorithmic conclusion: both sides showed waves within a valid time window, direction + confidence computed. | `DetectionResult` struct |
| **Transit** | Physical event of an object passing through the hoop plane. One transit → readings → waves → detection. | Conceptual term |

## Key Architectural Decisions

- **Composite Timestamp Key**: `(timestamp_ms * 10) + sensor_position` — allows multiple sensors to write simultaneously without DynamoDB key collisions
- **Dual-Core Split**: Core 0 = sensors (1000 Hz, time-critical), Core 1 = networking (WiFi, MQTT, display)
- **Dual MUX Chain**: TCA9548A (main) → PCA9546A (sensor board) → VCNL4040 — all sensors share address 0x60
- **Cloud Config Authority**: Device fetches sensor config from cloud on boot; frontend is the authoritative config source
- **Session Flow**: Start command → buffer in PSRAM → stop command → batch upload → Lambda processes → DynamoDB
- **Rigid + Flex PCB Split**: Flex allows ~2° sensor angle for direction discrimination; rigid carries mux and connectors

## Development Environment

- **Framework**: Arduino on PlatformIO
- **Board**: ESP32-S3 (LilyGO T-Display-S3)
- **IDE**: Cursor (VSCode-based)
- **Version Control**: GitHub
- **Laptop**: MacBook Pro

## Development Roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| Phase 0: Setup & Preparation | ✅ Complete | AWS infra, dev environments, PCB design |
| Phase 1: Basic Connectivity | ✅ Complete | WiFi, MQTT, TLS, display integration |
| Phase 2: Data Pipeline | ✅ Complete | 1000 Hz collection, PSRAM buffering, batch transmission |
| Phase 3: Web Interface | ✅ Complete | React frontend, visualization, device control |
| Phase 3-B: Enhancements | ✅ Complete | Labels, export, mode selector, config tracking, comparison |
| Phase 4: Integration & Polish | 🔄 77% | E2E testing, error handling, performance, security |
| Phase 5: Detection Algorithms | 📋 Future | Calibration, multi-sensor coordination, LED feedback |
| Phase 6: Advanced Features | 🔄 Partial | ML inference working; Bluetooth mesh, mobile app, game modes pending |

---

*Last Updated: March 4, 2026*
