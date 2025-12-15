import { useState, useEffect } from 'react';
import { X, HelpCircle, Zap } from 'lucide-react';
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
    // Primary sensor mode selection
    sensor_mode: 'polling' | 'interrupt';
    // Polling mode settings
    sample_rate_hz: number;
    led_current: string;
    integration_time: string;
    duty_cycle: string;
    high_resolution: boolean;
    read_ambient: boolean;
    i2c_clock_khz: number;
    multi_pulse: string;
    // Interrupt mode settings (calibration-based)
    interrupt_threshold_margin?: number;  // Trigger when prox exceeds baseline + margin
    interrupt_hysteresis?: number;        // Gap between high and low thresholds
    interrupt_integration_time?: number;  // 1-8 for 1T-8T
    interrupt_multi_pulse?: number;       // 1, 2, 4, or 8 pulses
    interrupt_persistence?: number;       // Consecutive hits before interrupt (1-4)
    interrupt_smart_persistence?: boolean;
    interrupt_mode?: 'normal' | 'logic';
}

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const DEFAULT_CONFIG: SensorConfig = {
    // Primary mode selection
    sensor_mode: 'polling',
    // Polling mode settings
    sample_rate_hz: 1000,
    led_current: '200mA',
    integration_time: '2T',
    duty_cycle: '1/40',
    high_resolution: true,
    read_ambient: true,
    i2c_clock_khz: 400,
    multi_pulse: '1',
    // Interrupt mode settings (calibration-based)
    interrupt_threshold_margin: 10,    // Trigger at 10+ counts above baseline
    interrupt_hysteresis: 5,           // Small gap for re-triggering
    interrupt_integration_time: 8,     // 8T for maximum range
    interrupt_multi_pulse: 8,          // 8 pulses for maximum signal strength
    interrupt_persistence: 1,
    interrupt_smart_persistence: true,
    interrupt_mode: 'normal',
};

type SettingsTab = 'proximity' | 'interrupt';

