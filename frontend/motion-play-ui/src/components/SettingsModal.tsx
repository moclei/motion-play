import { useState } from 'react';
import { X } from 'lucide-react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface SensorConfig {
    sample_rate: number;
    led_current: string;
    integration_time: string;
    high_resolution: boolean;
    read_ambient: boolean;
}

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const SettingsModal = ({ isOpen, onClose }: SettingsModalProps) => {
    const [config, setConfig] = useState<SensorConfig>({
        sample_rate: 1000,
        led_current: '200mA',
        integration_time: '1T',
        high_resolution: true,
        read_ambient: true,
    });

    const [applying, setApplying] = useState(false);

    const ledCurrentOptions = [
        '50mA', '75mA', '100mA', '120mA', 
        '140mA', '160mA', '180mA', '200mA'
    ];

    const integrationTimeOptions = [
        '1T', '1.5T', '2T', '2.5T', 
        '3T', '3.5T', '4T', '8T'
    ];

    const handleApplyConfig = async () => {
        try {
            setApplying(true);
            await api.configureSensors(config);
            toast.success('Configuration applied successfully!');
            onClose();
        } catch (err) {
            toast.error('Failed to apply configuration');
            console.error(err);
        } finally {
            setApplying(false);
        }
    };

    const handleResetDefaults = () => {
        setConfig({
            sample_rate: 1000,
            led_current: '200mA',
            integration_time: '1T',
            high_resolution: true,
            read_ambient: true,
        });
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
                            Integration Time
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
                            Longer time = better range & SNR, slower sample rate. 1T = fastest.
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
                            Target Sample Rate
                        </label>
                        <input
                            type="number"
                            value={config.sample_rate}
                            onChange={(e) => setConfig({ ...config, sample_rate: parseInt(e.target.value) || 1000 })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="mt-1 text-sm text-gray-500">
                            Target only - actual rate depends on configuration above
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
                            disabled={applying}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                        >
                            {applying ? 'Applying...' : 'Apply Configuration'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
