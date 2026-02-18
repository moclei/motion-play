import { useState } from 'react';
import { api } from '../services/api';
import { Play, Square, ChevronDown, Settings, Target, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

type StartMode = 'debug' | 'play' | 'live_debug';

interface HeaderProps {
    onCollectionStopped?: () => void;
    onSettingsClick: () => void;
}

const MODE_CONFIG: Record<StartMode, { label: string; color: string; activeColor: string }> = {
    debug: {
        label: 'Debug',
        color: 'bg-blue-500 hover:bg-blue-600',
        activeColor: 'bg-blue-600',
    },
    play: {
        label: 'Play',
        color: 'bg-green-500 hover:bg-green-600',
        activeColor: 'bg-green-600',
    },
    live_debug: {
        label: 'Live Debug',
        color: 'bg-fuchsia-500 hover:bg-fuchsia-600',
        activeColor: 'bg-fuchsia-600',
    },
};

export const Header = ({ onCollectionStopped, onSettingsClick }: HeaderProps) => {
    const [collecting, setCollecting] = useState(false);
    const [activeMode, setActiveMode] = useState<StartMode | null>(null);
    const [selectedMode, setSelectedMode] = useState<StartMode>('live_debug');
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [calibrating, setCalibrating] = useState(false);

    const handleStart = async () => {
        try {
            toast.loading('Starting...', { id: 'start' });
            await api.sendCommand('set_mode', { mode: selectedMode });
            await api.sendCommand('start_collection');
            setCollecting(true);
            setActiveMode(selectedMode);
            toast.success(`Started in ${MODE_CONFIG[selectedMode].label} mode`, { id: 'start' });
        } catch (err) {
            toast.error('Failed to start', { id: 'start' });
            console.error(err);
        }
    };

    const handleStop = async () => {
        try {
            await api.sendCommand('stop_collection');
            await api.sendCommand('set_mode', { mode: 'idle' });
            setCollecting(false);
            setActiveMode(null);
            toast.success('Stopped');

            if (onCollectionStopped) {
                onCollectionStopped();
            }
        } catch (err) {
            toast.error('Failed to stop');
            console.error(err);
        }
    };

    const handleStartCalibration = async () => {
        if (collecting) {
            toast.error('Stop collection first');
            return;
        }

        try {
            setCalibrating(true);
            toast.loading('Starting calibration...', { id: 'calibration' });

            await api.sendCommand('set_mode', { mode: 'calibrate' });

            toast.success('Calibration started! Follow instructions on device display.', {
                id: 'calibration',
                duration: 5000
            });

            setTimeout(() => {
                setCalibrating(false);
            }, 30000);
        } catch (err) {
            toast.error('Failed to start calibration', { id: 'calibration' });
            setCalibrating(false);
            console.error(err);
        }
    };

    const handleMissedEvent = async () => {
        try {
            toast.loading('Capturing missed event...', { id: 'missed-event' });
            await api.sendCommand('capture_missed_event');
            toast.success('Missed event captured', { id: 'missed-event', duration: 3000 });
        } catch (err) {
            toast.error('Failed to capture missed event', { id: 'missed-event' });
            console.error(err);
        }
    };

    const modeConfig = MODE_CONFIG[selectedMode];

    return (
        <div className="bg-white shadow-md border-b">
            <div className="px-6 py-4 space-y-4">
                {/* Title Row */}
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-bold text-gray-900">
                        Motion Play Dashboard
                    </h1>
                    <div className="text-sm text-gray-500">
                        Device: {import.meta.env.VITE_DEVICE_ID || 'unknown'}
                    </div>
                </div>

                {/* Controls Row */}
                <div className="flex items-center gap-4">
                    {/* Start with Mode Dropdown */}
                    <div className="flex items-center gap-0 relative">
                        <button
                            onClick={handleStart}
                            disabled={collecting}
                            className={`flex items-center gap-2 px-4 py-2 text-white rounded-l font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed ${collecting ? '' : modeConfig.color
                                }`}
                        >
                            <Play size={18} />
                            Start ({modeConfig.label})
                        </button>
                        <button
                            onClick={() => setDropdownOpen(!dropdownOpen)}
                            disabled={collecting}
                            className={`px-2 py-2 text-white rounded-r border-l border-white/30 font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed ${collecting ? '' : modeConfig.color
                                }`}
                        >
                            <ChevronDown size={18} />
                        </button>

                        {dropdownOpen && !collecting && (
                            <>
                                <div
                                    className="fixed inset-0 z-10"
                                    onClick={() => setDropdownOpen(false)}
                                />
                                <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-20 min-w-[180px]">
                                    {(Object.entries(MODE_CONFIG) as [StartMode, typeof modeConfig][]).map(([mode, config]) => (
                                        <button
                                            key={mode}
                                            onClick={() => {
                                                setSelectedMode(mode);
                                                setDropdownOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm font-medium ${selectedMode === mode ? 'bg-gray-100 text-gray-900' : 'text-gray-700'
                                                }`}
                                        >
                                            {config.label}
                                            {selectedMode === mode && <span className="ml-2 text-green-600">✓</span>}
                                        </button>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>

                    {/* Stop Button */}
                    <button
                        onClick={handleStop}
                        disabled={!collecting}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-400 disabled:text-gray-200 disabled:cursor-not-allowed transition-colors font-medium"
                    >
                        <Square size={18} />
                        Stop
                    </button>

                    {/* Status indicator */}
                    <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${collecting ? 'bg-red-500 animate-pulse' : 'bg-gray-300'}`}></div>
                        <span className="text-sm text-gray-600">
                            {collecting && activeMode
                                ? `Recording (${MODE_CONFIG[activeMode].label})`
                                : 'Idle'}
                        </span>
                    </div>

                    <div className="border-l h-8 mx-2"></div>

                    {/* Missed Event Button - visible in Live Debug mode while collecting */}
                    {activeMode === 'live_debug' && collecting && (
                        <button
                            onClick={handleMissedEvent}
                            className="flex items-center gap-2 px-4 py-2 bg-fuchsia-500 text-white rounded hover:bg-fuchsia-600 transition-colors font-medium"
                            title="Capture data for a missed detection (saves ~3s of data)"
                        >
                            <AlertCircle size={18} />
                            Missed Event
                        </button>
                    )}

                    {/* Calibration Button */}
                    <button
                        onClick={handleStartCalibration}
                        disabled={calibrating || collecting}
                        className={`flex items-center gap-2 px-4 py-2 rounded transition-colors font-medium ${calibrating
                            ? 'bg-purple-500 text-white animate-pulse'
                            : collecting
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                            }`}
                        title={collecting ? 'Stop collection first' : 'Calibrate sensor thresholds'}
                    >
                        <Target size={18} />
                        {calibrating ? 'Calibrating...' : 'Calibrate'}
                    </button>

                    {/* Settings Button */}
                    <button
                        onClick={onSettingsClick}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors ml-auto"
                    >
                        <Settings size={18} />
                        Settings
                    </button>
                </div>
            </div>
        </div>
    );
};
