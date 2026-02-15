#!/bin/bash

###############################################################################
# Motion Play - Diagnose Session (CloudWatch Logs)
#
# Queries CloudWatch Logs for Lambda invocations related to a session.
# Shows: how many invocations, errors, durations, and data processing details.
#
# Usage:
#   ./diagnose-session.sh <session_id>                     Full diagnosis
#   ./diagnose-session.sh <session_id> --errors            Show only errors
#   ./diagnose-session.sh <session_id> --since 30m         Look back 30 minutes
#   ./diagnose-session.sh <session_id> --raw               Show raw log events
#
# Examples:
#   ./diagnose-session.sh device-002_60643
#   ./diagnose-session.sh device-002_60643 --errors
#   ./diagnose-session.sh device-002_60643 --since 2h
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - jq installed
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
REGION="us-west-2"
PROCESS_DATA_LOG_GROUP="/aws/lambda/motionplay-processData"
GET_SESSION_LOG_GROUP="/aws/lambda/motionplay-getSessionData"

# Parse arguments
SESSION_ID=""
MODE="full"         # full, errors, raw
SINCE="1h"          # How far back to look

while [ $# -gt 0 ]; do
    case "$1" in
        --errors)
            MODE="errors"
            shift
            ;;
        --raw)
            MODE="raw"
            shift
            ;;
        --since)
            SINCE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 <session_id> [--errors|--raw] [--since <duration>]"
            echo ""
            echo "Options:"
            echo "  --errors   Show only error/timeout events"
            echo "  --raw      Show raw log events"
            echo "  --since    How far back to look (default: 1h). Examples: 30m, 2h, 1d"
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
    echo "Usage: $0 <session_id> [--errors|--raw] [--since <duration>]"
    exit 1
fi

# Convert --since to milliseconds ago
parse_since() {
    local val="${1%[mhd]}"
    local unit="${1: -1}"
    case "$unit" in
        m) echo $(( val * 60 * 1000 )) ;;
        h) echo $(( val * 3600 * 1000 )) ;;
        d) echo $(( val * 86400 * 1000 )) ;;
        *) echo $(( val * 3600 * 1000 )) ;;  # default to hours
    esac
}

