import { useState, useRef, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import toast from 'react-hot-toast';
import { SessionList, type SessionListRef } from './components/SessionList';
import { SessionChart, type BrushTimeRange } from './components/SessionChart';
import { InterruptSessionView } from './components/InterruptSessionView';
import { LabelEditor } from './components/LabelEditor';
import { ExportButton } from './components/ExportButton';
import { SessionConfig } from './components/SessionConfig';
import { Header } from './components/Header';
import { SettingsModal } from './components/SettingsModal';
import { api, isInterruptSession, isProximitySession } from './services/api';
import type { Session, SessionData, ProximitySessionData } from './services/api';
import { Trash2, RefreshCw, Download, X } from 'lucide-react';

function App() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [brushTimeRange, setBrushTimeRange] = useState<BrushTimeRange | null>(null);
  const sessionListRef = useRef<SessionListRef>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Stable callback for brush changes (won't cause SessionChart to re-render)
  const handleBrushChange = useCallback((range: BrushTimeRange | null) => {
    setBrushTimeRange(range);
  }, []);

  const handleSelectSession = async (session: Session) => {
    // Cancel any in-flight fetch so stale responses don't overwrite
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setSelectedSession(session);
    setLoading(true);
    setLoadingSessionId(session.session_id);
    setBrushTimeRange(null);

    try {
      const data = await api.getSessionData(session.session_id, controller.signal);
      if (controller.signal.aborted) return;
      setSessionData(data);
    } catch (err: any) {
      if (err?.name === 'CanceledError' || err?.name === 'AbortError') return;
      console.error('Failed to load session data:', err);
      toast.error('Failed to load session data');
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
        setLoadingSessionId(null);
      }
    }
  };

  const handleSessionUpdate = (labels: string[], notes: string) => {
    if (selectedSession && sessionData) {
      const updatedSession = { ...selectedSession, labels, notes };
      setSelectedSession(updatedSession);
      setSessionData({
        ...sessionData,
        session: { ...sessionData.session, labels, notes }
      });
      sessionListRef.current?.refresh();
    }
  };

  const handleCollectionStopped = async () => {
    await sessionListRef.current?.refresh();
  };

  const handleDeleteSession = async () => {
    if (!selectedSession) {
      return;
    }

    const sessionIdToDelete = selectedSession.session_id;

    if (!confirm(`Are you sure you want to delete session:\n${sessionIdToDelete}?`)) {
      return;
    }

    setLoadingSessionId(sessionIdToDelete);

    try {
      await api.deleteSession(sessionIdToDelete);
      toast.success('Session deleted successfully');

      setSelectedSession(null);
      setSessionData(null);
      await sessionListRef.current?.refresh();
    } catch (err) {
      console.error('Failed to delete session:', err);
      toast.error('Failed to delete session');
    } finally {
      setLoadingSessionId(null);
    }
  };

  const handleSessionDeleted = () => {
    setSelectedSession(null);
    setSessionData(null);
  };

  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
      <Toaster position="top-right" />

      {/* Header with controls */}
      <Header
        onCollectionStopped={handleCollectionStopped}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      {/* Main content - full width */}
      <main className="flex-1 flex overflow-hidden">
        <div className="flex gap-6 p-6 h-full w-full">
          {/* Left - Session List (narrower, scrollable) */}
          <div className="w-80 bg-white rounded-lg shadow flex flex-col max-h-full">
            <SessionList
              ref={sessionListRef}
              onSelectSession={handleSelectSession}
              onSessionDeleted={handleSessionDeleted}
              loadingSessionId={loadingSessionId}
            />
          </div>

          {/* Right - Session Detail (flexible width, scrollable) */}
          <div className="flex-1 bg-white rounded-lg shadow overflow-y-auto">
            {!selectedSession ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500">
                  <p className="text-lg">Select a session to view details</p>
                  <p className="text-sm mt-2">Click on a session from the list</p>
                </div>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <RefreshCw className="animate-spin mx-auto mb-2" size={32} />
                  <p className="text-gray-600">Loading session data...</p>
                </div>
              </div>
            ) : sessionData ? (
              <div className="p-4">
                {/* Compact Header */}
                <div className="flex items-center gap-3 mb-3 pb-2 border-b">
                  <h2 className="text-sm font-bold font-mono text-gray-800 truncate flex-1 min-w-0" title={selectedSession.session_id}>
                    {selectedSession.session_id}
                  </h2>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {isProximitySession(sessionData) && (
                      <button
                        onClick={() => setExportOpen(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                      >
                        <Download size={14} />
                        Export
                      </button>
                    )}
                    <button
                      onClick={handleDeleteSession}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                    >
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </div>
                </div>

                {/* Labels & Detection (near chart) */}
                <div className="mb-3">
                  <LabelEditor
                    sessionId={selectedSession.session_id}
                    currentLabels={sessionData.session.labels || []}
                    currentNotes={sessionData.session.notes || ''}
                    detectionDirection={sessionData.session.detection_direction}
                    detectionConfidence={sessionData.session.detection_confidence}
                    onUpdate={handleSessionUpdate}
                  />
                </div>

                {/* Chart/Visualization */}
                <div className="mb-4">
                  {isInterruptSession(sessionData) ? (
                    <InterruptSessionView
                      events={sessionData.events}
                      config={sessionData.session.interrupt_config}
                      durationMs={sessionData.session.duration_ms}
                      sessionId={sessionData.session.session_id}
                    />
                  ) : isProximitySession(sessionData) ? (
                    <SessionChart
                      readings={sessionData.readings}
                      session={sessionData.session}
                      onBrushChange={handleBrushChange}
                    />
                  ) : null}
                </div>

                {/* Compact Session Config */}
                <div className="mb-3">
                  <SessionConfig session={sessionData.session} />
                </div>

                {/* Export Modal */}
                {exportOpen && isProximitySession(sessionData) && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setExportOpen(false)}>
                    <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg mx-4" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-gray-800">Export Data</h3>
                        <button onClick={() => setExportOpen(false)} className="text-gray-400 hover:text-gray-600">
                          <X size={20} />
                        </button>
                      </div>
                      <ExportButton
                        sessionData={sessionData as ProximitySessionData}
                        brushTimeRange={brushTimeRange}
                      />
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-red-500">
                  <p className="text-lg">Failed to load session data</p>
                  <button
                    onClick={() => handleSelectSession(selectedSession)}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  );
}

export default App;