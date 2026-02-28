
import { useEffect, useState, useImperativeHandle, forwardRef, useCallback } from 'react';
import { api } from '../services/api';
import type { Session } from '../services/api';
import { Trash2, RefreshCw, ChevronLeft, ChevronRight, Zap, Radio } from 'lucide-react';
import toast from 'react-hot-toast';

function formatCompactTime(timestamp: number): string {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 5) return 'now';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
}

const DIRECTION_LABELS = ['a->b', 'b->a', 'no-transit', 'false-transit'] as const;

function getDirectionDisplay(session: Session): { text: string; color: string } | null {
    const dirLabel = session.labels?.find(l => DIRECTION_LABELS.includes(l as any));
    if (dirLabel) {
        const colors: Record<string, string> = {
            'a->b': 'bg-emerald-100 text-emerald-800',
            'b->a': 'bg-amber-100 text-amber-800',
            'no-transit': 'bg-gray-200 text-gray-700',
            'false-transit': 'bg-red-100 text-red-700',
        };
        return { text: dirLabel, color: colors[dirLabel] || 'bg-gray-100 text-gray-700' };
    }
    if (session.detection_direction && session.detection_direction !== 'unknown') {
        const text = session.detection_direction === 'a_to_b' ? 'a->b' : 'b->a';
        const color = session.detection_direction === 'a_to_b'
            ? 'bg-emerald-100 text-emerald-800'
            : 'bg-amber-100 text-amber-800';
        return { text, color: `${color} border border-dashed border-current opacity-75` };
    }
    return null;
}

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

    // Track sessions that are still uploading
    const [previousSampleCounts, setPreviousSampleCounts] = useState<Map<string, number>>(new Map());
    const [previousSessionIds, setPreviousSessionIds] = useState<Set<string>>(new Set());
    const [uploadingSessions, setUploadingSessions] = useState<Set<string>>(new Set());

    const isSessionReady = (session: Session): boolean => {
        if (session.pipeline_status === 'complete' || session.pipeline_status === 'partial') {
            return true;
        }
        return false;
    };

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

    // Auto-select newest ready session (that isn't already selected)
    const autoSelectNewest = useCallback(() => {
        if (sessions.length > 0) {
            const readySessions = sessions.filter(s => isSessionReady(s));
            if (readySessions.length > 0) {
                const newest = [...readySessions].sort((a, b) => b.created_at - a.created_at)[0];
                setSelectedId(newest.session_id);
                onSelectSession(newest);
            }
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
            loadSessions(false);
        }, 5000);

        return () => clearInterval(interval);
    }, [loadSessions]);

    // Track uploading sessions and auto-select on completion
    useEffect(() => {
        const newUploadingSessions = new Set<string>();
        const newCounts = new Map<string, number>();
        const currentSessionIds = new Set(sessions.map(s => s.session_id));
        const justCompleted: Session[] = [];

        sessions.forEach(session => {
            const prevCount = previousSampleCounts.get(session.session_id);
            const currentCount = session.sample_count;
            const wasKnownBefore = previousSessionIds.has(session.session_id);
            newCounts.set(session.session_id, currentCount);

            const ready = isSessionReady(session);

            if (ready && uploadingSessions.has(session.session_id)) {
                justCompleted.push(session);
            } else if (!ready) {
                if (prevCount !== undefined && currentCount > prevCount) {
                    newUploadingSessions.add(session.session_id);
                } else if (!wasKnownBefore && previousSessionIds.size > 0) {
                    newUploadingSessions.add(session.session_id);
                } else if (uploadingSessions.has(session.session_id)) {
                    // Count stabilized but pipeline_status not yet set -- still uploading
                    newUploadingSessions.add(session.session_id);
                }
            }
        });

        setPreviousSampleCounts(newCounts);
        setPreviousSessionIds(currentSessionIds);
        setUploadingSessions(newUploadingSessions);

        // Auto-select the newest session that just completed
        if (justCompleted.length > 0) {
            const newest = justCompleted.sort((a, b) => b.created_at - a.created_at)[0];
            setSelectedId(newest.session_id);
            onSelectSession(newest);
        }
    }, [sessions]);

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
                                        ? 'bg-amber-50/60 border-amber-300 opacity-60'
                                        : selectedId === session.session_id
                                            ? 'bg-blue-50 border-blue-300'
                                            : selectedForDeletion.has(session.session_id)
                                                ? 'bg-red-50 border-red-300'
                                                : 'hover:bg-gray-50 border-gray-200'
                                        } ${loadingSessionId === session.session_id ? 'opacity-50' : ''}`}
                                >
                                    {/* Uploading progress indicator */}
                                    {isUploading && (
                                        <div className="absolute top-0 left-0 right-0 h-1.5 bg-amber-200 rounded-t overflow-hidden">
                                            <div className="h-full bg-amber-400 rounded-full animate-[pulse_1.5s_ease-in-out_infinite]" style={{ width: '100%' }} />
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
                                            className={`flex-1 ${isUploading ? 'cursor-not-allowed select-none' : 'cursor-pointer'}`}
                                            onClick={() => {
                                                if (isUploading) return;
                                                setSelectedId(session.session_id);
                                                onSelectSession(session);
                                            }}
                                        >
                                            {/* Row 1: Session ID + timestamp */}
                                            <div className="flex justify-between items-start mb-1">
                                                <h3 className="font-mono text-xs font-semibold text-gray-800 truncate flex-1 min-w-0" title={session.session_id}>
                                                    {session.session_id}
                                                </h3>
                                                <span className="text-xs text-gray-400 ml-2 flex-shrink-0">
                                                    {session.created_at ? formatCompactTime(session.created_at) : '?'}
                                                </span>
                                            </div>
                                            {/* Row 2: Mode + duration + sample count */}
                                            <div className="flex flex-wrap items-center gap-1 mb-1">
                                                {(session.session_type === 'interrupt' || session.mode === 'interrupt_debug') && (
                                                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-cyan-100 text-cyan-700 rounded text-xs font-medium">
                                                        <Zap size={10} />
                                                        INT
                                                    </span>
                                                )}
                                                {session.mode === 'live_debug' && (
                                                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-fuchsia-100 text-fuchsia-700 rounded text-xs font-medium">
                                                        <Radio size={10} />
                                                        {session.capture_reason === 'missed_event' ? 'MISSED' : 'LIVE'}
                                                    </span>
                                                )}
                                                <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-mono">
                                                    {(session.duration_ms / 1000).toFixed(1)}s
                                                </span>
                                                {isUploading ? (
                                                    <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium flex items-center gap-1">
                                                        <RefreshCw size={10} className="animate-spin" />
                                                        Uploading...
                                                    </span>
                                                ) : (
                                                    <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-mono">
                                                        {session.session_type === 'interrupt' || session.mode === 'interrupt_debug'
                                                            ? `${session.event_count || 0} events`
                                                            : `${session.sample_count} samples`}
                                                    </span>
                                                )}
                                            </div>
                                            {/* Row 3: Direction label + config badges */}
                                            {(() => {
                                                const dir = getDirectionDisplay(session);
                                                const otherLabels = session.labels?.filter(l => !DIRECTION_LABELS.includes(l as any)) || [];
                                                const configTooltip = session.interrupt_config
                                                    ? `Margin: ${session.interrupt_config.threshold_margin} | Mode: ${session.interrupt_config.mode} | LED: ${session.interrupt_config.led_current}`
                                                    : session.vcnl4040_config
                                                        ? `${session.vcnl4040_config.sample_rate_hz}Hz | LED: ${session.vcnl4040_config.led_current} | Duty: ${session.vcnl4040_config.duty_cycle} | ${session.vcnl4040_config.high_resolution ? '16-bit' : '12-bit'}${session.vcnl4040_config.read_ambient ? ' | Ambient' : ''}${session.vcnl4040_config.i2c_clock_khz ? ` | I2C: ${session.vcnl4040_config.i2c_clock_khz}kHz` : ''}`
                                                        : undefined;
                                                return (
                                                    <div className="flex flex-wrap items-center gap-1" title={configTooltip}>
                                                        {dir && (
                                                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${dir.color}`}>
                                                                {dir.text}
                                                            </span>
                                                        )}
                                                        {otherLabels.slice(0, 2).map((label, i) => (
                                                            <span key={i} className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
                                                                {label}
                                                            </span>
                                                        ))}
                                                        {otherLabels.length > 2 && (
                                                            <span className="text-xs text-gray-500">+{otherLabels.length - 2}</span>
                                                        )}
                                                        {session.interrupt_config && (
                                                            <>
                                                                <span className="px-1.5 py-0.5 bg-green-100 text-green-800 rounded text-xs font-mono">
                                                                    {session.interrupt_config.integration_time}T
                                                                </span>
                                                                <span className="px-1.5 py-0.5 bg-pink-100 text-pink-800 rounded text-xs font-mono">
                                                                    {session.interrupt_config.multi_pulse}P
                                                                </span>
                                                            </>
                                                        )}
                                                        {session.vcnl4040_config && (
                                                            <>
                                                                <span className="px-1.5 py-0.5 bg-green-100 text-green-800 rounded text-xs font-mono">
                                                                    {session.vcnl4040_config.integration_time}
                                                                </span>
                                                                <span className="px-1.5 py-0.5 bg-pink-100 text-pink-800 rounded text-xs font-mono">
                                                                    {session.vcnl4040_config.multi_pulse || '1'}P
                                                                </span>
                                                            </>
                                                        )}
                                                    </div>
                                                );
                                            })()}
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