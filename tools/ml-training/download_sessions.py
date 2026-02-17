#!/usr/bin/env python3
"""
Download labeled sessions from the Motion Play API for ML training.

Fetches sessions filtered by labels and/or date, downloads full session data
(including readings), and saves them as JSON files organized by label.

Usage:
    # Download all sessions with label "a->b" from today
    python download_sessions.py --label "a->b" --date 2026-02-15

    # Download multiple labels
    python download_sessions.py --label "a->b" --label "b->a" --label "no-transit"

    # Download all labeled sessions from today
    python download_sessions.py --date 2026-02-15

    # Download all sessions with a specific label (any date)
    python download_sessions.py --label "successful-shot"

    # Specify output directory
    python download_sessions.py --label "a->b" --date 2026-02-15 --output ./data/run1

    # Dry run: show what would be downloaded without downloading
    python download_sessions.py --label "a->b" --date 2026-02-15 --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

API_BASE_URL = "https://gur8ivkb44.execute-api.us-west-2.amazonaws.com/prod"
DEFAULT_OUTPUT_DIR = "./data/sessions"


def fetch_sessions(limit=500):
    """Fetch session list from API."""
    url = f"{API_BASE_URL}/sessions?limit={limit}"
    print(f"Fetching sessions from {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    sessions = data.get("sessions", [])
    print(f"  Retrieved {len(sessions)} sessions")
    return sessions


def fetch_session_data(session_id):
    """Fetch full session data including readings."""
    url = f"{API_BASE_URL}/sessions/{session_id}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def filter_sessions(sessions, labels=None, date_str=None):
    """Filter sessions by labels and/or date."""
    filtered = sessions

    if labels:
        label_set = set(labels)
        filtered = [
            s for s in filtered
            if s.get("labels") and label_set.intersection(s["labels"])
        ]
        print(f"  After label filter ({', '.join(labels)}): {len(filtered)} sessions")

    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        date_filtered = []
        for s in filtered:
            ts = s.get("start_timestamp", "")
            if ts:
                try:
                    session_date = datetime.fromisoformat(
                        ts.replace("Z", "+00:00")
                    ).date()
                    if session_date == target_date:
                        date_filtered.append(s)
                except (ValueError, TypeError):
                    pass
            else:
                created_at = s.get("created_at", 0)
                if created_at:
                    session_date = datetime.fromtimestamp(
                        created_at / 1000, tz=timezone.utc
                    ).date()
                    if session_date == target_date:
                        date_filtered.append(s)
        filtered = date_filtered
        print(f"  After date filter ({date_str}): {len(filtered)} sessions")

    return filtered


def classify_session(session):
    """Determine the ML training class from session labels."""
    labels = session.get("labels", []) or []
    if "a->b" in labels:
        return "a_to_b"
    elif "b->a" in labels:
        return "b_to_a"
    elif "no-transit" in labels:
        return "no_transit"
    else:
        return "unlabeled"


def save_session(session_data, output_dir, class_name):
    """Save session data to a JSON file organized by class."""
    class_dir = os.path.join(output_dir, class_name)
    os.makedirs(class_dir, exist_ok=True)

    session_id = session_data.get("session", {}).get("session_id", "unknown")
    safe_id = session_id.replace("/", "_").replace("\\", "_")
    filepath = os.path.join(class_dir, f"{safe_id}.json")

    with open(filepath, "w") as f:
        json.dump(session_data, f, indent=2)

    return filepath


def print_summary(sessions):
    """Print a summary of sessions by class."""
    classes = {}
    for s in sessions:
        cls = classify_session(s)
        classes.setdefault(cls, []).append(s)

    print("\nSession summary by class:")
    print("-" * 40)
    for cls in sorted(classes.keys()):
        items = classes[cls]
        print(f"  {cls}: {len(items)} sessions")
        for s in items[:3]:
            labels = s.get("labels", [])
            mode = s.get("mode", "?")
            samples = s.get("sample_count", 0)
            print(f"    - {s['session_id']} (mode={mode}, labels={labels}, samples={samples})")
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")
    print("-" * 40)
    print(f"  Total: {len(sessions)} sessions")


def main():
    parser = argparse.ArgumentParser(
        description="Download labeled sessions for ML training"
    )
    parser.add_argument(
        "--label", action="append", dest="labels",
        help="Filter by label (can specify multiple). e.g. --label 'a->b' --label 'b->a'"
    )
    parser.add_argument(
        "--date", type=str,
        help="Filter by date (YYYY-MM-DD). e.g. --date 2026-02-15"
    )
    parser.add_argument(
        "--output", type=str, default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Max sessions to fetch from API (default: 500)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    parser.add_argument(
        "--delay", type=float, default=0.2,
        help="Delay between API calls in seconds (default: 0.2)"
    )

    args = parser.parse_args()

    if not args.labels and not args.date:
        print("Error: specify at least --label or --date to filter sessions.")
        print("Run with --help for usage.")
        sys.exit(1)

    # Fetch and filter
    sessions = fetch_sessions(limit=args.limit)
    filtered = filter_sessions(sessions, labels=args.labels, date_str=args.date)

    if not filtered:
        print("\nNo sessions match the filters.")
        sys.exit(0)

    print_summary(filtered)

    if args.dry_run:
        print("\nDry run — no files downloaded.")
        return

    # Download full session data
    print(f"\nDownloading {len(filtered)} sessions to {args.output}/...")
    os.makedirs(args.output, exist_ok=True)

    downloaded = 0
    errors = 0
    for i, session in enumerate(filtered):
        session_id = session["session_id"]
        class_name = classify_session(session)

        try:
            print(f"  [{i+1}/{len(filtered)}] {session_id} → {class_name}/", end="")
            session_data = fetch_session_data(session_id)

            readings = session_data.get("readings", [])
            filepath = save_session(session_data, args.output, class_name)
            print(f" ✓ ({len(readings)} readings)")
            downloaded += 1

            if args.delay > 0 and i < len(filtered) - 1:
                time.sleep(args.delay)

        except Exception as e:
            print(f" ✗ Error: {e}")
            errors += 1

    print(f"\nDone: {downloaded} downloaded, {errors} errors")
    print(f"Output: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
