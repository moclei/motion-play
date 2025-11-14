import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { SensorReading } from '../services/api';

interface Props {
    readings: SensorReading[];
}

export const SessionChart = ({ readings }: Props) => {
    const [selectedSide, setSelectedSide] = useState<number | null>(null);

    // Group readings by side for comparison
    const s1Readings = readings.filter(r => r.side === 1);
    const s2Readings = readings.filter(r => r.side === 2);

    // Filter readings based on selected side
    const filteredReadings = selectedSide === null
        ? readings
        : readings.filter(r => r.side === selectedSide);

    // Prepare data for chart (sample every 10th reading for performance)
    // Create separate arrays for each side, then merge them for the chart
    const side1Data = s1Readings
        .filter((_, i) => i % 10 === 0)
        .map(r => ({ time: r.timestamp_offset, side1: r.proximity, side2: undefined }));

    const side2Data = s2Readings
        .filter((_, i) => i % 10 === 0)
        .map(r => ({ time: r.timestamp_offset, side1: undefined, side2: r.proximity }));

    // Combine both arrays and sort by time
    let chartData: Array<{ time: number; side1?: number; side2?: number }>;

    if (selectedSide === 1) {
        chartData = side1Data;
    } else if (selectedSide === 2) {
        chartData = side2Data;
    } else {
        // Show both sides - merge the arrays
        chartData = [...side1Data, ...side2Data].sort((a, b) => a.time - b.time);
    }

    // Calculate statistics (guard against empty arrays and invalid values)
    const validProximities = readings
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

    return (
        <div className="space-y-4">
            {/* Statistics */}
            <div className="grid grid-cols-4 gap-4">
                <div className="p-4 bg-blue-50 rounded">
                    <div className="text-sm text-gray-600">Total Readings</div>
                    <div className="text-2xl font-bold text-gray-900">{readings.length}</div>
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

            {/* Proximity Chart */}
            <div className="bg-white p-4 rounded border">
                <h3 className="font-semibold mb-4">
                    Proximity Over Time
                    {selectedSide && (
                        <span className="text-sm font-normal text-gray-500 ml-2">
                            (Showing Side {selectedSide} only)
                        </span>
                    )}
                </h3>
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
                        {(selectedSide === null || selectedSide === 1) && (
                            <Line
                                type="monotone"
                                dataKey="side1"
                                stroke="#15803d"
                                strokeWidth={2}
                                name="Side 1"
                                dot={false}
                                connectNulls
                            />
                        )}
                        {(selectedSide === null || selectedSide === 2) && (
                            <Line
                                type="monotone"
                                dataKey="side2"
                                stroke="#1e40af"
                                strokeWidth={2}
                                name="Side 2"
                                dot={false}
                                connectNulls
                            />
                        )}
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Side Comparison - Click to filter chart */}
            <div className="grid grid-cols-2 gap-4">
                <div
                    onClick={() => setSelectedSide(selectedSide === 1 ? null : 1)}
                    className={`p-4 rounded border cursor-pointer transition-all ${selectedSide === 1
                        ? 'bg-green-100 border-green-600 ring-2 ring-green-600'
                        : selectedSide === 2
                            ? 'bg-gray-100 border-gray-300 opacity-50'
                            : 'bg-green-50 border-green-200 hover:bg-green-100 hover:border-green-400'
                        }`}
                    title="Click to filter chart to Side 1 only"
                >
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-800">Side 1 (S1)</h4>
                        <div className="w-4 h-4 rounded-full bg-green-700"></div>
                    </div>
                    <p className="text-sm text-gray-700">Readings: {s1Readings.length}</p>
                    <p className="text-sm text-gray-700">
                        Avg Proximity: {s1Readings.length > 0
                            ? (s1Readings.reduce((sum, r) => sum + r.proximity, 0) / s1Readings.length).toFixed(1)
                            : '0.0'}
                    </p>
                    {selectedSide === 1 && (
                        <p className="text-xs text-green-700 font-semibold mt-2">
                            ✓ Showing on chart
                        </p>
                    )}
                </div>
                <div
                    onClick={() => setSelectedSide(selectedSide === 2 ? null : 2)}
                    className={`p-4 rounded border cursor-pointer transition-all ${selectedSide === 2
                        ? 'bg-blue-100 border-blue-600 ring-2 ring-blue-600'
                        : selectedSide === 1
                            ? 'bg-gray-100 border-gray-300 opacity-50'
                            : 'bg-blue-50 border-blue-200 hover:bg-blue-100 hover:border-blue-400'
                        }`}
                    title="Click to filter chart to Side 2 only"
                >
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-800">Side 2 (S2)</h4>
                        <div className="w-4 h-4 rounded-full bg-blue-800"></div>
                    </div>
                    <p className="text-sm text-gray-700">Readings: {s2Readings.length}</p>
                    <p className="text-sm text-gray-700">
                        Avg Proximity: {s2Readings.length > 0
                            ? (s2Readings.reduce((sum, r) => sum + r.proximity, 0) / s2Readings.length).toFixed(1)
                            : '0.0'}
                    </p>
                    {selectedSide === 2 && (
                        <p className="text-xs text-blue-700 font-semibold mt-2">
                            ✓ Showing on chart
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};