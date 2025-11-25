#!/bin/bash

# Analyze session data discrepancies
# Usage: ./analyze-session-data.sh SESSION_ID

SESSION_ID=${1:-"device-001_4836993"}

echo "═══════════════════════════════════════════════════════"
echo "  📊 Session Data Analysis: $SESSION_ID"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. Check device logs for transmission summary
echo "🔍 Step 1: Device Transmission Summary"
echo "─────────────────────────────────────────────────────"
echo "From your device logs, you reported:"
echo "  • Samples collected: 1,486"
echo "  • Batches sent: 15 (14×100 + 1×86)"
echo "  • All batches: 'Published successfully' ✓"
echo ""

# 2. Check Lambda invocations
echo "🔍 Step 2: Lambda Invocations"
echo "─────────────────────────────────────────────────────"
echo "Checking CloudWatch metrics..."

aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=motionplay-processData \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum \
  --region us-west-2 \
  --query 'Datapoints[?Sum > `10`]' \
  --output json | jq -r '.[] | "  • \(.Timestamp): \(.Sum) invocations"'

echo ""

# 3. Check Lambda logs for actual readings processed
echo "🔍 Step 3: Lambda Processing Details"
echo "─────────────────────────────────────────────────────"
echo "Analyzing Lambda logs..."

LOGS=$(aws logs filter-log-events \
  --log-group-name /aws/lambda/motionplay-processData \
  --filter-pattern "$SESSION_ID" \
  --start-time $(($(date +%s -v-1H) * 1000)) \
  --output json)

PROCESSING_LINES=$(echo "$LOGS" | jq -r '.events[].message | select(contains("Processing") and contains("readings"))')

echo "$PROCESSING_LINES" | while read -r line; do
    if [[ $line =~ ([0-9]+)\ readings ]]; then
        echo "  • Batch processed: ${BASH_REMATCH[1]} readings"
    fi
done

TOTAL_IN_LOGS=$(echo "$PROCESSING_LINES" | grep -oE '[0-9]+ readings' | grep -oE '[0-9]+' | awk '{sum+=$1} END {print sum}')
echo ""
echo "  📊 Total from logs: $TOTAL_IN_LOGS readings"
echo ""

# 4. Check DynamoDB actual count
echo "🔍 Step 4: DynamoDB Actual Count"
echo "─────────────────────────────────────────────────────"
echo "Querying DynamoDB..."

DB_COUNT=$(aws dynamodb query \
  --table-name MotionPlaySensorData \
  --key-condition-expression "session_id = :sid" \
  --expression-attribute-values '{":sid":{"S":"'$SESSION_ID'"}}' \
  --select COUNT \
  --output json | jq -r '.Count')

echo "  📊 Readings in DynamoDB: $DB_COUNT"
echo ""

# 5. Check for errors
echo "🔍 Step 5: Lambda Errors"
echo "─────────────────────────────────────────────────────"

ERROR_COUNT=$(aws logs filter-log-events \
  --log-group-name /aws/lambda/motionplay-processData \
  --filter-pattern "$SESSION_ID ERROR" \
  --start-time $(($(date +%s -v-1H) * 1000)) \
  --output json | jq '.events | length')

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "  ⚠️  Found $ERROR_COUNT errors!"
    echo ""
    echo "  Recent errors:"
    aws logs filter-log-events \
      --log-group-name /aws/lambda/motionplay-processData \
      --filter-pattern "$SESSION_ID ERROR" \
      --start-time $(($(date +%s -v-1H) * 1000)) \
      --output json | jq -r '.events[] | "    • \(.message)"' | head -5
else
    echo "  ✓ No errors found"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  📋 Summary"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Device sent:        1,486 readings (15 batches)"
echo "Lambda received:    [Check metrics above]"
echo "Lambda processed:   $TOTAL_IN_LOGS readings"
echo "DynamoDB stored:    $DB_COUNT readings"
echo ""

# Calculate losses
if [ ! -z "$TOTAL_IN_LOGS" ] && [ ! -z "$DB_COUNT" ]; then
    LOSS_1=$((1486 - TOTAL_IN_LOGS))
    LOSS_2=$((TOTAL_IN_LOGS - DB_COUNT))
    TOTAL_LOSS=$((1486 - DB_COUNT))
    
    echo "📉 Data Loss Breakdown:"
    echo "  • Device → Lambda:    -$LOSS_1 readings ($(awk "BEGIN {printf \"%.1f\", $LOSS_1/1486*100}")%)"
    echo "  • Lambda → DynamoDB:  -$LOSS_2 readings ($(awk "BEGIN {printf \"%.1f\", $LOSS_2/1486*100}")%)"
    echo "  • Total Loss:         -$TOTAL_LOSS readings ($(awk "BEGIN {printf \"%.1f\", $TOTAL_LOSS/1486*100}")%)"
fi

echo ""
echo "═══════════════════════════════════════════════════════"

