# Documentation Index

This document serves as a master index for all documentation in the Motion Play project.

## Quick Navigation

- **Documentation Guide**: See [DOCUMENTATION.md](../DOCUMENTATION.md) for how documentation is organized
- **Project Overview**: See [README.md](../README.md) at the project root
- **Getting Started**: See [QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md)
- **AI Context**: See [.context/PROJECT.md](../.context/PROJECT.md) for comprehensive project context

## Active Initiatives

Below is a list of current and past initiatives. Each initiative folder contains its own README with detailed information and links to relevant documents.

### Data Collection
**Location**: `docs/initiatives/data-collection/`  
**Status**: Active (77% Complete)  
**Description**: Cloud-based platform for sensor data capture, labeling, and analysis. Enables remote control of ESP32-S3 device operation modes, collection and storage of labeled sensor data for algorithm development, and visualization of sensor readings. Foundation for future AI/ML-based detection systems.

**Key Documents**:
- Technical Requirements
- Technical Design Document
- Implementation Plan
- Phase-specific Implementation Guides

### Object Detection
**Location**: `docs/initiatives/object-detection/`  
**Status**: Active (Planning Phase)  
**Description**: Optimize detection of spherical objects (balls) passing through circular detection plane (hula hoop) using VCNL4040 proximity sensors. Focus on achieving adequate sample rate (200+ Hz), detection range (5-7 inches), and reliable direction determination (>90% accuracy) for varying object sizes (3-6") and velocities (5-30 mph).

**Key Documents**:
- [Problem Statement](./initiatives/object-detection/PROBLEM_STATEMENT.md) - Requirements, constraints, and success criteria
- [Calculations](./initiatives/object-detection/CALCULATIONS.md) - Mathematical analysis and formulas
- [README](./initiatives/object-detection/README.md) - Quick start and current status

**Current Focus**: Sample rate optimization (24 Hz → 200 Hz)

---

## Reference Materials

Hardware component datasheets, vendor documentation, and example code are organized in:
- **Location**: `docs/references/`
- **Organization**: By component name (e.g., `vcnl4040/`, `pca9546a/`, `i2c-multiplexer/`)

---

## Archive

Historical and stale documentation that may still be useful for context is stored in:
- **Location**: `docs/archive/`

---

## Sub-Project Documentation

Each major sub-project has its own README:
- **Firmware**: `firmware/README.md` - ESP32-S3 firmware architecture and components
- **Frontend**: `frontend/motion-play-ui/README.md` - React web interface
- **Infrastructure**: `infrastructure/README.md` - AWS infrastructure setup and deployment
- **Lambda**: `lambda/README.md` - AWS Lambda functions
- **Hardware**: `hardware/` - KiCad PCB designs and schematics

---

## Documentation Guidelines

### Where to Create New Documents

| Document Type | Location | Lifecycle |
|--------------|----------|-----------|
| New cross-cutting initiative | `docs/initiatives/[initiative-name]/` | Create new folder |
| Technical requirements/design | `docs/initiatives/[initiative-name]/` | Permanent |
| Implementation guides | `docs/initiatives/[initiative-name]/guides/` | Permanent |
| Working/ephemeral docs | `docs/initiatives/[initiative-name]/work/` | Delete when complete |
| Hardware reference material | `docs/references/[component-name]/` | Permanent |
| Sub-project specific | `[sub-project]/` | Per sub-project decision |
| Uncertain/stale docs | `docs/archive/` | Review periodically |

### Maintaining This Index

When creating a new initiative:
1. Create the folder structure in `docs/initiatives/[initiative-name]/`
2. Add a README.md to the initiative folder
3. Update this INDEX.md with a new entry in the "Active Initiatives" section
4. Include a brief description and list key documents

---

*Last Updated: November 21, 2025*

