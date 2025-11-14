# Phase 3: Web Interface Implementation Guide

This guide walks you through building a web interface to view, visualize, and manage your Motion Play sensor data collection system.

## Phase 3 Overview

**Goal:** Create a React web application that interfaces with AWS to view sessions, visualize sensor data, and control the device.

**Deliverables:**

1. API Gateway with REST endpoints
2. React web application with data visualization
3. Session management interface
4. Device control panel
5. Data export functionality

## Prerequisites

- ✅ Phase 0 complete (AWS infrastructure)
- ✅ Phase 1 complete (WiFi + MQTT)
- ✅ Phase 2 complete (Data pipeline working)
- ✅ Node.js and npm installed
- ✅ AWS CLI configured
- ✅ Data collected in DynamoDB

---

## Architecture Overview

### System Architecture

```
React Frontend (localhost:5173)
    ↓
API Gateway (REST API)
    ↓
Lambda Functions
    ↓
DynamoDB Tables
```

### API Endpoints We'll Create

```
GET    /sessions                    → getSessions Lambda
GET    /sessions/{session_id}       → getSessionData Lambda
PUT    /sessions/{session_id}       → updateSession Lambda
DELETE /sessions/{session_id}       → deleteSession Lambda
POST   /device/command              → sendCommand Lambda
GET    /device/status               → (query from DynamoDB)
```

---

## Part 1: API Gateway Setup

### Step 1.1: Create REST API

```bash
# Create the API
aws apigateway create-rest-api \
    --name "MotionPlayAPI" \
    --description "REST API for Motion Play data access" \
    --endpoint-configuration types=REGIONAL \
    --output json > api-creation.json

# Extract the API ID
export API_ID=$(cat api-creation.json | grep '"id"' | head -1 | cut -d'"' -f4)
echo "API ID: $API_ID"

# Get the root resource ID
export ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[0].id' \
    --output text)
echo "Root Resource ID: $ROOT_ID"
```

### Step 1.2: Create /sessions Resource

```bash
# Create /sessions resource
aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part sessions \
    --output json > sessions-resource.json

export SESSIONS_RESOURCE_ID=$(cat sessions-resource.json | grep '"id"' | cut -d'"' -f4)
echo "Sessions Resource ID: $SESSIONS_RESOURCE_ID"
```

### Step 1.3: Create GET /sessions Method

```bash
# Create GET method on /sessions
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $SESSIONS_RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE

# Get Lambda ARN
export GET_SESSIONS_ARN=$(aws lambda get-function \
    --function-name motionplay-getSessions \
    --query 'Configuration.FunctionArn' \
    --output text)

# Integrate with Lambda
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $SESSIONS_RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/$GET_SESSIONS_ARN/invocations"

# Get your AWS account ID (needed for source ARN)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Give API Gateway permission to invoke Lambda
aws lambda add-permission \
    --function-name motionplay-getSessions \
    --statement-id apigateway-get-sessions \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-west-2:${AWS_ACCOUNT_ID}:${API_ID}/*/GET/sessions"
```

### Step 1.4: Create /sessions/{session_id} Resource

```bash
# Create {session_id} resource under /sessions
aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $SESSIONS_RESOURCE_ID \
    --path-part '{session_id}' \
    --output json > infrastructure/session-id-resource.json

export SESSION_ID_RESOURCE_ID=$(cat infrastructure/session-id-resource.json | grep '"id"' | head -1 | cut -d'"' -f4)
echo "Session ID Resource: $SESSION_ID_RESOURCE_ID"
```

### Step 1.5: Create GET /sessions/{session_id} Method

```bash
# Create GET method on /sessions/{session_id}
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $SESSION_ID_RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE \
    --request-parameters method.request.path.session_id=true

# Get Lambda ARN
export GET_SESSION_DATA_ARN=$(aws lambda get-function \
    --function-name motionplay-getSessionData \
    --query 'Configuration.FunctionArn' \
    --output text)

# Integrate with Lambda
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $SESSION_ID_RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/$GET_SESSION_DATA_ARN/invocations"

# Give API Gateway permission
aws lambda add-permission \
    --function-name motionplay-getSessionData \
    --statement-id apigateway-get-session-data \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-west-2:${AWS_ACCOUNT_ID}:${API_ID}/*/GET/sessions/*"
```

