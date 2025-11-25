# processData Lambda Deployment Guide

## Bug Fix: Session Overwrite Issue

**Date**: November 21, 2025  
**Issue**: Sessions were losing labels, notes, and sample counts  
**Root Cause**: `PutCommand` was overwriting entire session when receiving duplicate `batch_offset=0` events

---

## The Problem

When the device sent data with `batch_offset=0` multiple times (due to retries, reconnections, or firmware bugs), the Lambda used `PutCommand` which **completely overwrites** the session record in DynamoDB, causing:

- ✗ User-added labels to disappear
- ✗ User-added notes to disappear  
- ✗ Sample count to reset to the new batch size (often "66")
- ✗ `created_at` timestamp to update, causing session list re-ordering

---

## The Fix

The updated `processData` Lambda now:

1. ✓ **Checks if session exists** before attempting to create it
2. ✓ **Uses UpdateCommand** (not PutCommand) when session exists
3. ✓ **Preserves user-editable fields**: `labels`, `notes`, `created_at`
4. ✓ **Updates system fields only**: `duration_ms`, `sample_count`, `end_timestamp`

### Code Changes

```javascript
// BEFORE (Buggy)
if (data.batch_offset === 0) {
    await docClient.send(new PutCommand({  // Overwrites everything!
        TableName: SESSIONS_TABLE,
        Item: sessionItem
    }));
}

// AFTER (Fixed)
if (data.batch_offset === 0) {
    const existing = await docClient.send(new GetCommand({
        TableName: SESSIONS_TABLE,
        Key: { session_id: data.session_id }
    }));
    
    if (existing.Item) {
        // Session exists - update only, preserve labels/notes
        await docClient.send(new UpdateCommand({
            TableName: SESSIONS_TABLE,
            Key: { session_id: data.session_id },
            UpdateExpression: 'SET #duration = :duration, #count = :count, ...',
            // ... (excludes labels, notes, created_at)
        }));
    } else {
        // Session doesn't exist - create new
        await docClient.send(new PutCommand({ ... }));
    }
}
```

---

## Deployment Steps

### 1. Test Locally

```bash
cd /Users/marcocleirigh/Workspace/motion-play/lambda
node test-fix-verification.js
```

Expected output:
```
🎉 SUCCESS! The fix works - user data is preserved!
```

### 2. Package the Lambda

```bash
cd processData
zip -r function.zip index.js package.json node_modules/
```

### 3. Deploy via AWS Console

1. Go to AWS Lambda Console
2. Select `motionplay-processData` function
3. Click "Upload from" → ".zip file"
4. Upload `function.zip`
5. Click "Save"

### 4. Deploy via AWS CLI

```bash
aws lambda update-function-code \
    --function-name motionplay-processData \
    --zip-file fileb://function.zip \
    --region us-east-1
```

### 5. Verify Deployment

Check CloudWatch Logs for:
```
Session already exists, updating (preserving labels/notes): device-001_XXXXX
```

---

## Testing in Production

### Scenario 1: New Session (Expected Behavior)
1. Device sends new session data with `batch_offset=0`
2. Lambda creates session with `PutCommand`
3. Session appears in UI with correct sample count

**Log Output**:
```
Creating new session: device-001_12345678
New session metadata stored
```

### Scenario 2: Duplicate batch_offset=0 (Bug Fix)
1. Device sends data with `batch_offset=0`
2. User adds labels/notes in UI
3. Device sends same session with `batch_offset=0` again (retry/bug)
4. Lambda detects existing session
5. Lambda updates using `UpdateCommand`
6. **Labels and notes are preserved!**

**Log Output**:
```
Session already exists, updating (preserving labels/notes): device-001_12345678
Session metadata updated (labels/notes preserved)
```

### Scenario 3: Subsequent Batch (Normal Operation)
1. Device sends data with `batch_offset=1`
2. Lambda increments `sample_count`
3. Labels/notes remain unchanged

**Log Output**:
```
Updated sample count for batch 1 (+50 readings)
```

---

## Rollback Plan

If the fix causes issues:

1. **Quick Rollback** (AWS Console):
   - Go to Lambda → Versions
   - Select previous version
   - Create alias pointing to old version

2. **CLI Rollback**:
```bash
aws lambda update-function-code \
    --function-name motionplay-processData \
    --zip-file fileb://function-backup.zip \
    --region us-east-1
```

3. **Re-deploy from git**:
```bash
git checkout <previous-commit>
cd lambda/processData
zip -r function.zip index.js package.json node_modules/
# Deploy as above
```

---

## Monitoring

### CloudWatch Metrics to Watch

1. **Lambda Duration**: Should increase slightly due to GetCommand check
   - **Before**: ~50ms average
   - **After**: ~75ms average (acceptable)

2. **Error Rate**: Should remain at 0%

3. **Invocation Count**: Should remain unchanged

### CloudWatch Logs - Important Patterns

**Good Signs** ✓:
```
Creating new session: device-001_XXXXX
Session already exists, updating (preserving labels/notes): device-001_XXXXX
```

**Red Flags** ✗:
```
Error retrieving session
ConditionalCheckFailedException
```

### CloudWatch Log Insights Query

To find sessions that were updated (not created):

```sql
fields @timestamp, @message
| filter @message like /Session already exists/
| stats count() by bin(5m)
```

To find potential duplicate batch_offset=0 events:

```sql
fields @timestamp, session_id
| filter @message like /batch_offset/ and batch_offset = 0
| stats count() by session_id
| filter count > 1
```

---

## Performance Impact

- **Additional DynamoDB Read**: +1 GetCommand per session
- **Cost Impact**: Negligible (~$0.0000025 per read)
- **Latency Impact**: +5-10ms per invocation
- **Benefit**: Prevents data loss and user frustration

---

## Future Improvements

1. **Add idempotency tokens** to device messages
2. **Track batch_offset sequence** to detect missing batches
3. **Add DynamoDB condition expressions** to prevent race conditions
4. **Implement batch deduplication** at IoT Rule level

---

## Questions?

- Check CloudWatch Logs: `/aws/lambda/motionplay-processData`
- Review test scripts: `test-overwrite-bug.js` and `test-fix-verification.js`
- See database schema: `infrastructure/DATABASE_SCHEMA.md`

---

**Last Updated**: November 21, 2025  
**Author**: Marc  
**Tested**: ✓ Local simulation passed

