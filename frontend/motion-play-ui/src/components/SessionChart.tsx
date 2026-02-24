import { useState, useRef, useCallback, memo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from 'recharts';
import type { SensorReading, Session } from '../services/api';

// Time range selection for export (decoupled from chart behavior)
export interface BrushTimeRange {
    startTime: number;
    endTime: number;
}

interface Props {
    readings: SensorReading[];
    session?: Session;  // Session metadata for confirmation panel
    onBrushChange?: (range: BrushTimeRange | null) => void;
}

// Data processing utilities
const applyMovingAverage = (data: number[], windowSize: number): number[] => {
    const result: number[] = [];
    for (let i = 0; i < data.length; i++) {
        const start = Math.max(0, i - Math.floor(windowSize / 2));
        const end = Math.min(data.length, i + Math.ceil(windowSize / 2));
        const window = data.slice(start, end);
        const avg = window.reduce((sum, val) => sum + val, 0) / window.length;
        result.push(avg);
    }
    return result;
};

const applyThreshold = (data: number[], threshold: number): (number | null)[] => {
    return data.map(val => val >= threshold ? val : null);
};

// Custom tooltip component for the chart
interface CustomTooltipProps {
    active?: boolean;
    payload?: Array<{ name: string; value: number; color: string }>;
    label?: number;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
    if (!active || !payload || payload.length === 0) {
        return null;
    }

    return (
        <div className="bg-white border border-gray-300 rounded shadow-lg p-2 text-sm">
            <p className="font-semibold text-gray-800 mb-1 border-b pb-1">
                Time: {label}ms
            </p>
            <div className="space-y-0.5">
                {payload.map((entry, index) => (
                    entry.value !== null && entry.value !== undefined && (
                        <p key={index} style={{ color: entry.color }}>
                            {entry.name}: {Math.round(entry.value)}
                        </p>
                    )
                ))}
            </div>
        </div>
    );
};

export const SessionChart = memo(({ readings, session, onBrushChange }: Props) => {
    const [selectedSide, setSelectedSide] = useState<number | null>(null);
    const [selectedPcb, setSelectedPcb] = useState<number | null>(null);
    const [brushRange, setBrushRange] = useState<{ startMs: number; endMs: number } | null>(null);

    // Ref for debouncing brush change notifications (doesn't affect chart behavior)
    const brushDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const onBrushChangeRef = useRef(onBrushChange);
    onBrushChangeRef.current = onBrushChange;

    // Data processing options
    const [enableSmoothing, setEnableSmoothing] = useState(false);
    const [smoothingWindow, setSmoothingWindow] = useState(5);
    const [enableBaselineRemoval, setEnableBaselineRemoval] = useState(false);
    const [enableThreshold, setEnableThreshold] = useState(false);
    const [thresholdValue, setThresholdValue] = useState(10);

    // Apply both PCB and Side filters
    const filteredReadings = readings.filter(r => {
        const pcbMatch = selectedPcb === null || r.pcb_id === selectedPcb;
        const sideMatch = selectedSide === null || r.side === selectedSide;
        return pcbMatch && sideMatch;
    });

    // Group readings by side for stats (within the PCB filter if active)
    const s1Readings = filteredReadings.filter(r => r.side === 1);
    const s2Readings = filteredReadings.filter(r => r.side === 2);

    // Group readings by individual sensor (pcb_id + side)
    const sensorGroups = new Map<string, SensorReading[]>();
    filteredReadings.forEach(r => {
        const key = `P${r.pcb_id}S${r.side}`;
        if (!sensorGroups.has(key)) {
            sensorGroups.set(key, []);
        }
        sensorGroups.get(key)!.push(r);
    });

    // Sort each sensor's readings by timestamp
    sensorGroups.forEach((readings) => {
        readings.sort((a, b) => a.timestamp_offset - b.timestamp_offset);
    });

    // Find the time range - always start from 0 for consistent x-axis intervals
    // This ensures the chart x-axis is always 0, 10, 20, 30... regardless of where actual data starts
    const allTimestamps = filteredReadings.map(r => r.timestamp_offset);
    const minTime = 0;
    const maxTime = Math.max(...allTimestamps);

    // Sample data at regular time intervals (every 10ms) for consistent spacing
    const SAMPLE_INTERVAL_MS = 10;
    const timePoints: number[] = [];
    for (let t = minTime; t <= maxTime; t += SAMPLE_INTERVAL_MS) {
        timePoints.push(t);
    }

    // For each sensor, map readings to nearest time point
    const sensorDataMaps = new Map<string, Map<number, number | null>>();

    sensorGroups.forEach((sensorReadings, sensorKey) => {
        // First, create base data array
        const rawData: number[] = [];
        const timeToIndexMap = new Map<number, number>();

        timePoints.forEach((timePoint, idx) => {
            timeToIndexMap.set(timePoint, idx);

            // Find reading closest to this time point
            let closestReading: SensorReading | null = null;
            let minDiff = Infinity;

            for (const reading of sensorReadings) {
                const diff = Math.abs(reading.timestamp_offset - timePoint);
                if (diff < minDiff && diff < SAMPLE_INTERVAL_MS * 2) {
                    minDiff = diff;
                    closestReading = reading;
                }
            }

            rawData.push(closestReading ? closestReading.proximity : 0);
        });

        // Apply data processing filters
        let processedData: (number | null)[] = [...rawData];

        // 1. Baseline removal (do this first if enabled)
        if (enableBaselineRemoval) {
            const nonZeroData = rawData.filter(v => v > 0);
            if (nonZeroData.length > 0) {
                const baseline = Math.min(...nonZeroData);
                processedData = rawData.map(v => v > 0 ? v - baseline : 0);
            }
        }

        // 2. Smoothing (moving average)
        if (enableSmoothing) {
            processedData = applyMovingAverage(
                processedData.map(v => v ?? 0),
                smoothingWindow
            );
        }

        // 3. Threshold filter (do this last)
        if (enableThreshold) {
            processedData = applyThreshold(
                processedData.map(v => v ?? 0),
                thresholdValue
            );
        }

        // Convert back to map
        const dataMap = new Map<number, number | null>();
        timePoints.forEach((timePoint, idx) => {
            const value = processedData[idx];
            // Only add non-zero values or nulls from threshold
            if (value !== null && (value > 0 || !enableThreshold)) {
                dataMap.set(timePoint, value);
            }
        });

        sensorDataMaps.set(sensorKey, dataMap);
    });

    // Create chart data with evenly spaced time points
    const chartData = timePoints.map(time => {
        const dataPoint: any = { time };
        sensorDataMaps.forEach((dataMap, sensorKey) => {
            dataPoint[sensorKey] = dataMap.get(time);
        });
        return dataPoint;
    });

    // Debounced brush change handler - notifies parent of time range without affecting chart
    const handleBrushChange = useCallback((brushState: { startIndex?: number; endIndex?: number }) => {
        // Cancel any pending notification
        if (brushDebounceRef.current) {
            clearTimeout(brushDebounceRef.current);
        }

        // Debounce: wait 300ms after last change before notifying parent
        brushDebounceRef.current = setTimeout(() => {
            if (!onBrushChangeRef.current) return;

            console.log('handleBrushChange, we have a brush change function');

            if (brushState.startIndex === undefined || brushState.endIndex === undefined) {
                console.log('handleBrushChange, no start or end index');
                onBrushChangeRef.current(null);
                return;
            }
            console.log('handleBrushChange, we had start and end index');

            const startTime = chartData[brushState.startIndex]?.time ?? 0;
            const endTime = chartData[brushState.endIndex]?.time ?? 0;

            // Only report as a selection if it's not the full range
            const isFullRange = brushState.startIndex === 0 && brushState.endIndex === chartData.length - 1;

            if (isFullRange) {
                console.log('handleBrushChange, it was full range so we are sending null');
                setBrushRange(null);
                onBrushChangeRef.current(null);
            } else {
                console.log('handleBrushChange, it was not full range so we are sending the time range');
                setBrushRange({ startMs: startTime, endMs: endTime });
                onBrushChangeRef.current({ startTime, endTime });
            }
        }, 300);
    }, [chartData]);

    // Calculate statistics (guard against empty arrays and invalid values)
    const validProximities = filteredReadings
        .map(r => r.proximity)
        .filter(p => typeof p === 'number' && !isNaN(p));

    const avgProximity = validProximities.length > 0
        ? validProximities.reduce((sum, p) => sum + p, 0) / validProximities.length
        : 0;
    const maxProximity = validProximities.length > 0
        ? Math.max(...validProximities)
        : 0;
    const minProximity = validProximities.length > 0
        ? Math.min(...validProximities)
        : 0;

    // Session Confirmation: compute time window in seconds
    const timeWindowMs = allTimestamps.length > 0
        ? Math.max(...allTimestamps) - Math.min(...allTimestamps)
        : 0;
    const timeWindowSeconds = (timeWindowMs / 1000).toFixed(3);

    // Get unique PCB IDs from the session for the dropdown
    // Filter to only valid PCB IDs (1-3) and sort them
    const uniquePcbs = Array.from(
        new Set(
            readings
                .map(r => r.pcb_id)
                .filter(pcb => pcb >= 1 && pcb <= 3) // Only valid PCB IDs
        )
    ).sort((a, b) => a - b); // Numeric sort

    return (
        <div className="space-y-4">
            {/* Data Processing Controls (collapsed by default) */}
            <details className="border border-purple-200 rounded">
                <summary className="p-2 bg-purple-50 cursor-pointer text-sm font-medium text-gray-700 flex items-center gap-2">
                    <span>Data Processing</span>
                    {(enableSmoothing || enableBaselineRemoval || enableThreshold) && (
                        <span className="text-xs text-purple-600 font-normal">
                            ({[enableSmoothing && 'smoothing', enableBaselineRemoval && 'baseline', enableThreshold && 'threshold'].filter(Boolean).join(', ')})
                        </span>
                    )}
                </summary>
                <div className="p-3 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <input type="checkbox" checked={enableSmoothing} onChange={(e) => setEnableSmoothing(e.target.checked)} className="rounded" />
                            Moving Average Smoothing
                        </label>
                        {enableSmoothing && (
                            <div className="ml-6 space-y-1">
                                <label className="text-xs text-gray-600">Window: {smoothingWindow}</label>
                                <input type="range" min="3" max="21" step="2" value={smoothingWindow} onChange={(e) => setSmoothingWindow(parseInt(e.target.value))} className="w-full" />
                            </div>
                        )}
                    </div>
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <input type="checkbox" checked={enableBaselineRemoval} onChange={(e) => setEnableBaselineRemoval(e.target.checked)} className="rounded" />
                            Remove Baseline
                        </label>
                        <p className="text-xs text-gray-500 ml-6">Subtract minimum value</p>
                    </div>
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <input type="checkbox" checked={enableThreshold} onChange={(e) => setEnableThreshold(e.target.checked)} className="rounded" />
                            Peak Threshold Filter
                        </label>
                        {enableThreshold && (
                            <div className="ml-6 space-y-1">
                                <label className="text-xs text-gray-600">Min: {thresholdValue}</label>
                                <input type="range" min="0" max="20" step="1" value={thresholdValue} onChange={(e) => setThresholdValue(parseInt(e.target.value))} className="w-full" />
                            </div>
                        )}
                    </div>
                </div>
            </details>

            {/* Filter Controls */}
            <div className="flex gap-4 items-center p-4 bg-gray-50 rounded border">
                <span className="font-semibold text-gray-700">Sensor Filter:</span>

                {/* PCB Filter */}
                <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">PCB:</label>
                    <select
                        value={selectedPcb ?? 'all'}
                        onChange={(e) => setSelectedPcb(e.target.value === 'all' ? null : Number(e.target.value))}
                        className="px-3 py-1.5 border rounded bg-white text-gray-900 text-sm"
                    >
                        <option value="all">All</option>
                        {uniquePcbs.map(pcb => (
                            <option key={pcb} value={pcb}>PCB {pcb}</option>
                        ))}
                    </select>
                </div>

                {/* Side Filter */}
                <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">Side:</label>
                    <select
                        value={selectedSide ?? 'all'}
                        onChange={(e) => setSelectedSide(e.target.value === 'all' ? null : Number(e.target.value))}
                        className="px-3 py-1.5 border rounded bg-white text-gray-900 text-sm"
                    >
                        <option value="all">All</option>
                        <option value="1">Side 1</option>
                        <option value="2">Side 2</option>
                    </select>
                </div>

                {/* Active Filter Display */}
                {(selectedPcb !== null || selectedSide !== null) && (
                    <div className="flex items-center gap-2 ml-auto">
                        <span className="text-sm text-gray-600">Showing:</span>
                        <span className="text-sm font-semibold text-blue-600">
                            {selectedPcb !== null && `PCB ${selectedPcb}`}
                            {selectedPcb !== null && selectedSide !== null && ' - '}
                            {selectedSide !== null && `Side ${selectedSide}`}
                        </span>
                        <button
                            onClick={() => {
                                setSelectedPcb(null);
                                setSelectedSide(null);
                            }}
                            className="text-xs px-2 py-1 bg-gray-200 hover:bg-gray-300 rounded"
                        >
                            Clear
                        </button>
                    </div>
                )}
            </div>

            {/* Stats + Legend row */}
            <div className="flex items-center gap-4 text-xs text-gray-600 px-1">
                <span><span className="font-medium">{timeWindowSeconds}s</span> window</span>
                <span className="text-gray-300">|</span>
                <span><span className="font-medium">{filteredReadings.length}</span> readings</span>
                <span className="text-gray-300">|</span>
                <span>avg <span className="font-medium">{isNaN(avgProximity) ? '0' : avgProximity.toFixed(1)}</span></span>
                <span>max <span className="font-medium">{isNaN(maxProximity) ? '0' : maxProximity}</span></span>
                <span>min <span className="font-medium">{isNaN(minProximity) ? '0' : minProximity}</span></span>
                {brushRange && (
                    <>
                        <span className="text-gray-300">|</span>
                        <span className="text-purple-600">viewing {((brushRange.endMs - brushRange.startMs) / 1000).toFixed(3)}s</span>
                    </>
                )}
                <span className="ml-auto flex items-center gap-3">
                    <span className="flex items-center gap-1"><span className="inline-block w-4 h-0.5 bg-green-700"></span> S1</span>
                    <span className="flex items-center gap-1"><span className="inline-block w-4 h-0.5 bg-blue-700"></span> S2</span>
                    <span className="text-gray-400">solid=PCB1 dash=PCB2 dot=PCB3</span>
                </span>
            </div>

            {/* Proximity Chart */}
            <div className="bg-white p-4 rounded border">
                <h3 className="font-semibold mb-4">
                    Proximity Over Time - Individual Sensors
                    {(enableSmoothing || enableBaselineRemoval || enableThreshold) && (
                        <span className="text-sm text-purple-600 ml-2">
                            (processed data)
                        </span>
                    )}
                </h3>

                <ResponsiveContainer width="100%" height={500}>
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                            dataKey="time"
                            label={{ value: 'Time (ms)', position: 'insideBottom', offset: -5 }}
                        />
                        <YAxis label={{ value: 'Proximity', angle: -90, position: 'insideLeft' }} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />

                        {/* Brush component for time window selection */}
                        <Brush
                            dataKey="time"
                            height={40}
                            stroke="#8884d8"
                            fill="#e0e7ff"
                            travellerWidth={10}
                            onChange={handleBrushChange}
                        >
                            {/* Mini chart in brush - simplified view */}
                            <LineChart>
                                {Array.from(sensorGroups.keys()).sort().map(sensorKey => {
                                    const side = parseInt(sensorKey.charAt(3));
                                    const color = side === 1 ? '#15803d' : '#1e40af';
                                    return (
                                        <Line
                                            key={sensorKey}
                                            type="monotone"
                                            dataKey={sensorKey}
                                            stroke={color}
                                            strokeWidth={1}
                                            dot={false}
                                            connectNulls
                                        />
                                    );
                                })}
                            </LineChart>
                        </Brush>

                        {/* Dynamically render lines for each sensor */}
                        {Array.from(sensorGroups.keys()).sort().map(sensorKey => {
                            // Parse sensor key (e.g., "P1S1" -> pcb=1, side=1)
                            const pcb = parseInt(sensorKey.charAt(1));
                            const side = parseInt(sensorKey.charAt(3));

                            // Color by side: Green for S1, Blue for S2
                            const color = side === 1 ? '#15803d' : '#1e40af';

                            // Stroke pattern by PCB: solid (PCB1), dash (PCB2), dot (PCB3)
                            const strokeDasharray = pcb === 1 ? '0' : pcb === 2 ? '5 5' : '2 2';

                            return (
                                <Line
                                    key={sensorKey}
                                    type="monotone"
                                    dataKey={sensorKey}
                                    stroke={color}
                                    strokeWidth={2}
                                    strokeDasharray={strokeDasharray}
                                    name={sensorKey}
                                    dot={false}
                                    connectNulls
                                />
                            );
                        })}
                    </LineChart>
                </ResponsiveContainer>

                {/* Time window zoom hint */}
                <div className="mt-2 text-xs text-gray-500 text-center">
                    💡 Drag the handles in the bottom timeline to zoom into specific time windows
                </div>
            </div>

            {/* Sensor Statistics (collapsed by default) */}
            <details className="border rounded">
                <summary className="p-3 bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 flex items-center justify-between">
                    <span>Sensor Statistics</span>
                    <span className="text-xs text-gray-500 font-normal">
                        S1: {s1Readings.length} readings (avg {s1Readings.length > 0 ? (s1Readings.reduce((sum, r) => sum + r.proximity, 0) / s1Readings.length).toFixed(1) : '0'})
                        &nbsp;·&nbsp;
                        S2: {s2Readings.length} readings (avg {s2Readings.length > 0 ? (s2Readings.reduce((sum, r) => sum + r.proximity, 0) / s2Readings.length).toFixed(1) : '0'})
                    </span>
                </summary>
                <div className="p-3 space-y-3">
                    <div className="grid grid-cols-3 gap-3">
                        {Array.from(sensorGroups.entries())
                            .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
                            .map(([sensorKey, sensorReadings]) => {
                                const pcb = parseInt(sensorKey.charAt(1));
                                const side = parseInt(sensorKey.charAt(3));
                                const avgProx = sensorReadings.length > 0
                                    ? (sensorReadings.reduce((sum, r) => sum + r.proximity, 0) / sensorReadings.length).toFixed(1)
                                    : '0.0';
                                const maxProx = sensorReadings.length > 0
                                    ? Math.max(...sensorReadings.map(r => r.proximity))
                                    : 0;
                                const bgColor = side === 1 ? 'bg-green-50' : 'bg-blue-50';
                                const borderColor = side === 1 ? 'border-green-200' : 'border-blue-200';
                                const dotColor = side === 1 ? 'bg-green-700' : 'bg-blue-800';
                                const lineStyle = pcb === 1 ? 'Solid' : pcb === 2 ? 'Dashed' : 'Dotted';

                                return (
                                    <div key={sensorKey} className={`p-2 rounded border text-xs ${bgColor} ${borderColor}`}>
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="font-semibold text-gray-800">{sensorKey}</span>
                                            <div className={`w-2 h-2 rounded-full ${dotColor}`}></div>
                                        </div>
                                        <span className="text-gray-600">{lineStyle}</span>
                                        <span className="mx-1">·</span>
                                        <span className="text-gray-700">{sensorReadings.length} readings</span>
                                        <span className="mx-1">·</span>
                                        <span className="text-gray-700">avg {avgProx}</span>
                                        <span className="mx-1">·</span>
                                        <span className="text-gray-700">max {maxProx}</span>
                                    </div>
                                );
                            })}
                    </div>
                </div>
            </details>

            {/* Session Confirmation Panel */}
            {session && <SessionConfirmationPanel
                session={session}
                displayedReadings={filteredReadings.length}
            />}
        </div>
    );
});

// ============================================================================
// Session Confirmation Panel Component
// ============================================================================

interface ConfirmationPanelProps {
    session: Session;
    displayedReadings: number;
}

function StatusDot({ ok }: { ok: boolean }) {
    return (
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
    );
}

function SessionConfirmationPanel({ session, displayedReadings }: ConfirmationPanelProps) {
    const [isOpen, setIsOpen] = useState(false);
    const summary = session.session_summary;
    const isLiveDebug = session.mode === 'live_debug';

    if (!summary && !session.pipeline_status) {
        return (
            <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="text-sm text-gray-500 italic">
                    Session confirmation data not available (older session or summary not received)
                </div>
            </div>
        );
    }

    const pipelineStatus = session.pipeline_status || 'pending';
    const statusColor = pipelineStatus === 'complete' ? 'text-green-700 bg-green-50 border-green-200'
        : pipelineStatus === 'partial' ? 'text-yellow-700 bg-yellow-50 border-yellow-200'
            : 'text-gray-600 bg-gray-50 border-gray-200';
    const statusLabel = pipelineStatus === 'complete' ? 'Complete'
        : pipelineStatus === 'partial' ? 'Partial'
            : 'Pending';

    return (
        <div className="border rounded">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full p-3 flex items-center justify-between text-left ${statusColor} border-0 rounded`}
            >
                <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">Session Confirmation</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColor}`}>
                        {statusLabel}
                    </span>
                </div>
                <span className="text-xs">{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && summary && (
                <div className="p-4 space-y-4 bg-white">
                    {/* Pipeline Chain */}
                    <div>
                        <h4 className="font-semibold text-sm text-gray-800 mb-2">Pipeline Integrity</h4>
                        {isLiveDebug && (
                            <p className="text-xs text-gray-500 mb-2 italic">
                                Live Debug: only a capture window is transmitted, so Collected &gt; Transmitted is normal.
                            </p>
                        )}
                        <div className="space-y-1.5 text-xs">
                            <PipelineRow
                                label="Firmware Collected"
                                value={summary.readings_collected.reduce((a, b) => a + b, 0)}
                                ok={summary.readings_collected.reduce((a, b) => a + b, 0) > 0}
                            />
                            <PipelineRow
                                label="I2C Errors"
                                value={summary.i2c_errors.reduce((a, b) => a + b, 0)}
                                ok={summary.i2c_errors.reduce((a, b) => a + b, 0) === 0}
                            />
                            <PipelineRow
                                label="Queue Drops"
                                value={summary.queue_drops}
                                ok={summary.queue_drops === 0}
                            />
                            <PipelineRow
                                label="Buffer Drops"
                                value={summary.buffer_drops}
                                ok={summary.buffer_drops === 0}
                            />
                            <PipelineRow
                                label="Firmware Transmitted"
                                value={summary.total_readings_transmitted}
                                ok={isLiveDebug
                                    ? summary.total_readings_transmitted > 0
                                    : summary.total_readings_transmitted === summary.readings_collected.reduce((a, b) => a + b, 0) - summary.queue_drops - summary.buffer_drops}
                            />
                            <PipelineRow
                                label="Frontend Loaded"
                                value={displayedReadings}
                                ok={displayedReadings > 0 && displayedReadings <= summary.total_readings_transmitted}
                            />
                        </div>
                    </div>

                    {/* Theoretical vs Actual */}
                    <div className="bg-gray-50 p-3 rounded text-xs">
                        <h4 className="font-semibold text-sm text-gray-800 mb-2">Theoretical vs Actual</h4>
                        {summary.measured_cycle_rate_hz > 0 && summary.duration_ms > 0 ? (
                            <p className="text-gray-700">
                                Config target: {summary.measured_cycle_rate_hz} Hz measured
                                × {summary.num_active_sensors} sensors
                                × {(summary.duration_ms / 1000).toFixed(3)}s
                                = <span className="font-bold">{summary.theoretical_max_readings}</span> readings
                            </p>
                        ) : (
                            <p className="text-gray-500 italic">
                                Theoretical estimate not available (duration or cycle rate not measured)
                            </p>
                        )}
                        <p className="text-gray-700 mt-1">
                            Firmware transmitted: <span className="font-bold">{summary.total_readings_transmitted}</span>
                            {isLiveDebug && (
                                <span className="ml-1 text-gray-500">
                                    (capture window — {summary.readings_collected.reduce((a, b) => a + b, 0).toLocaleString()} total collected during listening)
                                </span>
                            )}
                        </p>
                        <p className="text-gray-700 mt-1">
                            Frontend displaying: <span className="font-bold">{displayedReadings}</span>
                            {summary.total_readings_transmitted > 0 && (
                                <span className="ml-1">
                                    ({((displayedReadings / summary.total_readings_transmitted) * 100).toFixed(1)}% of transmitted)
                                </span>
                            )}
                        </p>
                    </div>

                    {/* Per-Sensor Breakdown */}
                    <div>
                        <h4 className="font-semibold text-sm text-gray-800 mb-2">Per-Sensor Breakdown</h4>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs text-gray-800">
                                <thead>
                                    <tr className="border-b text-left text-gray-600">
                                        <th className="py-1 pr-3">Sensor</th>
                                        <th className="py-1 pr-3">Collected</th>
                                        <th className="py-1 pr-3">I2C Errors</th>
                                        <th className="py-1 pr-3">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {summary.readings_collected.map((count, idx) => {
                                        const pcb = Math.floor(idx / 2) + 1;
                                        const side = (idx % 2) + 1;
                                        const sensorName = `P${pcb}S${side}`;
                                        const errors = summary.i2c_errors[idx] || 0;
                                        return (
                                            <tr key={idx} className="border-b border-gray-100">
                                                <td className="py-1 pr-3 font-medium">{sensorName}</td>
                                                <td className="py-1 pr-3">{count}</td>
                                                <td className="py-1 pr-3">{errors}</td>
                                                <td className="py-1 pr-3">
                                                    <StatusDot ok={errors === 0 && count > 0} />
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Session Info */}
                    <div className="text-xs text-gray-500 pt-2 border-t">
                        <span>Batches: {session.batches_received ?? '?'} received, {summary.total_batches_transmitted} transmitted</span>
                        <span className="mx-2">|</span>
                        <span>Cycle rate: {summary.measured_cycle_rate_hz} Hz</span>
                        <span className="mx-2">|</span>
                        <span>Duration: {(summary.duration_ms / 1000).toFixed(3)}s</span>
                    </div>
                </div>
            )}
        </div>
    );
}

function PipelineRow({ label, value, ok }: { label: string; value: number; ok: boolean }) {
    return (
        <div className="flex items-center gap-2">
            <StatusDot ok={ok} />
            <span className="text-gray-700 w-40">{label}:</span>
            <span className="font-mono font-bold text-gray-900">{value.toLocaleString()}</span>
        </div>
    );
}