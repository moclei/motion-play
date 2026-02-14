/**
 * Lambda Function: getDeviceConfig
 * 
 * Retrieves device sensor configuration from MotionPlayDevices table.
 * Triggered by API Gateway GET /device/{device_id}/config
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, GetCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const DEVICES_TABLE = process.env.DEVICES_TABLE || 'MotionPlayDevices';

// Default sensor configuration
const DEFAULT_CONFIG = {
    // Primary sensor mode
    sensor_mode: "polling",  // "polling" or "interrupt"
    // Polling mode settings
    sample_rate_hz: 1000,
    led_current: "200mA",
    integration_time: "2T",
    duty_cycle: "1/40",
    high_resolution: true,
    read_ambient: true,
    i2c_clock_khz: 400,
    multi_pulse: "1",
    // Interrupt mode settings (calibration-based)
    interrupt_threshold_margin: 10,    // Trigger at 10+ counts above baseline
    interrupt_hysteresis: 5,           // Gap between high and low thresholds
    interrupt_integration_time: 8,     // 8T for maximum range
    interrupt_multi_pulse: 8,          // 8 pulses for maximum signal
    interrupt_persistence: 1,
    interrupt_smart_persistence: true,
    interrupt_mode: "normal"
};

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const deviceId = event.pathParameters?.device_id || 'motionplay-device-002';
        
        console.log(`Fetching config for device: ${deviceId}`);
        
        // Query device record
        const result = await docClient.send(new GetCommand({
            TableName: DEVICES_TABLE,
            Key: {
                device_id: deviceId
            }
        }));
        
        let sensorConfig = DEFAULT_CONFIG;
        let configUpdatedAt = null;
        
        // If device exists and has config, use it
        if (result.Item && result.Item.sensor_config) {
            sensorConfig = result.Item.sensor_config;
            configUpdatedAt = result.Item.config_updated_at || null;
            console.log('Found existing config in database');
        } else {
            console.log('No config found, returning defaults');
        }
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                device_id: deviceId,
                sensor_config: sensorConfig,
                config_updated_at: configUpdatedAt
            })
        };
        
    } catch (error) {
        console.error('Error retrieving device config:', error);
        return {
            statusCode: 500,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({ error: error.message })
        };
    }
};

