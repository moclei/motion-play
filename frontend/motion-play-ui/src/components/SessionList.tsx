
import { useEffect, useState, useImperativeHandle, forwardRef } from 'react';
import { api } from '../services/api';
import type { Session } from '../services/api';
import { formatDistance } from 'date-fns';

export interface SessionListRef {
    refresh: () => Promise<void>;
}

interface SessionListProps {
    onSelectSession: (session: Session) => void;
}

export const SessionList = forwardRef<SessionListRef, SessionListProps>(({
    onSelectSession
}, ref) => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [filterMode, setFilterMode] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');

    const loadSessions = async () => {
        try {
            setLoading(true);
            const data = await api.getSessions();
            setSessions(data);
            setError(null);
        } catch (err) {
            setError('Failed to load sessions');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // Expose refresh function to parent via ref
    useImperativeHandle(ref, () => ({
        refresh: loadSessions
    }));

    useEffect(() => {
        loadSessions();
    }, []);

    // Filter sessions based on mode and search term
    const filteredSessions = sessions.filter(session => {
        console.log(session);
        // Mode filter
        if (filterMode !== 'all' && session.mode !== filterMode) {
            return false;
        }

        // Search filter
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            return (
                session.session_id.toLowerCase().includes(searchLower) ||
                session.labels?.some(label => label.toLowerCase().includes(searchLower)) ||
                session.notes?.toLowerCase().includes(searchLower)
            );
        }

        return true;
    });

    if (loading) {
        return <div className="p-4">Loading sessions...</div>;
    }

    if (error) {
        return (
            <div className="p-4 text-red-600">
                {error}
                <button onClick={loadSessions} className="ml-4 text-blue-600">
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-800">Sessions</h2>
                <button
                    onClick={loadSessions}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 font-medium"
                >
                    Refresh
                </button>
            </div>

            {/* Filter Controls */}
            <div className="mb-4 space-y-2">
                {/* Search */}
                <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search sessions, labels, or notes..."
                    className="w-full px-3 py-2 border rounded text-sm"
                />

                {/* Mode filter */}
                <select
                    value={filterMode}
                    onChange={(e) => setFilterMode(e.target.value)}
                    className="w-full px-3 py-2 border rounded text-sm bg-white text-gray-900"
                >
                    <option value="all">All Modes</option>
                    <option value="debug">Debug Mode</option>
                    <option value="play">Play Mode</option>
                    <option value="idle">Idle Mode</option>
                </select>

                {/* Results count */}
                <div className="text-xs text-gray-500">
                    Showing {filteredSessions.length} of {sessions.length} sessions
                </div>
            </div>

            <div className="space-y-2">
                {filteredSessions.length === 0 ? (
                    <p className="text-gray-500">
                        {sessions.length === 0 ? 'No sessions found' : 'No sessions match your filters'}
                    </p>
                ) : (
                    filteredSessions.map((session) => (
                        <div
                            key={session.session_id}
                            onClick={() => {
                                setSelectedId(session.session_id);
                                onSelectSession(session);
                            }}
                            className={`p-4 border rounded cursor-pointer transition-colors ${selectedId === session.session_id
                                ? 'bg-blue-50 border-blue-300'
                                : 'hover:bg-gray-50'
                                }`}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex-1">
                                    <div className="text-xs text-gray-500 mb-1">Session ID</div>
                                    <h3 className="font-mono text-sm font-semibold text-gray-800 break-all">
                                        {session.session_id}
                                    </h3>
                                </div>
                                <div className="text-right text-sm text-gray-500 ml-2">
                                    {formatDistance(new Date(session.created_at), new Date(), {
                                        addSuffix: true
                                    })}
                                </div>
                            </div>
                            <div className="flex gap-4">
                                <p className="text-sm text-gray-600">
                                    Duration: {(session.duration_ms / 1000).toFixed(1)}s
                                </p>
                                <p className="text-sm text-gray-600">
                                    Samples: {session.sample_count}
                                </p>
                                <p className="text-sm text-gray-600">
                                    Rate: {session.sample_rate} Hz
                                </p>
                            </div>
                            {session.labels && session.labels.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-2">
                                    {session.labels.map((label, i) => (
                                        <span key={i} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                                            {label}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
});