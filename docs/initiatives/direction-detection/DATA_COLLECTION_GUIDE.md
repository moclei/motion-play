# Data Collection Guide for Direction Detection

## Overview

This guide outlines the systematic data collection process needed to train and validate the direction detection system. Good data is the foundation of any successful detection algorithm.

## Session Labeling Convention

### Label Format

Use this naming convention for session labels:

```
{direction}_{speed}_{trajectory}_{notes}
```

**Examples**:
- `a_to_b_medium_center` - Front to back, medium speed, center trajectory
- `b_to_a_fast_edge` - Back to front, fast, near edge
- `no_event_baseline` - No object, ambient recording
- `false_positive_hand` - Hand waved near sensors

### Direction Labels

| Label | Meaning | Description |
|-------|---------|-------------|
| `a_to_b` | Side A → Side B | Object enters from "front" (Side A), exits "back" (Side B) |
| `b_to_a` | Side B → Side A | Object enters from "back" (Side B), exits "front" (Side A) |
| `no_event` | No detection | Baseline with no object passing |
| `false_positive` | Should not trigger | Event that looks like detection but isn't |

### Speed Labels

| Label | Speed | Description |
|-------|-------|-------------|
| `slow` | ~5 mph | Gentle roll or toss |
| `medium` | ~15 mph | Normal throw |
| `fast` | ~30 mph | Hard throw or kick |
| `very_fast` | ~50 mph | Maximum speed test |

### Trajectory Labels

| Label | Description |
|-------|-------------|
| `center` | Object passes through center of hoop |
| `offset` | Object passes off-center but within hoop |
| `edge` | Object passes near edge of hoop |
| `miss` | Object passes outside hoop (for false positive testing) |

---

## Required Data Collection Sessions

### Minimum Viable Dataset (MVP)

For Phase 1 heuristic validation:

| Category | Count | Priority |
|----------|-------|----------|
| `a_to_b` passes | 20 | **High** |
| `b_to_a` passes | 20 | **High** |
| `no_event` baseline | 5 | **High** |
| `false_positive` scenarios | 10 | Medium |

**Total: ~55 sessions**

### Complete Dataset (for ML)

For training a machine learning model:

| Category | Count | Notes |
|----------|-------|-------|
| `a_to_b` passes | 100+ | Varied speeds/trajectories |
| `b_to_a` passes | 100+ | Varied speeds/trajectories |
| `no_event` baseline | 30 | Different ambient conditions |
| `false_positive` scenarios | 50 | Various types |

**Total: ~280+ sessions**

---

## Collection Protocol

### Setup Checklist

Before collecting data:

- [ ] Hoop mounted stably (no vibration)
- [ ] Sensors positioned correctly (facing inward)
- [ ] Device connected to WiFi
- [ ] Web UI accessible
- [ ] Test ball(s) ready
- [ ] Video camera ready (optional, for ground truth)

### Per-Session Procedure

1. **Prepare**
   - Note the planned action (direction, speed, trajectory)
   - Position yourself on correct side

2. **Start Session**
   - Click "Start Collection" in web UI
   - Wait 1 second for baseline

3. **Perform Action**
   - Execute the planned pass
   - For multiple passes: wait 2 seconds between each

4. **Stop Session**
   - Click "Stop Collection" in web UI
   - Wait for data upload confirmation

5. **Label Session**
   - Add label following naming convention
   - Add notes if anything unusual occurred
   - Mark quality (good/fair/poor)

6. **Verify**
   - Check session appears in list
   - Quick visual check of data (optional)

---

## Data Quality Guidelines

### Good Session Characteristics

✅ **Clear signal peak** during object passage  
✅ **Clean baseline** before and after  
✅ **Consistent timing** (not interrupted)  
✅ **Single event** per session (initially)  
✅ **Accurate label** matching actual action

### Poor Session Indicators

❌ **Multiple unintended triggers**  
❌ **Hand visible in sensor field**  
❌ **Device bumped during session**  
❌ **WiFi dropout during upload**  
❌ **Inconsistent with label**

Mark poor sessions for exclusion or relabeling.

---

## Variation Matrix

### Speed × Direction (Minimum Coverage)

| | Slow | Medium | Fast |
|---|:---:|:---:|:---:|
| **A→B** | 5 | 10 | 5 |
| **B→A** | 5 | 10 | 5 |

### Trajectory × Direction (Extended Coverage)

