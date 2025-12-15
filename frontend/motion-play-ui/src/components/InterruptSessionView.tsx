import { useMemo, useState } from 'react';
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import type { InterruptEvent, InterruptConfig } from '../services/api';
import { Zap, Clock, ArrowUp, ArrowDown, ChevronDown, ChevronUp, ArrowRight, HelpCircle, Download } from 'lucide-react';

// Direction detection types
interface DetectionResult {
    direction: 'A_TO_B' | 'B_TO_A' | 'UNKNOWN';
    confidence: number;
    sideAFirstTime: number;  // microseconds
    sideBFirstTime: number;  // microseconds
    timeGapUs: number;
    sideAEvents: InterruptEvent[];
    sideBEvents: InterruptEvent[];
}

// Sensor position to side mapping
// S1 (positions 0, 2, 4) = Side A
// S2 (positions 1, 3, 5) = Side B
const getSide = (sensorPosition: number): 'A' | 'B' => {
    return sensorPosition % 2 === 0 ? 'A' : 'B';
};

// Detection algorithm parameters
const DETECTION_WINDOW_US = 200000;  // 200ms window to group events into a single detection
const MIN_CONFIDENCE_THRESHOLD = 0.5;

/**
 * Analyze interrupt events to detect direction of movement
 * Groups events into detection windows and determines direction based on
 * which side triggered first.
 */
function detectDirections(events: InterruptEvent[]): DetectionResult[] {
    if (events.length === 0) return [];

    // Filter to only "close" events (object approaching)
    const closeEvents = events.filter(e => e.event_type === 'close');
    if (closeEvents.length === 0) return [];

    // Sort by timestamp
    const sortedEvents = [...closeEvents].sort((a, b) => a.timestamp_us - b.timestamp_us);

    // Group events into detection windows
    const detections: DetectionResult[] = [];
    let windowStart = sortedEvents[0].timestamp_us;
    let currentWindow: InterruptEvent[] = [];

    for (const event of sortedEvents) {
        if (event.timestamp_us - windowStart > DETECTION_WINDOW_US) {
            // Process current window
            if (currentWindow.length > 0) {
                const result = analyzeWindow(currentWindow);
                if (result) detections.push(result);
            }
            // Start new window
            windowStart = event.timestamp_us;
            currentWindow = [event];
        } else {
            currentWindow.push(event);
        }
    }

    // Process final window
    if (currentWindow.length > 0) {
        const result = analyzeWindow(currentWindow);
        if (result) detections.push(result);
    }

    return detections;
}

/**
 * Analyze a single detection window to determine direction
 */
function analyzeWindow(events: InterruptEvent[]): DetectionResult | null {
    if (events.length === 0) return null;

    // Separate by side
    const sideAEvents = events.filter(e => getSide(e.sensor_position) === 'A');
    const sideBEvents = events.filter(e => getSide(e.sensor_position) === 'B');

    // Need events from at least one side
    if (sideAEvents.length === 0 && sideBEvents.length === 0) return null;

    // Get first event time for each side
    const sideAFirstTime = sideAEvents.length > 0
        ? Math.min(...sideAEvents.map(e => e.timestamp_us))
        : Infinity;
    const sideBFirstTime = sideBEvents.length > 0
        ? Math.min(...sideBEvents.map(e => e.timestamp_us))
        : Infinity;

    // Determine direction based on which side triggered first
    // IMPORTANT: We need BOTH sides to have events to determine direction
    let direction: 'A_TO_B' | 'B_TO_A' | 'UNKNOWN';
    let timeGapUs: number;

    // If either side has no events, we can't determine direction
    if (sideAEvents.length === 0 || sideBEvents.length === 0) {
        // Return null to indicate this window should be excluded from detections
        return null;
    }

    // Both sides have events - determine which triggered first
    if (sideAFirstTime < sideBFirstTime) {
        direction = 'A_TO_B';  // A triggered first
        timeGapUs = sideBFirstTime - sideAFirstTime;
    } else if (sideBFirstTime < sideAFirstTime) {
        direction = 'B_TO_A';  // B triggered first
        timeGapUs = sideAFirstTime - sideBFirstTime;
    } else {
        direction = 'UNKNOWN';  // Simultaneous (unlikely but possible)
        timeGapUs = 0;
    }

    // Calculate confidence based on:
    // 1. Time gap between sides (larger gap = more confident, but not TOO large)
    // 2. Number of events (more events = more confident)
    let confidence = 0;

    if (direction !== 'UNKNOWN') {
        // Base confidence from time gap (up to 50%)
        // Sweet spot: 5-50ms gap indicates clear directional movement
        const gapMs = timeGapUs / 1000;
        const gapConfidence = Math.min(gapMs / 50, 1) * 0.5;  // Max at 50ms gap

        // Both sides triggered - that's already a baseline (30%)
        const bothSidesConfidence = 0.3;

        // Confidence from number of events (20%)
        const eventCountConfidence = Math.min((sideAEvents.length + sideBEvents.length) / 4, 1) * 0.2;

        confidence = gapConfidence + bothSidesConfidence + eventCountConfidence;
    }

    return {
        direction,
        confidence,
        sideAFirstTime: sideAFirstTime === Infinity ? 0 : sideAFirstTime,
        sideBFirstTime: sideBFirstTime === Infinity ? 0 : sideBFirstTime,
        timeGapUs,
        sideAEvents,
        sideBEvents
    };
}

