#!/usr/bin/env python3
"""
Analyze Motion Play session data for configuration comparison.

Usage:
    python analyze_session.py <session.csv> [--verbose]
    python analyze_session.py session_data/short_sample_4T.csv --verbose

This script calculates:
- Firmware read rate (how fast your code is reading)
- Effective sensor update rate (how often values actually change)
- Redundancy factor (how many times you read before value changes)
- Per-sensor statistics (baseline, peak, signal-to-noise)
"""

import pandas as pd
import sys
from pathlib import Path
import argparse


def analyze_session(csv_path: str, verbose: bool = False):
    """Analyze a session CSV file."""
    df = pd.read_csv(csv_path)
    
    # Calculate metrics
    timestamps = df['timestamp_offset'].unique()
    time_span_ms = timestamps[-1] - timestamps[0]
    num_cycles = len(timestamps)
    firmware_rate = (num_cycles / time_span_ms) * 1000 if time_span_ms > 0 else 0
    
    # Calculate gaps between timestamps
    gaps = pd.Series(timestamps).diff().dropna()
    
    print(f"\n{'='*60}")
    print(f"Session Analysis: {Path(csv_path).name}")
    print(f"{'='*60}")
    
    print(f"\n--- Timing Metrics ---")
    print(f"Time span: {time_span_ms} ms ({time_span_ms/1000:.2f} seconds)")
    print(f"Complete 6-sensor cycles: {num_cycles}")
    print(f"Firmware read rate: {firmware_rate:.1f} Hz (all 6 sensors)")
    print(f"Average gap between reads: {gaps.mean():.2f} ms")
    print(f"Gap range: {gaps.min():.0f} - {gaps.max():.0f} ms")
    
    # Per-sensor proximity stats
    print(f"\n--- Per-Sensor Proximity Statistics ---")
    print(f"{'Sensor':<8} {'Baseline':<10} {'Peak':<8} {'Range':<10} {'SNR':<8}")
    print("-" * 50)
    
    for (pcb, side), group in df.groupby(['pcb_id', 'side']):
        prox = group['proximity']
        baseline = prox.median()
        peak = prox.max()
        signal_range = peak - baseline
        snr = peak / baseline if baseline > 0 else 0
        
        sensor_name = f"P{pcb}S{side}"
        print(f"{sensor_name:<8} {baseline:<10.0f} {peak:<8} {signal_range:<10.0f} {snr:<8.1f}x")
    
    # Calculate effective sensor update rate
    print(f"\n--- Effective Sensor Update Analysis ---")
    print("(How often the sensor value ACTUALLY changes vs how often you read it)")
    print(f"{'Sensor':<8} {'Reads':<8} {'Changes':<10} {'Effective Hz':<12} {'Redundancy':<10}")
    print("-" * 60)
    
    total_redundancy = 0
    sensor_count = 0
    
    for (pcb, side), group in df.groupby(['pcb_id', 'side']):
        values = group['proximity'].values
        changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
        effective_rate = (changes / time_span_ms) * 1000 if time_span_ms > 0 else 0
        redundancy = len(values) / max(changes, 1)
        
        sensor_name = f"P{pcb}S{side}"
        print(f"{sensor_name:<8} {len(values):<8} {changes:<10} {effective_rate:<12.1f} {redundancy:<10.1f}x")
        
        total_redundancy += redundancy
        sensor_count += 1
    
    avg_redundancy = total_redundancy / sensor_count if sensor_count > 0 else 0
    
    # Summary
    print(f"\n--- Summary ---")
    print(f"Average redundancy: {avg_redundancy:.1f}x")
    print(f"  → You're reading each sensor ~{avg_redundancy:.0f} times before it updates")
    
    # Estimate current integration time from redundancy
    # At 1/40 duty:
    # 1T -> 5ms period -> read at 2.2ms = 2.3x redundancy
    # 2T -> 10ms period -> ~4.5x redundancy
    # 4T -> 20ms period -> ~9x redundancy
    # 8T -> 40ms period -> ~18x redundancy
    
    if avg_redundancy > 12:
        estimated_it = "8T"
        estimated_rate = "~25 Hz"
    elif avg_redundancy > 6:
        estimated_it = "4T"
        estimated_rate = "~50 Hz"
    elif avg_redundancy > 3:
        estimated_it = "2T"
        estimated_rate = "~100 Hz"
    else:
        estimated_it = "1T or 1.5T"
        estimated_rate = "~150-200 Hz"
    
    print(f"\nEstimated current Integration Time: {estimated_it}")
    print(f"Estimated actual sensor update rate: {estimated_rate}")
    
    if verbose:
        print(f"\n--- Raw Data Sample (first 20 rows) ---")
        print(df.head(20).to_string())
    
    return df


def compare_sessions(paths: list):
    """Compare multiple sessions."""
    print("\n" + "="*60)
    print("MULTI-SESSION COMPARISON")
    print("="*60)
    
    results = []
    for path in paths:
        df = pd.read_csv(path)
        timestamps = df['timestamp_offset'].unique()
        time_span_ms = timestamps[-1] - timestamps[0]
        num_cycles = len(timestamps)
        firmware_rate = (num_cycles / time_span_ms) * 1000 if time_span_ms > 0 else 0
        
        # Calculate redundancy
        total_redundancy = 0
        sensor_count = 0
        for (pcb, side), group in df.groupby(['pcb_id', 'side']):
            values = group['proximity'].values
            changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
            redundancy = len(values) / max(changes, 1)
            total_redundancy += redundancy
            sensor_count += 1
        
        avg_redundancy = total_redundancy / sensor_count if sensor_count > 0 else 0
        
        results.append({
            'file': Path(path).name,
            'duration_ms': time_span_ms,
            'cycles': num_cycles,
            'firmware_hz': firmware_rate,
            'redundancy': avg_redundancy
        })
    
    # Print comparison table
    print(f"\n{'File':<40} {'Duration':<12} {'Cycles':<10} {'FW Rate':<12} {'Redundancy':<10}")
    print("-" * 90)
    for r in results:
        print(f"{r['file']:<40} {r['duration_ms']:<12.0f} {r['cycles']:<10} {r['firmware_hz']:<12.1f} {r['redundancy']:<10.1f}x")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze Motion Play session data')
    parser.add_argument('files', nargs='+', help='CSV file(s) to analyze')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--compare', '-c', action='store_true', help='Compare multiple sessions')
    
    args = parser.parse_args()
    
    if args.compare and len(args.files) > 1:
        compare_sessions(args.files)
    else:
        for csv_file in args.files:
            analyze_session(csv_file, args.verbose)

