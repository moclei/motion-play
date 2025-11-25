#!/bin/bash

# Monitor MQTT messages from MotionPlay device
# Usage: ./monitor-mqtt.sh

echo "🔍 Monitoring MQTT topic: motionplay/+/data"
echo "📊 This will show message count and sizes"
echo ""
echo "Start a session on your device, then watch the output..."
echo ""

ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)
TOPIC="motionplay/+/data"

echo "Endpoint: $ENDPOINT"
echo "Topic: $TOPIC"
echo "----------------------------------------"

# Subscribe to MQTT topic and count messages
aws iot-data subscribe \
    --topic "$TOPIC" \
    --cli-read-timeout 300 \
    --output json | \
while IFS= read -r line; do
    # Parse the message
    if echo "$line" | jq -e . >/dev/null 2>&1; then
        SESSION_ID=$(echo "$line" | jq -r '.session_id // "unknown"')
        BATCH_OFFSET=$(echo "$line" | jq -r '.batch_offset // "unknown"')
        READINGS_COUNT=$(echo "$line" | jq -r '.readings | length // 0')
        PAYLOAD_SIZE=$(echo "$line" | wc -c)
        
        TIMESTAMP=$(date '+%H:%M:%S')
        
        echo "[$TIMESTAMP] Session: $SESSION_ID | Batch: $BATCH_OFFSET | Readings: $READINGS_COUNT | Size: $PAYLOAD_SIZE bytes"
        
        # Keep a running total
        TOTAL_READINGS=$((TOTAL_READINGS + READINGS_COUNT))
        echo "  📈 Total readings received so far: $TOTAL_READINGS"
    fi
done

