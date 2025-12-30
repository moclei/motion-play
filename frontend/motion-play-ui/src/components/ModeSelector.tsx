import { useState } from 'react';
import { api } from '../services/api';
import { Activity, Target } from 'lucide-react';

type DeviceMode = 'idle' | 'debug' | 'play' | 'interrupt_debug';

interface ModeSelectorProps {
    currentMode?: DeviceMode;
}

export const ModeSelector = ({ currentMode = 'idle' }: ModeSelectorProps) => {
    const [mode, setMode] = useState<DeviceMode>(currentMode);
    const [changing, setChanging] = useState(false);
    const [status, setStatus] = useState<string>('');
    const [calibrating, setCalibrating] = useState(false);

    const handleModeChange = async (newMode: DeviceMode) => {
        try {
            setChanging(true);
            setStatus(`Changing to ${newMode.replace('_', ' ')} mode...`);

            await api.sendCommand('set_mode', { mode: newMode });

            setMode(newMode);
            setStatus(`Mode changed to ${newMode.replace('_', ' ')}`);

            setTimeout(() => setStatus(''), 3000);
        } catch (err) {
            setStatus(`Failed to change mode`);
            console.error(err);
        } finally {
            setChanging(false);
        }
    };

    const handleStartCalibration = async () => {
        try {
            setCalibrating(true);
            setStatus('Starting calibration wizard on device...');

            await api.sendCommand('set_mode', { mode: 'calibrate' });

            setStatus('Calibration started! Follow instructions on device display.');

            // Reset after a bit - calibration runs on device
            setTimeout(() => {
                setCalibrating(false);
                setStatus('');
            }, 5000);
        } catch (err) {
            setStatus('Failed to start calibration');
            setCalibrating(false);
            console.error(err);
        }
    };

    const getModeColor = (m: DeviceMode) => {
        switch (m) {
            case 'debug': return 'bg-blue-500 border-blue-600';
            case 'play': return 'bg-green-500 border-green-600';
            case 'interrupt_debug': return 'bg-cyan-500 border-cyan-600';
            case 'idle': return 'bg-gray-500 border-gray-600';
        }
    };

    const getModeDescription = (m: DeviceMode) => {
        switch (m) {
            case 'debug': return 'Polling-based data collection';
            case 'play': return 'Active game mode';
            case 'interrupt_debug': return 'Interrupt-based detection';
            case 'idle': return 'Standby mode';
        }
    };

    const getModeLabel = (m: DeviceMode) => {
        switch (m) {
            case 'debug': return 'Debug (Proximity)';
            case 'play': return 'Play';
            case 'interrupt_debug': return 'Debug (Interrupt)';
            case 'idle': return 'Idle';
        }
    };

    return (
        <div className="p-4 border rounded bg-white">
            <div className="flex items-center gap-2 mb-4">
                <Activity size={20} />
                <h3 className="text-xl font-bold">Device Mode</h3>
            </div>

            <div className="space-y-3">
                {(['idle', 'debug', 'interrupt_debug', 'play'] as DeviceMode[]).map((m) => (
                    <button
                        key={m}
                        onClick={() => handleModeChange(m)}
                        disabled={changing || mode === m}
                        className={`w-full p-4 rounded border-2 transition-all text-left ${mode === m
                                ? `${getModeColor(m)} text-white`
                                : 'bg-white border-gray-300 hover:border-gray-400'
                            } ${changing ? 'opacity-50' : ''}`}
                    >
                        <div className="font-semibold">{getModeLabel(m)} Mode</div>
                        <div className="text-sm mt-1 opacity-90">
                            {getModeDescription(m)}
                        </div>
                        {mode === m && (
                            <div className="text-xs mt-2 font-semibold">
                                ● ACTIVE
                            </div>
                        )}
                    </button>
                ))}
            </div>

            {/* Calibration Section */}
            <div className="mt-6 pt-4 border-t border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                    <Target size={18} className="text-purple-600" />
                    <h4 className="font-semibold text-gray-700">Sensor Calibration</h4>
                </div>
                <button
                    onClick={handleStartCalibration}
                    disabled={changing || calibrating || mode !== 'idle'}
                    className={`w-full p-4 rounded border-2 transition-all text-left ${
                        calibrating
                            ? 'bg-purple-500 border-purple-600 text-white'
                            : mode !== 'idle'
                            ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
                            : 'bg-purple-50 border-purple-300 hover:border-purple-500 hover:bg-purple-100'
                    }`}
                >
                    <div className="font-semibold flex items-center gap-2">
                        <Target size={16} />
                        {calibrating ? 'Calibrating...' : 'Start Calibration'}
                    </div>
                    <div className="text-sm mt-1 opacity-80">
                        {mode !== 'idle' 
                            ? 'Set device to Idle mode first'
                            : 'Guided wizard to calibrate sensor thresholds'
                        }
                    </div>
                    {calibrating && (
                        <div className="text-xs mt-2 animate-pulse">
                            ● Follow instructions on device display
                        </div>
                    )}
                </button>
                <p className="text-xs text-gray-500 mt-2">
                    💡 You can also hold the LEFT button on the device for 3 seconds to start calibration.
                </p>
            </div>

            {status && (
                <div className={`mt-3 p-3 rounded text-sm ${status.includes('Failed')
                        ? 'bg-red-100 text-red-800'
                        : status.includes('Calibration')
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-green-100 text-green-800'
                    }`}>
                    {status}
                </div>
            )}
        </div>
    );
};