| | Center | Offset | Edge |
|---|:---:|:---:|:---:|
| **A→B** | 15 | 10 | 5 |
| **B→A** | 15 | 10 | 5 |

### False Positive Scenarios

| Scenario | Count | Notes |
|----------|-------|-------|
| Hand wave (single) | 5 | Quick wave past sensors |
| Hand wave (lingering) | 5 | Slow movement near sensors |
| Shadow/light change | 5 | Walk past, lights on/off |
| Object held (no pass) | 5 | Ball held near sensor, not passing |
| Near miss (outside hoop) | 5 | Ball passes just outside hoop |
| Vibration/bump | 5 | Tap the hoop structure |

---

## Batch Collection Strategy

### Sprint 1: Core Passes (Day 1)

**Goal**: 40 labeled passes

| Time | Sessions | Description |
|------|----------|-------------|
| 0:00-0:30 | 10 | A→B medium center |
| 0:30-1:00 | 10 | B→A medium center |
| 1:00-1:30 | 10 | A→B slow/fast mix |
| 1:30-2:00 | 10 | B→A slow/fast mix |

### Sprint 2: Variations (Day 2)

**Goal**: 30 varied passes + false positives

| Time | Sessions | Description |
|------|----------|-------------|
| 0:00-0:30 | 10 | Off-center passes |
| 0:30-1:00 | 10 | Edge passes |
| 1:00-1:30 | 10 | False positive scenarios |

### Sprint 3: Edge Cases (Day 3)

**Goal**: Stress testing

- Very fast passes
- Very slow passes
- Consecutive rapid passes
- Different ball sizes
- Different lighting conditions

---

## Data Export for Analysis

### From Web UI

1. Navigate to Session List
2. Select sessions to export
3. Click "Export CSV"
4. Download combined or individual files

### CSV Format

```csv
timestamp_offset,pcb_id,side,proximity,ambient,session_id,device_id,start_timestamp
-20,1,1,0,0,device-001_58233009,motionplay-device-001,58233031
-20,1,2,1,0,device-001_58233009,motionplay-device-001,58233031
...
```

### Metadata to Track

For each session, record in notes or separate spreadsheet:

| Field | Example | Purpose |
|-------|---------|---------|
| session_id | device-001_58233009 | Unique identifier |
| label | a_to_b_medium_center | Classification target |
| quality | good/fair/poor | Data quality filter |
| speed_estimate | 15 mph | Ground truth |
| ball_size | 4 inch | Object characteristics |
| notes | "slightly off-center" | Additional context |

---

## Tools and Automation

### Video Correlation (Optional)

For ground truth verification:

1. Start phone video recording
2. Verbally announce session ID and planned action
3. Perform action in view of camera
4. Stop session and video together
5. Use video to verify labels

### Batch Labeling Script (Future)

Could create a script to:
- Parse session timestamps
- Correlate with video timestamps
- Auto-suggest labels
- Flag ambiguous cases

---

## Common Pitfalls

### 1. Inconsistent Speed
**Problem**: "Medium" varies between throws  
**Solution**: Use consistent technique, or measure with video

### 2. Label Errors
**Problem**: Wrong direction labeled  
**Solution**: Always face the same way, use clear markers for A/B

### 3. Baseline Contamination
**Problem**: Movement during "baseline" start  
**Solution**: Stand clear for 1 second after starting session

### 4. Too Few Variations
**Problem**: Model overfits to specific scenario  
**Solution**: Follow variation matrix systematically

### 5. Imbalanced Classes
**Problem**: 100 A→B but only 20 B→A  
**Solution**: Collect equal numbers per direction

---

## Checklist Summary

### Before Starting Collection Sprint

- [ ] Device powered and connected
- [ ] Web UI accessible
- [ ] Session list empty or at known state
- [ ] Collection protocol printed/visible
- [ ] Timer/stopwatch ready
- [ ] Ball(s) and props ready
- [ ] A/B sides clearly marked

### After Each Sprint

- [ ] All sessions appear in web UI
- [ ] Labels applied to all sessions
- [ ] Export backup copy
- [ ] Note any issues or anomalies
- [ ] Review sample session data

### Before Algorithm Development

- [ ] Minimum 50 labeled sessions collected
- [ ] At least 20 per direction
- [ ] False positive scenarios included
- [ ] Data exported and backed up
- [ ] Session quality reviewed

---

*Last Updated: November 27, 2024*

