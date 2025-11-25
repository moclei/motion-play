import { useState, useRef } from 'react';
import { Toaster } from 'react-hot-toast';
import toast from 'react-hot-toast';
import { SessionList, type SessionListRef } from './components/SessionList';
import { SessionChart } from './components/SessionChart';
import { LabelEditor } from './components/LabelEditor';
import { ExportButton } from './components/ExportButton';
import { SessionConfig } from './components/SessionConfig';
import { Header } from './components/Header';
import { SettingsModal } from './components/SettingsModal';
import { api } from './services/api';
import type { Session, SessionData } from './services/api';
import { Trash2, RefreshCw } from 'lucide-react';

function App() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const sessionListRef = useRef<SessionListRef>(null);

  const handleSelectSession = async (session: Session) => {
    setSelectedSession(session);
    setLoading(true);
    setLoadingSessionId(session.session_id);

    try {
      const data = await api.getSessionData(session.session_id);
      setSessionData(data);
    } catch (err) {
      console.error('Failed to load session data:', err);
      toast.error('Failed to load session data');
    } finally {
      setLoading(false);
      setLoadingSessionId(null);
    }
  };

  const handleSessionUpdate = (labels: string[], notes: string) => {
    if (selectedSession && sessionData) {
      // Update local state
      const updatedSession = { ...selectedSession, labels, notes };
      setSelectedSession(updatedSession);
      setSessionData({
        ...sessionData,
        session: { ...sessionData.session, labels, notes }
      });
      // Trigger session list refresh
      sessionListRef.current?.refresh();
    }
  };

  const handleCollectionStopped = async () => {
    // Wait a moment for data to be processed, then auto-select newest
    setTimeout(async () => {
      await sessionListRef.current?.refresh();
      sessionListRef.current?.autoSelectNewest();
    }, 2000);
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
              <div className="p-6">
                {/* Session Header */}
                <div className="flex justify-between items-start mb-6 pb-4 border-b">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-gray-500 mb-1">Selected Session</div>
                    <h2 className="text-lg font-bold font-mono text-gray-800 break-all">
                      {selectedSession.session_id}
                    </h2>
                  </div>
                  <button
                    onClick={handleDeleteSession}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 flex-shrink-0 ml-4 transition-colors"
                  >
                    <Trash2 size={18} />
                    Delete
                  </button>
                </div>

                {/* Chart - Most important, show first */}
                <div className="mb-6">
                  <SessionChart readings={sessionData.readings} />
                </div>

                {/* Session Config - Context about data collection */}
                <div className="mb-6">
                  <SessionConfig session={sessionData.session} />
                </div>

                {/* Label Editor - Metadata/annotation */}
                <div className="mb-6">
                  <LabelEditor
                    sessionId={selectedSession.session_id}
                    currentLabels={sessionData.session.labels || []}
                    currentNotes={sessionData.session.notes || ''}
                    onUpdate={handleSessionUpdate}
                  />
                </div>

                {/* Export - Utility function */}
                <div className="p-4 border rounded bg-gray-50">
                  <h3 className="font-semibold text-gray-800 mb-3">Export Data</h3>
                  <ExportButton sessionData={sessionData} />
                </div>
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