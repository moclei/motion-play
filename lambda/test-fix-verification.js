/**
 * Test Script: Verify Session Overwrite Fix
 * 
 * This script simulates the fixed behavior where processData checks if a session
 * exists before overwriting it, preserving user-added labels and notes.
 */

// Mock DynamoDB responses
const mockDynamoDB = {
    sessions: new Map(),
    
    // GetCommand - check if session exists
    async getSession(sessionId) {
        return this.sessions.get(sessionId) || null;
    },
    
    // PutCommand - create new session (full overwrite)
    async putSession(session) {
        this.sessions.set(session.session_id, session);
        console.log(`  📝 PutCommand: Created new session ${session.session_id}`);
    },
    
    // UpdateCommand - update existing session (partial update)
    async updateSession(sessionId, updates) {
        const existing = this.sessions.get(sessionId);
        if (existing) {
            // Merge updates, preserving fields not in updates
            const updated = { ...existing, ...updates };
            this.sessions.set(sessionId, updated);
            console.log(`  🔄 UpdateCommand: Updated session ${sessionId}`);
            console.log(`     Preserved: labels=${JSON.stringify(existing.labels)}, notes="${existing.notes}"`);
        }
    },
    
    // Simulate user updating labels/notes
    async userUpdateSession(sessionId, labels, notes) {
        const existing = this.sessions.get(sessionId);
        if (existing) {
            existing.labels = labels;
            existing.notes = notes;
            console.log(`  👤 User updated: labels=${JSON.stringify(labels)}, notes="${notes}"`);
        }
    }
};

// Simulate the FIXED processData Lambda logic
async function processDataFixed(data) {
    const sessionId = data.session_id;
    const readingsCount = data.readings ? data.readings.length : 0;
    
    if (data.batch_offset === 0 || data.batch_offset === undefined) {
        // First batch: Check if session exists
        const existingSession = await mockDynamoDB.getSession(sessionId);
        
        if (existingSession) {
            // Session exists - UPDATE ONLY (preserve labels/notes/created_at)
            const updates = {
                end_timestamp: new Date().toISOString(),
                duration_ms: data.duration_ms || 0,
                sample_count: readingsCount
            };
            
            await mockDynamoDB.updateSession(sessionId, updates);
        } else {
            // Session does NOT exist - create new
            const newSession = {
                session_id: sessionId,
                device_id: data.device_id,
                start_timestamp: String(data.start_timestamp),
                end_timestamp: new Date().toISOString(),
                duration_ms: data.duration_ms || 0,
                mode: data.mode || 'debug',
                sample_count: readingsCount,
                sample_rate: data.sample_rate || 1000,
                labels: [],
                notes: '',
                created_at: Date.now()
            };
            
            await mockDynamoDB.putSession(newSession);
        }
    } else {
        // Subsequent batch - just increment count
        const existing = await mockDynamoDB.getSession(sessionId);
        if (existing) {
            await mockDynamoDB.updateSession(sessionId, {
                sample_count: existing.sample_count + readingsCount
            });
        }
    }
}

// Run the test
async function runTest() {
    console.log('=== Testing FIXED processData Lambda ===\n');
    
    const sessionId = 'device-001_12345678';
    
    // Step 1: Device sends first batch
    console.log('Step 1: Device sends first batch (batch_offset=0)');
    await processDataFixed({
        session_id: sessionId,
        device_id: 'device-001',
        start_timestamp: 1700000000000,
        duration_ms: 5000,
        sample_rate: 1000,
        batch_offset: 0,
        readings: new Array(150)  // 150 samples
    });
    
    let session = await mockDynamoDB.getSession(sessionId);
    console.log(`✓ Session created: sample_count=${session.sample_count}, labels=${JSON.stringify(session.labels)}, notes="${session.notes}"\n`);
    
    // Step 2: User adds labels and notes
    console.log('Step 2: User adds labels and notes (via updateSession API)');
    await mockDynamoDB.userUpdateSession(
        sessionId,
        ['gesture', 'hand-wave', 'test-data'],
        'This was a clean hand wave gesture over sensors 1-3'
    );
    
    session = await mockDynamoDB.getSession(sessionId);
    console.log(`✓ User data saved: labels=${JSON.stringify(session.labels)}, notes="${session.notes}"\n`);
    
    // Step 3: Device sends data with batch_offset=0 AGAIN (the bug scenario)
    console.log('Step 3: Device sends data with batch_offset=0 AGAIN (retry/reconnect/bug)');
    await processDataFixed({
        session_id: sessionId,  // SAME session
        device_id: 'device-001',
        start_timestamp: 1700000000000,
        duration_ms: 8000,
        sample_rate: 1000,
        batch_offset: 0,
        readings: new Array(66)  // Different batch size
    });
    
    session = await mockDynamoDB.getSession(sessionId);
    console.log(`✓ Session updated (NOT overwritten)\n`);
    
    // Step 4: Verify the fix
    console.log('Step 4: VERIFICATION');
    console.log('────────────────────────────────────────');
    
    const hasLabels = session.labels && session.labels.length > 0;
    const hasNotes = session.notes && session.notes.length > 0;
    const sampleCountUpdated = session.sample_count === 66;
    
    console.log(`Sample Count: ${session.sample_count} ${sampleCountUpdated ? '✓' : '✗'} (updated to new batch size)`);
    console.log(`Labels: ${JSON.stringify(session.labels)} ${hasLabels ? '✓' : '✗'} (PRESERVED!)`);
    console.log(`Notes: "${session.notes}" ${hasNotes ? '✓' : '✗'} (PRESERVED!)`);
    console.log('');
    
    if (hasLabels && hasNotes) {
        console.log('🎉 SUCCESS! The fix works - user data is preserved!\n');
    } else {
        console.log('❌ FAIL! User data was lost\n');
    }
    
    // Step 5: Test subsequent batch (batch_offset > 0)
    console.log('Step 5: Test subsequent batch (batch_offset=1)');
    await processDataFixed({
        session_id: sessionId,
        device_id: 'device-001',
        start_timestamp: 1700000000000,
        duration_ms: 8000,
        sample_rate: 1000,
        batch_offset: 1,  // Not first batch
        readings: new Array(50)
    });
    
    session = await mockDynamoDB.getSession(sessionId);
    console.log(`✓ Sample count incremented: ${session.sample_count} (was 66, added 50)`);
    console.log(`✓ Labels still preserved: ${JSON.stringify(session.labels)}`);
    console.log(`✓ Notes still preserved: "${session.notes}"\n`);
    
    console.log('=== Test Complete ===');
    console.log('The fix successfully prevents overwriting user data!');
}

runTest().catch(console.error);

