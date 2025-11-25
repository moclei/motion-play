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
        
        // Get sensor data with pagination support
        let allReadings = [];
        let lastEvaluatedKey = undefined;
        let pageCount = 0;
        
        do {
            const queryParams = {
                TableName: SENSOR_DATA_TABLE,
                KeyConditionExpression: 'session_id = :sessionId',
                ExpressionAttributeValues: {
                    ':sessionId': sessionId
                }
            };
            
            // Add pagination token if we have one
            if (lastEvaluatedKey) {
                queryParams.ExclusiveStartKey = lastEvaluatedKey;
            }
            
            const dataResult = await docClient.send(new QueryCommand(queryParams));
            
            allReadings = allReadings.concat(dataResult.Items || []);
            lastEvaluatedKey = dataResult.LastEvaluatedKey;
            pageCount++;
            
            console.log(`Page ${pageCount}: Retrieved ${dataResult.Items?.length || 0} readings (Total: ${allReadings.length})`);
            
        } while (lastEvaluatedKey); // Keep fetching until no more pages
        
        console.log(`Retrieved session ${sessionId} with ${allReadings.length} readings across ${pageCount} page(s)`);
        
        // Transform readings to use actual timestamp for frontend compatibility
        const readings = allReadings.map(item => {
            // Use timestamp_ms if available (new format)
            let numericTimestamp = item.timestamp_ms;
            
            // If timestamp_ms not available, decode from composite timestamp_offset
            if (numericTimestamp === undefined && item.timestamp_offset) {
                // New format: composite key (timestamp * 10 + position)
                // Decode: timestamp = Math.floor(composite / 10)
                numericTimestamp = Math.floor(item.timestamp_offset / 10);
            }
            
            return {
                ...item,
                timestamp_offset: numericTimestamp  // Frontend expects base timestamp
            };
        });
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                session: sessionResult.Item,
                readings: readings
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

