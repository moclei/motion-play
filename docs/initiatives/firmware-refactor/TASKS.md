# Firmware Architecture Refactor — Tasks

## Phase A: Audit

Analyze the firmware in batches, documenting findings in PLAN.md. Each batch is one chat session.

- [x] **Batch 1: The Orchestrator** — `main.cpp` (1,845 lines). Understand how all components connect, where responsibilities are tangled, what can be extracted.
- [ ] **Batch 2: Sensor Pipeline** — `SensorManager` (1,429+142), `MuxController` (325+199), `VCNL4040` (423+539, skim), `SensorConfiguration` (49). The core sensor reading chain.
- [ ] **Batch 3: Detection & ML** — `DirectionDetector` (451+252), `MLDetector` (578+191), `CalibrationManager` (725+275), `CalibrationData` (207). Signal processing layer.
- [ ] **Batch 4: Session & Data** — `SessionManager` (302+132), `DataTransmitter` (769+85), `PSRAMAllocator` (98). Data management chain.
- [ ] **Batch 5: I/O & Peripherals** — `DisplayManager` (874+130), `InterruptManager` (795+357), `LEDController` (161+90), `SerialStudioOutput` (198+87). Output and interrupt handling.
- [ ] **Batch 6: Networking & Infrastructure** — `MQTTManager` (300+45), `NetworkManager` (122+29), `MemoryMonitor` (144), `pin_config` (44). Connectivity, utilities, and cross-cutting review (header hygiene, include structure, shared types).
- [ ] **Synthesis** — Consolidate findings into a prioritized refactoring plan. Populate Phase B tasks.

## Phase B: Refactor

Tasks will be populated after Phase A audit is complete. Each task will be a specific, incremental refactoring step that can be compiled and tested independently.
