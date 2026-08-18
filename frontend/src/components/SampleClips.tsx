/**
 * SampleClips — Demo audio clip selector for Phase 5.
 *
 * Fetches one of the pre-recorded clinical clips from /samples/,
 * constructs a File object, and fires onFileSelected — identical
 * to a real drag-and-drop upload from the user's perspective.
 */

interface Clip {
  id: string;
  label: string;
  file: string;
  description: string;
  noteType: string;
}

const CLIPS: Clip[] = [
  {
    id: "en-consultation",
    label: "🩺 Consultation (EN)",
    file: "/samples/clip_en_consultation.mp3",
    description: "Fever + hypertension — outpatient visit",
    noteType: "consultation",
  },
  {
    id: "en-discharge",
    label: "🏥 Discharge (EN)",
    file: "/samples/clip_en_discharge.mp3",
    description: "Post-MI discharge — 4 medications",
    noteType: "discharge",
  },
  {
    id: "en-prescription",
    label: "💊 Prescription (EN)",
    file: "/samples/clip_en_prescription.mp3",
    description: "Acid reflux — prescription-only encounter",
    noteType: "prescription",
  },
  {
    id: "ta-consultation",
    label: "🩺 Consultation (TA)",
    file: "/samples/clip_ta_consultation.mp3",
    description: "Tamil — fever + hypertension (en-IN-PallaviNeural)",
    noteType: "consultation",
  },
];

interface SampleClipsProps {
  onFileSelected: (file: File) => void;
  disabled: boolean;
}

export function SampleClips({ onFileSelected, disabled }: SampleClipsProps) {
  const handleSelect = async (clip: Clip) => {
    if (disabled) return;
    try {
      const res = await fetch(clip.file);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], `${clip.id}.mp3`, { type: "audio/mpeg" });
      onFileSelected(file);
    } catch (err) {
      console.error("Failed to load sample clip:", err);
    }
  };

  return (
    <div className="sample-clips">
      <span className="sample-clips__label">Demo clips</span>
      <div className="sample-clips__grid">
        {CLIPS.map((clip) => (
          <button
            key={clip.id}
            className="sample-clip-btn"
            onClick={() => handleSelect(clip)}
            disabled={disabled}
            title={clip.description}
            id={`sample-clip-${clip.id}`}
          >
            <span className="sample-clip-btn__label">{clip.label}</span>
            <span className="sample-clip-btn__desc">{clip.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