### Step 1.6: Enable CORS

```bash
# Enable CORS on /sessions
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $SESSIONS_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $SESSIONS_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --request-templates '{"application/json":"{\"statusCode\": 200}"}'

aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $SESSIONS_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        method.response.header.Access-Control-Allow-Headers=true,\
method.response.header.Access-Control-Allow-Methods=true,\
method.response.header.Access-Control-Allow-Origin=true

aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $SESSIONS_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{
        "method.response.header.Access-Control-Allow-Headers": "'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'",
        "method.response.header.Access-Control-Allow-Methods": "'"'"'GET,OPTIONS'"'"'",
        "method.response.header.Access-Control-Allow-Origin": "'"'"'*'"'"'"
    }'
```

### Step 1.7: Deploy API

```bash
# Create deployment stage
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --stage-description "Production stage" \
    --description "Initial deployment"

# Get the API endpoint
echo "API Endpoint: https://$API_ID.execute-api.us-west-2.amazonaws.com/prod"
```

### Step 1.8: Test API

```bash
# Test GET /sessions
curl "https://$API_ID.execute-api.us-west-2.amazonaws.com/prod/sessions"

# Test GET /sessions/{session_id} (use a real session ID from your data)
curl "https://$API_ID.execute-api.us-west-2.amazonaws.com/prod/sessions/device-001_709865"
```

---

## Part 2: Frontend Configuration

### Step 2.1: Update Frontend Environment

Create `frontend/motion-play-ui/.env`:

```env
VITE_API_ENDPOINT=https://YOUR_API_ID.execute-api.us-west-2.amazonaws.com/prod
VITE_AWS_REGION=us-west-2
VITE_DEVICE_ID=motionplay-device-001
```

Replace `YOUR_API_ID` with your actual API Gateway ID.

### Step 2.2: Install Additional Dependencies

```bash
cd frontend/motion-play-ui

# Install additional packages for charts and data handling
npm install recharts date-fns lucide-react
```

---

## Part 3: Build Frontend Components

### Step 3.1: Create API Service

Create `frontend/motion-play-ui/src/services/api.ts`:

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT;

export interface Session {
  session_id: string;
  device_id: string;
  start_timestamp: string;
  end_timestamp: string;
  duration_ms: number;
  sample_count: number;
  sample_rate: number;
  mode: string;
  labels: string[];
  notes: string;
  created_at: number;
}

export interface SensorReading {
  timestamp_offset: number;
  position: number;
  pcb_id: number;
  side: number;
  proximity: number;
  ambient: number;
}

export interface SessionData {
  session: Session;
  readings: SensorReading[];
}

class MotionPlayAPI {
  // Get all sessions
  async getSessions(limit = 50): Promise<Session[]> {
    const response = await axios.get(`${API_BASE_URL}/sessions`, {
      params: { limit }
    });
    return response.data.sessions || [];
  }

  // Get session with readings
  async getSessionData(sessionId: string): Promise<SessionData> {
    const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}`);
    return response.data;
  }

  // Update session metadata
  async updateSession(sessionId: string, updates: { labels?: string[], notes?: string }): Promise<void> {
    await axios.put(`${API_BASE_URL}/sessions/${sessionId}`, updates);
  }

  // Delete session
  async deleteSession(sessionId: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/sessions/${sessionId}`);
  }

  // Send command to device
  async sendCommand(command: string): Promise<void> {
    await axios.post(`${API_BASE_URL}/device/command`, {
      command,
      timestamp: Date.now()
    });
  }
}

export const api = new MotionPlayAPI();
```

### Step 3.2: Create Session List Component

Create `frontend/motion-play-ui/src/components/SessionList.tsx`:

```typescript
import React, { useEffect, useState } from 'react';
import { api, Session } from '../services/api';
import { formatDistance } from 'date-fns';

