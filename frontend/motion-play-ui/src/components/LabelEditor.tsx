import { useState } from 'react';
import { Tag, X, Plus } from 'lucide-react';
import { api } from '../services/api';

interface LabelEditorProps {
    sessionId: string;
    currentLabels: string[];
    currentNotes: string;
    detectionDirection?: 'a_to_b' | 'b_to_a' | 'unknown';
    detectionConfidence?: number;
    onUpdate: (labels: string[], notes: string) => void;
}

export const LabelEditor = ({ sessionId, currentLabels, currentNotes, detectionDirection, detectionConfidence, onUpdate }: LabelEditorProps) => {
    const [labels, setLabels] = useState<string[]>(currentLabels);
    const [notes, setNotes] = useState(currentNotes);
    const [newLabel, setNewLabel] = useState('');
    const [saving, setSaving] = useState(false);

    const suggestions = [
        'a->b', 'b->a', 'no-transit', 'false-transit',
        'successful-shot', 'missed-shot', 'practice', 'test',
    ];

    const addLabel = (label: string) => {
        if (label && !labels.includes(label)) {
            setLabels([...labels, label]);
            setNewLabel('');
        }
    };

    const removeLabel = (labelToRemove: string) => {
        setLabels(labels.filter(l => l !== labelToRemove));
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await api.updateSession(sessionId, { labels, notes });
            onUpdate(labels, notes);
            alert('Session updated successfully!');
        } catch (err) {
            console.error('Failed to update session:', err);
            alert('Failed to update session');
        } finally {
            setSaving(false);
        }
    };

    const directionLabel = detectionDirection === 'a_to_b' ? 'A → B'
        : detectionDirection === 'b_to_a' ? 'B → A'
        : detectionDirection === 'unknown' ? 'Unknown' : null;

    return (
        <div className="border rounded">
            {/* Always-visible summary line */}
            <div className="flex items-center gap-2 px-3 py-2 text-sm">
                {directionLabel && (
                    <span className="flex items-center gap-1.5">
                        <span className="font-medium text-indigo-700">Detected:</span>
                        <span className="font-bold text-indigo-900">{directionLabel}</span>
                        {detectionConfidence !== undefined && (
                            <span className="text-indigo-400 text-xs">
                                ({(detectionConfidence * 100).toFixed(0)}%)
                            </span>
                        )}
                    </span>
                )}
                {labels.length > 0 && (
                    <span className="flex items-center gap-1 ml-2">
                        {labels.map((label, i) => (
                            <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                                {label}
                            </span>
                        ))}
                    </span>
                )}
                {!directionLabel && labels.length === 0 && (
                    <span className="text-gray-400 text-xs">No labels</span>
                )}
            </div>

            {/* Collapsible editing section */}
            <details className="border-t">
                <summary className="px-3 py-1.5 text-xs text-gray-500 cursor-pointer hover:text-gray-700 bg-gray-50">
                    Edit labels & notes
                </summary>
                <div className="p-3 space-y-3">
                    {/* Current labels */}
                    <div className="flex flex-wrap gap-1.5">
                        {labels.map((label, i) => (
                            <span key={i} className="flex items-center gap-1 px-2 py-0.5 bg-blue-500 text-white rounded-full text-xs">
                                <Tag size={10} />
                                {label}
                                <button onClick={() => removeLabel(label)} className="hover:bg-blue-600 rounded-full p-0.5">
                                    <X size={10} />
                                </button>
                            </span>
                        ))}
                    </div>

                    {/* Add label */}
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={newLabel}
                            onChange={(e) => setNewLabel(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && addLabel(newLabel)}
                            placeholder="Add a label..."
                            className="flex-1 px-2 py-1 border rounded text-sm"
                        />
                        <button
                            onClick={() => addLabel(newLabel)}
                            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm flex items-center gap-1"
                        >
                            <Plus size={14} /> Add
                        </button>
                    </div>

                    {/* Quick-add suggestions */}
                    <div className="flex flex-wrap gap-1">
                        {suggestions.filter(s => !labels.includes(s)).slice(0, 6).map((s, i) => (
                            <button key={i} onClick={() => addLabel(s)} className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300">
                                {s}
                            </button>
                        ))}
                    </div>

                    {/* Notes */}
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Notes..."
                        className="w-full px-2 py-1 border rounded text-sm"
                        rows={2}
                    />

                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="w-full px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300 text-sm"
                    >
                        {saving ? 'Saving...' : 'Save'}
                    </button>
                </div>
            </details>
        </div>
    );
};