interface InterruptSessionViewProps {
    events: InterruptEvent[];
    config?: InterruptConfig;
    durationMs: number;
    sessionId?: string;
}

// Color palette for sensors
const SENSOR_COLORS = [
    '#ef4444', // red - sensor 0
    '#f97316', // orange - sensor 1
    '#eab308', // yellow - sensor 2
    '#22c55e', // green - sensor 3
    '#3b82f6', // blue - sensor 4
    '#8b5cf6', // purple - sensor 5
];

const SENSOR_LABELS = ['P1S1', 'P1S2', 'P2S1', 'P2S2', 'P3S1', 'P3S2'];

// Custom tooltip component
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="bg-white p-3 border rounded-lg shadow-lg text-sm">
                <p className="font-bold text-gray-800">
                    {SENSOR_LABELS[data.sensor_position] || `Sensor ${data.sensor_position}`}
                </p>
                <p className="text-gray-600">
                    Time: <span className="font-mono">{(data.timestamp_us / 1000).toFixed(1)} ms</span>
                </p>
                <p className={data.event_type === 'close' ? 'text-green-600' : 'text-red-600'}>
                    {data.event_type === 'close' ? '↑ Close' : '↓ Away'}
                </p>
                <p className="text-gray-500 text-xs">Board {data.board_id}</p>
                {data.isPartOfDetection && (
                    <p className="text-purple-600 font-medium text-xs mt-1">
                        ★ Part of direction detection
                    </p>
                )}
            </div>
        );
    }
    return null;
};

type EventFilter = 'close' | 'away' | 'unknown' | 'all';

