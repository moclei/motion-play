#!/usr/bin/env python3
"""
Direction Detection - Attempt 1: Derivative-Based Peak Detection

This script implements and validates the algorithm described in:
docs/initiatives/direction-detection/attempt1/IMPLEMENTATION.md

Usage:
    python scripts/direction_detection/attempt1.py
"""

import os
import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Direction(Enum):
    UNKNOWN = "unknown"
    A_TO_B = "a_to_b"
    B_TO_A = "b_to_a"


@dataclass
class SensorReading:
    timestamp: int
    pcb_id: int
    side: int
    proximity: int


@dataclass
class DetectionResult:
    direction: Direction
    confidence: float
    peak_time_a: Optional[int]
    peak_time_b: Optional[int]
    peak_gap_ms: Optional[int]
    side_a_max: int
    side_b_max: int


@dataclass
class Config:
    """Tunable parameters for the algorithm."""
    smoothing_window: int = 3      # Moving average window size
    min_rise: int = 10             # Minimum signal increase to consider a peak
    max_peak_gap_ms: int = 100     # Maximum time between paired peaks (ms)


def load_csv(filepath: Path) -> list[SensorReading]:
    """Load sensor readings from a CSV file."""
    readings = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            readings.append(SensorReading(
                timestamp=int(row['timestamp_offset']),
                pcb_id=int(row['pcb_id']),
                side=int(row['side']),
                proximity=int(row['proximity'])
            ))
    return readings


def aggregate_by_side(readings: list[SensorReading]) -> tuple[dict[int, int], dict[int, int]]:
    """
    Aggregate sensor readings by side (PCB-agnostic).
    
    Returns:
        side_a: {timestamp: sum of all side 2 sensors}
        side_b: {timestamp: sum of all side 1 sensors}
    """
    side_a = {}  # Side 2 sensors (A-facing)
    side_b = {}  # Side 1 sensors (B-facing)
    
    for reading in readings:
        ts = reading.timestamp
        if reading.side == 2:
            side_a[ts] = side_a.get(ts, 0) + reading.proximity
        else:  # side == 1
            side_b[ts] = side_b.get(ts, 0) + reading.proximity
    
    return side_a, side_b


def smooth_signal(signal: dict[int, int], window: int) -> dict[int, float]:
    """Apply simple moving average smoothing."""
    timestamps = sorted(signal.keys())
    smoothed = {}
    
    for i, ts in enumerate(timestamps):
        start_idx = max(0, i - window + 1)
        window_ts = timestamps[start_idx:i + 1]
        window_values = [signal[t] for t in window_ts]
        smoothed[ts] = sum(window_values) / len(window_values)
    
    return smoothed


def compute_derivative(signal: dict[int, float]) -> dict[int, float]:
    """Compute first derivative (rate of change)."""
    timestamps = sorted(signal.keys())
    derivative = {}
    
    for i in range(1, len(timestamps)):
        prev_ts = timestamps[i - 1]
        curr_ts = timestamps[i]
        derivative[curr_ts] = signal[curr_ts] - signal[prev_ts]
    
    return derivative


def find_peaks(signal: dict[int, float], derivative: dict[int, float], min_rise: int) -> list[int]:
    """
    Find peaks where derivative crosses from positive to negative.
    Only count peaks with sufficient rise from the preceding trough.
    """
    timestamps = sorted(derivative.keys())
    peaks = []
    
    # Track the start of current rise
    rise_start_value = signal[min(signal.keys())]
    in_rise = False
    
    for i in range(1, len(timestamps)):
        prev_ts = timestamps[i - 1]
        curr_ts = timestamps[i]
        prev_d = derivative[prev_ts]
        curr_d = derivative[curr_ts]
        
        # Detect start of rise
        if curr_d > 0 and prev_d <= 0:
            rise_start_value = signal.get(prev_ts, 0)
            in_rise = True
        
        # Detect peak (end of rise)
        if prev_d > 0 and curr_d <= 0 and in_rise:
            rise_amount = signal.get(prev_ts, 0) - rise_start_value
            if rise_amount >= min_rise:
                peaks.append(prev_ts)  # Peak is at the previous timestamp
            in_rise = False
    
    return peaks


