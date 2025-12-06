/**
 * Direction Detection Algorithm - Version 1: Rise Timing Based
 * 
 * ARCHIVED: 2024-12-06
 * REASON: Replaced with center-of-mass (wave envelope) approach for better accuracy
 * 
 * This version detected direction by:
 * 1. Finding when each side's signal started rising (derivative threshold)
 * 2. Using rise start times as primary direction indicator
 * 3. Center-of-mass as tiebreaker only
 * 
 * Issues with this approach:
 * - Rise start detection is sensitive to noise at beginning of signal
 * - Didn't capture the "whole wave" timing that humans perceive visually
 * - Rise times were often very close together, making direction unclear
 * 
 * Ported from: scripts/direction_detection/attempt1.py
 * Mirrors firmware: firmware/src/components/detection/DirectionDetector.cpp
 */

import type { SensorReading } from '../../services/api';

// ============================================================================
// Types
// ============================================================================

export type Direction = 'A_TO_B' | 'B_TO_A' | 'UNKNOWN';

export interface DetectorConfig {
    smoothingWindow: number;      // Moving average window size (default: 3)
    minRise: number;              // Minimum signal increase to consider a peak (default: 10)
    maxPeakGapMs: number;         // Maximum time between paired peaks (default: 100)
    derivativeThreshold: number;  // Minimum derivative to count as "rising" (default: 2.0)
    // Sliding window parameters
    windowSizeMs: number;         // Size of analysis window in ms (default: 200)
    windowStepMs: number;         // Step size for sliding window (default: 50)
}

export interface DetectionEvent {
    direction: Direction;
    confidence: number;
    riseTimeA: number;            // Timestamp when side A started rising
    riseTimeB: number;            // Timestamp when side B started rising
    gapMs: number;                // Time gap between rise starts
    peakTimeA: number;            // Timestamp of peak on side A
    peakTimeB: number;            // Timestamp of peak on side B
    maxSignalA: number;           // Maximum signal value on side A
    maxSignalB: number;           // Maximum signal value on side B
    windowStart: number;          // Start timestamp of detection window
    windowEnd: number;            // End timestamp of detection window
}

interface RiseInfo {
    startTime: number;
    peakTime: number;
    riseAmount: number;
    valid: boolean;
}

// ============================================================================
// Default Configuration
// ============================================================================