export const SettingsModal = ({ isOpen, onClose }: SettingsModalProps) => {
    const [config, setConfig] = useState<SensorConfig>(DEFAULT_CONFIG);
    const [loading, setLoading] = useState(false);
    const [applying, setApplying] = useState(false);
    const [activeTab, setActiveTab] = useState<SettingsTab>('proximity');

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
            const cloudConfig = response.sensor_config as SensorConfig;
            setConfig({
                ...DEFAULT_CONFIG,
                ...cloudConfig,
                // Primary mode
                sensor_mode: cloudConfig.sensor_mode ?? 'polling',
                // Polling settings
                i2c_clock_khz: cloudConfig.i2c_clock_khz || 400,
                multi_pulse: cloudConfig.multi_pulse || '1',
                // Interrupt settings (calibration-based)
                interrupt_threshold_margin: cloudConfig.interrupt_threshold_margin ?? 10,
                interrupt_hysteresis: cloudConfig.interrupt_hysteresis ?? 5,
                interrupt_integration_time: cloudConfig.interrupt_integration_time ?? 8,
                interrupt_multi_pulse: cloudConfig.interrupt_multi_pulse ?? 8,
                interrupt_persistence: cloudConfig.interrupt_persistence ?? 1,
                interrupt_smart_persistence: cloudConfig.interrupt_smart_persistence ?? true,
                interrupt_mode: cloudConfig.interrupt_mode ?? 'normal',
            });
            // Switch to appropriate tab based on sensor mode
            setActiveTab(cloudConfig.sensor_mode === 'interrupt' ? 'interrupt' : 'proximity');
        } catch (err) {
            console.error('Failed to load config from cloud:', err);
            toast.error('Failed to load configuration');
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

                {/* Sensor Mode Selector - Primary Setting */}
                <div className="px-6 py-3 bg-gray-50 border-b">
                    <div className="flex items-center gap-4">
                        <span className="text-sm font-medium text-gray-700">Sensor Mode:</span>
                        <div className="flex gap-2">
                            <button
                                onClick={() => {
                                    setConfig({ ...config, sensor_mode: 'polling' });
                                    setActiveTab('proximity');
                                }}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${config.sensor_mode === 'polling'
                                        ? 'bg-blue-600 text-white shadow-md'
                                        : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                                    }`}
                            >
                                <span className="w-2 h-2 rounded-full bg-current opacity-75"></span>
                                Polling (High-frequency)
                            </button>
                            <button
                                onClick={() => {
                                    setConfig({ ...config, sensor_mode: 'interrupt' });
                                    setActiveTab('interrupt');
                                }}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${config.sensor_mode === 'interrupt'
                                        ? 'bg-cyan-600 text-white shadow-md'
                                        : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                                    }`}
                            >
                                <Zap size={14} />
                                Interrupt (Event-based)
                            </button>
                        </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                        {config.sensor_mode === 'polling'
                            ? 'Sensors are read continuously at the configured sample rate. Best for detailed waveform analysis.'
                            : 'Sensors trigger events when thresholds are crossed. Best for low-power detection.'}
                    </p>
                </div>

                {/* Tab Navigation - for detailed settings */}
                <div className="flex border-b px-6">
                    <button
                        onClick={() => setActiveTab('proximity')}
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'proximity'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        Polling Settings
                    </button>
                    <button
                        onClick={() => setActiveTab('interrupt')}
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1 ${activeTab === 'interrupt'
                                ? 'border-cyan-500 text-cyan-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        Interrupt Settings
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

                    {!loading && activeTab === 'proximity' && (
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

                    {/* Interrupt Mode Settings Tab */}
                    {!loading && activeTab === 'interrupt' && (
                        <div className="space-y-4">
                            <div className="bg-cyan-50 border border-cyan-200 rounded-md p-3 mb-4">
                                <div className="flex items-center gap-2 text-cyan-800 text-sm">
                                    <Zap size={16} />
                                    <span className="font-medium">Interrupt Mode Settings</span>
                                </div>
                                <p className="text-xs text-cyan-700 mt-1">
                                    Configure hardware interrupts for event-based detection. The sensor triggers when proximity values cross thresholds.
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                {/* Threshold Margin */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Threshold Margin
                                        <Tooltip text="Trigger when proximity exceeds calibrated baseline by this amount. Lower = more sensitive. At 250mm, objects produce 8-25 counts." />
                                    </label>
                                    <input
                                        type="number"
                                        value={config.interrupt_threshold_margin}
                                        onChange={(e) => setConfig({ ...config, interrupt_threshold_margin: parseInt(e.target.value) || 10 })}
                                        min={1}
                                        max={1000}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
                                    />
                                </div>

                                {/* Hysteresis */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Hysteresis
                                        <Tooltip text="Gap between high and low thresholds. Prevents rapid triggering. Low threshold = margin - hysteresis." />
                                    </label>
                                    <input
                                        type="number"
                                        value={config.interrupt_hysteresis}
                                        onChange={(e) => setConfig({ ...config, interrupt_hysteresis: parseInt(e.target.value) || 5 })}
                                        min={0}
                                        max={500}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
                                    />
                                </div>

                                {/* Integration Time */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Integration Time
                                        <Tooltip text="Longer integration = stronger signal, better range. 8T recommended for maximum detection distance." />
                                    </label>
                                    <select
                                        value={config.interrupt_integration_time}
                                        onChange={(e) => setConfig({ ...config, interrupt_integration_time: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
                                    >
                                        <option value="1">1T (Fastest)</option>
                                        <option value="2">2T</option>
                                        <option value="3">3T</option>
                                        <option value="4">4T</option>
                                        <option value="8">8T (Best range)</option>
                                    </select>
                                </div>

                                {/* Multi-Pulse */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Multi-Pulse
                                        <Tooltip text="More pulses = stronger signal. 8 pulses recommended for maximum detection range." />
                                    </label>
                                    <select
                                        value={config.interrupt_multi_pulse}
                                        onChange={(e) => setConfig({ ...config, interrupt_multi_pulse: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
                                    >
                                        <option value="1">1 pulse (default)</option>
                                        <option value="2">2 pulses (~2× signal)</option>
                                        <option value="4">4 pulses (~4× signal)</option>
                                        <option value="8">8 pulses (~8× signal)</option>
                                    </select>
                                </div>

                                {/* Persistence */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Persistence
                                        <Tooltip text="Consecutive readings required before interrupt triggers. Higher = less noise, slower response." />
                                    </label>
                                    <select
                                        value={config.interrupt_persistence}
                                        onChange={(e) => setConfig({ ...config, interrupt_persistence: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
                                    >
                                        <option value="1">1 (Fastest)</option>
                                        <option value="2">2</option>
                                        <option value="3">3</option>
                                        <option value="4">4 (Most stable)</option>
                                    </select>
                                </div>

                                {/* Interrupt Mode */}
                                <div>
                                    <label className="flex items-center text-sm font-medium text-gray-700 mb-1">
                                        Interrupt Mode
                                        <Tooltip text="Normal: INT pin pulses on events. Logic: INT stays LOW while object present." />
                                    </label>
                                    <select
                                        value={config.interrupt_mode}
                                        onChange={(e) => setConfig({ ...config, interrupt_mode: e.target.value as 'normal' | 'logic' })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
                                    >
                                        <option value="normal">Normal (pulse on events)</option>
                                        <option value="logic">Logic Output (level while close)</option>
                                    </select>
                                </div>
                            </div>

                            {/* Smart Persistence Checkbox */}
                            <div className="flex gap-6 py-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={config.interrupt_smart_persistence}
                                        onChange={(e) => setConfig({ ...config, interrupt_smart_persistence: e.target.checked })}
                                        className="w-4 h-4 text-cyan-600 border-gray-300 rounded focus:ring-cyan-500"
                                    />
                                    <span className="text-sm font-medium text-gray-700">Smart Persistence</span>
                                    <Tooltip text="When enabled, persistence checks happen in rapid succession after first detection, reducing response time from ~115ms to ~40ms." />
                                </label>
                            </div>

                            {/* Tuning Tips */}
                            <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                                <h3 className="font-semibold text-gray-800 text-sm mb-1">📊 Auto-Calibration Mode</h3>
                                <div className="text-xs text-gray-600 space-y-1">
                                    <p>Sensors auto-calibrate at startup by measuring baseline (with cover, no objects).</p>
                                    <p><strong>Threshold margin:</strong> How much above baseline triggers "close". At 250mm distance, objects produce only 8-25 counts, so keep this low (5-15).</p>
                                    <p><strong>Best range:</strong> 8T integration + 8 pulses gives maximum detection distance.</p>
                                    <p><strong>Hysteresis:</strong> Prevents rapid close/away toggling. Set to about half of margin.</p>
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
