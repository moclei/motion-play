import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT;

export interface Session {
    session_id: string;
    device_id: string;
    start_timestamp: string;
    end_timestamp?: string;
    duration_ms: number;
    mode: string;
    sample_count: number;
    sample_rate: number;
    labels?: string[];
    notes?: string;
    created_at: number;

    // Config fields
    active_sensors?: ActiveSensor[];
    vcnl4040_config?: VCNL4040Config;
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

export interface VCNL4040Config {
    sample_rate_hz: number;
    led_current: string;
    integration_time: string;
    high_resolution: boolean;
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
}

export const api = new MotionPlayAPI();