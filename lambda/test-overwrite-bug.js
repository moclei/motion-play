/**
 * Test Script: Diagnose Session Overwrite Bug
 * 
 * This script simulates the bug where processData overwrites session metadata
 * when it receives data with batch_offset=0 multiple times.
 */

// Simulate what happens when you:
// 1. Create a session (batch 0)
// 2. Update it with labels/notes via updateSession
// 3. Receive another batch with batch_offset=0 (the bug)

const simulateSessionLifecycle = () => {
    console.log('=== Simulating Session Overwrite Bug ===\n');
    
    // Step 1: Device sends first batch (batch_offset=0)
    const initialSession = {
        session_id: 'device-001_12345678',
        device_id: 'device-001',
        start_timestamp: '1700000000000',
        duration_ms: 5000,
        sample_count: 150,  // Initial batch has 150 samples
        sample_rate: 1000,
        labels: [],
        notes: '',
        created_at: Date.now()
    };
    
    console.log('Step 1: Initial session created by processData (batch_offset=0)');
    console.log('Sample Count:', initialSession.sample_count);
    console.log('Labels:', initialSession.labels);
    console.log('Notes:', initialSession.notes);
    console.log('Created At:', new Date(initialSession.created_at).toISOString());
    console.log('');
    
    // Wait a bit...
    const userEditTime = Date.now() + 10000; // 10 seconds later
    
    // Step 2: User adds labels and notes via updateSession
    const updatedSession = {
        ...initialSession,
        labels: ['gesture', 'hand-wave', 'test-data'],
        notes: 'This was a clean hand wave gesture over sensors 1-3'
    };
    
    console.log('Step 2: User updates session via updateSession Lambda');
    console.log('Sample Count:', updatedSession.sample_count);
    console.log('Labels:', updatedSession.labels);
    console.log('Notes:', updatedSession.notes);
    console.log('Created At:', new Date(updatedSession.created_at).toISOString());
    console.log('');
    
    // Wait some more...
    const bugTriggerTime = Date.now() + 20000; // 20 seconds after initial
    
    // Step 3: BUG TRIGGERS - Device sends data with batch_offset=0 again
    // This could happen due to:
    // - Device retry/reconnection
    // - Firmware bug sending batch_offset=0 for subsequent batches
    // - Multiple batch_offset=0 messages for same session
    const buggedSession = {
        session_id: 'device-001_12345678',  // SAME session_id
        device_id: 'device-001',
        start_timestamp: '1700000000000',
        duration_ms: 8000,
        sample_count: 66,  // New batch has 66 samples (THIS IS THE "66" BUG!)
        sample_rate: 1000,
        labels: [],  // RESET TO EMPTY!
        notes: '',   // RESET TO EMPTY!
        created_at: bugTriggerTime  // NEW TIMESTAMP - causes re-ordering!
    };
    
    console.log('Step 3: BUG TRIGGERED - processData receives batch_offset=0 AGAIN');
    console.log('PutCommand OVERWRITES the entire session:');
    console.log('Sample Count:', buggedSession.sample_count, '(CHANGED from 150 to 66!)');
    console.log('Labels:', buggedSession.labels, '(LOST!)');
    console.log('Notes:', buggedSession.notes, '(LOST!)');
    console.log('Created At:', new Date(buggedSession.created_at).toISOString(), '(CHANGED - causes re-ordering!)');
    console.log('');
    
    console.log('=== RESULT ===');
    console.log('✗ All user-added labels disappeared');
    console.log('✗ All user-added notes disappeared');
    console.log('✗ Sample count changed from 150 to 66');
    console.log('✗ Created timestamp changed, causing session list re-ordering');
    console.log('');
    console.log('This explains exactly what you\'re seeing in the UI!');
};

simulateSessionLifecycle();

console.log('\n=== How to Diagnose ===');
console.log('1. Check AWS CloudWatch logs for processData Lambda');
console.log('   Look for: Multiple "Session metadata stored" logs with same session_id');
console.log('2. Search for pattern: "Session metadata stored: device-001_XXXXX" appearing twice');
console.log('3. Check device firmware - is it sending batch_offset=0 multiple times?');
console.log('4. Enable debug logging in processData to log every incoming event');

console.log('\n=== Potential Root Causes ===');
console.log('A) Device firmware bug: sending batch_offset=0 for multiple batches');
console.log('B) Device retry logic: resending data with batch_offset=0');
console.log('C) Network issues: causing duplicate message delivery');
console.log('D) Session lifecycle: device restarting same session with batch_offset=0');

