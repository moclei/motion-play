#!/bin/bash

###############################################################################
# Motion Play - Download Session Data
#
# Downloads session data (metadata + readings) from the API Gateway.
# Useful for offline analysis and debugging.
#
# Usage:
#   ./download-session.sh <session_id>                    Download as JSON
#   ./download-session.sh <session_id> --summary          Print summary only
#   ./download-session.sh <session_id> --check-keys       Check for composite key collisions
#   ./download-session.sh <session_id> -o output.json     Save to specific file
#
# Examples:
#   ./download-session.sh device-002_60643
#   ./download-session.sh device-002_60643 --summary
#   ./download-session.sh device-002_60643 --check-keys
#
# Prerequisites:
#   - curl and jq installed
#   - API endpoint configured (reads from frontend .env or set API_ENDPOINT env var)
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Try to read API endpoint from frontend .env
ENV_FILE="$PROJECT_ROOT/frontend/motion-play-ui/.env"
if [ -z "$API_ENDPOINT" ] && [ -f "$ENV_FILE" ]; then
    API_ENDPOINT=$(grep '^VITE_API_ENDPOINT=' "$ENV_FILE" | cut -d'=' -f2)
fi

if [ -z "$API_ENDPOINT" ]; then
    echo -e "${RED}Error: API_ENDPOINT not set.${NC}"
    echo "Set it via environment variable or in frontend/motion-play-ui/.env"
    exit 1
fi

# Parse arguments
SESSION_ID=""
OUTPUT_FILE=""
MODE="download"  # download, summary, check-keys

while [ $# -gt 0 ]; do
    case "$1" in
        --summary)
            MODE="summary"
            shift
            ;;
        --check-keys)
            MODE="check-keys"
            shift
            ;;
        -o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 <session_id> [--summary|--check-keys] [-o output.json]"
            exit 0
            ;;
        *)
            if [ -z "$SESSION_ID" ]; then
                SESSION_ID="$1"
            else
                echo -e "${RED}Unknown argument: $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$SESSION_ID" ]; then
    echo "Usage: $0 <session_id> [--summary|--check-keys] [-o output.json]"
    exit 1
fi

echo -e "${BLUE}Downloading session: ${SESSION_ID}${NC}"
echo -e "  API: ${API_ENDPOINT}"

# Download the session data
RESPONSE=$(curl -s "${API_ENDPOINT}/sessions/${SESSION_ID}")

# Check for errors
if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR=$(echo "$RESPONSE" | jq -r '.error')
    echo -e "${RED}Error: ${ERROR}${NC}"
    exit 1
fi

SESSION_TYPE=$(echo "$RESPONSE" | jq -r '.session_type // "proximity"')
echo -e "  Session type: ${SESSION_TYPE}"

if [ "$MODE" = "download" ]; then
    # Save to file
    if [ -z "$OUTPUT_FILE" ]; then
        OUTPUT_FILE="${SESSION_ID}.json"
    fi
    echo "$RESPONSE" | jq '.' > "$OUTPUT_FILE"
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo -e "${GREEN}Saved to: ${OUTPUT_FILE} (${FILE_SIZE})${NC}"

    # Print quick stats
    if [ "$SESSION_TYPE" = "proximity" ]; then
        READING_COUNT=$(echo "$RESPONSE" | jq '.readings | length')
        echo -e "  Readings: ${READING_COUNT}"
    fi

