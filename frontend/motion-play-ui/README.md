# Motion Play Web Interface

React-based web interface for device control, data visualization, and session management.

## Tech Stack

- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS v3
- **Charts:** Recharts
- **HTTP Client:** Axios
- **Icons:** Lucide React
- **Date Formatting:** date-fns

## Architecture Overview

```
frontend/motion-play-ui/src/
├── App.tsx                    # Main application & routing
├── index.css                  # Global styles (Tailwind)
├── main.tsx                   # Application entry point
├── components/                # React components
│   ├── SessionList.tsx       # Session list with filtering
│   ├── SessionChart.tsx      # Data visualization
│   ├── DeviceControl.tsx     # Start/stop collection
│   ├── LabelEditor.tsx       # Session labels & notes
│   ├── ExportButton.tsx      # JSON/CSV export
│   ├── ModeSelector.tsx      # Device mode selection
│   ├── SensorConfig.tsx      # Live sensor configuration
│   └── SessionConfig.tsx     # Historical config display
└── services/
    └── api.ts                 # API client (Axios)
```

## Components

### Core Components (Phase 3)

#### `App.tsx`
**Purpose:** Main application container and state coordinator

**State Management:**
- `selectedSession` - Currently viewed session
- `sessionData` - Full session data with readings
- `sessionListRef` - Reference to SessionList for refresh

**Key Functions:**
- `handleSessionSelect()` - Load and display session details
- `handleDeleteSession()` - Delete session with confirmation
- `handleCollectionStopped()` - Refresh list after collection

**Layout:**
- Left column: Device control + session list
- Right column: Session detail + chart

#### `SessionList.tsx`
**Purpose:** Display and filter recorded sessions

**Props:**
```typescript
interface SessionListProps {
    onSessionSelect: (session: Session) => void;
    selectedId?: string;
}
```

**Features:**
- Real-time session loading
- Search by session ID, labels, notes
- Filter by mode (all/idle/debug/play)
- Visual selection highlighting
- Results counter
- Exposed `refresh()` method via `useImperativeHandle`

**Display:**
- Session ID (monospace)
- Duration, sample count, sample rate
- Labels (if present)
- Mode badge

#### `SessionChart.tsx`
**Purpose:** Interactive time-series visualization with statistics

**Props:**
```typescript
interface SessionChartProps {
    readings: Reading[];
}
```

**Features:**
- Dual-line chart (Side 1: dark green, Side 2: dark blue)
- Clickable side filtering (show one or both sides)
- Real-time statistics:
  - Average proximity (overall + per side)
  - Max/Min proximity
  - Sample counts per side
- Handles empty/invalid data gracefully

**Chart Details:**
- X-axis: Time offset (ms)
- Y-axis: Proximity value
- Tooltip: Shows exact values on hover
- `connectNulls` for smooth lines

#### `DeviceControl.tsx`
**Purpose:** Start/stop data collection

**Props:**
```typescript
interface DeviceControlProps {
    onCollectionStopped?: () => void;
}
```

**Features:**
- Start/stop buttons with loading states
- Visual feedback on success/error
- Calls parent callback when collection stops

**Commands Sent:**
- `start_collection`
- `stop_collection`

### Enhancement Components (Phase 3-B)

#### `LabelEditor.tsx`
**Purpose:** Add labels and notes to sessions

**Props:**
```typescript
interface LabelEditorProps {
    session: Session;
    onUpdate: (session: Session) => void;
}
```

**Features:**
- Add/remove labels (tags)
- Predefined label suggestions:
  - `successful-shot`, `miss`, `practice`
  - `baseline`, `experiment`, `calibration`
  - `fast`, `slow`, `normal`
- Free-text notes field
- Save to backend (PUT request)

**UI Elements:**
- Tag chips with X to remove
- Input field for new labels
- Suggestion buttons
- Notes textarea

#### `ExportButton.tsx`
**Purpose:** Export session data for ML training

**Props:**
```typescript
interface ExportButtonProps {
    sessionData: SessionData;
}
```

**Features:**
- Export as JSON (complete data structure)
- Export as CSV (tabular format)
- Proper filename generation: `session_{id}.json`
- Download triggers automatically

**CSV Format:**
```csv
timestamp_offset,sensor_pcb,sensor_side,proximity,ambient,timestamp
0,0,1,1234,567,2025-11-14T10:30:00Z
1,0,2,1235,568,2025-11-14T10:30:00Z
...
```

