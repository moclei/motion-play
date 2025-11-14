import { Download } from 'lucide-react';
import type { SessionData } from '../services/api';

interface ExportButtonProps {
    sessionData: SessionData;
}

export const ExportButton = ({ sessionData }: ExportButtonProps) => {

    const exportJSON = () => {
        const dataStr = JSON.stringify(sessionData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${sessionData.session.session_id}.json`;
        link.click();
        URL.revokeObjectURL(url);
    };

    const exportCSV = () => {
        // CSV Header
        const headers = [
            'timestamp_offset',
            'pcb_id',
            'side',
            'proximity',
            'ambient',
            'session_id',
            'device_id',
            'start_timestamp'
        ].join(',');

        // CSV Rows
        const rows = sessionData.readings.map(reading => {
            return [
                reading.timestamp_offset,
                reading.pcb_id,
                reading.side,
                reading.proximity,
                reading.ambient,
                sessionData.session.session_id,
                sessionData.session.device_id,
                sessionData.session.start_timestamp
            ].join(',');
        });

        const csv = [headers, ...rows].join('\n');
        const dataBlob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${sessionData.session.session_id}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="flex gap-2">
            <button
                onClick={exportJSON}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
                <Download size={18} />
                Export JSON
            </button>
            <button
                onClick={exportCSV}
                className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
                <Download size={18} />
                Export CSV
            </button>
        </div>
    );
};