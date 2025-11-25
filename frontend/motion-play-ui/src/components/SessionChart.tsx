import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from 'recharts';
import type { SensorReading } from '../services/api';

interface Props {
    readings: SensorReading[];
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

export const SessionChart = ({ readings }: Props) => {
    const [selectedSide, setSelectedSide] = useState<number | null>(null);
    const [selectedPcb, setSelectedPcb] = useState<number | null>(null);

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

    // Find the time range - use 0 as minimum to avoid negative timestamps
    const allTimestamps = filteredReadings.map(r => r.timestamp_offset);
    const minTime = Math.max(0, Math.min(...allTimestamps));
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
            {/* Data Processing Controls */}
            <div className="p-4 bg-purple-50 border border-purple-200 rounded">
                <div className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <span>📊 Data Processing</span>
                    <span className="text-xs font-normal text-gray-600">(for analysis & ML prep)</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Smoothing */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <input
                                type="checkbox"
                                checked={enableSmoothing}
                                onChange={(e) => setEnableSmoothing(e.target.checked)}
                                className="rounded"
                            />
                            Moving Average Smoothing
                        </label>
                        {enableSmoothing && (
                            <div className="ml-6 space-y-1">
                                <label className="text-xs text-gray-600">
                                    Window Size: {smoothingWindow} samples
                                </label>
                                <input
                                    type="range"
                                    min="3"
                                    max="21"
                                    step="2"
                                    value={smoothingWindow}
                                    onChange={(e) => setSmoothingWindow(parseInt(e.target.value))}
                                    className="w-full"
                                />
                            </div>
                        )}
                    </div>

                    {/* Baseline Removal */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <input
                                type="checkbox"
                                checked={enableBaselineRemoval}
                                onChange={(e) => setEnableBaselineRemoval(e.target.checked)}
                                className="rounded"
                            />
                            Remove Baseline
                        </label>
                        <p className="text-xs text-gray-500 ml-6">
                            Subtract minimum value to show relative changes
                        </p>
                    </div>

                    {/* Threshold Filter */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <input
                                type="checkbox"
                                checked={enableThreshold}
                                onChange={(e) => setEnableThreshold(e.target.checked)}
                                className="rounded"
                            />
                            Peak Threshold Filter
                        </label>
                        {enableThreshold && (
                            <div className="ml-6 space-y-1">
                                <label className="text-xs text-gray-600">
                                    Show only values ≥ {thresholdValue}
                                </label>
                                <input
                                    type="range"
                                    min="0"
                                    max="20"
                                    step="1"
                                    value={thresholdValue}
                                    onChange={(e) => setThresholdValue(parseInt(e.target.value))}
                                    className="w-full"
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>

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

            {/* Statistics */}
            <div className="grid grid-cols-4 gap-4">
                <div className="p-4 bg-blue-50 rounded">
                    <div className="text-sm text-gray-600">Total Readings</div>
                    <div className="text-2xl font-bold text-gray-900">{filteredReadings.length}</div>
                </div>
                <div className="p-4 bg-green-50 rounded">
                    <div className="text-sm text-gray-600">Avg Proximity</div>
                    <div className="text-2xl font-bold text-gray-900">
                        {isNaN(avgProximity) ? '0.0' : avgProximity.toFixed(1)}
                    </div>
                </div>
                <div className="p-4 bg-yellow-50 rounded">
                    <div className="text-sm text-gray-600">Max Proximity</div>
                    <div className="text-2xl font-bold text-gray-900">
                        {isNaN(maxProximity) ? '0' : maxProximity}
                    </div>
                </div>
                <div className="p-4 bg-red-50 rounded">
                    <div className="text-sm text-gray-600">Min Proximity</div>
                    <div className="text-2xl font-bold text-gray-900">
                        {isNaN(minProximity) ? '0' : minProximity}
                    </div>
                </div>
            </div>

            {/* Visual Legend */}
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
                <div className="text-sm font-semibold text-gray-800 mb-2">Chart Legend:</div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                        <span className="font-medium text-gray-700">Colors:</span>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="w-8 h-0.5 bg-green-700"></div>
                            <span className="text-gray-600">Side 1 (S1)</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="w-8 h-0.5 bg-blue-700"></div>
                            <span className="text-gray-600">Side 2 (S2)</span>
                        </div>
                    </div>
                    <div>
                        <span className="font-medium text-gray-700">Line Styles:</span>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="w-8 h-0.5 bg-gray-700"></div>
                            <span className="text-gray-600">Solid = PCB 1</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="w-8 h-0.5 bg-gray-700" style={{ borderTop: '2px dashed' }}></div>
                            <span className="text-gray-600">Dashed = PCB 2</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="w-8 h-0.5 bg-gray-700" style={{ borderTop: '2px dotted' }}></div>
                            <span className="text-gray-600">Dotted = PCB 3</span>
                        </div>
                    </div>
                </div>
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
                        <Tooltip />
                        <Legend />

                        {/* Brush component for time window selection */}
                        <Brush
                            dataKey="time"
                            height={40}
                            stroke="#8884d8"
                            fill="#e0e7ff"
                            travellerWidth={10}
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

            {/* Individual Sensor Stats */}
            <div>
                <h4 className="font-semibold text-gray-800 mb-3">Individual Sensor Statistics</h4>
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

                            // Style based on side
                            const bgColor = side === 1 ? 'bg-green-50' : 'bg-blue-50';
                            const borderColor = side === 1 ? 'border-green-200' : 'border-blue-200';
                            const dotColor = side === 1 ? 'bg-green-700' : 'bg-blue-800';

                            // Line style indicator
                            const lineStyle = pcb === 1 ? 'Solid' : pcb === 2 ? 'Dashed' : 'Dotted';

                            return (
                                <div key={sensorKey} className={`p-3 rounded border ${bgColor} ${borderColor}`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <h5 className="font-semibold text-gray-800 text-sm">{sensorKey}</h5>
                                        <div className={`w-3 h-3 rounded-full ${dotColor}`}></div>
                                    </div>
                                    <p className="text-xs text-gray-600 mb-1">{lineStyle} Line</p>
                                    <p className="text-xs text-gray-700">Readings: {sensorReadings.length}</p>
                                    <p className="text-xs text-gray-700">Avg: {avgProx}</p>
                                    <p className="text-xs text-gray-700">Max: {maxProx}</p>
                                </div>
                            );
                        })}
                </div>
            </div>

            {/* Side Aggregates - Quick summary */}
            <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded border bg-green-50 border-green-200">
                    <div className="flex items-center justify-between mb-1">
                        <h4 className="font-semibold text-gray-800 text-sm">
                            All Side 1 Sensors (S1)
                        </h4>
                        <div className="w-3 h-3 rounded-full bg-green-700"></div>
                    </div>
                    <p className="text-xs text-gray-700">Total Readings: {s1Readings.length}</p>
                    <p className="text-xs text-gray-700">
                        Avg Proximity: {s1Readings.length > 0
                            ? (s1Readings.reduce((sum, r) => sum + r.proximity, 0) / s1Readings.length).toFixed(1)
                            : '0.0'}
                    </p>
                </div>
                <div className="p-3 rounded border bg-blue-50 border-blue-200">
                    <div className="flex items-center justify-between mb-1">
                        <h4 className="font-semibold text-gray-800 text-sm">
                            All Side 2 Sensors (S2)
                        </h4>
                        <div className="w-3 h-3 rounded-full bg-blue-800"></div>
                    </div>
                    <p className="text-xs text-gray-700">Total Readings: {s2Readings.length}</p>
                    <p className="text-xs text-gray-700">
                        Avg Proximity: {s2Readings.length > 0
                            ? (s2Readings.reduce((sum, r) => sum + r.proximity, 0) / s2Readings.length).toFixed(1)
                            : '0.0'}
                    </p>
                </div>
            </div>
        </div>
    );
};