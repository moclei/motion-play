import { useState, useEffect } from 'react';
import { X, HelpCircle } from 'lucide-react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

// Tooltip component for compact descriptions - shows below to avoid cutoff
const Tooltip = ({ text }: { text: string }) => (
    <div className="group relative inline-flex ml-1">
        <HelpCircle size={14} className="text-gray-400 cursor-help" />
        <div className="absolute left-0 top-full mt-1 px-2 py-1.5 bg-gray-900 text-white text-xs rounded opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 w-48 leading-relaxed shadow-lg">
            {text}
        </div>
    </div>
);

interface SensorConfig {
    sample_rate_hz: number;
    led_current: string;
    integration_time: string;
    duty_cycle: string;
    high_resolution: boolean;
    read_ambient: boolean;
    i2c_clock_khz: number;
    multi_pulse: string;
}

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const DEFAULT_CONFIG: SensorConfig = {
    sample_rate_hz: 1000,
    led_current: '200mA',
    integration_time: '2T',
    duty_cycle: '1/40',
    high_resolution: true,
    read_ambient: true,
    i2c_clock_khz: 400,
    multi_pulse: '1',
};

export const SettingsModal = ({ isOpen, onClose }: SettingsModalProps) => {
    const [config, setConfig] = useState<SensorConfig>(DEFAULT_CONFIG);
    const [loading, setLoading] = useState(false);
    const [applying, setApplying] = useState(false);

    // Load config from cloud when modal opens
    useEffect(() => {
        if (isOpen) {
            loadConfigFromCloud();
        }
    }, [isOpen]);

    const loadConfigFromCloud = async () => {
        try {
            setLoading(true);
            const response = await api.getDeviceConfig();
            setConfig({
                ...response.sensor_config,
                i2c_clock_khz: response.sensor_config.i2c_clock_khz || 400,
                multi_pulse: response.sensor_config.multi_pulse || '1',
            });
        } catch (err) {
            console.error('Failed to load config from cloud:', err);
            toast.error('Failed to load configuration');
            // Keep default config on error
        } finally {
            setLoading(false);
        }
    };

    const ledCurrentOptions = [
        '50mA', '75mA', '100mA', '120mA',
        '140mA', '160mA', '180mA', '200mA'
    ];

    const integrationTimeOptions = [
        '1T', '1.5T', '2T', '2.5T',
        '3T', '3.5T', '4T', '8T'
    ];

    const dutyCycleOptions = [
        '1/40',   // ~200 Hz - Fastest
        '1/80',   // ~100 Hz
        '1/160',  // ~50 Hz
        '1/320'   // ~25 Hz - Slowest, best battery
    ];

    const multiPulseOptions = [
        { value: '1', label: '1 pulse (default)' },
        { value: '2', label: '2 pulses (~2× signal)' },
        { value: '4', label: '4 pulses (~4× signal)' },
        { value: '8', label: '8 pulses (~8× signal)' },
    ];

    const handleApplyConfig = async () => {
        try {
            setApplying(true);
            await api.updateDeviceConfig(config);
            toast.success('Configuration saved to cloud and applied to device!');
            onClose();
        } catch (err) {
            toast.error('Failed to apply configuration');
            console.error(err);
        } finally {
            setApplying(false);
        }
    };

    const handleResetDefaults = () => {
        setConfig(DEFAULT_CONFIG);
        toast.success('Reset to defaults');
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
                {/* Header - fixed */}
                <div className="flex items-center justify-between px-6 py-3 border-b flex-shrink-0">
                    <h2 className="text-lg font-bold text-gray-900">Sensor Configuration</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content - scrollable */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    {/* Loading State */}
                    {loading && (
                        <div className="text-center py-8">
                            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            <p className="mt-2 text-sm text-gray-600">Loading configuration...</p>
                        </div>
                    )}

                    {!loading && (
                        <div className="space-y-4">
                            {/* 2-column grid for dropdowns */}
                            <div className="grid grid-cols-2 gap-4">
                                {/* LED Current */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        LED Current
                                        <Tooltip text="Higher current = longer detection range, more power consumption" />
                                    </label>
                                    <select
                                        value={config.led_current}
                                        onChange={(e) => setConfig({ ...config, led_current: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    >
                                        {ledCurrentOptions.map((option) => (
                                            <option key={option} value={option}>
                                                {option}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Integration Time */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Integration Time
                                        <Tooltip text="Longer pulse = stronger signal, better range & SNR. Independent of sample rate." />
                                    </label>
                                    <select
                                        value={config.integration_time}
                                        onChange={(e) => setConfig({ ...config, integration_time: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    >
                                        {integrationTimeOptions.map((option) => (
                                            <option key={option} value={option}>
                                                {option}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Duty Cycle */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Duty Cycle
                                        <Tooltip text="Controls measurement frequency. 1/40 = fastest response, 1/320 = best battery life." />
                                    </label>
                                    <select
                                        value={config.duty_cycle}
                                        onChange={(e) => setConfig({ ...config, duty_cycle: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    >
                                        {dutyCycleOptions.map((option) => (
                                            <option key={option} value={option}>
                                                {option} {option === '1/40' ? '(~200 Hz)' : option === '1/80' ? '(~100 Hz)' : option === '1/160' ? '(~50 Hz)' : '(~25 Hz)'}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Multi-Pulse Mode */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Multi-Pulse Mode
                                        <Tooltip text="Fires multiple IR pulses per measurement. More pulses = stronger signal, same sample rate." />
                                    </label>
                                    <select
                                        value={config.multi_pulse}
                                        onChange={(e) => setConfig({ ...config, multi_pulse: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    >
                                        {multiPulseOptions.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Sample Rate */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Target Sample Rate (Hz)
                                        <Tooltip text="Target only - actual rate depends on configuration above" />
                                    </label>
                                    <input
                                        type="number"
                                        value={config.sample_rate_hz}
                                        onChange={(e) => setConfig({ ...config, sample_rate_hz: parseInt(e.target.value) || 1000 })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    />
                                </div>

                                {/* I2C Clock Speed */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        I2C Clock Speed
                                        <Tooltip text="Higher speed = faster sensor communication. 400kHz recommended." />
                                    </label>
                                    <select
                                        value={config.i2c_clock_khz}
                                        onChange={(e) => setConfig({ ...config, i2c_clock_khz: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    >
                                        <option value="100">100 kHz (Standard)</option>
                                        <option value="400">400 kHz (Fast)</option>
                                    </select>
                                </div>
                            </div>

                            {/* Checkboxes in a row */}
                            <div className="flex gap-6 py-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={config.high_resolution}
                                        onChange={(e) => setConfig({ ...config, high_resolution: e.target.checked })}
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <span className="text-sm font-medium text-gray-700">High Resolution (16-bit)</span>
                                    <Tooltip text="16-bit vs 12-bit. Disable for faster sampling (20-30% speed boost)." />
                                </label>

                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={config.read_ambient}
                                        onChange={(e) => setConfig({ ...config, read_ambient: e.target.checked })}
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <span className="text-sm font-medium text-gray-700">Read Ambient Light</span>
                                    <Tooltip text="Disable to read only proximity (2x faster - recommended for speed)." />
                                </label>
                            </div>

                            {/* Performance Tips - compact */}
                            <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                                <h3 className="font-semibold text-blue-900 text-sm mb-1">⚡ Speed Optimization Tips</h3>
                                <div className="text-xs text-blue-800 flex flex-wrap gap-x-4 gap-y-0.5">
                                    <span><strong>Fastest:</strong> No ambient + 12-bit + 1T</span>
                                    <span><strong>Balanced:</strong> No ambient + 16-bit + 2T</span>
                                    <span><strong>Best Range:</strong> All + 200mA + 4T/8T</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer - fixed */}
                <div className="flex items-center justify-between px-6 py-3 border-t bg-gray-50 flex-shrink-0">
                    <button
                        onClick={handleResetDefaults}
                        className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                    >
                        Reset to Defaults
                    </button>
                    <div className="flex gap-2">
                        <button
                            onClick={onClose}
                            className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleApplyConfig}
                            disabled={applying || loading}
                            className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                        >
                            {applying ? 'Saving...' : 'Save & Apply'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
