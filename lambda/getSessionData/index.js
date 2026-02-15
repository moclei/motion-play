/**
 * Lambda Function: getSessionData
 * 
 * Retrieves detailed session data including all sensor readings or interrupt events.
 * Triggered by API Gateway GET /sessions/{session_id}
 * 
 * Supports two session types:
 * - "proximity" (default): Returns sensor readings from MotionPlaySensorData
 * - "interrupt": Returns interrupt events from MotionPlayInterruptEvents
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, GetCommand, QueryCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const SESSIONS_TABLE = process.env.SESSIONS_TABLE || 'MotionPlaySessions';
const SENSOR_DATA_TABLE = process.env.SENSOR_DATA_TABLE || 'MotionPlaySensorData';
const INTERRUPT_EVENTS_TABLE = process.env.INTERRUPT_EVENTS_TABLE || 'MotionPlayInterruptEvents';

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
        
        const session = sessionResult.Item;
        const sessionType = session.session_type || 'proximity';
        
        console.log(`Retrieving ${sessionType} session: ${sessionId}`);
        
        if (sessionType === 'interrupt') {
            return await getInterruptSessionData(session);
        } else {
            return await getProximitySessionData(session);
        }
        
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

// ============================================================================
// Interrupt Session Data Retrieval
// ============================================================================

async function getInterruptSessionData(session) {
    const sessionId = session.session_id;
    
    // Query interrupt events with pagination
    let allEvents = [];
    let lastEvaluatedKey = undefined;
    let pageCount = 0;
    
    do {
        const queryParams = {
            TableName: INTERRUPT_EVENTS_TABLE,
            KeyConditionExpression: 'session_id = :sessionId',
            ExpressionAttributeValues: {
                ':sessionId': sessionId
            }
        };
        
        if (lastEvaluatedKey) {
            queryParams.ExclusiveStartKey = lastEvaluatedKey;
        }
        
        const result = await docClient.send(new QueryCommand(queryParams));
        
        allEvents = allEvents.concat(result.Items || []);
        lastEvaluatedKey = result.LastEvaluatedKey;
        pageCount++;
        
        console.log(`Page ${pageCount}: Retrieved ${result.Items?.length || 0} events (Total: ${allEvents.length})`);
        
    } while (lastEvaluatedKey);
    
    console.log(`Retrieved interrupt session ${sessionId} with ${allEvents.length} events across ${pageCount} page(s)`);
    
    // Transform events for frontend
    const events = allEvents.map(item => ({
        timestamp_us: item.timestamp_us,
        board_id: item.board_id,
        sensor_position: item.sensor_position,
        event_type: item.event_type,
        raw_flags: item.raw_flags
    }));
    
    // Sort by timestamp
    events.sort((a, b) => a.timestamp_us - b.timestamp_us);
    
    return {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        body: JSON.stringify({
            session: session,
            session_type: 'interrupt',
            events: events
        })
    };
}

// ============================================================================
// Proximity Session Data Retrieval (existing logic)
// ============================================================================

async function getProximitySessionData(session) {
    const sessionId = session.session_id;
        
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
            
            if (lastEvaluatedKey) {
                queryParams.ExclusiveStartKey = lastEvaluatedKey;
            }
            
            const dataResult = await docClient.send(new QueryCommand(queryParams));
            
            allReadings = allReadings.concat(dataResult.Items || []);
            lastEvaluatedKey = dataResult.LastEvaluatedKey;
            pageCount++;
            
            console.log(`Page ${pageCount}: Retrieved ${dataResult.Items?.length || 0} readings (Total: ${allReadings.length})`);
            
    } while (lastEvaluatedKey);
        
    console.log(`Retrieved proximity session ${sessionId} with ${allReadings.length} readings across ${pageCount} page(s)`);
        
        // Transform readings to use millisecond timestamp for frontend compatibility
        // 
        // Backwards compatibility:
        // - Old sessions (pre-microsecond): timestamp_ms is in ms, timestamp_offset is ms-based (small values)
        // - New sessions (microsecond): timestamp_ms is derived ms value, timestamp_offset is us-based (large values)
        // 
        // Detection: if timestamp_offset values exceed 1,000,000, the session uses microsecond timestamps
        const isMicrosecondSession = allReadings.length > 0 && allReadings.some(item => 
            item.timestamp_offset !== undefined && item.timestamp_offset > 1_000_000
        );
        
        const readings = allReadings.map(item => {
            // Prefer the stored timestamp_ms (always in ms, set by processData)
            let numericTimestamp = item.timestamp_ms;
            
            // Fallback: derive from timestamp_offset if timestamp_ms is missing
            if (numericTimestamp === undefined && item.timestamp_offset !== undefined) {
                if (isMicrosecondSession) {
                    // Microsecond-based composite key: divide by 10 to get us, then by 1000 to get ms
                    numericTimestamp = Math.floor(item.timestamp_offset / 10 / 1000);
                } else {
                    // Millisecond-based composite key: divide by 10 to get ms
                    numericTimestamp = Math.floor(item.timestamp_offset / 10);
                }
            }
            
            return {
                ...item,
            timestamp_offset: numericTimestamp
            };
        });
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
            session: session,
            session_type: 'proximity',
                readings: readings
            })
        };
}
