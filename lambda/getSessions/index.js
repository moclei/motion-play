/**
 * Lambda Function: getSessions
 * 
 * Retrieves list of sessions, optionally filtered by device_id.
 * Triggered by API Gateway GET /sessions
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, ScanCommand, QueryCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const queryParams = event.queryStringParameters || {};
        const deviceId = queryParams.device_id;
        const limit = parseInt(queryParams.limit) || 50;
        
        let result;
        
        if (deviceId) {
            // Query by device_id using GSI
            result = await docClient.send(new QueryCommand({
                TableName: SESSIONS_TABLE,
                IndexName: 'DeviceTimeIndex',
                KeyConditionExpression: 'device_id = :deviceId',
                ExpressionAttributeValues: {
                    ':deviceId': deviceId
                },
                Limit: limit,
                ScanIndexForward: false // Sort by timestamp descending
            }));
        } else {
            // Scan all sessions
            result = await docClient.send(new ScanCommand({
                TableName: SESSIONS_TABLE,
                Limit: limit
            }));
        }
        
        console.log(`Retrieved ${result.Items.length} sessions`);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                sessions: result.Items,
                count: result.Items.length
            })
        };
        
    } catch (error) {
        console.error('Error retrieving sessions:', error);
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

