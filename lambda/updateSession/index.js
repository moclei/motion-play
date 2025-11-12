/**
 * Lambda Function: updateSession
 * 
 * Updates session metadata (labels, notes).
 * Triggered by API Gateway PATCH /sessions/{session_id}
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, UpdateCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        const sessionId = event.pathParameters?.session_id;
        const body = JSON.parse(event.body || '{}');
        
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
        
        // Build update expression
        const updateExpressions = [];
        const expressionAttributeNames = {};
        const expressionAttributeValues = {};
        
        if (body.labels !== undefined) {
            updateExpressions.push('#labels = :labels');
            expressionAttributeNames['#labels'] = 'labels';
            expressionAttributeValues[':labels'] = body.labels;
        }
        
        if (body.notes !== undefined) {
            updateExpressions.push('#notes = :notes');
            expressionAttributeNames['#notes'] = 'notes';
            expressionAttributeValues[':notes'] = body.notes;
        }
        
        if (updateExpressions.length === 0) {
            return {
                statusCode: 400,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({ error: 'No fields to update' })
            };
        }
        
        // Update session
        const result = await docClient.send(new UpdateCommand({
            TableName: SESSIONS_TABLE,
            Key: { session_id: sessionId },
            UpdateExpression: `SET ${updateExpressions.join(', ')}`,
            ExpressionAttributeNames: expressionAttributeNames,
            ExpressionAttributeValues: expressionAttributeValues,
            ReturnValues: 'ALL_NEW'
        }));
        
        console.log(`Updated session ${sessionId}`);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                session: result.Attributes
            })
        };
        
    } catch (error) {
        console.error('Error updating session:', error);
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

