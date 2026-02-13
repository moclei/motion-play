import { useState, useRef, useCallback, useMemo, memo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush, ReferenceArea } from 'recharts';
import type { SensorReading, Session } from '../services/api';
import { detectEvents, formatDirection, summarizeEvents, DEFAULT_CONFIG, type DetectionEvent, type DetectorConfig } from '../lib/directionDetector';

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

    // Direction detection
    const [enableDetection, setEnableDetection] = useState(true);
    const [detectorConfig, setDetectorConfig] = useState<DetectorConfig>(DEFAULT_CONFIG);

    // Run direction detection on readings
    const detectionResults = useMemo(() => {
        if (!enableDetection || readings.length === 0) {
            return [];
        }
        return detectEvents(readings, detectorConfig);
    }, [readings, enableDetection, detectorConfig]);

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
                onBrushChangeRef.current(null);
            } else {
                console.log('handleBrushChange, it was not full range so we are sending the time range');
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

            {/* Direction Detection Results */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded">
                <div className="flex items-center justify-between mb-3">
                    <div className="font-semibold text-gray-800 flex items-center gap-2">
                        <span>🎯 Direction Detection</span>
                        <span className="text-xs font-normal text-gray-600">(algorithm testing)</span>
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                        <input
                            type="checkbox"
                            checked={enableDetection}
                            onChange={(e) => setEnableDetection(e.target.checked)}
                            className="rounded"
                        />
                        <span className="text-gray-700">Enable</span>
                    </label>
                </div>

                {enableDetection && (
                    <>
                        {/* Detection Config (collapsible) */}
                        <details className="mb-3">
                            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                                ⚙️ Algorithm Parameters
                            </summary>
                            <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-3 p-2 bg-white rounded border">
                                <div>
                                    <label className="text-xs text-gray-600 block">Smoothing Window</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="10"
                                        value={detectorConfig.smoothingWindow}
                                        onChange={(e) => setDetectorConfig(c => ({ ...c, smoothingWindow: parseInt(e.target.value) || 3 }))}
                                        className="w-full px-2 py-1 text-sm border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-600 block">Min Rise</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="50"
                                        value={detectorConfig.minRise}
                                        onChange={(e) => setDetectorConfig(c => ({ ...c, minRise: parseInt(e.target.value) || 10 }))}
                                        className="w-full px-2 py-1 text-sm border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-600 block">Max Peak Gap (ms)</label>
                                    <input
                                        type="number"
                                        min="10"
                                        max="500"
                                        value={detectorConfig.maxPeakGapMs}
                                        onChange={(e) => setDetectorConfig(c => ({ ...c, maxPeakGapMs: parseInt(e.target.value) || 100 }))}
                                        className="w-full px-2 py-1 text-sm border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-600 block">Wave Threshold (%)</label>
                                    <input
                                        type="number"
                                        min="0.05"
                                        max="0.5"
                                        step="0.05"
                                        value={detectorConfig.waveThresholdPct}
                                        onChange={(e) => setDetectorConfig(c => ({ ...c, waveThresholdPct: parseFloat(e.target.value) || 0.2 }))}
                                        className="w-full px-2 py-1 text-sm border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-600 block">Window Size (ms)</label>
                                    <input
                                        type="number"
                                        min="50"
                                        max="500"
                                        step="10"
                                        value={detectorConfig.windowSizeMs}
                                        onChange={(e) => setDetectorConfig(c => ({ ...c, windowSizeMs: parseInt(e.target.value) || 200 }))}
                                        className="w-full px-2 py-1 text-sm border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-600 block">Window Step (ms)</label>
                                    <input
                                        type="number"
                                        min="10"
                                        max="100"
                                        step="5"
                                        value={detectorConfig.windowStepMs}
                                        onChange={(e) => setDetectorConfig(c => ({ ...c, windowStepMs: parseInt(e.target.value) || 50 }))}
                                        className="w-full px-2 py-1 text-sm border rounded"
                                    />
                                </div>

                                {/* Adaptive Threshold Section */}
                                <div className="col-span-4 border-t pt-2 mt-2">
                                    <label className="flex items-center gap-2 text-xs font-medium text-gray-700 mb-2">
                                        <input
                                            type="checkbox"
                                            checked={detectorConfig.useAdaptiveThreshold}
                                            onChange={(e) => setDetectorConfig(c => ({ ...c, useAdaptiveThreshold: e.target.checked }))}
                                            className="rounded"
                                        />
                                        Adaptive Threshold (calculates noise floor from first N ms)
                                    </label>
                                </div>

                                {detectorConfig.useAdaptiveThreshold && (
                                    <>
                                        <div>
                                            <label className="text-xs text-gray-600 block">Baseline Window (ms)</label>
                                            <input
                                                type="number"
                                                min="50"
                                                max="500"
                                                step="50"
                                                value={detectorConfig.baselineWindowMs}
                                                onChange={(e) => setDetectorConfig(c => ({ ...c, baselineWindowMs: parseInt(e.target.value) || 200 }))}
                                                className="w-full px-2 py-1 text-sm border rounded"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-gray-600 block">Peak Multiplier (×baseline)</label>
                                            <input
                                                type="number"
                                                min="1.05"
                                                max="2"
                                                step="0.05"
                                                value={detectorConfig.peakMultiplier}
                                                onChange={(e) => setDetectorConfig(c => ({ ...c, peakMultiplier: parseFloat(e.target.value) || 2.0 }))}
                                                className="w-full px-2 py-1 text-sm border rounded"
                                            />
                                        </div>
                                    </>
                                )}

                                <div className="col-span-2 flex items-end">
                                    <button
                                        onClick={() => setDetectorConfig(DEFAULT_CONFIG)}
                                        className="px-3 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded"
                                    >
                                        Reset to Defaults
                                    </button>
                                </div>
                            </div>
                        </details>

                        {/* Results Summary */}
                        <div className="text-sm font-medium text-gray-800 mb-2">
                            {summarizeEvents(detectionResults)}
                        </div>

                        {/* Individual Events */}
                        {detectionResults.length > 0 ? (
                            <div className="space-y-2">
                                {detectionResults.map((event, idx) => (
                                    <div
                                        key={idx}
                                        className={`p-3 rounded border ${event.direction === 'A_TO_B'
                                            ? 'bg-green-50 border-green-300'
                                            : event.direction === 'B_TO_A'
                                                ? 'bg-blue-50 border-blue-300'
                                                : 'bg-gray-50 border-gray-300'
                                            }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <span className={`text-lg font-bold ${event.direction === 'A_TO_B' ? 'text-green-700' : 'text-blue-700'
                                                    }`}>
                                                    {formatDirection(event.direction)}
                                                </span>
                                                <span className="text-sm text-gray-600">
                                                    {Math.round(event.confidence * 100)}% confidence
                                                </span>
                                            </div>
                                            <span className="text-xs text-gray-500">
                                                Event #{idx + 1}
                                            </span>
                                        </div>
                                        <div className="mt-1 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-600">
                                            <div>
                                                <span className="font-medium">CoM A:</span> {Math.round(event.centerOfMassA)}ms
                                            </div>
                                            <div>
                                                <span className="font-medium">CoM B:</span> {Math.round(event.centerOfMassB)}ms
                                            </div>
                                            <div>
                                                <span className="font-medium">CoM Gap:</span> {Math.round(event.comGapMs)}ms
                                            </div>
                                            <div>
                                                <span className="font-medium">Window:</span> {event.windowStart}-{event.windowEnd}ms
                                            </div>
                                            <div>
                                                <span className="font-medium">Wave A:</span> {event.waveStartA}-{event.waveEndA}ms
                                            </div>
                                            <div>
                                                <span className="font-medium">Wave B:</span> {event.waveStartB}-{event.waveEndB}ms
                                            </div>
                                            <div>
                                                <span className="font-medium">Peak A:</span> {event.peakTimeA}ms ({Math.round(event.maxSignalA)})
                                            </div>
                                            <div>
                                                <span className="font-medium">Peak B:</span> {event.peakTimeB}ms ({Math.round(event.maxSignalB)})
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-sm text-gray-500 italic">
                                No events detected in this session. Try adjusting the algorithm parameters.
                            </div>
                        )}
                    </>
                )}
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
            <div className="grid grid-cols-5 gap-4">
                <div className="p-4 bg-purple-50 rounded">
                    <div className="text-sm text-gray-600">Time Window</div>
                    <div className="text-2xl font-bold text-gray-900">{timeWindowSeconds}s</div>
                </div>
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

                {/* Detection event wave markers - rendered above the chart */}
                {enableDetection && detectionResults.length > 0 && chartData.length > 0 && (
                    <div className="mb-2 space-y-1">
                        {detectionResults.map((event, idx) => {
                            // Calculate positions as percentages of the time range
                            const minTime = chartData[0]?.time ?? 0;
                            const maxTime = chartData[chartData.length - 1]?.time ?? 1;
                            const timeRange = maxTime - minTime;

                            if (timeRange <= 0) return null;

                            // Convert wave boundaries to percentages
                            const waveAStartPct = ((event.waveStartA - minTime) / timeRange) * 100;
                            const waveAEndPct = ((event.waveEndA - minTime) / timeRange) * 100;
                            const waveBStartPct = ((event.waveStartB - minTime) / timeRange) * 100;
                            const waveBEndPct = ((event.waveEndB - minTime) / timeRange) * 100;

                            // Clamp to valid range
                            const clamp = (val: number) => Math.max(0, Math.min(100, val));

                            return (
                                <div key={`wave-markers-${idx}`} className="relative h-8 bg-gray-50 rounded border">
                                    {/* Wave A bar (green) */}
                                    <div
                                        className="absolute h-2 top-1 rounded"
                                        style={{
                                            left: `${clamp(waveAStartPct)}%`,
                                            width: `${clamp(waveAEndPct - waveAStartPct)}%`,
                                            backgroundColor: '#22c55e',
                                        }}
                                    >
                                        <span className="absolute -top-0.5 left-1/2 -translate-x-1/2 text-[10px] font-bold text-green-700">A</span>
                                    </div>

                                    {/* Wave B bar (blue) */}
                                    <div
                                        className="absolute h-2 bottom-1 rounded"
                                        style={{
                                            left: `${clamp(waveBStartPct)}%`,
                                            width: `${clamp(waveBEndPct - waveBStartPct)}%`,
                                            backgroundColor: '#3b82f6',
                                        }}
                                    >
                                        <span className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 text-[10px] font-bold text-blue-700">B</span>
                                    </div>

                                    {/* Direction indicator */}
                                    <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-bold">
                                        <span className={event.direction === 'A_TO_B' ? 'text-green-600' : 'text-blue-600'}>
                                            {event.direction === 'A_TO_B' ? 'A → B' : 'B → A'}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

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

                        {/* Detection event reference areas - highlight the full wave span */}
                        {enableDetection && detectionResults.map((event, idx) => {
                            // Determine the full span based on direction
                            // A→B: A starts first, B ends last
                            // B→A: B starts first, A ends last
                            const rawX1 = event.direction === 'A_TO_B' ? event.waveStartA : event.waveStartB;
                            const rawX2 = event.direction === 'A_TO_B' ? event.waveEndB : event.waveEndA;

                            // Round to nearest 10 to match chart data points (sampled at 10ms intervals, starting from 0)
                            const x1 = Math.round(rawX1 / 10) * 10;
                            const x2 = Math.round(rawX2 / 10) * 10;

                            // Find max individual sensor reading within the detection window from actual chart data
                            const windowData = chartData.filter(d => d.time >= x1 && d.time <= x2);
                            let maxY = 0;
                            windowData.forEach(dataPoint => {
                                Array.from(sensorGroups.keys()).forEach(sensorKey => {
                                    const val = dataPoint[sensorKey];
                                    if (typeof val === 'number' && val > maxY) {
                                        maxY = val;
                                    }
                                });
                            });

                            // Y bounds: peak from chart data as top, threshold as bottom
                            // Clamp y2 to be within chart range (0 to maxY)
                            const y1 = maxY;
                            const threshold = detectorConfig.minRise;
                            const y2 = Math.min(threshold, maxY); // Don't go above the peak

                            const fill = event.direction === 'A_TO_B' ? '#22c55e' : '#3b82f6'; // green / blue

                            // DEBUG: Log the values
                            console.log(`ReferenceArea ${idx}:`, {
                                x1, x2, y1, y2,
                                threshold,
                                windowDataPoints: windowData.length
                            });

                            return (
                                <ReferenceArea
                                    key={`ref-area-${idx}`}
                                    x1={x1}
                                    x2={x2}
                                    y1={y1}
                                    y2={y2}
                                    fill={fill}
                                    fillOpacity={0.2}
                                    stroke={fill}
                                    strokeOpacity={0.6}
                                    strokeWidth={1}
                                />
                            );
                        })}

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

    if (!summary && !session.pipeline_status) {
        return (
            <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="text-sm text-gray-500 italic">
                    Session confirmation data not available (older session or summary not received)
                </div>
            </div>
        );
    }

    const storedCount = session.sample_count || 0;
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
                                ok={summary.total_readings_transmitted === summary.readings_collected.reduce((a, b) => a + b, 0) - summary.queue_drops - summary.buffer_drops}
                            />
                            <PipelineRow
                                label="Lambda Stored"
                                value={storedCount}
                                ok={storedCount === summary.total_readings_transmitted}
                            />
                            <PipelineRow
                                label="Frontend Loaded"
                                value={displayedReadings}
                                ok={displayedReadings === storedCount}
                            />
                        </div>
                    </div>

                    {/* Theoretical vs Actual */}
                    <div className="bg-gray-50 p-3 rounded text-xs">
                        <h4 className="font-semibold text-sm text-gray-800 mb-2">Theoretical vs Actual</h4>
                        <p className="text-gray-700">
                            Config target: {summary.measured_cycle_rate_hz || '?'} Hz measured
                            × {summary.num_active_sensors} sensors
                            × {(summary.duration_ms / 1000).toFixed(3)}s
                            = <span className="font-bold">{summary.theoretical_max_readings}</span> readings
                        </p>
                        <p className="text-gray-700 mt-1">
                            Actual collected: <span className="font-bold">{summary.readings_collected.reduce((a, b) => a + b, 0)}</span>
                            {summary.theoretical_max_readings > 0 && (
                                <span className="ml-1">
                                    ({((summary.readings_collected.reduce((a, b) => a + b, 0) / summary.theoretical_max_readings) * 100).toFixed(1)}% of theoretical)
                                </span>
                            )}
                        </p>
                        <p className="text-gray-700 mt-1">
                            Frontend displaying: <span className="font-bold">{displayedReadings}</span>
                            {summary.readings_collected.reduce((a, b) => a + b, 0) > 0 && (
                                <span className="ml-1">
                                    ({((displayedReadings / summary.readings_collected.reduce((a, b) => a + b, 0)) * 100).toFixed(1)}% of collected)
                                </span>
                            )}
                        </p>
                    </div>

                    {/* Per-Sensor Breakdown */}
                    <div>
                        <h4 className="font-semibold text-sm text-gray-800 mb-2">Per-Sensor Breakdown</h4>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs">
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
            <span className="font-mono font-bold">{value.toLocaleString()}</span>
        </div>
    );
}