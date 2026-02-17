#!/usr/bin/env python3
"""
ML Training Pipeline for Motion Play Direction Detection.

Loads downloaded session data, preprocesses into fixed-size tensors,
trains a 1D CNN, evaluates, quantizes to int8 TFLite, and exports
as a C header file for firmware embedding.

Usage:
    python train.py                          # Train with defaults
    python train.py --data-dir ./data/sessions --window-ms 300
    python train.py --epochs 50 --batch-size 16
"""

import argparse
import json
import os
import sys

import numpy as np

# Class mapping
CLASSES = ["a_to_b", "b_to_a", "no_transit"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


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


def extract_window(matrix, window_ms, center=None):
    """
    Extract a fixed-size window from a (T, 6) matrix.

    If center is provided, extracts around that point.
    Otherwise, centers on the peak signal.
    Pads with zeros if the window extends beyond the matrix.
    """
    T = matrix.shape[0]

    if center is None:
        center = find_event_center(matrix)

    half = window_ms // 2
    start = center - half
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


def preprocess_session(session, window_ms=300):
    """Convert a session to a (window_ms, 6) normalized tensor."""
    readings = session["readings"]
    matrix = readings_to_matrix(readings)

    if session["class"] == "no_transit":
        # For no-transit: use center of session (or random for augmentation)
        center = matrix.shape[0] // 2
    else:
        # For transit events: center on peak activity
        center = find_event_center(matrix)

    window = extract_window(matrix, window_ms, center=center)
    return window


def normalize(X):
    """Normalize proximity values to [0, 1] range based on actual data."""
    max_val = X.max()
    if max_val == 0:
        return X
    return X / max_val


def build_dataset(sessions, window_ms=300):
    """Build X (features) and y (labels) arrays from sessions."""
    X_list = []
    y_list = []
    session_ids = []

    for session in sessions:
        try:
            window = preprocess_session(session, window_ms=window_ms)
            X_list.append(window)
            y_list.append(session["class_idx"])
            session_ids.append(session["session_id"])
        except Exception as e:
            print(f"  Warning: failed to preprocess {session['session_id']}: {e}")

    X = np.stack(X_list, axis=0)  # (N, window_ms, 6)
    y = np.array(y_list, dtype=np.int32)  # (N,)

    raw_max = X.max()
    print(f"Dataset: X={X.shape}, y={y.shape}")
    print(f"  Class distribution: "
          + ", ".join(f"{CLASSES[i]}={np.sum(y==i)}" for i in range(len(CLASSES))))
    print(f"  Raw value range: [{X.min():.1f}, {X.max():.1f}]")
    print(f"  Normalization max: {raw_max:.1f}")

    X = normalize(X)
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


def export_c_header(tflite_path, header_path="model_data.h"):
    """Convert TFLite model to a C header file."""
    with open(tflite_path, "rb") as f:
        model_bytes = f.read()

    # Generate C array
    var_name = "direction_model_tflite"
    lines = [
        "#ifndef DIRECTION_MODEL_DATA_H",
        "#define DIRECTION_MODEL_DATA_H",
        "",
        f"// Auto-generated from {os.path.basename(tflite_path)}",
        f"// Model size: {len(model_bytes)} bytes",
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
    X, y, session_ids = build_dataset(sessions, window_ms=args.window_ms)

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

        export_tflite(model, X_train, output_path=tflite_path)
        export_c_header(tflite_path, header_path=header_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
