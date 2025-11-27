/**
 * Lambda Function: updateDeviceConfig
 * 
 * Updates device sensor configuration in MotionPlayDevices table.
 * Also sends configure_sensors command to device via MQTT.
 * Triggered by API Gateway PUT /device/{device_id}/config
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, UpdateCommand, GetCommand } = require('@aws-sdk/lib-dynamodb');
const { IoTDataPlaneClient, PublishCommand } = require('@aws-sdk/client-iot-data-plane');

const dynamoClient = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(dynamoClient);
const iotClient = new IoTDataPlaneClient({ region: process.env.AWS_REGION });

const DEVICES_TABLE = process.env.DEVICES_TABLE || 'MotionPlayDevices';

// Validate and sanitize config
function sanitizeConfig(config) {
    if (!config) {
        throw new Error('sensor_config is required');
    }
    
    return {
        sample_rate_hz: Number.isFinite(config.sample_rate_hz) ? config.sample_rate_hz : 1000,
        led_current: config.led_current || "200mA",
        integration_time: config.integration_time || "2T",
        duty_cycle: config.duty_cycle || "1/40",
        high_resolution: typeof config.high_resolution === 'boolean' ? config.high_resolution : true,
        read_ambient: typeof config.read_ambient === 'boolean' ? config.read_ambient : true,
        i2c_clock_khz: Number.isFinite(config.i2c_clock_khz) ? config.i2c_clock_khz : 400
    };
}

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const deviceId = event.pathParameters?.device_id || 'motionplay-device-001';
        const body = JSON.parse(event.body || '{}');
        
        if (!body.sensor_config) {
            return {
                statusCode: 400,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({ error: 'sensor_config is required' })
            };
        }
        
        // Sanitize config
        const sensorConfig = sanitizeConfig(body.sensor_config);
        const timestamp = Date.now();
        
        console.log(`Updating config for device: ${deviceId}`);
        console.log('New config:', JSON.stringify(sensorConfig, null, 2));
        
        // Update device record in DynamoDB
        await docClient.send(new UpdateCommand({
            TableName: DEVICES_TABLE,
            Key: {
                device_id: deviceId
            },
            UpdateExpression: 'SET sensor_config = :config, config_updated_at = :timestamp, last_seen = :timestamp',
            ExpressionAttributeValues: {
                ':config': sensorConfig,
                ':timestamp': timestamp
            }
        }));
        
        console.log('Config saved to DynamoDB');
        
        // Send MQTT command to device
        const mqttPayload = {
            command: 'configure_sensors',
            sensor_config: {
                sample_rate: sensorConfig.sample_rate_hz,
                led_current: sensorConfig.led_current,
                integration_time: sensorConfig.integration_time,
                duty_cycle: sensorConfig.duty_cycle,
                high_resolution: sensorConfig.high_resolution,
                read_ambient: sensorConfig.read_ambient
            },
            timestamp: new Date().toISOString()
        };
        
        const topic = `motionplay/${deviceId}/commands`;
        
        await iotClient.send(new PublishCommand({
            topic: topic,
            qos: 1,
            payload: Buffer.from(JSON.stringify(mqttPayload))
        }));
        
        console.log(`MQTT command sent to ${deviceId}`);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                device_id: deviceId,
                sensor_config: sensorConfig,
                config_updated_at: timestamp,
                message: 'Config updated and command sent to device'
            })
        };
        
    } catch (error) {
        console.error('Error updating device config:', error);
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

