/**
 * Lambda Function: sendCommand
 * 
 * Sends commands to Motion Play devices via AWS IoT Core MQTT.
 * Triggered by API Gateway.
 */

const { IoTDataPlaneClient, PublishCommand } = require('@aws-sdk/client-iot-data-plane');
const { randomUUID } = require('crypto');

const iotClient = new IoTDataPlaneClient({ region: process.env.AWS_REGION });

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        // Parse API Gateway event
        const body = JSON.parse(event.body || '{}');
        const deviceId = body.device_id || 'motionplay-device-002'; // Default device ID
        const command = body.command;
        
        if (!command) {
            return {
                statusCode: 400,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({ error: 'Missing command' })
            };
        }
        
        // Build command payload
        const payload = {
            command: command,
            timestamp: new Date().toISOString()
        };
        
        // Add session_id for start_collection commands
        if (command === 'start_collection') {
            payload.session_id = body.session_id || randomUUID();
        }
        
        // Add mode for set_mode commands
        if (command === 'set_mode' && body.mode) {
            payload.mode = body.mode;
        }

        // Add sensor configuration for configure_sensors commands
        if (command === 'configure_sensors' && body.sensor_config) {
            payload.sensor_config = body.sensor_config;
        }

        // capture_missed_event: no extra params needed, firmware handles it
        // (command name is sufficient — firmware extracts buffer on receipt)
        
        // Publish to IoT Core
        const topic = `motionplay/${deviceId}/commands`;
        
        await iotClient.send(new PublishCommand({
            topic: topic,
            qos: 1,
            payload: Buffer.from(JSON.stringify(payload))
        }));
        
        console.log(`Command sent to ${deviceId}:`, command);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                message: 'Command sent successfully',
                device_id: deviceId,
                command: command,
                session_id: payload.session_id
            })
        };
        
    } catch (error) {
        console.error('Error sending command:', error);
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

