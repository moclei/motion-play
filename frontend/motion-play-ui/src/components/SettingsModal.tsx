import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b">
                    <h2 className="text-xl font-bold text-gray-900">Sensor Configuration</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="px-6 py-4 space-y-6">
                    {/* Loading State */}
                    {loading && (
                        <div className="text-center py-8">
                            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            <p className="mt-2 text-sm text-gray-600">Loading configuration...</p>
                        </div>
                    )}

                    {!loading && (
                        <>
                            {/* LED Current */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    LED Current
                                </label>
                                <select
                                    value={config.led_current}
                                    onChange={(e) => setConfig({ ...config, led_current: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    {ledCurrentOptions.map((option) => (
                                        <option key={option} value={option}>
                                            {option}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-500">
                                    Higher current = longer detection range, more power consumption
                                </p>
                            </div>

                            {/* Integration Time */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Integration Time (Pulse Length)
                                </label>
                                <select
                                    value={config.integration_time}
                                    onChange={(e) => setConfig({ ...config, integration_time: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    {integrationTimeOptions.map((option) => (
                                        <option key={option} value={option}>
                                            {option}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-500">
                                    Longer pulse = stronger signal, better range & SNR. Independent of sample rate.
                                </p>
                            </div>

                            {/* Duty Cycle */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Duty Cycle (Sample Rate)
                                </label>
                                <select
                                    value={config.duty_cycle}
                                    onChange={(e) => setConfig({ ...config, duty_cycle: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    {dutyCycleOptions.map((option) => (
                                        <option key={option} value={option}>
                                            {option} {option === '1/40' ? '(~200 Hz - Fastest)' : option === '1/80' ? '(~100 Hz)' : option === '1/160' ? '(~50 Hz)' : '(~25 Hz - Slowest)'}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-500">
                                    Controls measurement frequency. 1/40 = fastest response, 1/320 = best battery life.
                                </p>
                            </div>

                            {/* Multi-Pulse Mode */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Multi-Pulse Mode
                                </label>
                                <select
                                    value={config.multi_pulse}
                                    onChange={(e) => setConfig({ ...config, multi_pulse: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    {multiPulseOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1 text-sm text-gray-500">
                                    Fires multiple IR pulses per measurement. More pulses = stronger signal, same sample rate.
                                </p>
                            </div>

                            {/* High Resolution */}
                            <div>
                                <label className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={config.high_resolution}
                                        onChange={(e) => setConfig({ ...config, high_resolution: e.target.checked })}
                                        className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <div>
                                        <span className="font-medium text-gray-700">High Resolution Mode</span>
                                        <p className="text-sm text-gray-500">
                                            16-bit vs 12-bit. Disable for faster sampling (20-30% speed boost).
                                        </p>
                                    </div>
                                </label>
                            </div>

                            {/* Read Ambient Light */}
                            <div>
                                <label className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={config.read_ambient}
                                        onChange={(e) => setConfig({ ...config, read_ambient: e.target.checked })}
                                        className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <div>
                                        <span className="font-medium text-gray-700">Read Ambient Light</span>
                                        <p className="text-sm text-gray-500">
                                            Disable to read only proximity (2x faster - recommended for speed).
                                        </p>
                                    </div>
                                </label>
                            </div>

                            {/* Sample Rate (Display Only) */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Target Sample Rate (Hz)
                                </label>
                                <input
                                    type="number"
                                    value={config.sample_rate_hz}
                                    onChange={(e) => setConfig({ ...config, sample_rate_hz: parseInt(e.target.value) || 1000 })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                                <p className="mt-1 text-sm text-gray-500">
                                    Target only - actual rate depends on configuration above
                                </p>
                            </div>

                            {/* I2C Clock Speed */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    I2C Clock Speed (kHz)
                                </label>
                                <select
                                    value={config.i2c_clock_khz}
                                    onChange={(e) => setConfig({ ...config, i2c_clock_khz: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="100">100 kHz (Standard Mode)</option>
                                    <option value="400">400 kHz (Fast Mode) - Recommended</option>
                                </select>
                                <p className="mt-1 text-sm text-gray-500">
                                    Higher speed = faster sensor communication. 400kHz recommended.
                                </p>
                            </div>

                            {/* Performance Tips */}
                            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                                <h3 className="font-semibold text-blue-900 mb-2">⚡ Speed Optimization Tips</h3>
                                <ul className="text-sm text-blue-800 space-y-1">
                                    <li>• <strong>Fastest</strong>: Disable ambient + low resolution + 1T integration</li>
                                    <li>• <strong>Balanced</strong>: Disable ambient + high res + 2T integration</li>
                                    <li>• <strong>Best Range</strong>: All enabled + 200mA + 4T or 8T integration</li>
                                </ul>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
                    <button
                        onClick={handleResetDefaults}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                    >
                        Reset to Defaults
                    </button>
                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleApplyConfig}
                            disabled={applying || loading}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                        >
                            {applying ? 'Saving...' : 'Save & Apply'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
