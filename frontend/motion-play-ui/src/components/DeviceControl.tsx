import { useState } from 'react';
import { api } from '../services/api';
import { Play, Square } from 'lucide-react';

interface DeviceControlProps {
    onCollectionStopped?: () => void;
}

export const DeviceControl = ({ onCollectionStopped }: DeviceControlProps) => {
    const [collecting, setCollecting] = useState(false);
    const [status, setStatus] = useState<string>('');

    const handleStartCollection = async () => {
        try {
            setStatus('Starting collection...');
            await api.sendCommand('start_collection');
            setCollecting(true);
            setStatus('Collection started');
        } catch (err) {
            setStatus('Failed to start collection');
            console.error(err);
        }
    };

    const handleStopCollection = async () => {
        try {
            setStatus('Stopping collection...');
            await api.sendCommand('stop_collection');
            setCollecting(false);
            setStatus('Collection stopped');

            // Notify parent that collection stopped
            if (onCollectionStopped) {
                onCollectionStopped();
            }
        } catch (err) {
            setStatus('Failed to stop collection');
            console.error(err);
        }
    };

    return (
        <div className="p-4 border rounded bg-white">
            <h3 className="text-xl font-bold mb-4">Device Control</h3>

            <div className="space-y-4">
                <div className="flex gap-4 flex-col">
                    <button
                        onClick={handleStartCollection}
                        disabled={collecting}
                        className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300"
                    >
                        <Play size={20} />
                        Start Collection
                    </button>

                    <button
                        onClick={handleStopCollection}
                        disabled={!collecting}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-300"
                    >
                        <Square size={20} />
                        Stop Collection
                    </button>
                </div>

                {status && (
                    <div className={`p-3 rounded ${status.includes('Failed') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                        }`}>
                        {status}
                    </div>
                )}

                <div className="text-sm text-gray-600">
                    <p><strong>Status:</strong> {collecting ? 'Collecting...' : 'Idle'}</p>
                    <p><strong>Device:</strong> motionplay-device-001</p>
                </div>
            </div>
        </div>
    );
};