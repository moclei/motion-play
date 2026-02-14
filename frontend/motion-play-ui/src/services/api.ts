import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT;

export type SessionType = 'proximity' | 'interrupt';

export interface Session {
    session_id: string;
    device_id: string;
    session_type?: SessionType;  // 'proximity' (default) or 'interrupt'
    start_timestamp: string;
    end_timestamp?: string;
    duration_ms: number;
    mode: string;
    sample_count: number;
    event_count?: number;  // For interrupt sessions
    sample_rate: number;
    labels?: string[];
    notes?: string;
    created_at: number;

    // Config fields
    active_sensors?: ActiveSensor[];
    vcnl4040_config?: VCNL4040Config;
    interrupt_config?: InterruptConfig;

    // Live Debug capture metadata (optional, present when mode === 'live_debug')
    capture_reason?: 'detection' | 'missed_event';
    detection_direction?: 'a_to_b' | 'b_to_a';
    detection_confidence?: number;
}

export interface SensorReading {
    timestamp_offset: number;
    position: number;
    pcb_id: number;
    side: number;
    proximity: number;
    ambient: number;
}

export interface ProximitySessionData {
    session: Session;
    session_type: 'proximity';
    readings: SensorReading[];
}

export interface InterruptSessionData {
    session: Session;
    session_type: 'interrupt';
    events: InterruptEvent[];
}

export type SessionData = ProximitySessionData | InterruptSessionData;

// Type guards for session data
export function isInterruptSession(data: SessionData): data is InterruptSessionData {
    return data.session_type === 'interrupt' || data.session.session_type === 'interrupt';
}

export function isProximitySession(data: SessionData): data is ProximitySessionData {
    return !isInterruptSession(data);
}

export interface VCNL4040Config {
    sample_rate_hz: number;
    led_current: string;
    integration_time: string;
    duty_cycle: string;
    high_resolution: boolean;
    read_ambient: boolean;
    i2c_clock_khz?: number; // Optional for backward compatibility with old sessions
    multi_pulse?: string;   // Multi-pulse mode: "1", "2", "4", or "8" pulses per measurement
}

export interface InterruptConfig {
    // Calibration-based thresholds (relative to auto-calibrated baseline)
    threshold_margin: number;    // Trigger when prox exceeds baseline + margin
    hysteresis: number;          // Gap between high and low thresholds
    integration_time: number;    // 1-8 for 1T-8T
    multi_pulse: number;         // 1, 2, 4, or 8 pulses
    persistence: number;         // Consecutive hits before interrupt (1-4)
    smart_persistence: boolean;  // Enable fast response mode
    mode: 'normal' | 'logic';    // normal or logic output mode
    led_current: string;         // LED current (e.g., "200mA")
}

export interface InterruptEvent {
    timestamp_us: number;
    board_id: number;
    sensor_position: number;
    event_type: 'close' | 'away' | 'unknown';
    raw_flags?: number;
}

export interface ActiveSensor {
    pos: number;
    pcb: number;
    side: number;
    name: string;
    active: boolean;
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
    async deleteSession(sessionId: string): Promise<any> {
        console.log('API: Deleting session:', sessionId);
        const response = await axios.delete(`${API_BASE_URL}/sessions/${sessionId}`);
        console.log('API: Delete response:', response.data);
        return response.data;
    }

    // Send command to device
    async sendCommand(command: string, params?: Record<string, any>): Promise<void> {
        const deviceId = import.meta.env.VITE_DEVICE_ID || 'motionplay-device-001';
        await axios.post(`${API_BASE_URL}/device/command`, {
            device_id: deviceId,
            command,
            timestamp: Date.now(),
            ...params
        });
    }

    // Configure sensors (DEPRECATED - use updateDeviceConfig instead)
    async configureSensors(config: {
        sample_rate: number;
        led_current: string;
        integration_time: string;
        duty_cycle: string;
        high_resolution: boolean;
        read_ambient: boolean;
    }): Promise<void> {
        await this.sendCommand('configure_sensors', {
            sensor_config: config
        });
    }

    // Get device configuration from cloud (single source of truth)
    async getDeviceConfig(deviceId?: string): Promise<{
        device_id: string;
        sensor_config: VCNL4040Config;
        config_updated_at: number | null;
    }> {
        const device = deviceId || import.meta.env.VITE_DEVICE_ID || 'motionplay-device-001';
        const response = await axios.get(`${API_BASE_URL}/device/${device}/config`);
        return response.data;
    }

    // Update device configuration in cloud (and sends to firmware via MQTT)
    async updateDeviceConfig(config: VCNL4040Config, deviceId?: string): Promise<{
        device_id: string;
        sensor_config: VCNL4040Config;
        config_updated_at: number;
        message: string;
    }> {
        const device = deviceId || import.meta.env.VITE_DEVICE_ID || 'motionplay-device-001';
        const response = await axios.put(`${API_BASE_URL}/device/${device}/config`, {
            sensor_config: config
        });
        return response.data;
    }
}

export const api = new MotionPlayAPI();