export const DEFAULT_CONFIG: DetectorConfig = {
    smoothingWindow: 3,
    minRise: 10,
    maxPeakGapMs: 100,
    derivativeThreshold: 2.0,
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
 * Compute first derivative (rate of change).
 */
function computeDerivative(signal: Map<number, number>): Map<number, number> {
    const timestamps = Array.from(signal.keys()).sort((a, b) => a - b);
    const derivative = new Map<number, number>();

    for (let i = 1; i < timestamps.length; i++) {
        const prevTs = timestamps[i - 1];
        const currTs = timestamps[i];
        const prevVal = signal.get(prevTs) ?? 0;
        const currVal = signal.get(currTs) ?? 0;
        derivative.set(currTs, currVal - prevVal);
    }

    return derivative;
}

/**
 * Find when significant rises BEGIN (not when they peak).
 * Returns array of (riseStartTime, peakTime, riseAmount) tuples.
 */
function findRiseStartTimes(
    signal: Map<number, number>,
    derivative: Map<number, number>,
    minRise: number,
    derivativeThreshold: number
): RiseInfo[] {
    const timestamps = Array.from(derivative.keys()).sort((a, b) => a - b);
    const rises: RiseInfo[] = [];

    let riseStartTs: number | null = null;
    let riseStartValue = 0;
    let consecutivePositive = 0;

    for (let i = 1; i < timestamps.length; i++) {
        const prevTs = timestamps[i - 1];
        const currTs = timestamps[i];
        const prevD = derivative.get(prevTs) ?? 0;
        const currD = derivative.get(currTs) ?? 0;

        // Count consecutive positive derivatives (sustained rise)
        if (currD > derivativeThreshold) {
            consecutivePositive++;
            if (consecutivePositive >= 2 && riseStartTs === null) {
                // This is the start of a significant rise
                const startIdx = Math.max(0, i - consecutivePositive);
                riseStartTs = timestamps[startIdx] ?? currTs;
                riseStartValue = signal.get(riseStartTs) ?? 0;
            }
        } else {
            consecutivePositive = 0;
        }

        // Detect peak (end of rise)
        if (prevD > 0 && currD <= 0 && riseStartTs !== null) {
            const peakValue = signal.get(prevTs) ?? 0;
            const riseAmount = peakValue - riseStartValue;
            if (riseAmount >= minRise) {
                rises.push({
                    startTime: riseStartTs,
                    peakTime: prevTs,
                    riseAmount,
                    valid: true,
                });
            }
            riseStartTs = null;
        }
    }

    return rises;
}

/**
 * Calculate the weighted average timestamp (center of mass) of the signal.
 * Only considers values above minValue to filter baseline noise.
 */
function calculateCenterOfMass(
    signal: Map<number, number>,
    minValue: number
): number | null {
    let totalWeight = 0;
    let weightedSum = 0;

    for (const [ts, value] of signal.entries()) {
        if (value > minValue) {
            const weight = value - minValue;
            weightedSum += ts * weight;
            totalWeight += weight;
        }
    }

    if (totalWeight < 10) {
        return null; // Not enough activity
    }

    return weightedSum / totalWeight;
}

/**
 * Analyze a window of sensor readings to detect direction.
 * Uses the hybrid algorithm: derivative-based rise detection + center-of-mass.
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

    // Find max values
    const sideAMax = Math.max(...sideA.values());
    const sideBMax = Math.max(...sideB.values());

    // Step 2: Smooth signals
    const sideASmooth = smoothSignal(sideA, config.smoothingWindow);
    const sideBSmooth = smoothSignal(sideB, config.smoothingWindow);

    // Step 3: Compute derivatives
    const dA = computeDerivative(sideASmooth);
    const dB = computeDerivative(sideBSmooth);

    if (dA.size === 0 || dB.size === 0) {
        return null;
    }

    // Step 4: Find rise start times
    const risesA = findRiseStartTimes(sideASmooth, dA, config.minRise, config.derivativeThreshold);
    const risesB = findRiseStartTimes(sideBSmooth, dB, config.minRise, config.derivativeThreshold);

    // If no significant rises on both sides, no event
    if (risesA.length === 0 || risesB.length === 0) {
        return null;
    }

    // Find main rises (largest rise amount on each side)
    const mainRiseA = risesA.reduce((best, r) => r.riseAmount > best.riseAmount ? r : best);
    const mainRiseB = risesB.reduce((best, r) => r.riseAmount > best.riseAmount ? r : best);

    // Check if peaks are close enough (same event)
    const peakGap = Math.abs(mainRiseA.peakTime - mainRiseB.peakTime);
    if (peakGap > config.maxPeakGapMs) {
        return null; // Not the same event
    }

    // Step 5: Event confirmed! Use center-of-mass for direction
    const comA = calculateCenterOfMass(sideA, config.minRise / 2);
    const comB = calculateCenterOfMass(sideB, config.minRise / 2);

    let direction: Direction;
    let comGap: number;

    if (comA === null || comB === null) {
        // Fallback to rise start timing
        if (mainRiseA.startTime < mainRiseB.startTime) {
            direction = 'A_TO_B';
        } else if (mainRiseB.startTime < mainRiseA.startTime) {
            direction = 'B_TO_A';
        } else {
            // Tie - use peak timing
            direction = mainRiseA.peakTime < mainRiseB.peakTime ? 'A_TO_B' : 'B_TO_A';
        }
        comGap = Math.abs(mainRiseA.startTime - mainRiseB.startTime);
    } else {
        comGap = Math.abs(comA - comB);
        direction = comA < comB ? 'A_TO_B' : 'B_TO_A';
    }

    // Calculate confidence
    const gapConfidence = Math.min(1.0, comGap / 30);
    const signalConfidence = Math.min(1.0, (sideAMax + sideBMax) / 100);
    const confidence = (gapConfidence + signalConfidence) / 2;

    return {
        direction,
        confidence,
        riseTimeA: mainRiseA.startTime,
        riseTimeB: mainRiseB.startTime,
        gapMs: Math.abs(mainRiseA.startTime - mainRiseB.startTime),
        peakTimeA: mainRiseA.peakTime,
        peakTimeB: mainRiseB.peakTime,
        maxSignalA: sideAMax,
        maxSignalB: sideBMax,
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

