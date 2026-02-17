#!/usr/bin/env python3
"""
ML Training Pipeline for Motion Play Direction Detection.

Loads downloaded session data, preprocesses into fixed-size tensors,
trains a 1D CNN, evaluates, and exports as a C header file for
firmware embedding via TFLite.

Usage:
    python train.py                          # Train with defaults (trigger-aligned, norm=490, augmented)
    python train.py --data-dir ./data/sessions --window-ms 300
    python train.py --epochs 50 --batch-size 16
    python train.py --alignment center       # Legacy centered window alignment
    python train.py --norm-max 500           # Custom normalization constant
    python train.py --model-version "v2-test" # Custom version string
    python train.py --no-augment             # Disable channel-swap data augmentation
"""

import argparse
import json
import os
import sys

import numpy as np

# Class mapping
CLASSES = ["a_to_b", "b_to_a", "no_transit"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

# Normalization constant — MUST match ML_NORMALIZATION_MAX in firmware (MLDetector.h).
# This is the fixed divisor for proximity values. Using a fixed constant ensures
# training and on-device inference see identical input distributions.
# Value is based on observed practical maximum proximity at operating distance.
DEFAULT_NORMALIZATION_MAX = 490.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sessions(data_dir):
    """Load all session JSON files organized by class subdirectory."""
    sessions = []
    for class_name in CLASSES:
        class_dir = os.path.join(data_dir, class_name)
        if not os.path.isdir(class_dir):
            print(f"  Warning: directory {class_dir} not found, skipping class {class_name}")
            continue

        files = sorted(f for f in os.listdir(class_dir) if f.endswith(".json"))
        for fname in files:
            filepath = os.path.join(class_dir, fname)
            with open(filepath) as f:
                data = json.load(f)
            sessions.append({
                "class": class_name,
                "class_idx": CLASS_TO_IDX[class_name],
                "session_id": data.get("session", {}).get("session_id", fname),
                "readings": data.get("readings", []),
                "session": data.get("session", {}),
            })

    print(f"Loaded {len(sessions)} sessions: "
          + ", ".join(f"{c}={sum(1 for s in sessions if s['class']==c)}" for c in CLASSES))
    return sessions


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def readings_to_matrix(readings, num_positions=6):
    """
    Convert a list of sensor readings into a (T, 6) matrix.

    Each row = 1 millisecond, each column = sensor position (0-5).
    Values are proximity readings, forward-filled from the most recent reading.
    """
    # Filter out readings with invalid timestamps
    valid = [r for r in readings if r.get("timestamp_offset", 0) >= 0]
    if not valid:
        return np.zeros((1, num_positions), dtype=np.float32)

    # Sort by timestamp
    valid.sort(key=lambda r: r["timestamp_offset"])

    min_ts = valid[0]["timestamp_offset"]
    max_ts = valid[-1]["timestamp_offset"]
    duration = max_ts - min_ts

    if duration <= 0:
        return np.zeros((1, num_positions), dtype=np.float32)

    # Create matrix: (duration+1, 6), initialized to 0
    matrix = np.zeros((duration + 1, num_positions), dtype=np.float32)

    # Place readings
    for r in valid:
        t = r["timestamp_offset"] - min_ts
        pos = r.get("position", 0)
        if 0 <= pos < num_positions and 0 <= t <= duration:
            matrix[t, pos] = float(r.get("proximity", 0))

    # Forward-fill: for each column, propagate non-zero values forward
    for col in range(num_positions):
        last_val = 0.0
        for row in range(matrix.shape[0]):
            if matrix[row, col] != 0:
                last_val = matrix[row, col]
            else:
                matrix[row, col] = last_val

    return matrix


def find_event_center(matrix):
    """
    Find the center of the event in a (T, 6) matrix.
    Uses the timestamp of peak total proximity across all sensors.
    """
    total_signal = matrix.sum(axis=1)
    return int(np.argmax(total_signal))


def extract_window(matrix, window_ms, anchor=None, anchor_position=0.5):
    """
    Extract a fixed-size window from a (T, 6) matrix.

    Args:
        matrix: (T, 6) proximity data matrix.
        window_ms: Output window length in ms.
        anchor: Timestamp index to anchor the window around. If None, uses peak signal.
        anchor_position: Where in the output window the anchor should land, as a
            fraction [0, 1]. 0.5 = centered, 0.67 = anchor at 2/3 of window (matching
            firmware trigger-aligned behavior).

    Pads with zeros if the window extends beyond the matrix.
    """
    T = matrix.shape[0]

    if anchor is None:
        anchor = find_event_center(matrix)

    # Position the anchor at the specified fraction of the window
    offset_before = int(window_ms * anchor_position)
    start = anchor - offset_before
    end = start + window_ms

    # Create output window
    window = np.zeros((window_ms, matrix.shape[1]), dtype=np.float32)

    # Calculate overlap between source and destination
    src_start = max(0, start)
    src_end = min(T, end)
    dst_start = src_start - start
    dst_end = dst_start + (src_end - src_start)

    if src_end > src_start:
        window[dst_start:dst_end] = matrix[src_start:src_end]

    return window


def preprocess_session(session, window_ms=300, alignment="trigger"):
    """Convert a session to a (window_ms, 6) tensor.

    Args:
        alignment: How to position the transit event in the window.
            "center" — Peak signal centered in window (legacy behavior).
            "trigger" — Peak at ~2/3 of window, matching firmware behavior where
                the trigger fires early in the wave and the 150ms post-trigger delay
                places the peak in the latter portion of the captured window.
    """
    readings = session["readings"]
    matrix = readings_to_matrix(readings)

    if session["class"] == "no_transit":
        center = matrix.shape[0] // 2
        anchor_position = 0.5  # no-transit: centered regardless of alignment mode
    else:
        center = find_event_center(matrix)
        if alignment == "trigger":
            # Firmware behavior: trigger fires at start of wave, then 150ms delay,
            # then captures 300ms window ending at current time. Peak is typically
            # ~50-100ms after trigger, so ~100ms from end of window → 2/3 through.
            anchor_position = 0.67
        else:
            anchor_position = 0.5

    window = extract_window(matrix, window_ms, anchor=center,
                            anchor_position=anchor_position)
    return window


def normalize(X, norm_max=DEFAULT_NORMALIZATION_MAX):
    """Normalize proximity values using a fixed constant (must match firmware).

    Uses a fixed divisor rather than per-sample or per-dataset max to ensure
    training normalization matches on-device inference exactly.
    Values exceeding norm_max are clipped to 1.0.
    """
    if norm_max <= 0:
        return X
    X_norm = X / norm_max
    clipped_count = int(np.sum(X_norm > 1.0))
    if clipped_count > 0:
        over_max = X[X > norm_max].max()
        print(f"  WARNING: {clipped_count} values exceed norm_max ({norm_max:.1f}), "
              f"max observed = {over_max:.1f}. Clipping to 1.0.")
        X_norm = np.clip(X_norm, 0.0, 1.0)
    return X_norm


def channel_swap_augment(X, y):
    """Augment directional samples by swapping Side A / Side B sensor channels.

    Sensor layout (6 channels):
        Positions [0, 2, 4] = Side B (S1 sensors)
        Positions [1, 3, 5] = Side A (S2 sensors)

    Swapping Side A ↔ Side B and flipping the direction label produces a
    physically valid mirror of the transit event. This doubles directional
    training data without any hand-crafted noise.

    no_transit samples are included unchanged (label stays the same).

    Returns augmented (X_aug, y_aug) concatenated with the originals.
    """
    SWAP_ORDER = [1, 0, 3, 2, 5, 4]  # swap within each module pair
    DIRECTION_FLIP = {
        CLASS_TO_IDX["a_to_b"]: CLASS_TO_IDX["b_to_a"],
        CLASS_TO_IDX["b_to_a"]: CLASS_TO_IDX["a_to_b"],
        CLASS_TO_IDX["no_transit"]: CLASS_TO_IDX["no_transit"],
    }

    X_swapped = X[:, :, SWAP_ORDER]
    y_swapped = np.array([DIRECTION_FLIP[label] for label in y], dtype=y.dtype)

    X_aug = np.concatenate([X, X_swapped], axis=0)
    y_aug = np.concatenate([y, y_swapped], axis=0)

    n_original = len(y)
    n_dir_original = int(np.sum((y == CLASS_TO_IDX["a_to_b"]) | (y == CLASS_TO_IDX["b_to_a"])))
    print(f"  Channel-swap augmentation: {n_original} → {len(y_aug)} samples "
          f"(+{n_dir_original} mirrored directional, +{n_original - n_dir_original} mirrored no_transit)")

    return X_aug, y_aug


def build_dataset(sessions, window_ms=300, norm_max=DEFAULT_NORMALIZATION_MAX,
                   alignment="trigger", augment=True):
    """Build X (features) and y (labels) arrays from sessions."""
    X_list = []
    y_list = []
    session_ids = []

    for session in sessions:
        try:
            window = preprocess_session(session, window_ms=window_ms,
                                        alignment=alignment)
            X_list.append(window)
            y_list.append(session["class_idx"])
            session_ids.append(session["session_id"])
        except Exception as e:
            print(f"  Warning: failed to preprocess {session['session_id']}: {e}")

    X = np.stack(X_list, axis=0)  # (N, window_ms, 6)
    y = np.array(y_list, dtype=np.int32)  # (N,)

    print(f"Dataset (before augmentation): X={X.shape}, y={y.shape}")
    print(f"  Class distribution: "
          + ", ".join(f"{CLASSES[i]}={np.sum(y==i)}" for i in range(len(CLASSES))))

    if augment:
        X, y = channel_swap_augment(X, y)
        # Duplicate session_ids for augmented samples (with suffix)
        session_ids = session_ids + [f"{sid}_swapped" for sid in session_ids]
        print(f"  Post-augmentation distribution: "
              + ", ".join(f"{CLASSES[i]}={np.sum(y==i)}" for i in range(len(CLASSES))))

    print(f"  Raw value range: [{X.min():.1f}, {X.max():.1f}]")
    print(f"  Normalization: fixed constant = {norm_max:.1f} (must match firmware ML_NORMALIZATION_MAX)")

    X = normalize(X, norm_max=norm_max)
    print(f"  Normalized range: [{X.min():.4f}, {X.max():.4f}]")

    return X, y, session_ids


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def build_model(input_shape, num_classes=3):
    """Build a small 1D CNN for direction classification."""
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers

    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv1D(16, kernel_size=5, activation="relu", padding="same"),
        layers.MaxPooling1D(pool_size=2),
        layers.Conv1D(32, kernel_size=3, activation="relu", padding="same"),
        layers.MaxPooling1D(pool_size=2),
        layers.Flatten(),
        layers.Dense(32, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(num_classes, activation="softmax"),
    ])

    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(model, X_test, y_test):
    """Print evaluation metrics."""
    from sklearn.metrics import classification_report, confusion_matrix

    y_pred = model.predict(X_test, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)

    print("\n=== Classification Report ===")
    print(classification_report(y_test, y_pred_classes, target_names=CLASSES))

    print("=== Confusion Matrix ===")
    cm = confusion_matrix(y_test, y_pred_classes)
    print(f"{'':>12s} " + " ".join(f"{c:>10s}" for c in CLASSES))
    for i, row in enumerate(cm):
        print(f"{CLASSES[i]:>12s} " + " ".join(f"{v:>10d}" for v in row))

    return y_pred_classes


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_tflite(model, X_train, output_path="model.tflite"):
    """Export model as fully float32 TFLite (no quantization).
    
    Dynamic range quantization creates hybrid models (int8 weights, float32
    activations) which TFLite Micro's Conv2D kernel does not support.
    Exporting as pure float32 avoids this issue — the model is small enough
    (~100KB) that quantization is unnecessary.
    """
    import tensorflow as tf

    # Save as SavedModel first for more reliable conversion
    import tempfile
    saved_model_dir = tempfile.mkdtemp()
    model.export(saved_model_dir)

    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    # No quantization — fully float32 for TFLite Micro compatibility

    tflite_model = converter.convert()

    with open(output_path, "wb") as f:
        f.write(tflite_model)

    print(f"\nTFLite model saved (float32, no quantization): {output_path} ({len(tflite_model)} bytes)")

    # Clean up
    import shutil
    shutil.rmtree(saved_model_dir, ignore_errors=True)

    return tflite_model


