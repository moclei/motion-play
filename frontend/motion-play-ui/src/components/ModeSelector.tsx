import { useState } from 'react';
import { api } from '../services/api';
import { Activity } from 'lucide-react';

type DeviceMode = 'idle' | 'debug' | 'play' | 'interrupt_debug';

interface ModeSelectorProps {
    currentMode?: DeviceMode;
}

export const ModeSelector = ({ currentMode = 'idle' }: ModeSelectorProps) => {
    const [mode, setMode] = useState<DeviceMode>(currentMode);
    const [changing, setChanging] = useState(false);
    const [status, setStatus] = useState<string>('');

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

            {status && (
                <div className={`mt-3 p-3 rounded text-sm ${status.includes('Failed')
                        ? 'bg-red-100 text-red-800'
                        : 'bg-green-100 text-green-800'
                    }`}>
                    {status}
                </div>
            )}
        </div>
    );
};