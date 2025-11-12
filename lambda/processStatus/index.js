/**
 * Lambda Function: processStatus
 * 
 * Updates device status information.
 * Triggered by IoT Rule when device publishes status.
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, UpdateCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const DEVICES_TABLE = process.env.DEVICES_TABLE || 'MotionPlayDevices';

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const status = event;
        
        if (!status.device_id) {
            throw new Error('Missing device_id');
        }
        
        // Update device status
        await docClient.send(new UpdateCommand({
            TableName: DEVICES_TABLE,
            Key: { device_id: status.device_id },
            UpdateExpression: 'SET #status = :status, last_seen = :lastSeen, current_mode = :mode, wifi_rssi = :rssi, free_heap = :heap, uptime_ms = :uptime',
            ExpressionAttributeNames: {
                '#status': 'status'
            },
            ExpressionAttributeValues: {
                ':status': 'online',
                ':lastSeen': new Date().toISOString(),
                ':mode': status.mode || 'unknown',
                ':rssi': status.wifi_rssi || 0,
                ':heap': status.free_heap || 0,
                ':uptime': status.uptime_ms || 0
            }
        }));
        
        console.log(`Updated status for device ${status.device_id}`);
        
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: 'Status updated successfully',
                device_id: status.device_id
            })
        };
        
    } catch (error) {
        console.error('Error updating status:', error);
        throw error;
    }
};