def generate_model_version(args, num_sessions):
    """Generate a model version string from training parameters."""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    aug_tag = "aug" if not args.no_augment else "noaug"
    return f"v{date_str}-{num_sessions}sess-{args.alignment}-norm{int(args.norm_max)}-{aug_tag}"


def export_c_header(tflite_path, header_path="model_data.h", model_version=None):
    """Convert TFLite model to a C header file with version metadata."""
    with open(tflite_path, "rb") as f:
        model_bytes = f.read()

    version_str = model_version or "unknown"

    # Generate C array
    var_name = "direction_model_tflite"
    lines = [
        "#ifndef DIRECTION_MODEL_DATA_H",
        "#define DIRECTION_MODEL_DATA_H",
        "",
        f"// Auto-generated from {os.path.basename(tflite_path)}",
        f"// Model size: {len(model_bytes)} bytes",
        f"// Model version: {version_str}",
        "",
        f'#define ML_MODEL_VERSION "{version_str}"',
        "",
        f"const unsigned int {var_name}_len = {len(model_bytes)};",
        f"alignas(8) const unsigned char {var_name}[] = {{",
    ]

    # Write hex bytes, 12 per line
    for i in range(0, len(model_bytes), 12):
        chunk = model_bytes[i:i+12]
        hex_vals = ", ".join(f"0x{b:02x}" for b in chunk)
        comma = "," if i + 12 < len(model_bytes) else ""
        lines.append(f"    {hex_vals}{comma}")

    lines.append("};")
    lines.append("")
    lines.append("#endif  // DIRECTION_MODEL_DATA_H")
    lines.append("")

    with open(header_path, "w") as f:
        f.write("\n".join(lines))

    print(f"C header saved: {header_path}")
    print(f"  Model version: {version_str}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train ML direction detection model")
    parser.add_argument("--data-dir", default="./data/sessions", help="Session data directory")
    parser.add_argument("--window-ms", type=int, default=300, help="Input window size in ms")
    parser.add_argument("--epochs", type=int, default=30, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--test-split", type=float, default=0.2, help="Test split ratio")
    parser.add_argument("--output-dir", default="./output", help="Output directory for model files")
    parser.add_argument("--no-export", action="store_true", help="Skip TFLite export")
    parser.add_argument("--norm-max", type=float, default=DEFAULT_NORMALIZATION_MAX,
                        help=f"Normalization constant (must match firmware ML_NORMALIZATION_MAX, default: {DEFAULT_NORMALIZATION_MAX})")
    parser.add_argument("--alignment", choices=["trigger", "center"], default="trigger",
                        help="Window alignment mode: 'trigger' matches firmware behavior (default), 'center' is legacy centered")
    parser.add_argument("--model-version", type=str, default=None,
                        help="Model version string (auto-generated if not provided)")
    parser.add_argument("--no-augment", action="store_true",
                        help="Disable channel-swap data augmentation")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load data
    print("=== Loading Data ===")
    sessions = load_sessions(args.data_dir)
    if not sessions:
        print("No sessions found. Run download_sessions.py first.")
        sys.exit(1)

    # Build dataset
    print("\n=== Preprocessing ===")
    print(f"  Window alignment: {args.alignment}")
    augment = not args.no_augment
    if augment:
        print(f"  Channel-swap augmentation: ENABLED")
    else:
        print(f"  Channel-swap augmentation: DISABLED")
    X, y, session_ids = build_dataset(sessions, window_ms=args.window_ms,
                                      norm_max=args.norm_max,
                                      alignment=args.alignment,
                                      augment=augment)

    # Train/test split (stratified)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, session_ids, test_size=args.test_split, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)} samples, Test: {len(X_test)} samples")

    # Build and train model
    print("\n=== Training ===")
    import tensorflow as tf
    tf.get_logger().setLevel("ERROR")

    input_shape = (args.window_ms, 6)
    model = build_model(input_shape, num_classes=len(CLASSES))
    model.summary()

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=args.epochs,
        batch_size=args.batch_size,
        verbose=1,
    )

    # Evaluate
    print("\n=== Evaluation ===")
    evaluate_model(model, X_test, y_test)

    # Save Keras model
    keras_path = os.path.join(args.output_dir, "direction_model.keras")
    model.save(keras_path)
    print(f"\nKeras model saved: {keras_path}")

    # Export TFLite
    if not args.no_export:
        print("\n=== Exporting TFLite ===")
        tflite_path = os.path.join(args.output_dir, "direction_model.tflite")
        header_path = os.path.join(args.output_dir, "model_data.h")

        model_version = args.model_version or generate_model_version(args, len(sessions))
        print(f"Model version: {model_version}")

        export_tflite(model, X_train, output_path=tflite_path)
        export_c_header(tflite_path, header_path=header_path,
                        model_version=model_version)

    print("\nDone!")


if __name__ == "__main__":
    main()
