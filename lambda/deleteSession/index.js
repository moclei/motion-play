/**
 * Lambda Function: deleteSession
 * 
 * Deletes a session and all its sensor data.
 * Triggered by API Gateway DELETE /sessions/{session_id}
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, DeleteCommand, QueryCommand, BatchWriteCommand } = require('@aws-sdk/lib-dynamodb');

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
        
        // Query all sensor data for this session
        const dataResult = await docClient.send(new QueryCommand({
            TableName: SENSOR_DATA_TABLE,
            KeyConditionExpression: 'session_id = :sessionId',
            ExpressionAttributeValues: {
                ':sessionId': sessionId
            },
            ProjectionExpression: 'session_id, timestamp_offset'
        }));
        
        // Delete sensor data in batches
        if (dataResult.Items && dataResult.Items.length > 0) {
            const batchSize = 25;
            const items = dataResult.Items;
            
            for (let i = 0; i < items.length; i += batchSize) {
                const batch = items.slice(i, i + batchSize);
                const deleteRequests = batch.map(item => ({
                    DeleteRequest: {
                        Key: {
                            session_id: item.session_id,
                            timestamp_offset: item.timestamp_offset
                        }
                    }
                }));
                
                await docClient.send(new BatchWriteCommand({
                    RequestItems: {
                        [SENSOR_DATA_TABLE]: deleteRequests
                    }
                }));
                
                console.log(`Deleted batch ${i / batchSize + 1} (${batch.length} items)`);
            }
        }
        
        // Delete session metadata
        await docClient.send(new DeleteCommand({
            TableName: SESSIONS_TABLE,
            Key: { session_id: sessionId }
        }));
        
        console.log(`Deleted session ${sessionId}`);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                message: 'Session deleted successfully',
                session_id: sessionId,
                readings_deleted: dataResult.Items ? dataResult.Items.length : 0
            })
        };
        
    } catch (error) {
        console.error('Error deleting session:', error);
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

