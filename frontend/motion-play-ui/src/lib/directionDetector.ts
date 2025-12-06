/**
 * Direction Detection Algorithm - Version 2: Wave Envelope / Center of Mass
 * 
 * This module detects the direction of objects passing through the sensor hoop
 * by analyzing the complete "wave envelope" of each side's signal and comparing
 * their centers of mass (weighted average timestamps).
 * 
 * Algorithm Overview:
 * 1. Aggregate sensor readings by side (A vs B)
 * 2. Smooth signals to reduce noise
 * 3. Find wave boundaries (where signal crosses threshold on each side of peak)
 * 4. Calculate center of mass within wave boundaries for each side
 * 5. Compare centers of mass → earlier one determines direction
 * 
 * Previous Version: See archive/directionDetector_v1_rise_timing.ts
 * - Used derivative-based rise detection as primary method
 * - Center of mass was only used as tiebreaker
 * - Issue: Rise start times were often very close, making direction unclear
 * 
 * IMPORTANT: When porting to firmware, update DirectionDetector.cpp accordingly!
 */

import type { SensorReading } from '../services/api';

// ============================================================================
// Types
// ============================================================================

export type Direction = 'A_TO_B' | 'B_TO_A' | 'UNKNOWN';

export interface DetectorConfig {
  smoothingWindow: number;      // Moving average window size (default: 3)
  minRise: number;              // Minimum peak height above baseline (default: 10)
  maxPeakGapMs: number;         // Maximum time between paired peaks (default: 100)
  waveThresholdPct: number;     // Percentage of peak to define wave boundaries (default: 0.2 = 20%)
  // Sliding window parameters
  windowSizeMs: number;         // Size of analysis window in ms (default: 200)
  windowStepMs: number;         // Step size for sliding window (default: 50)
}

export interface DetectionEvent {
  direction: Direction;
  confidence: number;
  centerOfMassA: number;        // Center of mass timestamp for side A
  centerOfMassB: number;        // Center of mass timestamp for side B
  comGapMs: number;             // Time gap between centers of mass
  peakTimeA: number;            // Timestamp of peak on side A
  peakTimeB: number;            // Timestamp of peak on side B
  waveStartA: number;           // Wave boundary start for side A
  waveEndA: number;             // Wave boundary end for side A
  waveStartB: number;           // Wave boundary start for side B
  waveEndB: number;             // Wave boundary end for side B
  maxSignalA: number;           // Maximum signal value on side A
  maxSignalB: number;           // Maximum signal value on side B
  windowStart: number;          // Start timestamp of detection window
  windowEnd: number;            // End timestamp of detection window
}

interface WaveEnvelope {
  startTime: number;
  endTime: number;
  peakTime: number;
  peakValue: number;
  centerOfMass: number;
  valid: boolean;
}

// ============================================================================
// Default Configuration
// ============================================================================

export const DEFAULT_CONFIG: DetectorConfig = {
  smoothingWindow: 3,
  minRise: 10,
  maxPeakGapMs: 100,
  waveThresholdPct: 0.2,  // 20% of peak height defines wave boundaries
  windowSizeMs: 200,
  windowStepMs: 50,
};

// ============================================================================
// Core Algorithm Functions
// ============================================================================

/**
 * Aggregate sensor readings by side (PCB-agnostic).
 * Side 2 = Side A (A-facing sensors)
 * Side 1 = Side B (B-facing sensors)
 */
function aggregateBySide(
  readings: SensorReading[]
): { sideA: Map<number, number>; sideB: Map<number, number> } {
  const sideA = new Map<number, number>(); // Side 2 sensors
  const sideB = new Map<number, number>(); // Side 1 sensors

  for (const reading of readings) {
    const ts = reading.timestamp_offset;
    if (reading.side === 2) {
      sideA.set(ts, (sideA.get(ts) ?? 0) + reading.proximity);
    } else {
      sideB.set(ts, (sideB.get(ts) ?? 0) + reading.proximity);
    }
  }

  return { sideA, sideB };
}

/**
 * Apply simple moving average smoothing.
 */
function smoothSignal(
  signal: Map<number, number>,
  windowSize: number
): Map<number, number> {
  const timestamps = Array.from(signal.keys()).sort((a, b) => a - b);
  const smoothed = new Map<number, number>();

  for (let i = 0; i < timestamps.length; i++) {
    const startIdx = Math.max(0, i - windowSize + 1);
    const windowTs = timestamps.slice(startIdx, i + 1);
    const windowValues = windowTs.map(t => signal.get(t) ?? 0);
    const avg = windowValues.reduce((sum, v) => sum + v, 0) / windowValues.length;
    smoothed.set(timestamps[i], avg);
  }

  return smoothed;
}