elif [ "$MODE" = "summary" ]; then
    echo ""
    echo -e "${CYAN}━━━ Session Summary ━━━${NC}"

    # Session metadata
    echo "$RESPONSE" | jq -r '
        .session as $s |
        "  Session ID:   \($s.session_id // "N/A")",
        "  Device:       \($s.device_id // "N/A")",
        "  Mode:         \($s.mode // "N/A")",
        "  Duration:     \($s.duration_ms // 0)ms",
        "  Sample Rate:  \($s.sample_rate // "N/A") Hz",
        "  Sample Count: \($s.sample_count // "N/A")",
        "  Pipeline:     \($s.pipeline_status // "N/A")",
        "  Batches Rcvd: \($s.batches_received // "N/A")",
        "  Created:      \($s.end_timestamp // "N/A")"
    '

    if [ "$SESSION_TYPE" = "proximity" ]; then
        READING_COUNT=$(echo "$RESPONSE" | jq '.readings | length')
        echo ""
        echo -e "${CYAN}━━━ Readings ━━━${NC}"
        echo "  Total readings in DynamoDB: ${READING_COUNT}"

        # Per-sensor breakdown
        echo "$RESPONSE" | jq -r '
            .readings | group_by(.position) | map({
                position: .[0].position,
                count: length,
                pcb: .[0].pcb_id,
                side: .[0].side
            }) | sort_by(.position) | .[] |
            "  P\(.pcb)S\(.side) (pos \(.position)): \(.count) readings"
        '

        # Time window
        echo ""
        echo -e "${CYAN}━━━ Time Window ━━━${NC}"
        echo "$RESPONSE" | jq -r '
            .readings | map(.timestamp_offset // .timestamp_ms) |
            if length > 0 then
                (min) as $min | (max) as $max |
                "  First timestamp: \($min)ms",
                "  Last timestamp:  \($max)ms",
                "  Window:          \(($max - $min))ms (\((($max - $min) / 1000 * 100 | floor) / 100)s)"
            else
                "  No readings"
            end
        '

        # Session confirmation summary
        SUMMARY=$(echo "$RESPONSE" | jq '.session.session_summary // null')
        if [ "$SUMMARY" != "null" ]; then
            echo ""
            echo -e "${CYAN}━━━ Session Confirmation ━━━${NC}"
            echo "$SUMMARY" | jq -r '
                "  Firmware collected:    \(.readings_collected | add // 0)",
                "  Firmware transmitted:  \(.total_readings_transmitted // 0)",
                "  Batches transmitted:   \(.total_batches_transmitted // 0)",
                "  Cycle rate:            \(.measured_cycle_rate_hz // 0) Hz",
                "  Duration:              \(.duration_ms // 0)ms",
                "  I2C errors:            \(.i2c_errors | add // 0)",
                "  Queue drops:           \(.queue_drops // 0)",
                "  Buffer drops:          \(.buffer_drops // 0)"
            '
            echo "  DynamoDB stored:       ${READING_COUNT}"
            TRANSMITTED=$(echo "$SUMMARY" | jq '.total_readings_transmitted // 0')
            if [ "$TRANSMITTED" -gt 0 ]; then
                RATE=$(echo "scale=1; ${READING_COUNT} * 100 / ${TRANSMITTED}" | bc)
                echo "  Delivery rate:         ${RATE}% (stored/transmitted)"
            fi
        fi
    fi

elif [ "$MODE" = "check-keys" ]; then
    echo ""
    echo -e "${CYAN}━━━ Composite Key Analysis (DynamoDB direct) ━━━${NC}"
    echo ""
    echo -e "  ${YELLOW}Note: Querying DynamoDB directly for raw sort keys.${NC}"
    echo -e "  ${YELLOW}The API returns decoded millisecond values, not raw keys.${NC}"
    echo ""

    # Query DynamoDB directly for raw timestamp_offset values
    RAW_KEYS=$(aws dynamodb query \
        --table-name MotionPlaySensorData \
        --key-condition-expression "session_id = :sid" \
        --expression-attribute-values "{\":sid\": {\"S\": \"${SESSION_ID}\"}}" \
        --projection-expression "timestamp_offset, #pos" \
        --expression-attribute-names '{"#pos": "position"}' \
        --region us-west-2 \
        --output json 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo -e "  ${RED}Failed to query DynamoDB directly. Falling back to API data.${NC}"
        echo -e "  ${YELLOW}Make sure AWS CLI is configured with appropriate credentials.${NC}"
        exit 1
    fi

    READING_COUNT=$(echo "$RAW_KEYS" | jq '.Items | length')
    echo "  Total readings in DynamoDB: ${READING_COUNT}"

    # Check uniqueness of raw sort keys
    UNIQUE_KEYS=$(echo "$RAW_KEYS" | jq '[.Items[].timestamp_offset.N] | unique | length')
    echo "  Unique sort keys:           ${UNIQUE_KEYS}"

    if [ "$UNIQUE_KEYS" -eq "$READING_COUNT" ]; then
        echo -e "  ${GREEN}No composite key collisions — all keys unique${NC}"
    else
        DUPES=$((READING_COUNT - UNIQUE_KEYS))
        echo -e "  ${RED}${DUPES} duplicate keys detected (data was overwritten)!${NC}"

        echo ""
        echo "  Duplicated keys (first 10):"
        echo "$RAW_KEYS" | jq -r '
            [.Items[].timestamp_offset.N] | group_by(.) |
            map(select(length > 1)) |
            .[:10][] |
            "    key=\(.[0]) count=\(length)"
        '
    fi

    # Detect key scheme
    echo ""
    echo -e "${CYAN}━━━ Key Scheme ━━━${NC}"
    KEY_STATS=$(echo "$RAW_KEYS" | jq '
        [.Items[].timestamp_offset.N | tonumber] |
        {min: min, max: max, count: length}
    ')
    MIN_KEY=$(echo "$KEY_STATS" | jq '.min')
    MAX_KEY=$(echo "$KEY_STATS" | jq '.max')

    if [ "$MAX_KEY" -gt 1000000 ]; then
        echo -e "  Key scheme: ${GREEN}Microsecond-based${NC}"
        # Decode the key: key = (relative_timestamp_us * 10) + position
        MAX_TS_US=$(( MAX_KEY / 10 ))
        echo "  Max raw key:     ${MAX_KEY}"
        echo "  Max timestamp:   ${MAX_TS_US}µs ($(echo "scale=3; ${MAX_TS_US} / 1000000" | bc)s)"
    else
        echo -e "  Key scheme: ${YELLOW}Millisecond-based (legacy)${NC}"
        MAX_TS_MS=$(( MAX_KEY / 10 ))
        echo "  Max raw key:     ${MAX_KEY}"
        echo "  Max timestamp:   ${MAX_TS_MS}ms ($(echo "scale=3; ${MAX_TS_MS} / 1000" | bc)s)"
    fi

    # Per-sensor counts from raw data
    echo ""
    echo -e "${CYAN}━━━ Per-Sensor Breakdown ━━━${NC}"
    echo "$RAW_KEYS" | jq -r '
        [.Items[] | .position.N | tonumber] |
        group_by(.) | map({pos: .[0], count: length}) |
        sort_by(.pos) | .[] |
        "  Position \(.pos): \(.count) readings"
    '

    # Cycle completeness (group by decoded timestamp, check for 6 sensors per cycle)
    echo ""
    echo -e "${CYAN}━━━ Cycle Completeness (first 20) ━━━${NC}"
    echo "$RAW_KEYS" | jq -r '
        [.Items[] | {
            ts: (.timestamp_offset.N | tonumber | . / 10 | floor),
            pos: (.position.N | tonumber)
        }] |
        group_by(.ts) |
        .[:20] | .[] |
        "\(.[0].ts): \(length) sensors \(if length == 6 then "✓" else "⚠ missing \(6 - length)" end)"
    '

    # Session confirmation comparison
    echo ""
    echo -e "${CYAN}━━━ Pipeline Comparison ━━━${NC}"
    SUMMARY=$(echo "$RESPONSE" | jq '.session.session_summary // null')
    if [ "$SUMMARY" != "null" ]; then
        TRANSMITTED=$(echo "$SUMMARY" | jq '.total_readings_transmitted // 0')
        COLLECTED=$(echo "$SUMMARY" | jq '[.readings_collected[] // 0] | add // 0')
        echo "  Firmware collected:    ${COLLECTED}"
        echo "  Firmware transmitted:  ${TRANSMITTED}"
        echo "  DynamoDB stored:       ${READING_COUNT}"
        if [ "$TRANSMITTED" -gt 0 ]; then
            RATE=$(echo "scale=1; ${READING_COUNT} * 100 / ${TRANSMITTED}" | bc)
            echo "  Delivery rate:         ${RATE}% (stored/transmitted)"
        fi
        LOST=$((TRANSMITTED - READING_COUNT))
        if [ "$LOST" -gt 0 ]; then
            echo -e "  ${RED}Readings lost in pipeline: ${LOST}${NC}"
        else
            echo -e "  ${GREEN}No pipeline losses detected${NC}"
        fi
    fi
fi