SINCE_MS=$(parse_since "$SINCE")
START_TIME=$(( $(date +%s)000 - SINCE_MS ))

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Motion Play Session Diagnostics${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Session:  ${SESSION_ID}"
echo -e "  Region:   ${REGION}"
echo -e "  Lookback: ${SINCE}"
echo ""

###############################################################################
# Helper: Query CloudWatch Logs
###############################################################################

query_logs() {
    local log_group="$1"
    local filter_pattern="$2"
    local description="$3"

    echo -e "${CYAN}━━━ ${description} ━━━${NC}"
    echo -e "  Log group: ${log_group}"
    echo -e "  Filter:    ${filter_pattern}"
    echo ""

    aws logs filter-log-events \
        --log-group-name "$log_group" \
        --filter-pattern "$filter_pattern" \
        --start-time "$START_TIME" \
        --region "$REGION" \
        --output json 2>/dev/null
}

###############################################################################
# processData Lambda — Data ingestion
###############################################################################

echo -e "${CYAN}━━━ processData Lambda (data ingestion) ━━━${NC}"
echo ""

# Get all log events mentioning this session
PROCESS_LOGS=$(aws logs filter-log-events \
    --log-group-name "$PROCESS_DATA_LOG_GROUP" \
    --filter-pattern "\"${SESSION_ID}\"" \
    --start-time "$START_TIME" \
    --region "$REGION" \
    --output json 2>/dev/null || echo '{"events":[]}')

EVENT_COUNT=$(echo "$PROCESS_LOGS" | jq '.events | length')
echo -e "  Log events found: ${EVENT_COUNT}"

if [ "$EVENT_COUNT" -eq 0 ]; then
    echo -e "  ${YELLOW}No log events found. Try --since with a longer duration.${NC}"
    echo ""
else
    if [ "$MODE" = "raw" ]; then
        echo "$PROCESS_LOGS" | jq -r '.events[] | "\(.timestamp | . / 1000 | strftime("%H:%M:%S")) | \(.message)"' | head -100
        echo ""
    else
        # Extract key information
        echo ""

        # Count invocations (START events)
        INVOCATIONS=$(echo "$PROCESS_LOGS" | jq '[.events[] | select(.message | contains("Processing")) | select(.message | contains("'"$SESSION_ID"'"))] | length')
        echo -e "  Lambda invocations: ${INVOCATIONS}"

        # Count errors (exclude false positives from JSON field names like "i2c_errors")
        ERRORS=$(echo "$PROCESS_LOGS" | jq '[.events[] | select(
            (.message | test("\\bERROR\\b|\\bError\\b|\\bTimeout\\b|\\bTIMEOUT\\b|Task timed out|failed to|Failed to")) and
            (.message | test("\"i2c_errors\"") | not)
        )] | length')
        if [ "$ERRORS" -gt 0 ]; then
            echo -e "  ${RED}Errors: ${ERRORS}${NC}"
        else
            echo -e "  ${GREEN}Errors: 0${NC}"
        fi

        # Show batch processing events
        echo ""
        echo "  Processing events:"
        echo "$PROCESS_LOGS" | jq -r '
            .events[] |
            select(.message | contains("Processing") or contains("Stored batch") or contains("Updated sample") or contains("New session") or contains("Session already") or contains("Pipeline status") or contains("summary")) |
            "\("  " + (.timestamp | . / 1000 | strftime("%H:%M:%S")))  \(.message | rtrimstr("\n"))"
        ' | head -50

        # Show errors if any
        if [ "$ERRORS" -gt 0 ] || [ "$MODE" = "errors" ]; then
            echo ""
            echo -e "  ${RED}Error events:${NC}"
            echo "$PROCESS_LOGS" | jq -r '
                .events[] |
                select(
                    (.message | test("\\bERROR\\b|\\bError\\b|\\bTimeout\\b|\\bTIMEOUT\\b|Task timed out|failed to|Failed to")) and
                    (.message | test("\"i2c_errors\"") | not)
                ) |
                "\("  " + (.timestamp | . / 1000 | strftime("%H:%M:%S")))  \(.message | rtrimstr("\n"))"
            ' | head -20
        fi

        # Batch analysis — how many readings per invocation
        echo ""
        echo "  Batch analysis (readings processed per invocation):"
        echo "$PROCESS_LOGS" | jq -r '
            [.events[] |
            select(.message | test("Processing [0-9]+ readings")) |
            (.message | capture("Processing (?<count>[0-9]+) readings") | .count | tonumber)
            ] |
            if length > 0 then
                "    Batches seen:      \(length)",
                "    Readings per batch: \(.)",
                "    Total readings:    \(add)",
                "    Avg per batch:     \(add / length | floor)"
            else
                "    No batch events found"
            end
        '

        # Show Lambda duration/memory from REPORT lines
        echo ""
        echo "  Lambda execution reports:"
        echo "$PROCESS_LOGS" | jq -r '
            .events[] |
            select(.message | startswith("REPORT")) |
            .message | rtrimstr("\n") |
            capture("Duration: (?<dur>[0-9.]+) ms.*Billed Duration: (?<billed>[0-9]+) ms.*Memory Size: (?<mem>[0-9]+) MB.*Max Memory Used: (?<used>[0-9]+) MB") |
            "    Duration: \(.dur)ms | Billed: \(.billed)ms | Memory: \(.used)/\(.mem)MB"
        ' | head -20

        # Check for timeouts
        TIMEOUTS=$(echo "$PROCESS_LOGS" | jq '[.events[] | select(.message | contains("Task timed out"))] | length')
        if [ "$TIMEOUTS" -gt 0 ]; then
            echo ""
            echo -e "  ${RED}⚠ TIMEOUTS DETECTED: ${TIMEOUTS} Lambda invocations timed out!${NC}"
            echo -e "  ${RED}  This is likely causing data loss.${NC}"
        fi
    fi
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Diagnosis Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Session:       ${SESSION_ID}"
echo -e "  Log events:    ${EVENT_COUNT}"
if [ "$EVENT_COUNT" -gt 0 ]; then
    echo -e "  Invocations:   ${INVOCATIONS:-N/A}"
    if [ "${ERRORS:-0}" -gt 0 ]; then
        echo -e "  Errors:        ${RED}${ERRORS}${NC}"
    else
        echo -e "  Errors:        ${GREEN}0${NC}"
    fi
    if [ "${TIMEOUTS:-0}" -gt 0 ]; then
        echo -e "  Timeouts:      ${RED}${TIMEOUTS}${NC}"
    else
        echo -e "  Timeouts:      ${GREEN}0${NC}"
    fi
fi
echo ""
echo -e "  ${YELLOW}Tip: Use './download-session.sh ${SESSION_ID} --check-keys' to verify composite key uniqueness${NC}"
echo ""
