# Live Debug

## Intent

A hybrid mode that combines Play's live detection and LED feedback with selective data capture. When the device detects a trigger, it pauses detection, syncs that detection plus a short sample window to the cloud, and resumes. A "missed event" button captures data leading up to the button press when a throw wasn't detected. The goal is to build a curated, labeled dataset for refining the heuristic algorithm and — later — training ML models on clean, labeled event windows, without the overhead of full-session recording. This feature directly supports the project's three detection approaches: heuristic tuning benefits from labeled good/bad examples, and the ML approach requires exactly the kind of short, labeled windows this mode produces.

## Goals

- **Capture good detections easily**: Every live detection automatically uploads a small window of sensor data with the detection result.
- **Capture bad detections for analysis**: False positives and wrong-direction detections are visible in the frontend and can be labeled.
- **Capture missed events**: A button press saves a time window (e.g. 3 seconds) before the press when the user threw something that wasn't detected.
- **Labeled dataset**: All captured windows have or can receive labels (correct, false positive, wrong direction, missed), suitable for heuristic tuning and future ML.
- **Live feedback preserved**: LEDs and display behave like Play mode; no UX regression.

## Scope

**What's in:**
- New "Live Debug" mode selectable from frontend
- Detection-triggered capture: on each detection, transmit a configurable window of sample data around the event
- "Missed event" button (frontend-initiated) that sends a command to save a configurable time window of data before the button press
- Frontend: detection feed / event list, ability to view and label each captured window
- Stored as sessions in existing schema with `mode: "live_debug"`
- Pause detection during transmission with visual feedback on T-Display

**What's out:**
- Full-session recording in Live Debug mode (we only save event windows)
- Device hardware button for missed events in initial implementation (can add later)
- Support for interrupt-based sensing in Live Debug (polling/proximity only initially)
- Frontend settings for capture windows (future improvement; design should not preclude it)

## Constraints

- Uses existing data path: MQTT → processData Lambda → DynamoDB. No new tables; `mode` is a free-form string.
- Must not break Play or Debug modes.
- Dataset format should remain compatible with future ML training (short windows + labels).
- Capture window durations should be easy to make configurable later (store as constants initially).
