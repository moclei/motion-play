# Data Collection Initiative

## Overview

The Data Collection Initiative implements a cloud-based platform for sensor data capture, labeling, and analysis. This system enables remote control of the Motion Play ESP32-S3 device and provides structured data collection capabilities for algorithm development and future AI/ML-based detection systems.

## Status

**Active** - Phase 1 implementation complete, ongoing enhancements

## Objectives

- Remote control of Motion Play device operation modes (Debug/Play)
- Collection and storage of labeled sensor data
- Analysis and visualization of sensor readings
- Foundation for future neural network training and object detection
- Multi-device support architecture

## Key Documents

### Planning & Requirements

- **[tech_reqs.md](tech_reqs.md)** - Technical requirements document defining system objectives, scope, and success criteria
- **[technical_design_doc.md](technical_design_doc.md)** - Comprehensive technical design covering architecture, components, data structures, and interfaces
- **[implementation_plan.md](implementation_plan.md)** - Phased implementation plan with timelines and dependencies

### Implementation Guides

All implementation guides are located in the `guides/` subfolder:

- **[phase1-connectivity-guide.md](guides/phase1-connectivity-guide.md)** - Device-to-cloud connectivity setup
- **[phase2-data-pipeline-guide.md](guides/phase2-data-pipeline-guide.md)** - Data collection pipeline implementation
- **[phase3-web-interface-guide.md](guides/phase3-web-interface-guide.md)** - Web frontend development
- **[phase3-b-enhancements-guide.md](guides/phase3-b-enhancements-guide.md)** - System enhancements and refinements
- **[IMPLEMENTATION_GUIDE.md](guides/IMPLEMENTATION_GUIDE.md)** - General implementation guidance

### Status & Progress

- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current implementation status and completed features
- **[REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md)** - Summary of project reorganization efforts

## Architecture Overview

### Components

**Firmware (ESP32-S3)**
- Sensor data collection from VCNL4040 proximity sensors
- MQTT communication with AWS IoT Core
- Operation mode management (Debug/Play)
- Display management on T-Display S3

**Cloud Infrastructure (AWS)**
- IoT Core for device connectivity
- Lambda functions for data processing and API endpoints
- DynamoDB for data storage
- API Gateway for web interface communication

**Frontend (React + TypeScript)**
- Session management and control
- Real-time data visualization
- Device configuration
- Data export and analysis tools

## Getting Started

1. Review the [tech_reqs.md](tech_reqs.md) to understand system objectives
2. Study the [technical_design_doc.md](technical_design_doc.md) for architecture details
3. Follow the implementation guides in sequence (phase1 → phase2 → phase3)
4. Check [PROJECT_STATUS.md](PROJECT_STATUS.md) for current state

## Related Documentation

- **Firmware**: See [/firmware/README.md](../../../firmware/README.md)
- **Frontend**: See [/frontend/motion-play-ui/README.md](../../../frontend/motion-play-ui/README.md)
- **Lambda Functions**: See [/lambda/README.md](../../../lambda/README.md)
- **Infrastructure**: See [/infrastructure/README.md](../../../infrastructure/README.md)

## Working Documents

Ephemeral working documents (bug investigations, testing notes, etc.) should be placed in the `work/` subfolder and deleted when no longer needed.

---

*Last Updated: November 21, 2025*