/**
 * Find the wave envelope for a signal.
 * 
 * A wave envelope is defined by:
 * 1. Finding the peak (maximum value)
 * 2. Finding where the signal crosses the threshold (% of peak) on each side
 * 3. Calculating center of mass within those boundaries
 */
function findWaveEnvelope(
  signal: Map<number, number>,
  thresholdPct: number,
  minPeakHeight: number
): WaveEnvelope | null {
  if (signal.size === 0) {
    return null;
  }

  const timestamps = Array.from(signal.keys()).sort((a, b) => a - b);
  const values = timestamps.map(t => signal.get(t) ?? 0);

  // Find peak
  let peakIdx = 0;
  let peakValue = values[0];
  for (let i = 1; i < values.length; i++) {
    if (values[i] > peakValue) {
      peakValue = values[i];
      peakIdx = i;
    }
  }

  // Check if peak is significant
  const baseline = Math.min(...values);
  const peakHeight = peakValue - baseline;
  if (peakHeight < minPeakHeight) {
    return null;
  }

  // Calculate threshold
  const threshold = baseline + (peakHeight * thresholdPct);

  // Find wave start (search backwards from peak)
  let startIdx = peakIdx;
  for (let i = peakIdx; i >= 0; i--) {
    if (values[i] < threshold) {
      startIdx = i + 1;
      break;
    }
    if (i === 0) {
      startIdx = 0;
    }
  }

  // Find wave end (search forwards from peak)
  let endIdx = peakIdx;
  for (let i = peakIdx; i < values.length; i++) {
    if (values[i] < threshold) {
      endIdx = i - 1;
      break;
    }
    if (i === values.length - 1) {
      endIdx = values.length - 1;
    }
  }

  // Ensure we have a valid range
  if (startIdx > endIdx) {
    startIdx = peakIdx;
    endIdx = peakIdx;
  }

  // Calculate center of mass within wave boundaries
  let totalWeight = 0;
  let weightedSum = 0;

  for (let i = startIdx; i <= endIdx; i++) {
    const ts = timestamps[i];
    const value = values[i];
    // Weight is signal value minus baseline
    const weight = Math.max(0, value - baseline);
    weightedSum += ts * weight;
    totalWeight += weight;
  }

  if (totalWeight === 0) {
    return null;
  }

  const centerOfMass = weightedSum / totalWeight;

  return {
    startTime: timestamps[startIdx],
    endTime: timestamps[endIdx],
    peakTime: timestamps[peakIdx],
    peakValue,
    centerOfMass,
    valid: true,
  };
}

/**
 * Analyze a window of sensor readings to detect direction.
 * Uses wave envelope / center-of-mass as the primary detection method.
 */
function analyzeWindow(
  readings: SensorReading[],
  config: DetectorConfig
): DetectionEvent | null {
  if (readings.length === 0) {
    return null;
  }

  // Step 1: Aggregate by side
  const { sideA, sideB } = aggregateBySide(readings);

  if (sideA.size === 0 || sideB.size === 0) {
    return null;
  }

  const timestamps = readings.map(r => r.timestamp_offset);
  const windowStart = Math.min(...timestamps);
  const windowEnd = Math.max(...timestamps);

  // Step 2: Smooth signals
  const sideASmooth = smoothSignal(sideA, config.smoothingWindow);
  const sideBSmooth = smoothSignal(sideB, config.smoothingWindow);

  // Step 3: Find wave envelopes
  const waveA = findWaveEnvelope(sideASmooth, config.waveThresholdPct, config.minRise);
  const waveB = findWaveEnvelope(sideBSmooth, config.waveThresholdPct, config.minRise);

  // Need valid waves on both sides
  if (!waveA || !waveB) {
    return null;
  }

  // Step 4: Check if peaks are close enough (same event)
  const peakGap = Math.abs(waveA.peakTime - waveB.peakTime);
  if (peakGap > config.maxPeakGapMs) {
    return null; // Not the same event
  }

  // Step 5: Determine direction from center of mass comparison
  const comGap = Math.abs(waveA.centerOfMass - waveB.centerOfMass);
  let direction: Direction;

  if (waveA.centerOfMass < waveB.centerOfMass) {
    direction = 'A_TO_B';
  } else if (waveB.centerOfMass < waveA.centerOfMass) {
    direction = 'B_TO_A';
  } else {
    // Exact tie (unlikely) - use peak time as tiebreaker
    direction = waveA.peakTime < waveB.peakTime ? 'A_TO_B' : 'B_TO_A';
  }

  // Step 6: Calculate confidence
  // Higher gap = more confident, stronger signals = more confident
  const gapConfidence = Math.min(1.0, comGap / 30);
  const signalConfidence = Math.min(1.0, (waveA.peakValue + waveB.peakValue) / 100);
  const confidence = (gapConfidence + signalConfidence) / 2;

  return {
    direction,
    confidence,
    centerOfMassA: waveA.centerOfMass,
    centerOfMassB: waveB.centerOfMass,
    comGapMs: comGap,
    peakTimeA: waveA.peakTime,
    peakTimeB: waveB.peakTime,
    waveStartA: waveA.startTime,
    waveEndA: waveA.endTime,
    waveStartB: waveB.startTime,
    waveEndB: waveB.endTime,
    maxSignalA: waveA.peakValue,
    maxSignalB: waveB.peakValue,
    windowStart,
    windowEnd,
  };
}

