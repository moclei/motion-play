import { useState, useMemo } from 'react';
import { Download, ChevronDown, Tag, Edit3 } from 'lucide-react';
import type { ProximitySessionData, SensorReading } from '../services/api';
import type { BrushTimeRange } from './SessionChart';

type ExportFormat = 'csv' | 'json';

interface ExportButtonProps {
    sessionData: ProximitySessionData;
    brushTimeRange?: BrushTimeRange | null;
}

// Convert tags to filename-safe format
const tagsToFilenameSuffix = (tags: string[]): string => {
    if (!tags || tags.length === 0) return '';
    return '-' + tags
        .map(tag => tag.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_-]/g, ''))
        .join('-');
};

export const ExportButton = ({ sessionData, brushTimeRange }: ExportButtonProps) => {
    const [format, setFormat] = useState<ExportFormat>('csv');
    const [customFilename, setCustomFilename] = useState('');
    const [useTagsInFilename, setUseTagsInFilename] = useState(false);
    const [showFilenameOptions, setShowFilenameOptions] = useState(false);
    
    const sessionTags = sessionData.session.labels || [];
    
    // Compute the effective filename
    const getFilename = (suffix: string = ''): string => {
        const defaultName = sessionData.session.session_id;
        let baseName = customFilename.trim() || defaultName;
        
        // Add tags if option is selected and there are tags
        if (useTagsInFilename && sessionTags.length > 0) {
            baseName += tagsToFilenameSuffix(sessionTags);
        }
        
        return `${baseName}${suffix}`;
    };
    
    // Preview of the filename
    const filenamePreview = useMemo(() => {
        return getFilename() + (format === 'csv' ? '.csv' : '.json');
    }, [customFilename, useTagsInFilename, sessionTags, format, sessionData.session.session_id]);

    const filterReadingsBySelection = (readings: SensorReading[]): SensorReading[] => {
        if (!brushTimeRange) return readings;
        
        return readings.filter(reading => 
            reading.timestamp_offset >= brushTimeRange.startTime && 
            reading.timestamp_offset <= brushTimeRange.endTime
        );
    };

    const exportData = (readings: SensorReading[], suffix: string = '') => {
        const filename = getFilename(suffix);
        
        if (format === 'json') {
            const exportPayload = {
                ...sessionData,
                readings
            };
            const dataStr = JSON.stringify(exportPayload, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${filename}.json`;
            link.click();
            URL.revokeObjectURL(url);
        } else {
            // CSV format
            const headers = [
                'timestamp_offset',
                'pcb_id',
                'side',
                'proximity',
                'ambient',
                'session_id',
                'device_id',
                'start_timestamp'
            ].join(',');

            const rows = readings.map(reading => {
                return [
                    reading.timestamp_offset,
                    reading.pcb_id,
                    reading.side,
                    reading.proximity,
                    reading.ambient,
                    sessionData.session.session_id,
                    sessionData.session.device_id,
                    sessionData.session.start_timestamp
                ].join(',');
            });

            const csv = [headers, ...rows].join('\n');
            const dataBlob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${filename}.csv`;
            link.click();
            URL.revokeObjectURL(url);
        }
    };

    const handleExportAll = () => {
        exportData(sessionData.readings);
    };

    const handleExportSelection = () => {
        if (!brushTimeRange) return;
        const filteredReadings = filterReadingsBySelection(sessionData.readings);
        exportData(filteredReadings, '_selection');
    };

    const formatTimeRange = (ms: number): string => {
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    };

    const selectionReadingCount = brushTimeRange 
        ? filterReadingsBySelection(sessionData.readings).length 
        : 0;

    return (
        <div className="space-y-3">
            {/* Filename options toggle */}
            <div className="flex items-center gap-2">
                <button
                    onClick={() => setShowFilenameOptions(!showFilenameOptions)}
                    className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded transition-colors ${
                        showFilenameOptions 
                            ? 'bg-gray-200 text-gray-700' 
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                    }`}
                >
                    <Edit3 size={12} />
                    Custom filename
                </button>
                {(customFilename || useTagsInFilename) && (
                    <span className="text-xs text-gray-500 font-mono truncate max-w-xs" title={filenamePreview}>
                        → {filenamePreview}
                    </span>
                )}
            </div>
            
            {/* Filename customization panel */}
            {showFilenameOptions && (
                <div className="p-3 bg-gray-100 rounded-lg space-y-2">
                    <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Custom filename (optional)</label>
                        <input
                            type="text"
                            value={customFilename}
                            onChange={(e) => setCustomFilename(e.target.value)}
                            placeholder={sessionData.session.session_id}
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    
                    {sessionTags.length > 0 && (
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={useTagsInFilename}
                                onChange={(e) => setUseTagsInFilename(e.target.checked)}
                                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <Tag size={14} className="text-gray-500" />
                            <span className="text-sm text-gray-700">Use tags in filename</span>
                            <span className="text-xs text-gray-500">
                                ({sessionTags.join(', ')})
                            </span>
                        </label>
                    )}
                    
                    <div className="text-xs text-gray-500">
                        Preview: <span className="font-mono">{filenamePreview}</span>
                    </div>
                </div>
            )}

            {/* Export buttons row */}
            <div className="flex flex-wrap items-center gap-3">
                {/* Format Dropdown */}
                <div className="relative">
                    <select
                        value={format}
                        onChange={(e) => setFormat(e.target.value as ExportFormat)}
                        className="appearance-none pl-3 pr-8 py-2 border border-gray-300 rounded bg-white text-gray-700 text-sm font-medium cursor-pointer hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                        <option value="csv">CSV</option>
                        <option value="json">JSON</option>
                    </select>
                    <ChevronDown 
                        size={16} 
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" 
                    />
                </div>

                {/* Download All Button */}
                <button
                    onClick={handleExportAll}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                    <Download size={16} />
                    Download All
                    <span className="text-blue-200 text-xs">
                        ({sessionData.readings.length.toLocaleString()})
                    </span>
                </button>

                {/* Download Selection Button */}
                <button
                    onClick={handleExportSelection}
                    disabled={!brushTimeRange}
                    className={`flex items-center gap-2 px-4 py-2 rounded transition-colors text-sm font-medium ${
                        brushTimeRange 
                            ? 'bg-emerald-600 text-white hover:bg-emerald-700' 
                            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    }`}
                    title={brushTimeRange ? `Export ${selectionReadingCount} readings from ${formatTimeRange(brushTimeRange.startTime)} to ${formatTimeRange(brushTimeRange.endTime)}` : 'Use the brush tool on the chart to select a time range'}
                >
                    <Download size={16} />
                    {brushTimeRange ? (
                        <>
                            Download Selection
                            <span className="text-emerald-200 text-xs">
                                ({formatTimeRange(brushTimeRange.startTime)} – {formatTimeRange(brushTimeRange.endTime)})
                            </span>
                        </>
                    ) : (
                        'No Selection'
                    )}
                </button>
            </div>
        </div>
    );
};
