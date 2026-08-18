/**
 * TranscriptPanel — Displays the diarized transcript with speaker labels.
 * Phase 0: Shows placeholder/demo lines; will be wired to real ASR in Phase 1.
 */

export interface TranscriptEntry {
  id: string;
  speaker: "doctor" | "patient" | "unknown";
  text: string;
}

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
}

const speakerLabel: Record<string, string> = {
  doctor: "Doctor",
  patient: "Patient",
  unknown: "???",
};

export function TranscriptPanel({ entries }: TranscriptPanelProps) {
  return (
    <section className="panel" id="transcript-panel">
      <div className="panel__header">
        <h2 className="panel__title">
          <span className="panel__title-icon">📝</span>
          Live Transcript
        </h2>
        <div className="panel__actions">
          <button
            className="btn btn--secondary btn--icon"
            title="Clear transcript"
            id="btn-clear-transcript"
            disabled
          >
            🗑
          </button>
        </div>
      </div>

      <div className="panel__body">
        {entries.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state__icon">🎙️</span>
            <h3 className="empty-state__title">No transcript yet</h3>
            <p className="empty-state__description">
              Start recording or upload an audio file to see the diarized
              transcript appear here in real time.
            </p>
          </div>
        ) : (
          entries.map((entry) => (
            <div className="transcript-line animate-fade-in" key={entry.id}>
              <span
                className={`transcript-line__speaker transcript-line__speaker--${entry.speaker}`}
              >
                {speakerLabel[entry.speaker]}
              </span>
              <span className="transcript-line__text">{entry.text}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
