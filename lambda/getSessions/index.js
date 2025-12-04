/**
 * Lambda Function: getSessions
 * 
 * Retrieves list of sessions, optionally filtered by device_id.
 * Triggered by API Gateway GET /sessions
 * 
 * IMPORTANT: DynamoDB Scan doesn't guarantee order, so we scan all items
 * and sort by created_at descending to return the newest sessions first.
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
        
        let sessions = [];
        
        if (deviceId) {
            // Query by device_id using GSI - this respects sort order
            const result = await docClient.send(new QueryCommand({
                TableName: SESSIONS_TABLE,
                IndexName: 'DeviceTimeIndex',
                KeyConditionExpression: 'device_id = :deviceId',
                ExpressionAttributeValues: {
                    ':deviceId': deviceId
                },
                Limit: limit,
                ScanIndexForward: false // Sort by timestamp descending
            }));
            sessions = result.Items;
        } else {
            // Scan all sessions - DynamoDB Scan doesn't guarantee order,
            // so we must scan all items and sort manually
            let lastEvaluatedKey = undefined;
            
            do {
                const scanParams = {
                    TableName: SESSIONS_TABLE
                };
                
                if (lastEvaluatedKey) {
                    scanParams.ExclusiveStartKey = lastEvaluatedKey;
                }
                
                const result = await docClient.send(new ScanCommand(scanParams));
                sessions = sessions.concat(result.Items);
                lastEvaluatedKey = result.LastEvaluatedKey;
                
                // Safety limit: stop if we've retrieved more than 1000 sessions
                // to prevent runaway costs
                if (sessions.length > 1000) {
                    console.warn('Safety limit reached: more than 1000 sessions');
                    break;
                }
            } while (lastEvaluatedKey);
            
            // Sort by created_at descending (newest first)
            sessions.sort((a, b) => {
                const aTime = a.created_at || 0;
                const bTime = b.created_at || 0;
                return bTime - aTime;
            });
            
            // Apply limit after sorting
            sessions = sessions.slice(0, limit);
        }
        
        console.log(`Retrieved ${sessions.length} sessions (sorted by created_at desc)`);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                sessions: sessions,
                count: sessions.length
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

