/**
 * Lambda Function: processData
 * 
 * Triggered by IoT Rule when device publishes sensor data.
 * Processes and stores data in DynamoDB.
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, BatchWriteCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';
const SENSOR_DATA_TABLE = process.env.SENSOR_DATA_TABLE || 'MotionPlaySensorData';

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        // Parse incoming data from IoT Rule
        const data = event;
        
        // Validate required fields
        if (!data.session_id || !data.device_id || !data.start_timestamp) {
            throw new Error('Missing required fields');
        }
        
        // Store session metadata
        const sessionItem = {
            session_id: data.session_id,
            device_id: data.device_id,
            start_timestamp: String(data.start_timestamp), // Convert to string for GSI
            end_timestamp: new Date().toISOString(),
            duration_ms: data.duration_ms || 0,
            mode: data.mode || 'debug',
            sample_count: data.readings ? data.readings.length : 0,
            sample_rate: data.sample_rate || 1000,
            labels: data.labels || [],
            notes: data.notes || '',
            created_at: Date.now(),
            // Store both sensor status and VCNL4040 configuration
            active_sensors: data.active_sensors || data.sensor_config || [],  // Backward compatible
            vcnl4040_config: data.vcnl4040_config || {
                sample_rate_hz: data.sample_rate || 1000,
                led_current: "200mA",
                integration_time: "1T",
                high_resolution: true
            }
        };
        
        await docClient.send(new PutCommand({
            TableName: SESSIONS_TABLE,
            Item: sessionItem
        }));
        
        console.log('Session metadata stored:', data.session_id);
        
        // Store sensor readings in batches (DynamoDB batch write limit: 25 items)
        if (data.readings && data.readings.length > 0) {
            const batchSize = 25;
            const readings = data.readings;
            
            for (let i = 0; i < readings.length; i += batchSize) {
                const batch = readings.slice(i, i + batchSize);
                const putRequests = batch.map(reading => ({
                    PutRequest: {
                        Item: {
                            session_id: data.session_id,
                            timestamp_offset: reading.ts || reading.t, // Sort key - DynamoDB expects this name
                            position: reading.pos || reading.p, // Sensor array index (0-5)
                            pcb_id: reading.pcb, // PCB board number (1-3)
                            side: reading.side, // Sensor side (1=S1, 2=S2)
                            proximity: reading.prox,
                            ambient: reading.amb
                        }
                    }
                }));
                
                await docClient.send(new BatchWriteCommand({
                    RequestItems: {
                        [SENSOR_DATA_TABLE]: putRequests
                    }
                }));
                
                console.log(`Stored batch ${i / batchSize + 1} (${batch.length} readings)`);
            }
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

