import { useState, useRef } from 'react';
import { SessionList, type SessionListRef } from './components/SessionList';
import { SessionChart } from './components/SessionChart';
import { DeviceControl } from './components/DeviceControl';
import { LabelEditor } from './components/LabelEditor';
import { ExportButton } from './components/ExportButton';
import { ModeSelector } from './components/ModeSelector';
import { SessionConfig } from './components/SessionConfig';
import { SensorConfig } from './components/SensorConfig';
import { api } from './services/api';
import type { Session, SessionData } from './services/api';
import { Trash2 } from 'lucide-react';

function App() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const sessionListRef = useRef<SessionListRef>(null);

  const handleSelectSession = async (session: Session) => {
    setSelectedSession(session);
    setLoading(true);

    try {
      const data = await api.getSessionData(session.session_id);
      setSessionData(data);
    } catch (err) {
      console.error('Failed to load session data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Add handler
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
    // Wait a moment for data to be processed
    setTimeout(async () => {
      await sessionListRef.current?.refresh();
    }, 2000);
  };

  const handleDeleteSession = async () => {
    if (!selectedSession) {
      console.log('No session selected');
      return;
    }

    const sessionIdToDelete = selectedSession.session_id;
    console.log('Attempting to delete session:', sessionIdToDelete);

    if (!confirm(`Are you sure you want to delete session:\n${sessionIdToDelete}?`)) {
      return;
    }

    try {
      console.log('Calling deleteSession API for:', sessionIdToDelete);
      const result = await api.deleteSession(sessionIdToDelete);
      console.log('Delete result:', result);

      setSelectedSession(null);
      setSessionData(null);
      await sessionListRef.current?.refresh();

      alert(`Session deleted successfully:\n${sessionIdToDelete}`);
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert(`Failed to delete session:\n${sessionIdToDelete}\n\nError: ${err}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">
            Motion Play Dashboard
          </h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4">
        <div className="grid grid-cols-12 gap-6">
          {/* Left sidebar - Device Control */}
          <div className="col-span-3 space-y-4 overflow-y-auto max-h-screen pb-6">
            <DeviceControl onCollectionStopped={handleCollectionStopped} />
            <ModeSelector />
            <SensorConfig />
          </div>

          {/* Middle - Session List */}
          <div className="col-span-3 bg-white rounded shadow">
            <SessionList ref={sessionListRef} onSelectSession={handleSelectSession} />
          </div>

          {/* Right - Session Detail */}
          <div className="col-span-6 bg-white rounded shadow p-4">
            {!selectedSession ? (
              <div className="text-center text-gray-500 py-20">
                Select a session to view details
              </div>
            ) : loading ? (
              <div className="text-center py-20">Loading session data...</div>
            ) : sessionData ? (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Selected Session</div>
                    <h2 className="text-xl font-bold font-mono text-gray-800 break-all">
                      {selectedSession.session_id}
                    </h2>
                  </div>
                  <button
                    onClick={handleDeleteSession}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 flex-shrink-0"
                  >
                    <Trash2 size={18} />
                    Delete
                  </button>
                </div>
                <LabelEditor
                  sessionId={selectedSession.session_id}
                  currentLabels={sessionData.session.labels || []}
                  currentNotes={sessionData.session.notes || ''}
                  onUpdate={handleSessionUpdate}
                />
                <div className="mt-4 p-4 border rounded bg-gray-50">
                  <h3 className="font-semibold text-gray-800 mb-3">Export Data</h3>
                  <ExportButton sessionData={sessionData} />
                </div>
                <div className="mt-4">
                  <SessionConfig session={sessionData.session} />
                </div>
                <div className="mt-4">
                  <SessionChart readings={sessionData.readings} />
                </div>
              </div>
            ) : (
              <div className="text-center text-red-500 py-20">
                Failed to load session data
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;