export const SessionList: React.FC<{ onSelectSession: (session: Session) => void }> = ({ 
  onSelectSession 
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await api.getSessions();
      setSessions(data);
      setError(null);
    } catch (err) {
      setError('Failed to load sessions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading sessions...</div>;
  }

  if (error) {
    return (
      <div className="p-4 text-red-600">
        {error}
        <button onClick={loadSessions} className="ml-4 text-blue-600">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Sessions</h2>
        <button 
          onClick={loadSessions}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-2">
        {sessions.length === 0 ? (
          <p className="text-gray-500">No sessions found</p>
        ) : (
          sessions.map((session) => (
            <div
              key={session.session_id}
              onClick={() => onSelectSession(session)}
              className="p-4 border rounded hover:bg-gray-50 cursor-pointer"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">{session.session_id}</h3>
                  <p className="text-sm text-gray-600">
                    Duration: {(session.duration_ms / 1000).toFixed(1)}s
                  </p>
                  <p className="text-sm text-gray-600">
                    Samples: {session.sample_count} @ {session.sample_rate} Hz
                  </p>
                </div>
                <div className="text-right text-sm text-gray-500">
                  {formatDistance(new Date(session.created_at), new Date(), {
                    addSuffix: true
                  })}
                </div>
              </div>
              {session.labels.length > 0 && (
                <div className="mt-2 flex gap-2">
                  {session.labels.map((label, i) => (
                    <span key={i} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                      {label}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
```

### Step 3.3: Create Data Visualization Component

Create `frontend/motion-play-ui/src/components/SessionChart.tsx`:

```typescript
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { SensorReading } from '../services/api';

interface Props {
  readings: SensorReading[];
}

export const SessionChart: React.FC<Props> = ({ readings }) => {
  // Group readings by side for comparison
  const s1Readings = readings.filter(r => r.side === 1);
  const s2Readings = readings.filter(r => r.side === 2);

  // Prepare data for chart (sample every 10th reading for performance)
  const chartData = readings
    .filter((_, i) => i % 10 === 0)
    .map(reading => ({
      time: reading.timestamp_offset,
      proximity: reading.proximity,
      ambient: reading.ambient,
      side: reading.side === 1 ? 'S1' : 'S2'
    }));

  // Calculate statistics
  const avgProximity = readings.reduce((sum, r) => sum + r.proximity, 0) / readings.length;
  const maxProximity = Math.max(...readings.map(r => r.proximity));
  const minProximity = Math.min(...readings.map(r => r.proximity));

  return (
    <div className="space-y-4">
      {/* Statistics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 bg-blue-50 rounded">
          <div className="text-sm text-gray-600">Total Readings</div>
          <div className="text-2xl font-bold">{readings.length}</div>
        </div>
        <div className="p-4 bg-green-50 rounded">
          <div className="text-sm text-gray-600">Avg Proximity</div>
          <div className="text-2xl font-bold">{avgProximity.toFixed(1)}</div>
        </div>
        <div className="p-4 bg-yellow-50 rounded">
          <div className="text-sm text-gray-600">Max Proximity</div>
          <div className="text-2xl font-bold">{maxProximity}</div>
        </div>
        <div className="p-4 bg-red-50 rounded">
          <div className="text-sm text-gray-600">Min Proximity</div>
          <div className="text-2xl font-bold">{minProximity}</div>
        </div>
      </div>

      {/* Proximity Chart */}
      <div className="bg-white p-4 rounded border">
        <h3 className="font-semibold mb-4">Proximity Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time" 
              label={{ value: 'Time (ms)', position: 'insideBottom', offset: -5 }}
            />
            <YAxis label={{ value: 'Proximity', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="proximity" stroke="#8884d8" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Side Comparison */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-green-50 rounded">
          <h4 className="font-semibold mb-2">Side 1 (S1)</h4>
          <p className="text-sm">Readings: {s1Readings.length}</p>
          <p className="text-sm">
            Avg Proximity: {(s1Readings.reduce((sum, r) => sum + r.proximity, 0) / s1Readings.length).toFixed(1)}
          </p>
        </div>
        <div className="p-4 bg-blue-50 rounded">
          <h4 className="font-semibold mb-2">Side 2 (S2)</h4>
          <p className="text-sm">Readings: {s2Readings.length}</p>
          <p className="text-sm">
            Avg Proximity: {(s2Readings.reduce((sum, r) => sum + r.proximity, 0) / s2Readings.length).toFixed(1)}
          </p>
        </div>
      </div>
    </div>
  );
};
```

### Step 3.4: Create Device Control Component

Create `frontend/motion-play-ui/src/components/DeviceControl.tsx`:

```typescript
import React, { useState } from 'react';
import { api } from '../services/api';
import { Play, Square } from 'lucide-react';

export const DeviceControl: React.FC = () => {
  const [collecting, setCollecting] = useState(false);
  const [status, setStatus] = useState<string>('');

  const handleStartCollection = async () => {
    try {
      setStatus('Starting collection...');
      await api.sendCommand('start_collection');
      setCollecting(true);
      setStatus('Collection started');
    } catch (err) {
      setStatus('Failed to start collection');
      console.error(err);
    }
  };

  const handleStopCollection = async () => {
    try {
      setStatus('Stopping collection...');
      await api.sendCommand('stop_collection');
      setCollecting(false);
      setStatus('Collection stopped');
    } catch (err) {
      setStatus('Failed to stop collection');
      console.error(err);
    }
  };

  return (
    <div className="p-4 border rounded bg-white">
      <h3 className="text-xl font-bold mb-4">Device Control</h3>
      
      <div className="space-y-4">
        <div className="flex gap-4">
          <button
            onClick={handleStartCollection}
            disabled={collecting}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300"
          >
            <Play size={20} />
            Start Collection
          </button>

          <button
            onClick={handleStopCollection}
            disabled={!collecting}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-300"
          >
            <Square size={20} />
            Stop Collection
          </button>
        </div>

        {status && (
          <div className={`p-3 rounded ${
            status.includes('Failed') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
          }`}>
            {status}
          </div>
        )}

        <div className="text-sm text-gray-600">
          <p><strong>Status:</strong> {collecting ? 'Collecting...' : 'Idle'}</p>
          <p><strong>Device:</strong> motionplay-device-001</p>
        </div>
      </div>
    </div>
  );
};
```

### Step 3.5: Update Main App Component

Update `frontend/motion-play-ui/src/App.tsx`:

```typescript
import React, { useState } from 'react';
import { SessionList } from './components/SessionList';
import { SessionChart } from './components/SessionChart';
import { DeviceControl } from './components/DeviceControl';
import { Session, SessionData, api } from './services/api';

function App() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSelectSession = async (session: Session) => {
    setSelectedSession(session);
    setLoading(true);
    
    try {
      const data = await api.getSessionData(session.session_id);
      setSessionData(data);
    } catch (err) {
      console.error('Failed to load session data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">
            Motion Play Dashboard
          </h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4">
        <div className="grid grid-cols-12 gap-6">
          {/* Left sidebar - Device Control */}
          <div className="col-span-3">
            <DeviceControl />
          </div>

          {/* Middle - Session List */}
          <div className="col-span-3 bg-white rounded shadow">
            <SessionList onSelectSession={handleSelectSession} />
          </div>

          {/* Right - Session Detail */}
          <div className="col-span-6 bg-white rounded shadow p-4">
            {!selectedSession ? (
              <div className="text-center text-gray-500 py-20">
                Select a session to view details
              </div>
            ) : loading ? (
              <div className="text-center py-20">Loading session data...</div>
            ) : sessionData ? (
              <div>
                <h2 className="text-2xl font-bold mb-4">
                  {selectedSession.session_id}
                </h2>
                <SessionChart readings={sessionData.readings} />
              </div>
            ) : (
              <div className="text-center text-red-500 py-20">
                Failed to load session data
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
```

---

## Part 4: Testing the Complete System

### Step 4.1: Start Frontend

```bash
cd frontend/motion-play-ui
npm run dev
```

Open browser to `http://localhost:5173`

### Step 4.2: Test Flow

1. **View Sessions**: Should see list of collected sessions
2. **Select Session**: Click on a session to see details
3. **View Charts**: Proximity data should display in chart
4. **Device Control**: 
   - Click "Start Collection"
   - Wait 10 seconds
   - Click "Stop Collection"
   - Refresh sessions to see new session

### Step 4.3: Verify Data Flow

Check that:
- Sessions load from DynamoDB
- Charts display sensor readings
- Commands reach the device
- New sessions appear after collection

---

## Troubleshooting

### Issue: Tailwind CSS PostCSS Plugin Error

**Symptoms:** Error when starting dev server: `[postcss] It looks like you're trying to use 'tailwindcss' directly as a PostCSS plugin`

**Solution:**
This happens if Tailwind v4 was installed. Tailwind v4 has breaking changes. Downgrade to stable v3:
```bash
cd frontend/motion-play-ui
npm uninstall tailwindcss @tailwindcss/postcss
npm install -D 'tailwindcss@^3.4.1' 'postcss@^8.4.35' 'autoprefixer@^10.4.18'
# Make sure postcss.config.js uses: tailwindcss: {} (not @tailwindcss/postcss)
npm run dev
```

### Issue: Lambda Permission Validation Error

**Symptoms:** `ValidationException` when adding Lambda permissions: "failed to satisfy constraint: Member must satisfy regular expression pattern"

**Solution:**
AWS requires your actual account ID in the source ARN. Get it and use it:
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
# Then use ${AWS_ACCOUNT_ID} instead of * in source ARNs
```

### Issue: Internal Server Error on Session Detail

**Symptoms:** API returns `{"message": "Internal server error"}` when accessing `/sessions/{session_id}`

**Solution:**
Path parameter name must match what Lambda expects. Lambda expects `session_id`, not `id`:
```bash
# Make sure the resource uses {session_id}
aws apigateway get-resources --rest-api-id $API_ID
# If you see {id}, delete and recreate with {session_id}
```

### Issue: Response Parameters JSON Format Error

**Symptoms:** `BadRequestException: Invalid mapping expression specified` when setting up CORS

**Solution:**
Use proper JSON format for `--response-parameters`:
```bash
--response-parameters '{
    "method.response.header.Access-Control-Allow-Headers": "'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'",
    "method.response.header.Access-Control-Allow-Methods": "'"'"'GET,OPTIONS'"'"'",
    "method.response.header.Access-Control-Allow-Origin": "'"'"'*'"'"'"
}'
```

### Issue: API Gateway CORS Errors

**Symptoms:** Browser console shows "No 'Access-Control-Allow-Origin' header"

**Solution:**
```bash
# Re-run CORS setup for each resource
# Make sure OPTIONS method is configured with proper headers
```

### Issue: Lambda Not Returning Data

**Symptoms:** API returns 502 or timeout

**Solution:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/motionplay-getSessions --follow

# Verify Lambda has DynamoDB permissions
```

### Issue: Frontend Can't Connect to API

**Symptoms:** Network errors in browser

**Solution:**
- Verify `.env` file has correct API endpoint
- Check API Gateway deployment stage
- Test API with curl first

---

## Success Criteria

Phase 3 is complete when:

- ✅ API Gateway endpoints working for all Lambda functions
- ✅ Frontend displays session list from DynamoDB
- ✅ Session detail view shows sensor readings
- ✅ Charts visualize proximity data over time
- ✅ Device control sends MQTT commands
- ✅ New sessions appear after collection
- ✅ No CORS errors in browser console

---

## Next Steps

Once Phase 3 is working:

**Phase 4: Enhancement & Polish**
- Add authentication (Cognito)
- Export data to CSV/JSON
- Advanced filtering and search
- Real-time device status monitoring
- Mobile responsive design
- Production deployment

---

## Useful Commands

```bash
# Check API Gateway
aws apigateway get-rest-apis

# Test endpoint
curl https://YOUR_API_ID.execute-api.us-west-2.amazonaws.com/prod/sessions

# View Lambda logs
aws logs tail /aws/lambda/motionplay-getSessions --follow --since 5m

# Frontend development
cd frontend/motion-play-ui
npm run dev

# Build for production
npm run build
```

---

**Ready to build your web interface!** Follow the steps above to create a complete dashboard for your Motion Play system.

