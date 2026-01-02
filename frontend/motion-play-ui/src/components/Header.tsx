import { useState } from 'react';
import { api } from '../services/api';
import { Play, Square, Activity, Settings, Target } from 'lucide-react';
import toast from 'react-hot-toast';

type DeviceMode = 'idle' | 'debug' | 'play';

interface HeaderProps {
    onCollectionStopped?: () => void;
    onSettingsClick: () => void;
}

export const Header = ({ onCollectionStopped, onSettingsClick }: HeaderProps) => {
    const [collecting, setCollecting] = useState(false);
    const [mode, setMode] = useState<DeviceMode>('idle');
    const [changingMode, setChangingMode] = useState(false);
    const [calibrating, setCalibrating] = useState(false);

    const handleStartCollection = async () => {
        try {
            await api.sendCommand('start_collection');
            setCollecting(true);
            toast.success('Collection started');
        } catch (err) {
            toast.error('Failed to start collection');
            console.error(err);
        }
    };

    const handleStopCollection = async () => {
        try {
            await api.sendCommand('stop_collection');
            setCollecting(false);
            toast.success('Collection stopped');

            if (onCollectionStopped) {
                onCollectionStopped();
            }
        } catch (err) {
            toast.error('Failed to stop collection');
            console.error(err);
        }
    };

    const handleModeChange = async (newMode: DeviceMode) => {
        if (mode === newMode) return;

        try {
            setChangingMode(true);
            await api.sendCommand('set_mode', { mode: newMode });
            setMode(newMode);
            toast.success(`Mode changed to ${getModeLabel(newMode)}`);
        } catch (err) {
            toast.error('Failed to change mode');
            console.error(err);
        } finally {
            setChangingMode(false);
        }
    };

    const handleStartCalibration = async () => {
        if (mode !== 'idle') {
            toast.error('Set device to Idle mode first');
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

            // Reset state after calibration timeout
            setTimeout(() => {
                setCalibrating(false);
            }, 30000); // 30 seconds max calibration time
        } catch (err) {
            toast.error('Failed to start calibration', { id: 'calibration' });
            setCalibrating(false);
            console.error(err);
        }
    };

    const getModeColor = (m: DeviceMode) => {
        switch (m) {
            case 'debug': return 'border-blue-600';
            case 'play': return 'border-green-600';
            case 'idle': return 'border-gray-600';
        }
    };

    const getModeLabel = (m: DeviceMode) => {
        switch (m) {
            case 'debug': return 'Debug';
            case 'play': return 'Play';
            case 'idle': return 'Idle';
        }
    };

    return (
        <div className="bg-white shadow-md border-b">
            <div className="px-6 py-4 space-y-4">
                {/* Title Row */}
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-bold text-gray-900">
                        Motion Play Dashboard
                    </h1>
                    <div className="text-sm text-gray-500">
                        Device: motionplay-device-001
                    </div>
                </div>

                {/* Controls Row */}
                <div className="flex items-center gap-6">
                    {/* Collection Controls */}
                    <div className="flex items-center gap-3 border-r pr-6">
                        <button
                            onClick={handleStartCollection}
                            disabled={collecting}
                            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400 disabled:text-gray-200 disabled:cursor-not-allowed transition-colors font-medium"
                        >
                            <Play size={18} />
                            Start
                        </button>

                        <button
                            onClick={handleStopCollection}
                            disabled={!collecting}
                            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-400 disabled:text-gray-200 disabled:cursor-not-allowed transition-colors font-medium"
                        >
                            <Square size={18} />
                            Stop
                        </button>

                        <div className="flex items-center gap-2 ml-2">
                            <div className={`w-2 h-2 rounded-full ${collecting ? 'bg-red-500 animate-pulse' : 'bg-gray-300'}`}></div>
                            <span className="text-sm text-gray-600">
                                {collecting ? 'Recording' : 'Idle'}
                            </span>
                        </div>
                    </div>

                    {/* Mode Selector */}
                    <div className="flex items-center gap-3 border-r pr-6">
                        <Activity size={20} className="text-gray-600" />
                        <span className="text-sm font-medium text-gray-700">Mode:</span>
                        <div className="flex gap-2">
                            {(['idle', 'debug', 'play'] as DeviceMode[]).map((m) => (
                                <button
                                    key={m}
                                    onClick={() => handleModeChange(m)}
                                    disabled={changingMode}
                                    className={`px-4 py-2 rounded border-2 transition-all text-sm font-medium capitalize ${
                                        mode === m
                                            ? `${getModeColor(m)} bg-gray-100 text-gray-800`
                                            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                                    } ${changingMode ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    {getModeLabel(m)}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Calibration Button */}
                    <button
                        onClick={handleStartCalibration}
                        disabled={calibrating || mode !== 'idle'}
                        className={`flex items-center gap-2 px-4 py-2 rounded transition-colors font-medium ${
                            calibrating
                                ? 'bg-purple-500 text-white animate-pulse'
                                : mode !== 'idle'
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                        }`}
                        title={mode !== 'idle' ? 'Set device to Idle mode first' : 'Calibrate sensor thresholds'}
                    >
                        <Target size={18} />
                        {calibrating ? 'Calibrating...' : 'Calibrate'}
                    </button>

                    {/* Settings Button */}
                    <button
                        onClick={onSettingsClick}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                    >
                        <Settings size={18} />
                        Settings
                    </button>
                </div>
            </div>
        </div>
    );
};