def find_rise_start_times(
    signal: dict[int, float], 
    derivative: dict[int, float], 
    min_rise: int,
    derivative_threshold: float = 2.0
) -> list[tuple[int, int, float]]:
    """
    Find when significant rises BEGIN (not when they peak).
    
    Returns list of (rise_start_time, peak_time, rise_amount) tuples.
    """
    timestamps = sorted(derivative.keys())
    rises = []
    
    rise_start_ts = None
    rise_start_value = 0
    consecutive_positive = 0
    
    for i in range(1, len(timestamps)):
        prev_ts = timestamps[i - 1]
        curr_ts = timestamps[i]
        prev_d = derivative.get(prev_ts, 0)
        curr_d = derivative.get(curr_ts, 0)
        
        # Count consecutive positive derivatives (sustained rise)
        if curr_d > derivative_threshold:
            consecutive_positive += 1
            if consecutive_positive >= 2 and rise_start_ts is None:
                # This is the start of a significant rise
                rise_start_ts = timestamps[i - consecutive_positive]
                rise_start_value = signal.get(rise_start_ts, 0)
        else:
            consecutive_positive = 0
        
        # Detect peak (end of rise)
        if prev_d > 0 and curr_d <= 0 and rise_start_ts is not None:
            peak_value = signal.get(prev_ts, 0)
            rise_amount = peak_value - rise_start_value
            if rise_amount >= min_rise:
                rises.append((rise_start_ts, prev_ts, rise_amount))
            rise_start_ts = None
    
    return rises


