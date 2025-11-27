
import { useEffect, useState, useImperativeHandle, forwardRef, useCallback } from 'react';
import { api } from '../services/api';
import type { Session } from '../services/api';
import { formatDistance } from 'date-fns';
import { Trash2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export interface SessionListRef {
    refresh: () => Promise<void>;
    autoSelectNewest: () => void;
}

interface SessionListProps {
    onSelectSession: (session: Session) => void;
    onSessionDeleted?: () => void;
    loadingSessionId?: string | null;
}

export const SessionList = forwardRef<SessionListRef, SessionListProps>(({
    onSelectSession,
    onSessionDeleted,
    loadingSessionId
}, ref) => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [filterMode, setFilterMode] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedForDeletion, setSelectedForDeletion] = useState<Set<string>>(new Set());
    const [deleting, setDeleting] = useState(false);

    const loadSessions = useCallback(async (showLoading = true) => {
        try {
            if (showLoading) {
                setRefreshing(true);
            }
            const data = await api.getSessions();
            setSessions(data);
            setError(null);
        } catch (err) {
            setError('Failed to load sessions');
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    // Auto-select newest session
    const autoSelectNewest = useCallback(() => {
        if (sessions.length > 0) {
            const sortedSessions = [...sessions].sort((a, b) => b.created_at - a.created_at);
            const newest = sortedSessions[0];
            setSelectedId(newest.session_id);
            onSelectSession(newest);
        }
    }, [sessions, onSelectSession]);

    // Expose functions to parent via ref
    useImperativeHandle(ref, () => ({
        refresh: loadSessions,
        autoSelectNewest
    }));

    // Initial load
    useEffect(() => {
        loadSessions();
    }, [loadSessions]);

    // Polling mechanism - check for new sessions every 5 seconds
    useEffect(() => {
        const interval = setInterval(() => {
            loadSessions(false); // Silent refresh
        }, 5000);

        return () => clearInterval(interval);
    }, [loadSessions]);

    // Handle batch deletion with rate limiting
    const handleBatchDelete = async () => {
        if (selectedForDeletion.size === 0) return;

        const count = selectedForDeletion.size;
        if (!confirm(`Are you sure you want to delete ${count} session(s)?`)) {
            return;
        }

        try {
            setDeleting(true);
            const sessionIds = Array.from(selectedForDeletion);

            // Delete in batches of 3 at a time to avoid overwhelming the backend
            const batchSize = 3;
            let successCount = 0;
            let failCount = 0;

            for (let i = 0; i < sessionIds.length; i += batchSize) {
                const batch = sessionIds.slice(i, i + batchSize);
                const results = await Promise.allSettled(
                    batch.map(id => api.deleteSession(id))
                );

                results.forEach((result, idx) => {
                    if (result.status === 'fulfilled') {
                        successCount++;
                    } else {
                        failCount++;
                        console.error(`Failed to delete session ${batch[idx]}:`, result.reason);
                    }
                });

                // Small delay between batches to avoid throttling
                if (i + batchSize < sessionIds.length) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }

            if (successCount > 0) {
                toast.success(`Successfully deleted ${successCount} of ${count} session(s)`);
            }
            if (failCount > 0) {
                toast.error(`Failed to delete ${failCount} session(s). Check console for details.`);
            }

            setSelectedForDeletion(new Set());
            setSelectedId(null);
            await loadSessions();

            if (onSessionDeleted) {
                onSessionDeleted();
            }
        } catch (err) {
            toast.error('Failed to delete sessions');
            console.error(err);
        } finally {
            setDeleting(false);
        }
    };

    // Toggle selection for deletion
    const toggleSelection = (sessionId: string) => {
        const newSelection = new Set(selectedForDeletion);
        if (newSelection.has(sessionId)) {
            newSelection.delete(sessionId);
        } else {
            newSelection.add(sessionId);
        }
        setSelectedForDeletion(newSelection);
    };

    // Select all filtered sessions
    const selectAll = () => {
        const allIds = filteredSessions.map(s => s.session_id);
        setSelectedForDeletion(new Set(allIds));
    };

    // Clear all selections
    const clearSelection = () => {
        setSelectedForDeletion(new Set());
    };

    // Filter sessions based on mode and search term, then sort by newest first
    const filteredSessions = sessions
        .filter(session => {
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
        })
        .sort((a, b) => b.created_at - a.created_at); // Sort by created_at descending (newest first)

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full p-8">
                <div className="text-center">
                    <RefreshCw className="animate-spin mx-auto mb-2" size={24} />
                    <p className="text-gray-600">Loading sessions...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-red-600">
                {error}
                <button onClick={() => loadSessions()} className="ml-4 text-blue-600">
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold text-gray-800">Sessions</h2>
                    <button
                        onClick={() => loadSessions()}
                        disabled={refreshing}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors disabled:opacity-50"
                        title="Refresh"
                    >
                        <RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />
                    </button>
                </div>

                {/* Filter Controls */}
                <div className="space-y-2">
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

                    {/* Results count and batch controls */}
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">
                            {filteredSessions.length} of {sessions.length} sessions
                        </span>
                        {selectedForDeletion.size > 0 && (
                            <span className="text-blue-600 font-medium">
                                {selectedForDeletion.size} selected
                            </span>
                        )}
                    </div>

                    {/* Batch selection controls */}
                    {filteredSessions.length > 0 && (
                        <div className="flex gap-2">
                            <button
                                onClick={selectAll}
                                className="flex-1 px-3 py-1.5 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                            >
                                Select All
                            </button>
                            {selectedForDeletion.size > 0 && (
                                <>
                                    <button
                                        onClick={clearSelection}
                                        className="flex-1 px-3 py-1.5 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                                    >
                                        Clear
                                    </button>
                                    <button
                                        onClick={handleBatchDelete}
                                        disabled={deleting}
                                        className="flex-1 px-3 py-1.5 text-xs bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-300 transition-colors flex items-center justify-center gap-1"
                                    >
                                        <Trash2 size={12} />
                                        {deleting ? 'Deleting...' : `Delete (${selectedForDeletion.size})`}
                                    </button>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Scrollable session list */}
            <div className="flex-1 overflow-y-auto px-4 pb-4">
                <div className="space-y-2">
                    {filteredSessions.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-gray-500">
                                {sessions.length === 0 ? 'No sessions found' : 'No sessions match your filters'}
                            </p>
                        </div>
                    ) : (
                        filteredSessions.map((session) => (
                            <div
                                key={session.session_id}
                                className={`p-3 border rounded transition-colors relative ${selectedId === session.session_id
                                    ? 'bg-blue-50 border-blue-300'
                                    : selectedForDeletion.has(session.session_id)
                                        ? 'bg-red-50 border-red-300'
                                        : 'hover:bg-gray-50 border-gray-200'
                                    } ${loadingSessionId === session.session_id ? 'opacity-50' : ''}`}
                            >
                                {/* Loading overlay */}
                                {loadingSessionId === session.session_id && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded">
                                        <RefreshCw className="animate-spin" size={20} />
                                    </div>
                                )}

                                <div className="flex items-start gap-2">
                                    {/* Checkbox for batch selection */}
                                    <input
                                        type="checkbox"
                                        checked={selectedForDeletion.has(session.session_id)}
                                        onChange={() => toggleSelection(session.session_id)}
                                        onClick={(e) => e.stopPropagation()}
                                        className="mt-1 w-4 h-4 flex-shrink-0"
                                    />

                                    {/* Session content */}
                                    <div
                                        className="flex-1 cursor-pointer"
                                        onClick={() => {
                                            setSelectedId(session.session_id);
                                            onSelectSession(session);
                                        }}
                                    >
                                        <div className="flex justify-between items-start mb-1">
                                            <div className="flex-1 min-w-0">
                                                <div className="text-xs text-gray-500 mb-0.5">Session ID</div>
                                                <h3 className="font-mono text-xs font-semibold text-gray-800 truncate">
                                                    {session.session_id}
                                                </h3>
                                            </div>
                                            <div className="text-right text-xs text-gray-500 ml-2 flex-shrink-0">
                                                {session.created_at ? formatDistance(new Date(session.created_at), new Date(), {
                                                    addSuffix: true
                                                }) : 'Unknown'}
                                            </div>
                                        </div>
                                        <div className="flex gap-3 text-xs text-gray-600 mb-1">
                                            <span>{(session.duration_ms / 1000).toFixed(1)}s</span>
                                            <span>{session.sample_count} samples</span>
                                            <span>{session.sample_rate} Hz</span>
                                        </div>
                                        {session.labels && session.labels.length > 0 && (
                                            <div className="flex flex-wrap gap-1 mb-1">
                                                {session.labels.slice(0, 3).map((label, i) => (
                                                    <span key={i} className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
                                                        {label}
                                                    </span>
                                                ))}
                                                {session.labels.length > 3 && (
                                                    <span className="text-xs text-gray-500">
                                                        +{session.labels.length - 3} more
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                        {/* Config Badges */}
                                        {session.vcnl4040_config && (
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                <span className="px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded text-xs font-mono">
                                                    {session.vcnl4040_config.sample_rate_hz}Hz
                                                </span>
                                                <span className="px-1.5 py-0.5 bg-orange-100 text-orange-800 rounded text-xs font-mono">
                                                    {session.vcnl4040_config.led_current}
                                                </span>
                                                <span className="px-1.5 py-0.5 bg-green-100 text-green-800 rounded text-xs font-mono">
                                                    {session.vcnl4040_config.integration_time}
                                                </span>
                                                <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-800 rounded text-xs">
                                                    {session.vcnl4040_config.high_resolution ? '16-bit' : '12-bit'}
                                                </span>
                                                {session.vcnl4040_config.read_ambient && (
                                                    <span className="px-1.5 py-0.5 bg-teal-100 text-teal-800 rounded text-xs">
                                                        Ambient
                                                    </span>
                                                )}
                                                {session.vcnl4040_config.i2c_clock_khz && (
                                                    <span className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-xs font-mono">
                                                        {session.vcnl4040_config.i2c_clock_khz}kHz
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
});