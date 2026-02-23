#!/usr/bin/env python3
"""
Transit Sample Rate Calculator for Motion Play

Calculates how many sensor samples you get per ball transit for different
combinations of hoop size, ball size, ball speed, and sensor measurement rate.

Usage:
    python3 tools/transit-calculator.py                          # defaults
    python3 tools/transit-calculator.py --hoop 450 --ball 3      # size 3 ball, 450mm hoop
    python3 tools/transit-calculator.py --hoop 500 --ball-mm 203 # custom ball diameter
    python3 tools/transit-calculator.py --max-speed-mph 20       # 20 mph design max

All distances in mm, speeds in m/s or mph.
"""

import argparse
import math
import sys

# FIFA standard soccer ball diameters (mm), derived from circumference specs
BALL_SIZES = {
    1: 150,   # ~47cm circumference (mini/skills ball, no FIFA standard)
    2: 165,   # ~51cm circumference
    3: 190,   # ~59cm circumference
    4: 206,   # ~65cm circumference
    5: 220,   # ~69cm circumference
}

# Empirical VCNL4040 measurement rates at 1/40 duty cycle (Hz)
SENSOR_CONFIGS = {
    "1T/x1":    200,
    "1T/x2":    160,
    "1T/x4":    100,
    "2T/x1":    100,
    "2.5T/x1":   80,
    "2.5T/x4":   55,
    "4T/x1":     50,
    "8T/x1":     25,
    "8T/x8":     12,
}

SENSOR_TILT_DEG = 2  # A/B sensor angular offset from radial
EMITTER_HALF_ANGLE_DEG = 15  # VCNL4040 IR emitter half-intensity angle


def detection_zone_depth_mm(ball_diameter_mm: float, hoop_inner_diameter_mm: float) -> float:
    """
    Estimate the detection zone depth along the transit axis (mm).

    The ball is detectable while its surface is within the sensor's emitter cone.
    The dominant factor is the ball diameter (the ball itself must pass through).
    The sensor's ±2° tilt adds a small extension from the cone geometry.
    """
    hoop_radius = hoop_inner_diameter_mm / 2
    ball_radius = ball_diameter_mm / 2
    sensor_to_ball = hoop_radius - ball_radius
    cone_extension = 2 * sensor_to_ball * math.tan(math.radians(SENSOR_TILT_DEG))
    conservative = ball_diameter_mm
    liberal = ball_diameter_mm + cone_extension
    return (conservative + liberal) / 2


def transit_time_ms(detection_zone_mm: float, speed_ms: float) -> float:
    """Time in ms for the ball to traverse the detection zone."""
    return (detection_zone_mm / 1000) / speed_ms * 1000


def samples_per_transit(sensor_rate_hz: float, transit_ms: float) -> float:
    """Number of sensor measurements during the transit."""
    return sensor_rate_hz * (transit_ms / 1000)


def speed_verdict(n_samples: float) -> str:
    if n_samples >= 9:
        return "Excellent (9+)"
    elif n_samples >= 5:
        return "Good (5-9)"
    elif n_samples >= 3:
        return "Adequate (3-5)"
    elif n_samples >= 1.5:
        return "Marginal (<3)"
    elif n_samples >= 0.5:
        return "LIKELY MISSED"
    else:
        return "INVISIBLE"


def estimate_speed_from_wave(wave_duration_ms: float, detection_zone_mm: float) -> float:
    """Estimate ball speed (m/s) from observed wave duration."""
    if wave_duration_ms <= 0:
        return 0
    return detection_zone_mm / wave_duration_ms  # mm/ms = m/s


