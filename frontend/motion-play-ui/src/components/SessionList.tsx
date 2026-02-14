
import { useEffect, useState, useImperativeHandle, forwardRef, useCallback } from 'react';
import { api } from '../services/api';
import type { Session } from '../services/api';
import { formatDistance } from 'date-fns';
import { Trash2, RefreshCw, ChevronLeft, ChevronRight, Zap, Radio } from 'lucide-react';
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
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    // Track sessions that are still uploading (sample_count is changing)
    const [previousSampleCounts, setPreviousSampleCounts] = useState<Map<string, number>>(new Map());
    const [previousSessionIds, setPreviousSessionIds] = useState<Set<string>>(new Set());
    const [uploadingSessions, setUploadingSessions] = useState<Set<string>>(new Set());
    const [justCompletedSession, setJustCompletedSession] = useState<string | null>(null);

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

    // Track uploading sessions (sample_count is changing OR newly appeared)
    useEffect(() => {
        const newUploadingSessions = new Set<string>();
        const newCounts = new Map<string, number>();
        const currentSessionIds = new Set(sessions.map(s => s.session_id));

        sessions.forEach(session => {
            const prevCount = previousSampleCounts.get(session.session_id);
            const currentCount = session.sample_count;
            const wasKnownBefore = previousSessionIds.has(session.session_id);
            newCounts.set(session.session_id, currentCount);

            // If sample count increased, it's still uploading
            if (prevCount !== undefined && currentCount > prevCount) {
                newUploadingSessions.add(session.session_id);
            }
            // If session is truly NEW (wasn't in the previous poll at all), mark as uploading
            else if (!wasKnownBefore && previousSessionIds.size > 0) {
                // Only mark as new/uploading if we've already done at least one poll
                // (previousSessionIds.size > 0 means this isn't the initial load)
                newUploadingSessions.add(session.session_id);
            }
            // If session was uploading but count is now stable, it just completed
            else if (uploadingSessions.has(session.session_id) && prevCount !== undefined && currentCount === prevCount) {
                setJustCompletedSession(session.session_id);
            }
        });

        setPreviousSampleCounts(newCounts);
        setPreviousSessionIds(currentSessionIds);
        setUploadingSessions(newUploadingSessions);
    }, [sessions]);

    // Auto-select just completed session
    useEffect(() => {
        if (justCompletedSession) {
            const session = sessions.find(s => s.session_id === justCompletedSession);
            if (session) {
                setSelectedId(justCompletedSession);
                onSelectSession(session);
            }
            setJustCompletedSession(null);
        }
    }, [justCompletedSession, sessions, onSelectSession]);

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

    // Select all sessions on current page
    const selectAll = () => {
        const allIds = paginatedSessions.map(s => s.session_id);
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

    // Pagination logic
    const totalPages = Math.ceil(filteredSessions.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedSessions = filteredSessions.slice(startIndex, startIndex + itemsPerPage);

    // Reset to page 1 when filters change
    useEffect(() => {
        setCurrentPage(1);
    }, [filterMode, searchTerm]);

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
                        <option value="debug">Debug (Proximity)</option>
                        <option value="interrupt_debug">Debug (Interrupt)</option>
                        <option value="play">Play Mode</option>
                        <option value="live_debug">Live Debug</option>
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
                    {paginatedSessions.length > 0 && (
                        <div className="flex gap-2">
                            <button
                                onClick={selectAll}
                                className="flex-1 px-3 py-1.5 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                            >
                                Select Page
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

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between pt-2 bg-gray-100 rounded px-2 py-1.5">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-700 hover:text-blue-600 hover:bg-white rounded disabled:text-gray-400 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronLeft size={14} />
                                Prev
                            </button>
                            <span className="text-xs font-medium text-gray-700">
                                Page {currentPage} of {totalPages}
                            </span>
                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-700 hover:text-blue-600 hover:bg-white rounded disabled:text-gray-400 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors"
                            >
                                Next
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Scrollable session list */}
            <div className="flex-1 overflow-y-auto px-4 pb-4">
                <div className="space-y-2">
                    {paginatedSessions.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-gray-500">
                                {sessions.length === 0 ? 'No sessions found' : 'No sessions match your filters'}
                            </p>
                        </div>
                    ) : (
                        paginatedSessions.map((session) => {
                            const isUploading = uploadingSessions.has(session.session_id);

                            return (
                                <div
                                    key={session.session_id}
                                    className={`p-3 border rounded transition-colors relative ${isUploading
                                        ? 'bg-amber-50 border-amber-300'
                                        : selectedId === session.session_id
                                            ? 'bg-blue-50 border-blue-300'
                                            : selectedForDeletion.has(session.session_id)
                                                ? 'bg-red-50 border-red-300'
                                                : 'hover:bg-gray-50 border-gray-200'
                                        } ${loadingSessionId === session.session_id ? 'opacity-50' : ''}`}
                                >
                                    {/* Uploading progress indicator */}
                                    {isUploading && (
                                        <div className="absolute top-0 left-0 right-0 h-1 bg-amber-200 rounded-t overflow-hidden">
                                            <div className="h-full bg-amber-500 animate-pulse" style={{ width: '100%' }} />
                                        </div>
                                    )}

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
                                            disabled={isUploading}
                                        />

                                        {/* Session content */}
                                        <div
                                            className={`flex-1 ${isUploading ? 'cursor-wait' : 'cursor-pointer'}`}
                                            onClick={() => {
                                                if (isUploading) return; // Prevent selection while uploading
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
                                                {/* Session type indicator */}
                                                {(session.session_type === 'interrupt' || session.mode === 'interrupt_debug') && (
                                                    <span className="flex items-center gap-0.5 text-cyan-600 font-medium">
                                                        <Zap size={10} />
                                                        INT
                                                    </span>
                                                )}
                                                {session.mode === 'live_debug' && (
                                                    <span className="flex items-center gap-0.5 text-fuchsia-600 font-medium">
                                                        <Radio size={10} />
                                                        {session.capture_reason === 'missed_event' ? 'MISSED' : 'LIVE'}
                                                    </span>
                                                )}
                                                <span>{(session.duration_ms / 1000).toFixed(1)}s</span>
                                                <span className={isUploading ? 'text-amber-600 font-medium' : ''}>
                                                    {session.session_type === 'interrupt' || session.mode === 'interrupt_debug'
                                                        ? `${session.event_count || 0} events`
                                                        : `${session.sample_count} samples`}
                                                    {isUploading && (
                                                        <span className="ml-1 inline-flex items-center">
                                                            <RefreshCw size={10} className="animate-spin" />
                                                        </span>
                                                    )}
                                                </span>
                                                {session.session_type !== 'interrupt' && session.mode !== 'interrupt_debug' && (
                                                    <span>{session.sample_rate} Hz</span>
                                                )}
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
                                            {/* Config Badges - show different info for interrupt vs proximity */}
                                            {session.interrupt_config ? (
                                                <div className="flex flex-wrap gap-1 mt-1">
                                                    <span className="px-1.5 py-0.5 bg-cyan-100 text-cyan-800 rounded text-xs font-mono">
                                                        M:{session.interrupt_config.threshold_margin}
                                                    </span>
                                                    <span className="px-1.5 py-0.5 bg-cyan-100 text-cyan-800 rounded text-xs font-mono">
                                                        {session.interrupt_config.integration_time}T
                                                    </span>
                                                    <span className="px-1.5 py-0.5 bg-pink-100 text-pink-800 rounded text-xs font-mono">
                                                        {session.interrupt_config.multi_pulse}P
                                                    </span>
                                                    <span className="px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded text-xs">
                                                        {session.interrupt_config.mode}
                                                    </span>
                                                </div>
                                            ) : session.vcnl4040_config && (
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
                                                    {session.vcnl4040_config.multi_pulse && session.vcnl4040_config.multi_pulse !== '1' && (
                                                        <span className="px-1.5 py-0.5 bg-pink-100 text-pink-800 rounded text-xs font-mono">
                                                            {session.vcnl4040_config.multi_pulse}P
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
});