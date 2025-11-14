import { useState } from 'react';
import { Tag, X, Plus } from 'lucide-react';
import { api } from '../services/api';

interface LabelEditorProps {
    sessionId: string;
    currentLabels: string[];
    currentNotes: string;
    onUpdate: (labels: string[], notes: string) => void;
}

export const LabelEditor = ({ sessionId, currentLabels, currentNotes, onUpdate }: LabelEditorProps) => {
    const [labels, setLabels] = useState<string[]>(currentLabels);
    const [notes, setNotes] = useState(currentNotes);
    const [newLabel, setNewLabel] = useState('');
    const [saving, setSaving] = useState(false);

    // Predefined label suggestions
    const suggestions = [
        'successful-shot',
        'missed-shot',
        'practice',
        'warmup',
        'test',
        'baseline',
        'calibration',
        'high-speed',
        'slow-motion',
        'left-side',
        'right-side',
        'center'
    ];

    const addLabel = (label: string) => {
        if (label && !labels.includes(label)) {
            const updated = [...labels, label];
            setLabels(updated);
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

    return (
        <div className="space-y-4 p-4 border rounded bg-gray-50">
            <h3 className="font-semibold text-gray-800">Labels & Notes</h3>

            {/* Current Labels */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Labels
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                    {labels.map((label, i) => (
                        <div
                            key={i}
                            className="flex items-center gap-1 px-3 py-1 bg-blue-500 text-white rounded-full text-sm"
                        >
                            <Tag size={14} />
                            {label}
                            <button
                                onClick={() => removeLabel(label)}
                                className="hover:bg-blue-600 rounded-full p-0.5"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    ))}
                    {labels.length === 0 && (
                        <p className="text-sm text-gray-500">No labels added</p>
                    )}
                </div>

                {/* Add Label Input */}
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={newLabel}
                        onChange={(e) => setNewLabel(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                addLabel(newLabel);
                            }
                        }}
                        placeholder="Add a label..."
                        className="flex-1 px-3 py-2 border rounded text-sm"
                    />
                    <button
                        onClick={() => addLabel(newLabel)}
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-1"
                    >
                        <Plus size={16} />
                        Add
                    </button>
                </div>

                {/* Label Suggestions */}
                <div className="mt-2">
                    <p className="text-xs text-gray-600 mb-1">Quick add:</p>
                    <div className="flex flex-wrap gap-1">
                        {suggestions
                            .filter(s => !labels.includes(s))
                            .slice(0, 6)
                            .map((suggestion, i) => (
                                <button
                                    key={i}
                                    onClick={() => addLabel(suggestion)}
                                    className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
                                >
                                    {suggestion}
                                </button>
                            ))}
                    </div>
                </div>
            </div>

            {/* Notes */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Notes
                </label>
                <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add notes about this session..."
                    className="w-full px-3 py-2 border rounded text-sm"
                    rows={3}
                />
            </div>

            {/* Save Button */}
            <button
                onClick={handleSave}
                disabled={saving}
                className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300"
            >
                {saving ? 'Saving...' : 'Save Changes'}
            </button>
        </div>
    );
};