def run_analysis(hoop_mm, ball_mm, max_speed_ms, sensor_rates, label=""):
    zone = detection_zone_depth_mm(ball_mm, hoop_mm)
    sensor_to_ball = hoop_mm / 2 - ball_mm / 2

    print(f"\n{'=' * 78}")
    if label:
        print(f"  {label}")
    print(f"{'=' * 78}")
    print(f"  Hoop inner diameter:    {hoop_mm:.0f} mm")
    print(f"  Ball diameter:          {ball_mm:.0f} mm")
    print(f"  Sensor-to-ball surface: {sensor_to_ball:.0f} mm (centered transit)")
    print(f"  Detection zone depth:   {zone:.0f} mm")
    print(f"  Max design speed:       {max_speed_ms:.1f} m/s ({max_speed_ms / 0.44704:.0f} mph)")
    print()

    speeds = [
        (max_speed_ms,        "Design max"),
        (max_speed_ms * 0.75, "Fast throw"),
        (max_speed_ms * 0.50, "Medium toss"),
        (max_speed_ms * 0.25, "Casual toss"),
        (1.0,                 "Slow hand pass"),
    ]

    rate_headers = "  ".join(f"{name:>10}" for name, _ in sensor_rates)
    print(f"  {'Speed':>10}  {'':>16} {'Transit':>9}  {rate_headers}  {'Best verdict'}")
    print(f"  {'-'*10}  {'-'*16} {'-'*9}  " +
          "  ".join("-" * 10 for _ in sensor_rates) +
          f"  {'-'*16}")

    for speed, context in speeds:
        t_ms = transit_time_ms(zone, speed)
        results = []
        for _, rate in sensor_rates:
            n = samples_per_transit(rate, t_ms)
            results.append(n)
        best = max(results)
        verdict = speed_verdict(best)
        mph = speed / 0.44704
        cols = "  ".join(f"{n:>10.1f}" for n in results)
        print(f"  {speed:>7.1f}m/s  {context:<16} {t_ms:>7.1f}ms  {cols}  {verdict}")

    print()
    for target in [3, 5, 9]:
        parts = []
        for name, rate in sensor_rates:
            max_v = rate * (zone / 1000) / target
            parts.append(f"{name}: {max_v:.1f}m/s ({max_v/0.44704:.0f}mph)")
        print(f"  Max speed for {target} samples: {', '.join(parts)}")

    print()
    print(f"  Speed estimation: v (m/s) ≈ {zone:.0f} / wave_duration_ms")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Transit sample rate calculator for Motion Play",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--hoop", type=float, default=450,
                        help="Hoop inner diameter in mm (default: 450)")
    parser.add_argument("--ball", type=int, default=None,
                        help="Soccer ball size number (1-5)")
    parser.add_argument("--ball-mm", type=float, default=None,
                        help="Ball diameter in mm (overrides --ball)")
    parser.add_argument("--max-speed-mph", type=float, default=30,
                        help="Maximum design speed in mph (default: 30)")
    parser.add_argument("--max-speed-ms", type=float, default=None,
                        help="Maximum design speed in m/s (overrides --max-speed-mph)")
    parser.add_argument("--rate", type=int, action="append", default=None,
                        help="Sensor rate(s) to evaluate in Hz (can specify multiple)")
    args = parser.parse_args()

    # Resolve ball diameter
    if args.ball_mm is not None:
        ball_mm = args.ball_mm
        ball_label = f"{ball_mm:.0f}mm"
    elif args.ball is not None:
        if args.ball not in BALL_SIZES:
            print(f"Error: Unknown ball size {args.ball}. Valid sizes: {list(BALL_SIZES.keys())}")
            sys.exit(1)
        ball_mm = BALL_SIZES[args.ball]
        ball_label = f"Size {args.ball} ({ball_mm}mm)"
    else:
        ball_mm = BALL_SIZES[3]
        ball_label = f"Size 3 ({ball_mm}mm)"

    # Resolve max speed
    max_speed = args.max_speed_ms if args.max_speed_ms else args.max_speed_mph * 0.44704

    # Print reference tables
    print("\nSOCCER BALL REFERENCE SIZES")
    print("-" * 40)
    for size, diam in BALL_SIZES.items():
        marker = " <--" if diam == ball_mm else ""
        print(f"  Size {size}: ~{diam}mm diameter{marker}")

    print("\nVCNL4040 MEASUREMENT RATES (1/40 duty)")
    print("-" * 40)
    for name, rate in SENSOR_CONFIGS.items():
        print(f"  {name:>10}: ~{rate} Hz")

    # Determine which sensor rates to show
    if args.rate:
        rates = [(f"{r}Hz", r) for r in args.rate]
    else:
        rates = [
            ("1T/x1", 200),
            ("2T/x1", 100),
            ("2.5T/x4", 55),
        ]

    label = f"{args.hoop:.0f}mm hoop, {ball_label}, max {max_speed:.1f}m/s ({max_speed/0.44704:.0f}mph)"
    run_analysis(args.hoop, ball_mm, max_speed, rates, label)


if __name__ == "__main__":
    main()
