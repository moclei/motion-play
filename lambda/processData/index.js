/**
 * Lambda Function: processData
 * 
 * Triggered by IoT Rule when device publishes sensor data.
 * Processes and stores data in DynamoDB.
 * 
 * Supports two session types:
 * - "proximity" (default): Traditional polling-based sensor readings
 * - "interrupt": Interrupt-based detection events
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, BatchWriteCommand, UpdateCommand, GetCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';
const SENSOR_DATA_TABLE = process.env.SENSOR_DATA_TABLE || 'MotionPlaySensorData';
const INTERRUPT_EVENTS_TABLE = process.env.INTERRUPT_EVENTS_TABLE || 'MotionPlayInterruptEvents';

// Sanitize config object to prevent NaN values
function sanitizeConfig(config) {
    if (!config) return null;
    
    // Validate multi_pulse is a valid value
    const validMultiPulse = ["1", "2", "4", "8"];
    const multiPulse = validMultiPulse.includes(config.multi_pulse) ? config.multi_pulse : "1";
    
    return {
        sample_rate_hz: Number.isFinite(config.sample_rate_hz) ? config.sample_rate_hz : 1000,
        led_current: config.led_current || "200mA",
        integration_time: config.integration_time || "2T",
        duty_cycle: config.duty_cycle || "1/40",
        high_resolution: typeof config.high_resolution === 'boolean' ? config.high_resolution : true,
        read_ambient: typeof config.read_ambient === 'boolean' ? config.read_ambient : true,
        i2c_clock_khz: Number.isFinite(config.i2c_clock_khz) ? config.i2c_clock_khz : 400,
        multi_pulse: multiPulse,
        actual_sample_rate_hz: Number.isFinite(config.actual_sample_rate_hz) ? config.actual_sample_rate_hz : 0
    };
}

// Sanitize interrupt config (calibration-based approach)
function sanitizeInterruptConfig(config) {
    if (!config) return null;
    
    return {
        threshold_margin: Number.isFinite(config.threshold_margin) ? config.threshold_margin : 10,
        hysteresis: Number.isFinite(config.hysteresis) ? config.hysteresis : 5,
        integration_time: Number.isFinite(config.integration_time) ? config.integration_time : 8,
        multi_pulse: Number.isFinite(config.multi_pulse) ? config.multi_pulse : 8,
        persistence: Number.isFinite(config.persistence) ? config.persistence : 1,
        smart_persistence: typeof config.smart_persistence === 'boolean' ? config.smart_persistence : true,
        mode: config.mode || "normal",
        led_current: config.led_current || "200mA"
    };
}

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const data = event;
        
        // Validate required fields
        if (!data.session_id || !data.device_id || !data.start_timestamp) {
            throw new Error('Missing required fields');
        }
        
        // Determine session type (default to 'proximity' for backwards compatibility)
        const sessionType = data.session_type || 'proximity';
        console.log(`Processing ${sessionType} session: ${data.session_id}`);
        
        if (sessionType === 'interrupt') {
            return await processInterruptSession(data);
        } else {
            return await processProximitySession(data);
        }
        
    } catch (error) {
        console.error('Error processing data:', error);
        throw error;
    }
};

// ============================================================================
// Interrupt Session Processing
// ============================================================================

async function processInterruptSession(data) {
    const eventsCount = data.events ? data.events.length : 0;
    
    // Safety limits
    const MAX_SESSION_DURATION_MS = 35000;
    const MAX_BATCH_SIZE = 500;
    
    if (data.duration_ms && data.duration_ms > MAX_SESSION_DURATION_MS) {
            throw new Error(`Session duration exceeds maximum allowed (${MAX_SESSION_DURATION_MS}ms)`);
        }
        
    if (eventsCount > MAX_BATCH_SIZE) {
            throw new Error(`Batch size exceeds maximum allowed (${MAX_BATCH_SIZE})`);
        }
        
        // Store or update session metadata
    if (data.batch_offset === 0 || data.batch_offset === undefined) {
        // First batch: Check if session exists
        const existingSession = await docClient.send(new GetCommand({
            TableName: SESSIONS_TABLE,
            Key: { session_id: data.session_id }
        }));
        
        if (existingSession.Item) {
            // Update existing session
            console.log('Updating existing interrupt session:', data.session_id);
            
            await docClient.send(new UpdateCommand({
                TableName: SESSIONS_TABLE,
                Key: { session_id: data.session_id },
                UpdateExpression: `SET 
                    #session_type = :session_type,
                    #end_timestamp = :end_timestamp,
                    #duration_ms = :duration_ms,
                    #event_count = :event_count,
                    #interrupt_config = :interrupt_config`,
                ExpressionAttributeNames: {
                    '#session_type': 'session_type',
                    '#end_timestamp': 'end_timestamp',
                    '#duration_ms': 'duration_ms',
                    '#event_count': 'event_count',
                    '#interrupt_config': 'interrupt_config'
                },
                ExpressionAttributeValues: {
                    ':session_type': 'interrupt',
                    ':end_timestamp': new Date().toISOString(),
                    ':duration_ms': data.duration_ms || 0,
                    ':event_count': eventsCount,
                    ':interrupt_config': sanitizeInterruptConfig(data.interrupt_config)
                }
            }));
        } else {
            // Create new interrupt session
            console.log('Creating new interrupt session:', data.session_id);
            
            const sessionItem = {
                session_id: data.session_id,
                device_id: data.device_id,
                session_type: 'interrupt',
                start_timestamp: String(data.start_timestamp),
                end_timestamp: new Date().toISOString(),
                duration_ms: data.duration_ms || 0,
                mode: 'interrupt_debug',
                event_count: eventsCount,
                labels: [],
                notes: '',
                created_at: Date.now(),
                interrupt_config: sanitizeInterruptConfig(data.interrupt_config)
            };
            
            await docClient.send(new PutCommand({
                TableName: SESSIONS_TABLE,
                Item: sessionItem
            }));
        }
        
        console.log('Interrupt session metadata stored');
    } else {
        // Subsequent batches: Increment event count
        await docClient.send(new UpdateCommand({
            TableName: SESSIONS_TABLE,
            Key: { session_id: data.session_id },
            UpdateExpression: 'ADD event_count :count',
            ExpressionAttributeValues: {
                ':count': eventsCount
            }
        }));
        
        console.log(`Updated event count for batch ${data.batch_offset} (+${eventsCount} events)`);
    }
    
    // Store interrupt events
    if (data.events && data.events.length > 0) {
        console.log(`Processing ${data.events.length} interrupt events for session ${data.session_id}`);
        
        const batchSize = 25;
        const events = data.events;
        const batchOffset = data.batch_offset || 0;
        
        for (let i = 0; i < events.length; i += batchSize) {
            const batch = events.slice(i, i + batchSize);
            const putRequests = batch.map((evt, idx) => {
                // Create unique sort key: combine batch offset, batch index, and event index
                // This ensures uniqueness even with multiple batches
                const eventIndex = batchOffset + i + idx;
                const compositeKey = eventIndex;  // Simple incrementing index
                
                return {
                    PutRequest: {
                        Item: {
                            session_id: data.session_id,
                            event_index: compositeKey,
                            timestamp_us: evt.ts,
                            board_id: evt.board,
                            sensor_position: evt.sensor,
                            event_type: evt.type,  // "close" or "away"
                            raw_flags: evt.flags || 0
                        }
                    }
                };
            });
            
            // Write batch with retry
            let requestItems = { [INTERRUPT_EVENTS_TABLE]: putRequests };
            let retryCount = 0;
            const maxRetries = 3;
            
            while (requestItems && Object.keys(requestItems).length > 0 && retryCount <= maxRetries) {
                if (retryCount > 0) {
                    const delay = 100 * Math.pow(2, retryCount - 1);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
                
                try {
                    const result = await docClient.send(new BatchWriteCommand({
                        RequestItems: requestItems
                    }));
                    
                    if (result.UnprocessedItems && 
                        result.UnprocessedItems[INTERRUPT_EVENTS_TABLE]?.length > 0) {
                        requestItems = result.UnprocessedItems;
                        retryCount++;
                    } else {
                        requestItems = null;
                        console.log(`Stored interrupt batch ${Math.floor(i / batchSize) + 1}`);
                    }
                } catch (err) {
                    console.error(`Batch write error:`, err);
                    retryCount++;
                    if (retryCount > maxRetries) throw err;
                }
            }
        }
    }
    
    return {
        statusCode: 200,
        body: JSON.stringify({
            message: 'Interrupt session processed successfully',
            session_id: data.session_id,
            events_count: eventsCount
        })
    };
}

// ============================================================================
// Proximity Session Processing (existing logic)
// ============================================================================

async function processProximitySession(data) {
    // Safety limits to prevent runaway costs
    const MAX_SESSION_DURATION_MS = 35000;
    const MAX_BATCH_SIZE = 1000;
    
    const readingsCount = data.readings ? data.readings.length : 0;
    
    if (data.duration_ms && data.duration_ms > MAX_SESSION_DURATION_MS) {
        throw new Error(`Session duration exceeds maximum allowed (${MAX_SESSION_DURATION_MS}ms)`);
    }
    
    if (readingsCount > MAX_BATCH_SIZE) {
        throw new Error(`Batch size exceeds maximum allowed (${MAX_BATCH_SIZE})`);
    }
    
    // Store or update session metadata
    if (data.batch_offset === 0 || data.batch_offset === undefined) {
        const existingSessionResult = await docClient.send(new GetCommand({
            TableName: SESSIONS_TABLE,
                Key: { session_id: data.session_id }
            }));
            
            if (existingSessionResult.Item) {
            // Session exists - UPDATE
                const existingSession = existingSessionResult.Item;
                const isSkeletonSession = !existingSession.device_id || !existingSession.created_at;
                
            console.log('Session already exists, updating:', data.session_id);
                
                const updateExpressions = [];
                const expressionAttributeNames = {};
                const expressionAttributeValues = {};
                
                updateExpressions.push('#end_timestamp = :end_timestamp');
                expressionAttributeNames['#end_timestamp'] = 'end_timestamp';
                expressionAttributeValues[':end_timestamp'] = new Date().toISOString();
                
                updateExpressions.push('#duration_ms = :duration_ms');
                expressionAttributeNames['#duration_ms'] = 'duration_ms';
                expressionAttributeValues[':duration_ms'] = data.duration_ms || 0;
                
                if (data.start_timestamp !== undefined && data.start_timestamp !== null) {
                    updateExpressions.push('#start_timestamp = :start_timestamp');
                    expressionAttributeNames['#start_timestamp'] = 'start_timestamp';
                    expressionAttributeValues[':start_timestamp'] = String(data.start_timestamp);
                }
                
                updateExpressions.push('#sample_count = :sample_count');
                expressionAttributeNames['#sample_count'] = 'sample_count';
                expressionAttributeValues[':sample_count'] = readingsCount;
                
            // Ensure session_type is set
            updateExpressions.push('#session_type = :session_type');
            expressionAttributeNames['#session_type'] = 'session_type';
            expressionAttributeValues[':session_type'] = 'proximity';
            
                if (isSkeletonSession) {
                    updateExpressions.push('#device_id = :device_id');
                    expressionAttributeNames['#device_id'] = 'device_id';
                    expressionAttributeValues[':device_id'] = data.device_id;
                    
                    updateExpressions.push('#mode = :mode');
                    expressionAttributeNames['#mode'] = 'mode';
                    expressionAttributeValues[':mode'] = data.mode || 'debug';
                    
                    updateExpressions.push('#sample_rate = :sample_rate');
                    expressionAttributeNames['#sample_rate'] = 'sample_rate';
                    expressionAttributeValues[':sample_rate'] = data.sample_rate || 1000;
                    
                    updateExpressions.push('#created_at = :created_at');
                    expressionAttributeNames['#created_at'] = 'created_at';
                    expressionAttributeValues[':created_at'] = Date.now();
                    
                    updateExpressions.push('#labels = :labels');
                    expressionAttributeNames['#labels'] = 'labels';
                    expressionAttributeValues[':labels'] = data.labels || [];
                    
                    updateExpressions.push('#notes = :notes');
                    expressionAttributeNames['#notes'] = 'notes';
                    expressionAttributeValues[':notes'] = data.notes || '';
                }
                
                if (data.active_sensors || data.sensor_config) {
                    updateExpressions.push('#active_sensors = :active_sensors');
                    expressionAttributeNames['#active_sensors'] = 'active_sensors';
                    expressionAttributeValues[':active_sensors'] = data.active_sensors || data.sensor_config || [];
                }
                
                if (data.vcnl4040_config) {
                    updateExpressions.push('#vcnl4040_config = :vcnl4040_config');
                    expressionAttributeNames['#vcnl4040_config'] = 'vcnl4040_config';
                    expressionAttributeValues[':vcnl4040_config'] = sanitizeConfig(data.vcnl4040_config);
                }
                
                await docClient.send(new UpdateCommand({
                    TableName: SESSIONS_TABLE,
                    Key: { session_id: data.session_id },
                    UpdateExpression: `SET ${updateExpressions.join(', ')}`,
                    ExpressionAttributeNames: expressionAttributeNames,
                    ExpressionAttributeValues: expressionAttributeValues
                }));
                
            console.log('Session metadata updated');
            } else {
            // Create new session
            console.log('Creating new proximity session:', data.session_id);
                
                const sessionItem = {
                    session_id: data.session_id,
                    device_id: data.device_id,
                session_type: 'proximity',
                start_timestamp: String(data.start_timestamp),
                    end_timestamp: new Date().toISOString(),
                    duration_ms: data.duration_ms || 0,
                    mode: data.mode || 'debug',
                    sample_count: readingsCount,
                    sample_rate: data.sample_rate || 1000,
                    labels: data.labels || [],
                    notes: data.notes || '',
                    created_at: Date.now(),
                active_sensors: data.active_sensors || data.sensor_config || [],
                    vcnl4040_config: sanitizeConfig(data.vcnl4040_config) || {
                        sample_rate_hz: data.sample_rate || 1000,
                        led_current: "200mA",
                        integration_time: "2T",
                        duty_cycle: "1/40",
                        high_resolution: true,
                        read_ambient: true,
                        i2c_clock_khz: 400,
                        actual_sample_rate_hz: 0
                    }
                };
                
                await docClient.send(new PutCommand({
                    TableName: SESSIONS_TABLE,
                    Item: sessionItem
                }));
                
                console.log('New session metadata stored');
            }
        } else {
            // Subsequent batches: Increment the sample_count
            await docClient.send(new UpdateCommand({
                TableName: SESSIONS_TABLE,
                Key: { session_id: data.session_id },
                UpdateExpression: 'ADD sample_count :count',
                ExpressionAttributeValues: {
                    ':count': readingsCount
                }
            }));
            
        console.log(`Updated sample count for batch ${data.batch_offset} (+${readingsCount} readings)`);
        }
        
    // Store sensor readings
        if (data.readings && data.readings.length > 0) {
            console.log(`Processing ${data.readings.length} readings for session ${data.session_id}`);
            
            const batchSize = 25;
            const readings = data.readings;
        const startTimestamp = Number(data.start_timestamp);
            
            for (let i = 0; i < readings.length; i += batchSize) {
                const batch = readings.slice(i, i + batchSize);
                const putRequests = batch.map(reading => {
                    const absoluteTimestamp = reading.ts || reading.t;
                    const relativeTimestamp = absoluteTimestamp - startTimestamp;
                    const position = reading.pos !== undefined ? reading.pos : reading.p;
                    const compositeKey = (relativeTimestamp * 10) + position;
                    
                return {
                    PutRequest: {
                        Item: {
                        session_id: data.session_id,
                            timestamp_offset: compositeKey,
                            timestamp_ms: relativeTimestamp,
                            position: position,
                            pcb_id: reading.pcb || 0,
                            side: reading.side || 0,
                        proximity: reading.prox || 0,
                        ambient: reading.amb || 0
                        }
                        }
                    };
                });
                
            let requestItems = { [SENSOR_DATA_TABLE]: putRequests };
                let retryCount = 0;
                const maxRetries = 3;
                
                while (requestItems && Object.keys(requestItems).length > 0 && retryCount <= maxRetries) {
                    if (retryCount > 0) {
                        const delay = 100 * Math.pow(2, retryCount - 1);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                    
                    const batchWriteResult = await docClient.send(new BatchWriteCommand({
                        RequestItems: requestItems
                    }));
                    
                    if (batchWriteResult.UnprocessedItems && 
                    batchWriteResult.UnprocessedItems[SENSOR_DATA_TABLE]?.length > 0) {
                        requestItems = batchWriteResult.UnprocessedItems;
                        retryCount++;
                    } else {
                        requestItems = null;
                    console.log(`Stored batch ${Math.floor(i / batchSize) + 1}`);
                    }
                }
                
                if (requestItems && Object.keys(requestItems).length > 0) {
                    const failedCount = requestItems[SENSOR_DATA_TABLE]?.length || 0;
                    throw new Error(`Failed to write ${failedCount} items after ${maxRetries} retries`);
            }
        }
        }
        
        return {
            statusCode: 200,
            body: JSON.stringify({
            message: 'Proximity session processed successfully',
                session_id: data.session_id,
            readings_count: readingsCount
            })
        };
    }