export const InterruptSessionView = ({ events, config, durationMs, sessionId }: InterruptSessionViewProps) => {
    const [showTable, setShowTable] = useState(true);
    const [tableLimit, setTableLimit] = useState(50);
    const [eventFilter, setEventFilter] = useState<EventFilter>('close');
    const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');

    // Export functions
    const exportEvents = (eventsToExport: InterruptEvent[], suffix: string = '') => {
        const filename = `${sessionId || 'interrupt-session'}${suffix}`;

        if (exportFormat === 'json') {
            const exportData = {
                session_id: sessionId,
                duration_ms: durationMs,
                config: config,
                event_count: eventsToExport.length,
                events: eventsToExport
            };
            const dataStr = JSON.stringify(exportData, null, 2);
            const blob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${filename}.json`;
            link.click();
            URL.revokeObjectURL(url);
        } else {
            // CSV format
            const headers = ['timestamp_us', 'timestamp_ms', 'board_id', 'sensor_position', 'sensor_name', 'event_type', 'raw_flags'].join(',');
            const rows = eventsToExport.map(evt => [
                evt.timestamp_us,
                (evt.timestamp_us / 1000).toFixed(2),
                evt.board_id,
                evt.sensor_position,
                SENSOR_LABELS[evt.sensor_position] || `S${evt.sensor_position}`,
                evt.event_type,
                evt.raw_flags || 0
            ].join(','));

            const csv = [headers, ...rows].join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${filename}.csv`;
            link.click();
            URL.revokeObjectURL(url);
        }
    };

    // Detect directions from events
    const detections = useMemo(() => detectDirections(events), [events]);

    // Create a Set of timestamps that are part of direction detections
    const detectionEventTimestamps = useMemo(() => {
        const timestamps = new Set<number>();
        detections.forEach(d => {
            d.sideAEvents.forEach(e => timestamps.add(e.timestamp_us));
            d.sideBEvents.forEach(e => timestamps.add(e.timestamp_us));
        });
        return timestamps;
    }, [detections]);

    // Filter events based on selected filter
    const filteredEvents = useMemo(() => {
        if (eventFilter === 'all') return events;
        return events.filter(e => e.event_type === eventFilter);
    }, [events, eventFilter]);

    // Transform events for scatter plot
    const chartData = useMemo(() => {
        return filteredEvents.map((evt, idx) => ({
            ...evt,
            // Convert microseconds to milliseconds for display
            time_ms: evt.timestamp_us / 1000,
            // Y-axis: sensor position (0-5)
            y_value: evt.sensor_position,
            // Size based on event type - larger if part of detection
            size: detectionEventTimestamps.has(evt.timestamp_us) ? 120 : (evt.event_type === 'close' ? 80 : 60),
            // Mark if part of a detection
            isPartOfDetection: detectionEventTimestamps.has(evt.timestamp_us),
            index: idx,
        }));
    }, [filteredEvents, detectionEventTimestamps]);

    // Separate data by detection status for different scatter styles
    const detectedCloseEvents = useMemo(() =>
        chartData.filter(e => e.event_type === 'close' && e.isPartOfDetection), [chartData]);
    const undetectedCloseEvents = useMemo(() =>
        chartData.filter(e => e.event_type === 'close' && !e.isPartOfDetection), [chartData]);
    const awayEvents = useMemo(() =>
        chartData.filter(e => e.event_type === 'away'), [chartData]);

    // Calculate statistics
    const stats = useMemo(() => {
        const sensorCounts: Record<number, { close: number; away: number }> = {};
        let firstEventTime = Infinity;
        let lastEventTime = 0;

        events.forEach(evt => {
            if (!sensorCounts[evt.sensor_position]) {
                sensorCounts[evt.sensor_position] = { close: 0, away: 0 };
            }
            sensorCounts[evt.sensor_position][evt.event_type]++;

            if (evt.timestamp_us < firstEventTime) firstEventTime = evt.timestamp_us;
            if (evt.timestamp_us > lastEventTime) lastEventTime = evt.timestamp_us;
        });

        return {
            totalEvents: events.length,
            closeCount: events.filter(e => e.event_type === 'close').length,
            awayCount: events.filter(e => e.event_type === 'away').length,
            sensorCounts,
            activeWindow: events.length > 0 ? (lastEventTime - firstEventTime) / 1000 : 0,
        };
    }, [events]);

    return (
        <div className="space-y-6">
            {/* Stats Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gradient-to-br from-cyan-50 to-cyan-100 p-4 rounded-lg border border-cyan-200">
                    <div className="flex items-center gap-2 text-cyan-700 mb-1">
                        <Zap size={16} />
                        <span className="text-xs font-medium uppercase">Total Events</span>
                    </div>
                    <div className="text-2xl font-bold text-cyan-900">{stats.totalEvents}</div>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                    <div className="flex items-center gap-2 text-green-700 mb-1">
                        <ArrowUp size={16} />
                        <span className="text-xs font-medium uppercase">Close Events</span>
                    </div>
                    <div className="text-2xl font-bold text-green-900">{stats.closeCount}</div>
                </div>

                <div className="bg-gradient-to-br from-red-50 to-red-100 p-4 rounded-lg border border-red-200">
                    <div className="flex items-center gap-2 text-red-700 mb-1">
                        <ArrowDown size={16} />
                        <span className="text-xs font-medium uppercase">Away Events</span>
                    </div>
                    <div className="text-2xl font-bold text-red-900">{stats.awayCount}</div>
                </div>

                <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 text-gray-700 mb-1">
                        <Clock size={16} />
                        <span className="text-xs font-medium uppercase">Active Window</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{stats.activeWindow.toFixed(0)} ms</div>
                </div>
            </div>

            {/* Direction Detection Results */}
            {detections.length > 0 && (
                <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-4">
                        <h3 className="font-semibold text-indigo-900">Direction Detection</h3>
                        <span className="text-xs text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
                            {detections.length} detection{detections.length !== 1 ? 's' : ''}
                        </span>
                    </div>

                    <div className="space-y-3">
                        {detections.map((detection, idx) => (
                            <div key={idx} className="bg-white rounded-lg p-3 border border-indigo-100 shadow-sm">
                                <div className="flex items-center justify-between">
                                    {/* Direction Arrow */}
                                    <div className="flex items-center gap-3">
                                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-bold ${detection.direction === 'A_TO_B'
                                            ? 'bg-blue-100 text-blue-700'
                                            : detection.direction === 'B_TO_A'
                                                ? 'bg-orange-100 text-orange-700'
                                                : 'bg-gray-100 text-gray-600'
                                            }`}>
                                            {detection.direction === 'A_TO_B' ? (
                                                <>
                                                    <span>A</span>
                                                    <ArrowRight size={20} />
                                                    <span>B</span>
                                                </>
                                            ) : detection.direction === 'B_TO_A' ? (
                                                <>
                                                    <span>B</span>
                                                    <ArrowRight size={20} />
                                                    <span>A</span>
                                                </>
                                            ) : (
                                                <>
                                                    <HelpCircle size={16} />
                                                    <span>Unknown</span>
                                                </>
                                            )}
                                        </div>

                                        {/* Confidence */}
                                        <div className="flex items-center gap-2">
                                            <div className="h-2 w-24 bg-gray-200 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full transition-all ${detection.confidence >= 0.7 ? 'bg-green-500' :
                                                        detection.confidence >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                                        }`}
                                                    style={{ width: `${detection.confidence * 100}%` }}
                                                />
                                            </div>
                                            <span className="text-sm text-gray-600 font-medium">
                                                {(detection.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </div>

                                    {/* Timing Details */}
                                    <div className="text-right text-sm">
                                        <div className="text-gray-500">
                                            Time gap: <span className="font-mono font-medium text-gray-700">
                                                {(detection.timeGapUs / 1000).toFixed(1)} ms
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            A: {detection.sideAEvents.length} events,
                                            B: {detection.sideBEvents.length} events
                                        </div>
                                    </div>
                                </div>

                                {/* Timeline mini-view */}
                                <div className="mt-3 pt-3 border-t border-gray-100">
                                    <div className="flex gap-4 text-xs">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-1 text-blue-600 font-medium mb-1">
                                                Side A (S1 sensors)
                                            </div>
                                            <div className="h-6 bg-blue-50 rounded relative">
                                                {detection.sideAEvents.map((evt, i) => (
                                                    <div
                                                        key={i}
                                                        className="absolute w-2 h-2 bg-blue-500 rounded-full top-1/2 -translate-y-1/2"
                                                        style={{
                                                            left: `${((evt.timestamp_us - Math.min(detection.sideAFirstTime, detection.sideBFirstTime)) / detection.timeGapUs) * 80 + 10}%`
                                                        }}
                                                        title={`${SENSOR_LABELS[evt.sensor_position]} at ${(evt.timestamp_us / 1000).toFixed(1)}ms`}
                                                    />
                                                ))}
                                                {detection.sideAEvents.length === 0 && (
                                                    <span className="absolute inset-0 flex items-center justify-center text-gray-400">No events</span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-1 text-orange-600 font-medium mb-1">
                                                Side B (S2 sensors)
                                            </div>
                                            <div className="h-6 bg-orange-50 rounded relative">
                                                {detection.sideBEvents.map((evt, i) => (
                                                    <div
                                                        key={i}
                                                        className="absolute w-2 h-2 bg-orange-500 rounded-full top-1/2 -translate-y-1/2"
                                                        style={{
                                                            left: `${((evt.timestamp_us - Math.min(detection.sideAFirstTime, detection.sideBFirstTime)) / detection.timeGapUs) * 80 + 10}%`
                                                        }}
                                                        title={`${SENSOR_LABELS[evt.sensor_position]} at ${(evt.timestamp_us / 1000).toFixed(1)}ms`}
                                                    />
                                                ))}
                                                {detection.sideBEvents.length === 0 && (
                                                    <span className="absolute inset-0 flex items-center justify-center text-gray-400">No events</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* No detections message */}
            {detections.length === 0 && events.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-yellow-800">
                        <HelpCircle size={16} />
                        <span className="font-medium">No direction detections</span>
                    </div>
                    <p className="text-sm text-yellow-700 mt-1">
                        No "close" events were found that could be analyzed for direction.
                        This session may only contain "away" events.
                    </p>
                </div>
            )}

            {/* Scatter Plot */}
            <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-800">Interrupt Event Timeline</h3>
                    <div className="flex items-center gap-2">
                        <label htmlFor="event-filter" className="text-sm text-gray-600">Show:</label>
                        <select
                            id="event-filter"
                            value={eventFilter}
                            onChange={(e) => setEventFilter(e.target.value as EventFilter)}
                            className="text-sm border border-gray-300 rounded-md px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="close">Close events only</option>
                            <option value="away">Away events only</option>
                            <option value="unknown">Unknown events only</option>
                            <option value="all">All events</option>
                        </select>
                    </div>
                </div>

                {filteredEvents.length === 0 ? (
                    <div className="h-64 flex items-center justify-center text-gray-500">
                        {events.length === 0
                            ? 'No interrupt events recorded in this session'
                            : `No ${eventFilter} events in this session`}
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height={300}>
                        <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 60 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                                type="number"
                                dataKey="time_ms"
                                name="Time"
                                unit=" ms"
                                domain={[0, durationMs]}
                                tick={{ fontSize: 12 }}
                                tickFormatter={(v) => `${v.toFixed(0)}`}
                                label={{ value: 'Time (ms)', position: 'bottom', offset: 0 }}
                            />
                            <YAxis
                                type="number"
                                dataKey="sensor_position"
                                name="Sensor"
                                domain={[-0.5, 5.5]}
                                ticks={[0, 1, 2, 3, 4, 5]}
                                tickFormatter={(v) => SENSOR_LABELS[v] || `S${v}`}
                                tick={{ fontSize: 11 }}
                                label={{ value: 'Sensor', angle: -90, position: 'insideLeft' }}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend />

                            {/* Close events that are part of direction detections - highlighted */}
                            <Scatter
                                name="Detected (Close)"
                                data={detectedCloseEvents}
                                fill="#8b5cf6"
                                stroke="#5b21b6"
                                strokeWidth={2}
                                shape="star"
                                legendType="star"
                            />

                            {/* Close events NOT part of detections */}
                            <Scatter
                                name="Unmatched (Close)"
                                data={undetectedCloseEvents}
                                fill="#22c55e"
                                shape="triangle"
                                legendType="triangle"
                            />

                            {/* Away events */}
                            <Scatter
                                name="Away"
                                data={awayEvents}
                                fill="#ef4444"
                                shape="diamond"
                                legendType="diamond"
                            />
                        </ScatterChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Config Info */}
            {config && (
                <div className="bg-gray-50 border rounded-lg p-4">
                    <h3 className="font-semibold text-gray-800 mb-3">Interrupt Configuration (Auto-Calibrated)</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                            <span className="text-gray-500">Threshold Margin:</span>
                            <span className="ml-2 font-mono">{config.threshold_margin}</span>
                        </div>
                        <div>
                            <span className="text-gray-500">Hysteresis:</span>
                            <span className="ml-2 font-mono">{config.hysteresis}</span>
                        </div>
                        <div>
                            <span className="text-gray-500">Integration:</span>
                            <span className="ml-2 font-mono">{config.integration_time}T</span>
                        </div>
                        <div>
                            <span className="text-gray-500">Multi-Pulse:</span>
                            <span className="ml-2 font-mono">{config.multi_pulse}P</span>
                        </div>
                        <div>
                            <span className="text-gray-500">Persistence:</span>
                            <span className="ml-2 font-mono">{config.persistence}</span>
                        </div>
                        <div>
                            <span className="text-gray-500">Mode:</span>
                            <span className="ml-2 font-mono">{config.mode}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Export Section */}
            <div className="bg-gray-50 border rounded-lg p-4">
                <h3 className="font-semibold text-gray-800 mb-3">Export Data</h3>
                <div className="flex flex-wrap items-center gap-3">
                    <select
                        value={exportFormat}
                        onChange={(e) => setExportFormat(e.target.value as 'csv' | 'json')}
                        className="appearance-none pl-3 pr-8 py-2 border border-gray-300 rounded bg-white text-gray-700 text-sm font-medium cursor-pointer hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="csv">CSV</option>
                        <option value="json">JSON</option>
                    </select>

                    <button
                        onClick={() => exportEvents(events)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm font-medium"
                    >
                        <Download size={16} />
                        Download All
                        <span className="text-blue-200 text-xs">({events.length})</span>
                    </button>

                    {eventFilter !== 'all' && filteredEvents.length !== events.length && (
                        <button
                            onClick={() => exportEvents(filteredEvents, `_${eventFilter}`)}
                            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 transition-colors text-sm font-medium"
                        >
                            <Download size={16} />
                            Download Filtered
                            <span className="text-emerald-200 text-xs">({filteredEvents.length} {eventFilter})</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Event Table */}
            <div className="bg-white border rounded-lg">
                <button
                    onClick={() => setShowTable(!showTable)}
                    className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                    <h3 className="font-semibold text-gray-800">
                        Event Log ({filteredEvents.length} {eventFilter === 'all' ? '' : eventFilter + ' '}events)
                    </h3>
                    {showTable ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </button>

                {showTable && (
                    <div className="border-t">
                        <div className="overflow-x-auto max-h-96 overflow-y-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-gray-50 sticky top-0">
                                    <tr>
                                        <th className="px-4 py-2 text-left font-medium text-gray-600">#</th>
                                        <th className="px-4 py-2 text-left font-medium text-gray-600">Time (ms)</th>
                                        <th className="px-4 py-2 text-left font-medium text-gray-600">Sensor</th>
                                        <th className="px-4 py-2 text-left font-medium text-gray-600">Board</th>
                                        <th className="px-4 py-2 text-left font-medium text-gray-600">Type</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    {filteredEvents.slice(0, tableLimit).map((evt, idx) => (
                                        <tr key={idx} className="hover:bg-gray-50">
                                            <td className="px-4 py-2 text-gray-500 font-mono">{idx + 1}</td>
                                            <td className="px-4 py-2 font-mono text-gray-800">
                                                {(evt.timestamp_us / 1000).toFixed(2)}
                                            </td>
                                            <td className="px-4 py-2">
                                                <span
                                                    className="px-2 py-0.5 rounded text-white text-xs font-medium"
                                                    style={{ backgroundColor: SENSOR_COLORS[evt.sensor_position] }}
                                                >
                                                    {SENSOR_LABELS[evt.sensor_position]}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 text-gray-600">{evt.board_id}</td>
                                            <td className="px-4 py-2">
                                                <span className={`flex items-center gap-1 ${evt.event_type === 'close'
                                                    ? 'text-green-600'
                                                    : 'text-red-600'
                                                    }`}>
                                                    {evt.event_type === 'close'
                                                        ? <ArrowUp size={14} />
                                                        : <ArrowDown size={14} />}
                                                    {evt.event_type}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {filteredEvents.length > tableLimit && (
                            <div className="p-4 border-t bg-gray-50 flex items-center justify-between">
                                <span className="text-sm text-gray-500">
                                    Showing {tableLimit} of {filteredEvents.length} events
                                </span>
                                <button
                                    onClick={() => setTableLimit(prev => prev + 50)}
                                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                                >
                                    Load more
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
