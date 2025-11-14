import { useState } from 'react';
import { api } from '../services/api';
import { Settings } from 'lucide-react';

export const SensorConfig = () => {
    const [sampleRate, setSampleRate] = useState(1000);
    const [ledCurrent, setLedCurrent] = useState('200mA');
    const [integrationTime, setIntegrationTime] = useState('1T');
    const [highResolution, setHighResolution] = useState(true);
    const [applying, setApplying] = useState(false);
    const [status, setStatus] = useState('');

    const applyConfig = async () => {
        try {
            setApplying(true);
            setStatus('Sending configuration...');

            await api.sendCommand('configure_sensors', {
                sensor_config: {
                    sample_rate: sampleRate,
                    led_current: ledCurrent,
                    integration_time: integrationTime,
                    high_resolution: highResolution
                }
            });

            setStatus('Configuration applied! Device restart may be required.');
        } catch (err) {
            setStatus('Failed to apply configuration');
            console.error(err);
        } finally {
            setApplying(false);
        }
    };

    return (
        <div className="p-4 border rounded bg-white">
            <div className="flex items-center gap-2 mb-4">
                <Settings size={20} className="text-gray-700" />
                <h3 className="text-xl font-bold text-gray-800">Sensor Configuration</h3>
            </div>

            <div className="space-y-4">
                {/* Sample Rate */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Sample Rate (Hz)
                    </label>
                    <select
                        value={sampleRate}
                        onChange={(e) => setSampleRate(Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded bg-white text-gray-900"
                    >
                        <option value={100}>100 Hz</option>
                        <option value={250}>250 Hz</option>
                        <option value={500}>500 Hz</option>
                        <option value={1000}>1000 Hz</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                        Higher rates = more data, lower battery life
                    </p>
                </div>

                {/* LED Current (affects sensitivity) */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        LED Current (Sensitivity)
                    </label>
                    <select
                        value={ledCurrent}
                        onChange={(e) => setLedCurrent(e.target.value)}
                        className="w-full px-3 py-2 border rounded bg-white text-gray-900"
                    >
                        <option value="50mA">50mA (Low)</option>
                        <option value="75mA">75mA</option>
                        <option value="100mA">100mA</option>
                        <option value="120mA">120mA</option>
                        <option value="140mA">140mA</option>
                        <option value="160mA">160mA</option>
                        <option value="180mA">180mA</option>
                        <option value="200mA">200mA (High)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                        Higher current = longer detection range, more power
                    </p>
                </div>

                {/* Integration Time */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Integration Time
                    </label>
                    <select
                        value={integrationTime}
                        onChange={(e) => setIntegrationTime(e.target.value)}
                        className="w-full px-3 py-2 border rounded bg-white text-gray-900"
                    >
                        <option value="1T">1T (Fast, 1x)</option>
                        <option value="1.5T">1.5T (1.5x)</option>
                        <option value="2T">2T (2x)</option>
                        <option value="4T">4T (4x)</option>
                        <option value="8T">8T (Slow, 8x)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                        Longer time = more accurate, slower response
                    </p>
                </div>

                {/* High Resolution */}
                <div>
                    <label className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            checked={highResolution}
                            onChange={(e) => setHighResolution(e.target.checked)}
                            className="w-4 h-4"
                        />
                        <span className="text-sm font-medium text-gray-700">
                            High Resolution Mode
                        </span>
                    </label>
                    <p className="text-xs text-gray-500 mt-1 ml-6">
                        16-bit readings (more precise, slightly slower)
                    </p>
                </div>

                {/* Apply Button */}
                <button
                    onClick={applyConfig}
                    disabled={applying}
                    className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 font-medium"
                >
                    {applying ? 'Applying...' : 'Apply Configuration'}
                </button>

                {status && (
                    <div className={`p-3 rounded text-sm ${status.includes('Failed')
                            ? 'bg-red-100 text-red-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                        {status}
                    </div>
                )}

                <div className="text-xs text-gray-600 p-2 bg-yellow-50 rounded border border-yellow-200">
                    ⚠️ Configuration changes may require device restart
                </div>
            </div>
        </div>
    );
};