#### `ModeSelector.tsx`
**Purpose:** Switch device operating mode

**Props:**
```typescript
interface ModeSelectorProps {
    deviceId?: string;
}
```

**Modes:**
- **Idle:** Minimal operation, ready for commands
- **Debug:** Full logging, detailed display
- **Play:** Game mode, LED feedback

**Features:**
- Visual indication of active mode
- Sends `set_mode` command
- Success/error feedback

#### `SensorConfig.tsx`
**Purpose:** Configure live sensor settings (control panel)

**Props:**
```typescript
interface SensorConfigProps {
    deviceId?: string;
}
```

**Configurable Settings:**
- Sample rate: 100/250/500/1000 Hz
- LED current: 50/75/100/150/200 mA
- Integration time: 1T/2T/4T/8T
- High resolution: true/false (12-bit vs 16-bit)

**Features:**
- Dropdown selectors
- Apply button sends `configure_sensors` command
- Visual feedback on success

**Important:** This configures FUTURE collections. Past sessions retain their original config.

#### `SessionConfig.tsx`
**Purpose:** Display historical sensor configuration (read-only)

**Props:**
```typescript
interface SessionConfigProps {
    sessionData: SessionData;
}
```

**Displays:**
- Sample rate used for this session
- LED current setting
- Integration time
- High resolution mode
- Number of active sensors

**Why This Matters:** For ML training, you need to know what settings were used for each dataset.

## Services

### `api.ts`
**Purpose:** Centralized API client for backend communication

**Base Configuration:**
```typescript
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;
const DEVICE_ID = import.meta.env.VITE_DEVICE_ID;
```

**Methods:**

#### Session Management
```typescript
getSessions(): Promise<Session[]>
getSessionData(sessionId: string): Promise<SessionData>
deleteSession(sessionId: string): Promise<any>
updateSession(sessionId: string, updates: UpdateData): Promise<void>
```

#### Device Control
```typescript
sendCommand(command: string, params?: Record<string, any>): Promise<void>
```

**Commands:**
- `start_collection`
- `stop_collection`
- `set_mode` (with `mode` param)
- `configure_sensors` (with `sensor_config` param)

#### API Endpoints Used:
- `GET /sessions` - List all sessions
- `GET /sessions/{session_id}` - Get session details
- `DELETE /sessions/{session_id}` - Delete session
- `PUT /sessions/{session_id}` - Update labels/notes
- `POST /device/command` - Send device command

## TypeScript Interfaces

### Core Types

```typescript
interface Session {
    session_id: string;
    device_id: string;
    start_timestamp: string;
    duration_ms: number;
    sample_count: number;
    sample_rate: number;
    mode: string;
    labels?: string[];
    notes?: string;
    created_at: number;
    active_sensors?: ActiveSensor[];
    vcnl4040_config?: VCNL4040Config;
}

interface SessionData {
    session: Session;
    readings: Reading[];
}

interface Reading {
    timestamp_offset: number;
    sensor_pcb: number;
    sensor_side: number;
    proximity: number;
    ambient: number;
    timestamp: string;
}

interface VCNL4040Config {
    sample_rate_hz: number;
    led_current: string;
    integration_time: string;
    high_resolution: boolean;
}

interface ActiveSensor {
    pos: number;
    pcb: number;
    side: number;
    name: string;
    active: boolean;
}
```

## Environment Variables

Create `.env` in the project root:

```env
VITE_API_ENDPOINT=https://your-api-gateway-id.execute-api.us-west-2.amazonaws.com/prod
VITE_AWS_REGION=us-west-2
VITE_DEVICE_ID=motionplay-device-001
```

**Access in code:**
```typescript
import.meta.env.VITE_API_ENDPOINT
```

## Development Workflow

### Install Dependencies
```bash
cd frontend/motion-play-ui/
npm install
```

### Start Dev Server
```bash
npm run dev
```
Opens at `http://localhost:5173`

### Build for Production
```bash
npm run build
```
Output in `dist/` directory

### Preview Production Build
```bash
npm run preview
```

### Lint Code
```bash
npm run lint
```

## Project Configuration

### `vite.config.ts`
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true
  }
})
```

### `tailwind.config.js`
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### `tsconfig.json`
Standard React + TypeScript configuration with strict mode enabled.

## Styling Approach

### Tailwind CSS Classes
Most styling uses Tailwind utility classes:

```tsx
<div className="bg-white rounded-lg shadow p-4 mb-4">
  <h3 className="text-lg font-semibold text-gray-800 mb-2">
    Title
  </h3>
