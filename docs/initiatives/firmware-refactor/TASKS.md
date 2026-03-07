# Firmware Architecture Audit — Tasks

- [x] **Batch 1: The Orchestrator** — `main.cpp` (1,845 lines). Understand how all components connect, where responsibilities are tangled, what can be extracted.
- [x] **Batch 2: Sensor Pipeline** — `SensorManager` (1,429+142), `MuxController` (325+199), `VCNL4040` (423+539, skim), `SensorConfiguration` (49). The core sensor reading chain.
- [x] **Batch 3: Detection & ML** — `DirectionDetector` (451+252), `MLDetector` (578+191), `CalibrationManager` (725+275), `CalibrationData` (207). Signal processing layer.
- [x] **Batch 4: Session & Data** — `SessionManager` (302+132), `DataTransmitter` (769+85), `PSRAMAllocator` (98). Data management chain.
- [x] **Batch 5: I/O & Peripherals** — `DisplayManager` (874+130), `InterruptManager` (795+357), `LEDController` (161+90), `SerialStudioOutput` (198+87). Output and interrupt handling.
- [x] **Batch 6: Networking & Infrastructure** — `MQTTManager` (300+45), `NetworkManager` (122+29), `MemoryMonitor` (144), `pin_config` (44). Connectivity, utilities, and cross-cutting review (header hygiene, include structure, shared types).
- [x] **Synthesis** — Consolidated findings into REPORT.md with prioritized recommendations and follow-on initiative proposal.
