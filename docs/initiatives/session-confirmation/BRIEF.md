# Session Confirmation

**Status**: In Progress (Feb 2026)

## Intent

Add pipeline integrity verification so that when viewing a session on the frontend, we can confirm that all sensor readings were collected by the firmware, transmitted via MQTT, stored by the Lambda, and displayed in the UI. Currently there are no counters or metadata tracking this, so there is no way to know if readings were lost at any stage. This feature also adds a clear time-in-seconds display so the actual duration of the captured data is immediately visible.

## Goals

- Know exactly how many readings the firmware collected from each sensor during a session, and how many were lost (I2C errors, queue drops, buffer overflow).
- Track readings through every pipeline stage (firmware -> MQTT -> Lambda -> DynamoDB -> frontend) and detect discrepancies.
- Display the session time window in seconds prominently on the frontend visualization.
- Show a theoretical expected reading count (from config settings) alongside the actual measured count, so config-vs-reality gaps are visible.
- Populate the existing but unused `actual_sample_rate_hz` field with a real measured value.

## Scope

**What's in:**
- Firmware-side `SessionSummary` with per-sensor counters (collected, I2C errors, queue drops, buffer drops, transmitted)
- Separate "session complete" MQTT message sent after all data batches, carrying the summary
- Lambda handling of the summary message: storage, batch counting, pipeline status computation
- Frontend: Session Confirmation panel (pipeline chain, per-sensor breakdown, theoretical vs actual)
- Frontend: time-in-seconds display on the chart and stats panel
- Applies to both Debug and Live Debug proximity sessions

**What's out:**
- Interrupt mode sessions (polling/proximity only for now)
- Checksum/hash verification of data content (deferred; counts are sufficient for v1)
- Firmware-to-cloud retry of failed data batches (only the summary message gets retries)
- Automated alerting or notifications on pipeline failures

## Constraints

- Uses existing MQTT data topic and `processData` Lambda — no new infrastructure.
- Must not break existing Debug, Live Debug, or Play mode behavior.
- DynamoDB is schemaless for optional attributes — no migration needed.
- Summary message failure degrades gracefully (session data is still stored, just without firmware-side verification metadata).
