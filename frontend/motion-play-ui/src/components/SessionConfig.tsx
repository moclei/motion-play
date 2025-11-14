import { Settings, Zap, Clock, Gauge } from 'lucide-react';
import type { Session } from '../services/api';

interface SessionConfigProps {
    session: Session;
}

export const SessionConfig = ({ session }: SessionConfigProps) => {
    const config = session.vcnl4040_config;

    if (!config) {
        return (
            <div className="p-4 border rounded bg-gray-50">
                <p className="text-sm text-gray-500">
                    Configuration data not available for this session
                </p>
            </div>
        );
    }

    return (
        <div className="p-4 border rounded bg-white">
            <div className="flex items-center gap-2 mb-4">
                <Settings size={20} className="text-gray-700" />
                <h3 className="font-semibold text-gray-800">
                    Sensor Configuration
                </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {/* Sample Rate */}
                <div className="flex items-start gap-3 p-3 bg-blue-50 rounded">
                    <Gauge size={20} className="text-blue-600 mt-1" />
                    <div>
                        <div className="text-sm font-medium text-gray-700">
                            Sample Rate
                        </div>
                        <div className="text-lg font-bold text-gray-900">
                            {config.sample_rate_hz} Hz
                        </div>
                    </div>
                </div>

                {/* LED Current */}
                <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded">
                    <Zap size={20} className="text-yellow-600 mt-1" />
                    <div>
                        <div className="text-sm font-medium text-gray-700">
                            LED Current
                        </div>
                        <div className="text-lg font-bold text-gray-900">
                            {config.led_current}
                        </div>
                    </div>
                </div>

                {/* Integration Time */}
                <div className="flex items-start gap-3 p-3 bg-green-50 rounded">
                    <Clock size={20} className="text-green-600 mt-1" />
                    <div>
                        <div className="text-sm font-medium text-gray-700">
                            Integration Time
                        </div>
                        <div className="text-lg font-bold text-gray-900">
                            {config.integration_time}
                        </div>
                    </div>
                </div>

                {/* Resolution */}
                <div className="flex items-start gap-3 p-3 bg-purple-50 rounded">
                    <Settings size={20} className="text-purple-600 mt-1" />
                    <div>
                        <div className="text-sm font-medium text-gray-700">
                            Resolution
                        </div>
                        <div className="text-lg font-bold text-gray-900">
                            {config.high_resolution ? '16-bit' : '12-bit'}
                        </div>
                    </div>
                </div>
            </div>

            {/* Active Sensors Count */}
            {session.active_sensors && (
                <div className="mt-4 p-3 bg-gray-50 rounded">
                    <div className="text-sm text-gray-700">
                        <span className="font-medium">Active Sensors:</span>{' '}
                        {session.active_sensors.filter(s => s.active).length} of{' '}
                        {session.active_sensors.length}
                    </div>
                </div>
            )}
        </div>
    );
};