// ============================================================================
// Sliding Window Detection
// ============================================================================

/**
 * Check if two events overlap significantly (likely the same event).
 */
function eventsOverlap(a: DetectionEvent, b: DetectionEvent): boolean {
  // Events overlap if their peak times are within 50ms of each other
  const peakGapA = Math.abs(a.peakTimeA - b.peakTimeA);
  const peakGapB = Math.abs(a.peakTimeB - b.peakTimeB);
  return peakGapA < 50 && peakGapB < 50;
}

/**
 * Merge overlapping events, keeping the one with highest confidence.
 */
function mergeOverlappingEvents(events: DetectionEvent[]): DetectionEvent[] {
  if (events.length === 0) return [];

  // Sort by peak time
  const sorted = [...events].sort((a, b) => a.peakTimeA - b.peakTimeA);
  const merged: DetectionEvent[] = [];

  let current = sorted[0];

  for (let i = 1; i < sorted.length; i++) {
    const next = sorted[i];
    if (eventsOverlap(current, next)) {
      // Keep the one with higher confidence
      if (next.confidence > current.confidence) {
        current = next;
      }
    } else {
      merged.push(current);
      current = next;
    }
  }

  merged.push(current);
  return merged;
}

/**
 * Detect all direction events in a session using sliding window analysis.
 * 
 * @param readings - All sensor readings from the session
 * @param config - Detection configuration
 * @returns Array of detected events, sorted by time
 */
export function detectEvents(
  readings: SensorReading[],
  config: Partial<DetectorConfig> = {}
): DetectionEvent[] {
  const cfg: DetectorConfig = { ...DEFAULT_CONFIG, ...config };

  if (readings.length === 0) {
    return [];
  }

  // Sort readings by timestamp
  const sorted = [...readings].sort((a, b) => a.timestamp_offset - b.timestamp_offset);

  // Get time range
  const minTime = sorted[0].timestamp_offset;
  const maxTime = sorted[sorted.length - 1].timestamp_offset;

  // Collect all detected events
  const allEvents: DetectionEvent[] = [];

  // Slide window across the session
  for (let windowStart = minTime; windowStart <= maxTime - cfg.windowSizeMs; windowStart += cfg.windowStepMs) {
    const windowEnd = windowStart + cfg.windowSizeMs;

    // Get readings in this window
    const windowReadings = sorted.filter(
      r => r.timestamp_offset >= windowStart && r.timestamp_offset <= windowEnd
    );

    if (windowReadings.length < 10) {
      continue; // Not enough data in window
    }

    // Analyze this window
    const event = analyzeWindow(windowReadings, cfg);
    if (event !== null) {
      allEvents.push(event);
    }
  }

  // Merge overlapping events (same event detected in adjacent windows)
  return mergeOverlappingEvents(allEvents);
}

/**
 * Format direction for display.
 */
export function formatDirection(direction: Direction): string {
  switch (direction) {
    case 'A_TO_B': return 'A → B';
    case 'B_TO_A': return 'B → A';
    default: return 'Unknown';
  }
}

/**
 * Get a human-readable summary of detection results.
 */
export function summarizeEvents(events: DetectionEvent[]): string {
  if (events.length === 0) {
    return 'No direction events detected';
  }

  const aToBCount = events.filter(e => e.direction === 'A_TO_B').length;
  const bToACount = events.filter(e => e.direction === 'B_TO_A').length;

  const parts: string[] = [];
  if (aToBCount > 0) parts.push(`${aToBCount} A→B`);
  if (bToACount > 0) parts.push(`${bToACount} B→A`);

  return `${events.length} event${events.length > 1 ? 's' : ''} detected: ${parts.join(', ')}`;
}