</div>
```

### Common Patterns

**Cards:**
```tsx
className="bg-white rounded-lg shadow p-4"
```

**Buttons:**
```tsx
className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
```

**Input Fields:**
```tsx
className="border border-gray-300 rounded px-3 py-2 w-full"
```

**Badges:**
```tsx
className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
```

## State Management

### Local State (useState)
Used for component-specific state:
- Form inputs
- Loading states
- Local UI toggles

### Refs (useRef)
Used for:
- Accessing child methods (`sessionListRef.current.refresh()`)
- Avoiding re-renders for non-visual state

### Props
Used for:
- Parent-child communication
- Callback functions
- Data passing

**No global state library** (Redux, Zustand, etc.) - Not needed for current complexity.

## Adding New Components

### 1. Create Component File
```bash
touch src/components/MyComponent.tsx
```

### 2. Component Template
```tsx
import { useState } from 'react';

interface MyComponentProps {
    data: string;
    onAction: () => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({ data, onAction }) => {
    const [localState, setLocalState] = useState('');

    return (
        <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-2">My Component</h3>
            {/* Component content */}
        </div>
    );
};
```

### 3. Import in App.tsx
```tsx
import { MyComponent } from './components/MyComponent';
```

### 4. Use in App.tsx
```tsx
<MyComponent data="example" onAction={handleAction} />
```

## Common Tasks

### Refresh Session List After Action
```typescript
// In App.tsx
const sessionListRef = useRef<{ refresh: () => void }>(null);

// Call after action
sessionListRef.current?.refresh();
```

### Add New API Endpoint
```typescript
// In api.ts
async myNewEndpoint(): Promise<ResponseType> {
    const response = await axios.get(`${this.baseUrl}/my-endpoint`);
    return response.data;
}
```

### Handle Loading States
```typescript
const [loading, setLoading] = useState(false);

const handleAction = async () => {
    setLoading(true);
    try {
        await api.someAction();
        alert('Success!');
    } catch (error) {
        console.error('Error:', error);
        alert('Failed!');
    } finally {
        setLoading(false);
    }
};
```

## Debugging Tips

### Check Browser Console
- Network tab: See API requests/responses
- Console tab: See `console.log()` output and errors
- React DevTools: Inspect component state

### Common Issues

**API Requests Failing:**
- Check `.env` file exists and has correct API endpoint
- Verify CORS configuration on API Gateway
- Check browser network tab for exact error

**Environment Variables Not Loading:**
- Restart dev server after changing `.env`
- Variables must start with `VITE_`
- Access via `import.meta.env.VITE_*`

**Tailwind Classes Not Working:**
- Check `tailwind.config.js` includes your file
- Verify `@tailwind` directives in `index.css`
- Restart dev server

**TypeScript Errors:**
- Check interface definitions match API responses
- Use `any` temporarily, then narrow down types
- Run `npm run build` to see all type errors

## Performance Considerations

### Chart Rendering
- `SessionChart` filters data before rendering
- Recharts handles 1000+ points efficiently
- Use `connectNulls` for smoother lines

### Session List
- Only loads metadata initially
- Full readings loaded on-demand
- Filtering happens client-side (fast)

### API Calls
- No caching (always fresh data)
- Consider adding React Query for optimization later

## Testing

Currently no automated tests. For manual testing:

1. **Session List:**
   - Load sessions
   - Filter by mode
   - Search by ID/labels/notes
   - Select session

2. **Session Detail:**
   - View chart
   - Toggle side filtering
   - Check statistics
   - Add labels/notes

3. **Device Control:**
   - Start collection
   - Stop collection
   - Verify list refreshes

4. **Export:**
   - Download JSON
   - Download CSV
   - Verify file contents

5. **Configuration:**
   - Change sensor settings
   - Change mode
   - Verify commands sent

## Further Reading

- **Implementation Guide:** `docs/data collection/phase3-web-interface-guide.md`
- **Enhancement Guide:** `docs/data collection/phase3-b-enhancements-guide.md`
- **Project Status:** `docs/data collection/PROJECT_STATUS.md`
- **Vite Docs:** https://vitejs.dev/
- **React Docs:** https://react.dev/
- **Tailwind Docs:** https://tailwindcss.com/

---

*Last Updated: November 14, 2025*
*For questions: Consult main project README.md*