def calculate_center_of_mass(signal: dict[int, float], min_value: float = 5.0) -> Optional[float]:
    """
    Calculate the weighted average timestamp (center of mass) of the signal.
    Only considers values above min_value to filter baseline noise.
    
    Returns the "center of mass" timestamp, or None if no significant activity.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    
    for ts, value in signal.items():
        if value > min_value:
            weight = value - min_value  # Weight is the excess above baseline
            weighted_sum += ts * weight
            total_weight += weight
    
    if total_weight < 10:  # Not enough activity
        return None
    
    return weighted_sum / total_weight


def find_paired_peaks(
    peaks_a: list[int], 
    peaks_b: list[int], 
    max_gap_ms: int
) -> Optional[tuple[int, int]]:
    """
    Find the best paired peaks (one from each side within max_gap_ms).
    Returns (peak_a_time, peak_b_time) or None if no valid pair.
    """
    best_pair = None
    min_gap = float('inf')
    
    for pa in peaks_a:
        for pb in peaks_b:
            gap = abs(pa - pb)
            if gap <= max_gap_ms and gap < min_gap:
                min_gap = gap
                best_pair = (pa, pb)
    
    return best_pair


def analyze_window_hybrid(readings: list[SensorReading], config: Config) -> DetectionResult:
    """
    Hybrid algorithm:
    1. Use derivative-based rise detection to confirm an event occurred
    2. Use center-of-mass to determine direction (more robust)
    """
    if not readings:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=0,
            side_b_max=0
        )
    
    # Aggregate by side
    side_a, side_b = aggregate_by_side(readings)
    
    if not side_a or not side_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=0,
            side_b_max=0
        )
    
    side_a_max = max(side_a.values())
    side_b_max = max(side_b.values())
    
    # Step 1: Check if there's a real event using derivative/peak detection
    side_a_smooth = smooth_signal(side_a, config.smoothing_window)
    side_b_smooth = smooth_signal(side_b, config.smoothing_window)
    d_a = compute_derivative(side_a_smooth)
    d_b = compute_derivative(side_b_smooth)
    
    if not d_a or not d_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    rises_a = find_rise_start_times(side_a_smooth, d_a, config.min_rise)
    rises_b = find_rise_start_times(side_b_smooth, d_b, config.min_rise)
    
    # If no significant rises on both sides, no event
    if not rises_a or not rises_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    # Find main rises
    main_rise_a = max(rises_a, key=lambda x: x[2])
    main_rise_b = max(rises_b, key=lambda x: x[2])
    _, peak_a, _ = main_rise_a
    _, peak_b, _ = main_rise_b
    
    # Check if peaks are close enough (same event)
    peak_gap = abs(peak_a - peak_b)
    if peak_gap > config.max_peak_gap_ms:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=peak_a,
            peak_time_b=peak_b,
            peak_gap_ms=peak_gap,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    # Step 2: Event confirmed! Now use center-of-mass for direction
    com_a = calculate_center_of_mass(side_a, min_value=config.min_rise / 2)
    com_b = calculate_center_of_mass(side_b, min_value=config.min_rise / 2)
    
    if com_a is None or com_b is None:
        # Fallback to peak timing
        if peak_a < peak_b:
            direction = Direction.A_TO_B
        else:
            direction = Direction.B_TO_A
        com_gap = abs(peak_a - peak_b)
    else:
        com_gap = abs(com_a - com_b)
        if com_a < com_b:
            direction = Direction.A_TO_B
        else:
            direction = Direction.B_TO_A
    
    # Confidence
    gap_confidence = min(1.0, com_gap / 30)
    signal_confidence = min(1.0, (side_a_max + side_b_max) / 100)
    confidence = (gap_confidence + signal_confidence) / 2
    
    return DetectionResult(
        direction=direction,
        confidence=confidence,
        peak_time_a=int(com_a) if com_a else peak_a,
        peak_time_b=int(com_b) if com_b else peak_b,
        peak_gap_ms=int(com_gap),
        side_a_max=side_a_max,
        side_b_max=side_b_max
    )


def analyze_window_com(readings: list[SensorReading], config: Config) -> DetectionResult:
    """
    Alternative algorithm: use Center of Mass timing comparison.
    
    If side A's center of mass is earlier than side B's → A→B
    """
    if not readings:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=0,
            side_b_max=0
        )
    
    # Aggregate by side
    side_a, side_b = aggregate_by_side(readings)
    
    if not side_a or not side_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=0,
            side_b_max=0
        )
    
    side_a_max = max(side_a.values())
    side_b_max = max(side_b.values())
    
    # Calculate center of mass for each side
    com_a = calculate_center_of_mass(side_a, min_value=config.min_rise / 2)
    com_b = calculate_center_of_mass(side_b, min_value=config.min_rise / 2)
    
    if com_a is None or com_b is None:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=int(com_a) if com_a else None,
            peak_time_b=int(com_b) if com_b else None,
            peak_gap_ms=None,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    com_gap = abs(com_a - com_b)
    
    # Check if there's meaningful activity (both sides should have risen)
    if side_a_max < config.min_rise or side_b_max < config.min_rise:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=int(com_a),
            peak_time_b=int(com_b),
            peak_gap_ms=int(com_gap),
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    # Determine direction based on which side's activity centroid is earlier
    if com_a < com_b:
        direction = Direction.A_TO_B
    else:
        direction = Direction.B_TO_A
    
    # Confidence based on gap and signal strength
    gap_confidence = min(1.0, com_gap / 30)  # 30ms gap = 100% confident
    signal_confidence = min(1.0, (side_a_max + side_b_max) / 100)
    confidence = (gap_confidence + signal_confidence) / 2
    
    return DetectionResult(
        direction=direction,
        confidence=confidence,
        peak_time_a=int(com_a),
        peak_time_b=int(com_b),
        peak_gap_ms=int(com_gap),
        side_a_max=side_a_max,
        side_b_max=side_b_max
    )


def analyze_window(readings: list[SensorReading], config: Config) -> DetectionResult:
    """
    Main algorithm: analyze a window of sensor readings to detect direction.
    
    Uses RISE START TIME (when signal begins climbing) rather than peak time,
    because peaks happen almost simultaneously when ball is in the middle.
    """
    if not readings:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=0,
            side_b_max=0
        )
    
    # Step 1: Aggregate by side
    side_a, side_b = aggregate_by_side(readings)
    
    if not side_a or not side_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=0,
            side_b_max=0
        )
    
    # Step 2: Smooth
    side_a_smooth = smooth_signal(side_a, config.smoothing_window)
    side_b_smooth = smooth_signal(side_b, config.smoothing_window)
    
    # Step 3: Compute derivatives
    d_a = compute_derivative(side_a_smooth)
    d_b = compute_derivative(side_b_smooth)
    
    side_a_max = max(side_a.values())
    side_b_max = max(side_b.values())
    
    if not d_a or not d_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    # Step 4: Find rise start times (not just peaks)
    rises_a = find_rise_start_times(side_a_smooth, d_a, config.min_rise)
    rises_b = find_rise_start_times(side_b_smooth, d_b, config.min_rise)
    
    if not rises_a or not rises_b:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=None,
            peak_time_b=None,
            peak_gap_ms=None,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    # Step 5: Find the largest rise on each side (main event)
    # Sort by rise_amount descending
    main_rise_a = max(rises_a, key=lambda x: x[2])  # (start_time, peak_time, rise_amount)
    main_rise_b = max(rises_b, key=lambda x: x[2])
    
    rise_start_a, peak_a, rise_amount_a = main_rise_a
    rise_start_b, peak_b, rise_amount_b = main_rise_b
    
    # Check if the rises are part of the same event (peaks within max_gap)
    peak_gap = abs(peak_a - peak_b)
    if peak_gap > config.max_peak_gap_ms:
        return DetectionResult(
            direction=Direction.UNKNOWN,
            confidence=0.0,
            peak_time_a=peak_a,
            peak_time_b=peak_b,
            peak_gap_ms=peak_gap,
            side_a_max=side_a_max,
            side_b_max=side_b_max
        )
    
    # Step 6: Determine direction based on RISE START TIME
    rise_gap = abs(rise_start_a - rise_start_b)
    
    if rise_start_a < rise_start_b:
        direction = Direction.A_TO_B
    elif rise_start_b < rise_start_a:
        direction = Direction.B_TO_A
    else:
        # Tie - fall back to peak timing
        if peak_a < peak_b:
            direction = Direction.A_TO_B
        else:
            direction = Direction.B_TO_A
    
    # Confidence based on rise gap (larger gap = more confident) and signal strength
    gap_confidence = min(1.0, rise_gap / 50)  # 50ms rise gap = 100% confident
    signal_confidence = min(1.0, (rise_amount_a + rise_amount_b) / 100)
    confidence = (gap_confidence + signal_confidence) / 2
    
    return DetectionResult(
        direction=direction,
        confidence=confidence,
        peak_time_a=rise_start_a,  # Now reporting rise start, not peak
        peak_time_b=rise_start_b,
        peak_gap_ms=rise_gap,
        side_a_max=side_a_max,
        side_b_max=side_b_max
    )


def get_expected_direction(filename: str) -> Direction:
    """Parse expected direction from filename."""
    name = filename.lower()
    if name.startswith('a_to_b'):
        return Direction.A_TO_B
    elif name.startswith('b_to_a'):
        return Direction.B_TO_A
    elif name.startswith('baseline'):
        return Direction.UNKNOWN
    return Direction.UNKNOWN


def main():
    """Run validation against all labeled data."""
    # Find the data directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    data_dir = project_root / 'session_data' / 'labeled-data' / 'group1'
    
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return
    
    # Configuration - try different parameter sets
    # Format: (name, config, method) where method is "rise", "com", or "hybrid"
    configs = [
        ("Rise-Start Default", Config(smoothing_window=3, min_rise=10, max_peak_gap_ms=100), "rise"),
        ("Hybrid Default", Config(smoothing_window=3, min_rise=10, max_peak_gap_ms=100), "hybrid"),
        ("Hybrid Sensitive", Config(smoothing_window=3, min_rise=8, max_peak_gap_ms=120), "hybrid"),
        ("Hybrid Smoothed", Config(smoothing_window=5, min_rise=10, max_peak_gap_ms=100), "hybrid"),
    ]
    
    best_accuracy = 0
    best_config_name = ""
    
    print("=" * 70)
    print("Direction Detection - Attempt 1: Validation")
    print("=" * 70)
    
    csv_files = sorted(data_dir.glob('*.csv'))
    
    for config_name, config, method in configs:
        print(f"\n{'='*70}")
        print(f"Config: {config_name}")
        print(f"  smoothing={config.smoothing_window}, min_rise={config.min_rise}, max_gap={config.max_peak_gap_ms}ms")
        print("-" * 70)
        
        # Track results
        total = 0
        correct = 0
        results = []
        
        for csv_file in csv_files:
            readings = load_csv(csv_file)
            if method == "com":
                result = analyze_window_com(readings, config)
            elif method == "hybrid":
                result = analyze_window_hybrid(readings, config)
            else:
                result = analyze_window(readings, config)
            expected = get_expected_direction(csv_file.name)
            
            is_correct = result.direction == expected
            total += 1
            if is_correct:
                correct += 1
            
            status = "✓" if is_correct else "✗"
            
            results.append({
                'file': csv_file.name,
                'expected': expected.value,
                'detected': result.direction.value,
                'correct': is_correct,
                'confidence': result.confidence,
                'peak_gap': result.peak_gap_ms,
                'side_a_max': result.side_a_max,
                'side_b_max': result.side_b_max
            })
            
            print(f"{status} {csv_file.name}")
            print(f"    Expected: {expected.value:10} | Detected: {result.direction.value:10} | Conf: {result.confidence:.2f}")
            print(f"    Rise A: {result.peak_time_a} | Rise B: {result.peak_time_b} | Gap: {result.peak_gap_ms}ms")
        
        # Summary for this config
        accuracy = (correct / total * 100) if total > 0 else 0
        print(f"\n  ACCURACY: {correct}/{total} = {accuracy:.1f}%")
        
        # Breakdown by category
        categories = {}
        for r in results:
            expected = r['expected']
            if expected not in categories:
                categories[expected] = {'total': 0, 'correct': 0}
            categories[expected]['total'] += 1
            if r['correct']:
                categories[expected]['correct'] += 1
        
        for cat, stats in categories.items():
            cat_accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"    {cat}: {stats['correct']}/{stats['total']} ({cat_accuracy:.1f}%)")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_config_name = config_name
    
    print("\n" + "=" * 70)
    print(f"BEST CONFIG: {best_config_name} with {best_accuracy:.1f}% accuracy")
    print("=" * 70)
    if best_accuracy >= 90:
        print("🎉 Target accuracy (90%) achieved!")
    else:
        print(f"⚠️  Below target. Best: {best_accuracy:.1f}%")


if __name__ == '__main__':
    main()

