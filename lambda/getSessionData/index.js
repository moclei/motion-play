/**
 * Lambda Function: getSessionData
 * 
 * Retrieves detailed session data including all sensor readings.
 * Triggered by API Gateway GET /sessions/{session_id}
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, GetCommand, QueryCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';
const SENSOR_DATA_TABLE = process.env.SENSOR_DATA_TABLE || 'MotionPlaySensorData';

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const sessionId = event.pathParameters?.session_id;
        
        if (!sessionId) {
            return {
                statusCode: 400,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({ error: 'Missing session_id' })
            };
        }
        
        // Get session metadata
        const sessionResult = await docClient.send(new GetCommand({
            TableName: SESSIONS_TABLE,
            Key: { session_id: sessionId }
        }));
        
        if (!sessionResult.Item) {
            return {
                statusCode: 404,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({ error: 'Session not found' })
            };
        }
        
        // Get sensor data
        const dataResult = await docClient.send(new QueryCommand({
            TableName: SENSOR_DATA_TABLE,
            KeyConditionExpression: 'session_id = :sessionId',
            ExpressionAttributeValues: {
                ':sessionId': sessionId
            }
        }));
        
        console.log(`Retrieved session ${sessionId} with ${dataResult.Items.length} readings`);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                session: sessionResult.Item,
                readings: dataResult.Items
            })
        };
        
    } catch (error) {
        console.error('Error retrieving session data:', error);
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

