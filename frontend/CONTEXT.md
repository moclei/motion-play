# Frontend Context

React web interface for device control, data visualization, and session management. Communicates with the ESP32 device indirectly through the AWS cloud infrastructure (API Gateway → Lambda → IoT Core).

> See `frontend/motion-play-ui/README.md` for detailed component documentation, TypeScript interfaces, and development workflow.

## Tech Stack

- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS v3
- **Charts:** Recharts
- **HTTP Client:** Axios
- **State Management:** Local state (useState/useRef) — no global state library

## What It Does

- **Device Control:** Start/stop data collection sessions, switch device modes (Idle/Debug/Play), configure sensor settings in real-time
- **Session Management:** Browse, filter, search, label, annotate, and delete recorded sessions
- **Data Visualization:** Interactive time-series charts of all 6 sensor channels with zoom, pan, hover. Data processing filters (smoothing, baseline removal, peak threshold) for analysis and ML prep
- **Data Export:** JSON and CSV export for ML training pipelines
- **Session Comparison:** Side-by-side visualization of multiple sessions

## Architecture

```
frontend/motion-play-ui/src/
├── App.tsx              # Main application, state coordinator, layout
├── components/          # React components (SessionList, SessionChart,
│                        #   DeviceControl, SensorConfig, ModeSelector, etc.)
└── services/
    └── api.ts           # Centralized API client (Axios)
```

Single-page app with a two-column layout: left column for device control + session list, right column for session detail + chart.

## Key Design Decisions

- **No WebSocket/real-time connection to device** — all communication goes through REST API → Lambda → MQTT. The frontend doesn't talk to the ESP32 directly.
- **Configuration tracking** — every session records the sensor config used, critical for ML training data integrity.
- **Client-side filtering** — session list filtering happens in the browser (fast, no extra API calls).
- **Cloud config authority** — the frontend is the authoritative source for sensor configuration. The device fetches config from cloud on boot.

## Environment Variables

```env
VITE_API_ENDPOINT=https://your-api-gateway-id.execute-api.us-west-2.amazonaws.com/prod
VITE_AWS_REGION=us-west-2
VITE_DEVICE_ID=motionplay-device-001
```

## Relationship to Other Aspects

- **Infrastructure:** Calls API Gateway endpoints defined in `infrastructure/`. See `infrastructure/CONTEXT.md` for endpoint details and MQTT message formats.
- **Firmware:** Sends commands that the firmware processes (start/stop collection, set mode, configure sensors). Does not communicate with the device directly.
- **Tools:** Exported session data (JSON/CSV) feeds into the ML training pipeline in `tools/ml-training/`.

---

*Last Updated: March 4, 2026*
