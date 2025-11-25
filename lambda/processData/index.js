/**
 * Lambda Function: processData
 * 
 * Triggered by IoT Rule when device publishes sensor data.
 * Processes and stores data in DynamoDB.
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, BatchWriteCommand, UpdateCommand, GetCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';
const SENSOR_DATA_TABLE = process.env.SENSOR_DATA_TABLE || 'MotionPlaySensorData';

// Sanitize config object to prevent NaN values
function sanitizeConfig(config) {
    if (!config) return null;
    
    return {
        sample_rate_hz: Number.isFinite(config.sample_rate_hz) ? config.sample_rate_hz : 1000,
        led_current: config.led_current || "200mA",
        integration_time: config.integration_time || "1T",
        high_resolution: typeof config.high_resolution === 'boolean' ? config.high_resolution : true,
        read_ambient: typeof config.read_ambient === 'boolean' ? config.read_ambient : true,
        i2c_clock_khz: Number.isFinite(config.i2c_clock_khz) ? config.i2c_clock_khz : 400,
        actual_sample_rate_hz: Number.isFinite(config.actual_sample_rate_hz) ? config.actual_sample_rate_hz : 0
    };
}

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        // Parse incoming data from IoT Rule
        const data = event;
        
        // Validate required fields
        if (!data.session_id || !data.device_id || !data.start_timestamp) {
            throw new Error('Missing required fields');
        }
        
        // Safety limits to prevent runaway costs
        const MAX_SESSION_DURATION_MS = 35000; // 35 seconds (give 5s buffer beyond device limit)
        const MAX_BATCH_SIZE = 1000; // No batch should have more than 1000 readings
        const MAX_TOTAL_SAMPLES = 200000; // Absolute max samples per session
        
        // Validate session duration
        if (data.duration_ms && data.duration_ms > MAX_SESSION_DURATION_MS) {
            console.error(`Session duration ${data.duration_ms}ms exceeds maximum ${MAX_SESSION_DURATION_MS}ms`);
            throw new Error(`Session duration exceeds maximum allowed (${MAX_SESSION_DURATION_MS}ms)`);
        }
        
        // Validate batch size
        const readingsCount = data.readings ? data.readings.length : 0;
        if (readingsCount > MAX_BATCH_SIZE) {
            console.error(`Batch size ${readingsCount} exceeds maximum ${MAX_BATCH_SIZE}`);
            throw new Error(`Batch size exceeds maximum allowed (${MAX_BATCH_SIZE})`);
        }
        
        // Store or update session metadata
        // CRITICAL FIX: Check if session exists first to avoid overwriting user data (labels, notes)
        
        if (data.batch_offset === 0 || data.batch_offset === undefined) {
            // First batch: Check if session already exists
            const existingSessionResult = await docClient.send(new GetCommand({
                TableName: SESSIONS_TABLE,
                Key: { session_id: data.session_id }
            }));
            
            if (existingSessionResult.Item) {
                // Session exists - UPDATE ONLY, preserving user-editable fields
                console.log('Session already exists, updating (preserving labels/notes):', data.session_id);
                
                const updateExpressions = [];
                const expressionAttributeNames = {};
                const expressionAttributeValues = {};
                
                // Update system fields only (DO NOT touch labels, notes, created_at)
                updateExpressions.push('#end_timestamp = :end_timestamp');
                expressionAttributeNames['#end_timestamp'] = 'end_timestamp';
                expressionAttributeValues[':end_timestamp'] = new Date().toISOString();
                
                updateExpressions.push('#duration_ms = :duration_ms');
                expressionAttributeNames['#duration_ms'] = 'duration_ms';
                expressionAttributeValues[':duration_ms'] = data.duration_ms || 0;
                
                // Update start_timestamp if present (important for batch 0 arriving late)
                if (data.start_timestamp !== undefined && data.start_timestamp !== null) {
                    updateExpressions.push('#start_timestamp = :start_timestamp');
                    expressionAttributeNames['#start_timestamp'] = 'start_timestamp';
                    expressionAttributeValues[':start_timestamp'] = String(data.start_timestamp);
                }
                
                updateExpressions.push('#sample_count = :sample_count');
                expressionAttributeNames['#sample_count'] = 'sample_count';
                expressionAttributeValues[':sample_count'] = readingsCount;
                
                // Only update sensor config if provided (for first batch of NEW data)
                if (data.active_sensors || data.sensor_config) {
                    updateExpressions.push('#active_sensors = :active_sensors');
                    expressionAttributeNames['#active_sensors'] = 'active_sensors';
                    expressionAttributeValues[':active_sensors'] = data.active_sensors || data.sensor_config || [];
                }
                
                if (data.vcnl4040_config) {
                    updateExpressions.push('#vcnl4040_config = :vcnl4040_config');
                    expressionAttributeNames['#vcnl4040_config'] = 'vcnl4040_config';
                    expressionAttributeValues[':vcnl4040_config'] = data.vcnl4040_config;
                }
                
                await docClient.send(new UpdateCommand({
                    TableName: SESSIONS_TABLE,
                    Key: { session_id: data.session_id },
                    UpdateExpression: `SET ${updateExpressions.join(', ')}`,
                    ExpressionAttributeNames: expressionAttributeNames,
                    ExpressionAttributeValues: expressionAttributeValues
                }));
                
                console.log('Session metadata updated (labels/notes preserved)');
            } else {
                // Session does NOT exist - create new one
                console.log('Creating new session:', data.session_id);
                
                const sessionItem = {
                    session_id: data.session_id,
                    device_id: data.device_id,
                    start_timestamp: String(data.start_timestamp), // Convert to string for GSI
                    end_timestamp: new Date().toISOString(),
                    duration_ms: data.duration_ms || 0,
                    mode: data.mode || 'debug',
                    sample_count: readingsCount,
                    sample_rate: data.sample_rate || 1000,
                    labels: data.labels || [],
                    notes: data.notes || '',
                    created_at: Date.now(),
                    // Store both sensor status and VCNL4040 configuration
                    active_sensors: data.active_sensors || data.sensor_config || [],  // Backward compatible
                    vcnl4040_config: sanitizeConfig(data.vcnl4040_config) || {
                        sample_rate_hz: data.sample_rate || 1000,
                        led_current: "200mA",
                        integration_time: "1T",
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
            
            console.log('Updated sample count for batch ' + data.batch_offset + ' (+' + readingsCount + ' readings)');
        }
        
        // Store sensor readings in batches (DynamoDB batch write limit: 25 items)
        if (data.readings && data.readings.length > 0) {
            console.log(`Processing ${data.readings.length} readings for session ${data.session_id}`);
            console.log(`First reading sample:`, JSON.stringify(data.readings[0]));
            
            const batchSize = 25;
            const readings = data.readings;
            const startTimestamp = Number(data.start_timestamp); // Session start time in ms
            
            console.log(`Start timestamp: ${startTimestamp}, type: ${typeof startTimestamp}`);
            
            for (let i = 0; i < readings.length; i += batchSize) {
                const batch = readings.slice(i, i + batchSize);
                const putRequests = batch.map(reading => {
                    const absoluteTimestamp = reading.ts || reading.t;
                    // Calculate relative timestamp from session start
                    const relativeTimestamp = absoluteTimestamp - startTimestamp;
                    const position = reading.pos !== undefined ? reading.pos : reading.p;
                    
                    // Create composite numeric sort key: (timestamp * 10) + position
                    // This ensures uniqueness even when sensors share timestamps
                    // Example: timestamp=100, position=0 -> 1000
                    //          timestamp=100, position=1 -> 1001
                    const compositeKey = (relativeTimestamp * 10) + position;
                    
                    const item = {
                        session_id: data.session_id,
                        timestamp_offset: compositeKey, // Numeric composite key: 1000, 1001, etc.
                        timestamp_ms: relativeTimestamp, // Store base timestamp for queries
                        position: position, // Sensor array index (0-5)
                        pcb_id: reading.pcb || 0, // PCB board number (1-3)
                        side: reading.side || 0, // Sensor side (1=S1, 2=S2)
                        proximity: reading.prox || 0,
                        ambient: reading.amb || 0
                    };
                    
                    // Log first item for debugging
                    if (i === 0 && batch.indexOf(reading) === 0) {
                        console.log(`First item to store:`, JSON.stringify(item));
                    }
                    
                    return {
                        PutRequest: {
                            Item: item
                        }
                    };
                });
                
                // Write batch with automatic retry for unprocessed items
                let requestItems = {
                    [SENSOR_DATA_TABLE]: putRequests
                };
                let retryCount = 0;
                const maxRetries = 3;
                
                while (requestItems && Object.keys(requestItems).length > 0 && retryCount <= maxRetries) {
                    if (retryCount > 0) {
                        // Exponential backoff: 100ms, 200ms, 400ms
                        const delay = 100 * Math.pow(2, retryCount - 1);
                        console.log(`Retry ${retryCount} after ${delay}ms delay for batch ${i / batchSize + 1}`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                    
                    const batchWriteResult = await docClient.send(new BatchWriteCommand({
                        RequestItems: requestItems
                    }));
                    
                    // Check for unprocessed items
                    if (batchWriteResult.UnprocessedItems && 
                        batchWriteResult.UnprocessedItems[SENSOR_DATA_TABLE] && 
                        batchWriteResult.UnprocessedItems[SENSOR_DATA_TABLE].length > 0) {
                        
                        const unprocessedCount = batchWriteResult.UnprocessedItems[SENSOR_DATA_TABLE].length;
                        console.warn(`Batch ${i / batchSize + 1}: ${unprocessedCount} unprocessed items (attempt ${retryCount + 1})`);
                        
                        // Prepare for retry with only unprocessed items
                        requestItems = batchWriteResult.UnprocessedItems;
                        retryCount++;
                    } else {
                        // All items processed successfully
                        requestItems = null;
                        console.log(`Stored batch ${i / batchSize + 1} (${batch.length} readings) to table ${SENSOR_DATA_TABLE}`);
                    }
                }
                
                // Check if we exhausted retries
                if (requestItems && Object.keys(requestItems).length > 0) {
                    const failedCount = requestItems[SENSOR_DATA_TABLE]?.length || 0;
                    console.error(`FAILED: Batch ${i / batchSize + 1} still has ${failedCount} unprocessed items after ${maxRetries} retries`);
                    throw new Error(`Failed to write ${failedCount} items after ${maxRetries} retries`);
                }
            }
        } else {
            console.log(`No readings to store. data.readings exists: ${!!data.readings}, length: ${data.readings?.length || 0}`);
        }
        
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: 'Data processed successfully',
                session_id: data.session_id,
                readings_count: data.readings ? data.readings.length : 0
            })
        };
        
    } catch (error) {
        console.error('Error processing data:', error);
        throw error;
    }
};

