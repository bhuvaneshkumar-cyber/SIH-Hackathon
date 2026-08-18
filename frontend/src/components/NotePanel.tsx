/**
 * NotePanel — Tabbed view for the three note templates:
 *   Consultation (SOAP), Discharge Summary, Prescription.
 *
 * Phase 4: Replaces empty-state stub with per-tab editable field rendering.
 *   - Each scalar field is a contentEditable div (.note-editable)
 *   - Diagnosis lists are comma-joined strings → contentEditable → array roundtrip
 *   - Medication rows rendered as .med-card with per-field editable sub-rows
 *   - Export button wired to onExportFhir
 */

import { useRef } from "react";

export type NoteType = "consultation" | "discharge" | "prescription";

type NoteStatus = "idle" | "loading" | "ready" | "error";
type PipelinePhase = "idle" | "running" | "done" | "error";

interface NotePanelProps {
  activeTab: NoteType;
  onTabChange: (tab: NoteType) => void;
  noteStatus: Record<NoteType, NoteStatus>;
  noteError: Partial<Record<NoteType, string>>;
  mergedNote: Record<string, unknown>;
  onFieldEdit: (noteType: NoteType, field: string, value: unknown) => void;
  onExportFhir: () => void;
  canExport: boolean;
  pipelinePhase: PipelinePhase;
  allNoteStatus: Record<NoteType, NoteStatus>;
}

const tabs: { key: NoteType; label: string; icon: string }[] = [
  { key: "consultation", label: "Consultation", icon: "📋" },
  { key: "discharge", label: "Discharge", icon: "🏥" },
  { key: "prescription", label: "Prescription", icon: "💊" },
];

// --- Editable field component ---
interface EditableFieldProps {
  label: string;
  value: string;
  multiline?: boolean;
  onBlur: (value: string) => void;
  id: string;
}

function EditableField({ label, value, multiline = false, onBlur, id }: EditableFieldProps) {
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div className="note-content__section">
      <span className="note-content__label">{label}</span>
      <div
        ref={ref}
        id={id}
        className={`note-editable${multiline ? " note-content__list-editable" : ""}`}
        contentEditable
        suppressContentEditableWarning
        onBlur={() => onBlur(ref.current?.innerText ?? "")}
        dangerouslySetInnerHTML={{ __html: value }}
      />
    </div>
  );
}

// --- Medication card ---
interface MedCardProps {
  idx: number;
  row: Record<string, unknown>;
  noteType: NoteType;
  onFieldEdit: (noteType: NoteType, field: string, value: unknown) => void;
}

function MedCard({ idx, row, noteType, onFieldEdit }: MedCardProps) {
  const fields: Array<{ key: string; label: string }> = [
    { key: "name", label: "Drug" },
    { key: "dosage", label: "Dose" },
    { key: "frequency", label: "Frequency" },
    { key: "route", label: "Route" },
    { key: "duration", label: "Duration" },
  ];

  return (
    <div className="med-card">
      {fields.map(({ key, label }) => {
        const fieldKey =
          noteType === "discharge" ? `discharge_medications[${idx}].${key}` : `medications[${idx}].${key}`;
        const ref = useRef<HTMLSpanElement>(null);
        return (
          <div className="med-card__row" key={key}>
            <span className="note-content__label">{label}</span>
            <span
              ref={ref}
              id={`med-${idx}-${key}`}
              className="note-editable"
              contentEditable
              suppressContentEditableWarning
              onBlur={() => onFieldEdit(noteType, fieldKey, ref.current?.innerText ?? "")}
              dangerouslySetInnerHTML={{ __html: String(row[key] ?? "") }}
            />
          </div>
        );
      })}
    </div>
  );
}

// --- Render helpers per tab ---
function ConsultationContent({
  note,
  onFieldEdit,
}: {
  note: Record<string, unknown>;
  onFieldEdit: (field: string, value: unknown) => void;
}) {
  const fields: Array<{ key: string; label: string; multiline?: boolean }> = [
    { key: "chief_complaint", label: "Chief Complaint" },
    { key: "history_of_present_illness", label: "History of Present Illness", multiline: true },
    { key: "assessment", label: "Assessment", multiline: true },
    { key: "plan", label: "Plan", multiline: true },
  ];

  return (
    <div className="note-content animate-fade-in">
      {fields.map(({ key, label, multiline }) => (
        <EditableField
          key={key}
          id={`field-consultation-${key}`}
          label={label}
          value={String(note[key] ?? "")}
          multiline={multiline}
          onBlur={(v) => onFieldEdit(key, v)}
        />
      ))}
    </div>
  );
}

function DischargeContent({
  note,
  onFieldEdit,
  noteType,
  onMedFieldEdit,
}: {
  note: Record<string, unknown>;
  onFieldEdit: (field: string, value: unknown) => void;
  noteType: NoteType;
  onMedFieldEdit: (noteType: NoteType, field: string, value: unknown) => void;
}) {
  const arrToStr = (v: unknown) =>
    Array.isArray(v) ? (v as string[]).join(", ") : String(v ?? "");

  const meds = Array.isArray(note.discharge_medications)
    ? (note.discharge_medications as Record<string, unknown>[])
    : [];

  return (
    <div className="note-content animate-fade-in">
      <EditableField
        id="field-discharge-admission_diagnoses"
        label="Admission Diagnoses"
        value={arrToStr(note.admission_diagnoses)}
        multiline
        onBlur={(v) => onFieldEdit("admission_diagnoses", v.split(/,\s*/).map((s) => s.trim()).filter(Boolean))}
      />
      <EditableField
        id="field-discharge-discharge_diagnoses"
        label="Discharge Diagnoses"
        value={arrToStr(note.discharge_diagnoses)}
        multiline
        onBlur={(v) => onFieldEdit("discharge_diagnoses", v.split(/,\s*/).map((s) => s.trim()).filter(Boolean))}
      />
      <EditableField
        id="field-discharge-hospital_course"
        label="Hospital Course"
        value={String(note.hospital_course ?? "")}
        multiline
        onBlur={(v) => onFieldEdit("hospital_course", v)}
      />
      {meds.length > 0 && (
        <div className="note-content__section">
          <span className="note-content__label">Discharge Medications</span>
          {meds.map((row, idx) => (
            <MedCard
              key={idx}
              idx={idx}
              row={row}
              noteType={noteType}
              onFieldEdit={onMedFieldEdit}
            />
          ))}
        </div>
      )}
      <EditableField
        id="field-discharge-follow_up"
        label="Follow Up"
        value={String(note.follow_up ?? "")}
        multiline
        onBlur={(v) => onFieldEdit("follow_up", v)}
      />
    </div>
  );
}

function PrescriptionContent({
  note,
  onFieldEdit,
  noteType,
  onMedFieldEdit,
}: {
  note: Record<string, unknown>;
  onFieldEdit: (field: string, value: unknown) => void;
  noteType: NoteType;
  onMedFieldEdit: (noteType: NoteType, field: string, value: unknown) => void;
}) {
  const arrToStr = (v: unknown) =>
    Array.isArray(v) ? (v as string[]).join(", ") : String(v ?? "");

  const meds = Array.isArray(note.medications)
    ? (note.medications as Record<string, unknown>[])
    : [];

  return (
    <div className="note-content animate-fade-in">
      <EditableField
        id="field-prescription-diagnoses"
        label="Diagnoses"
        value={arrToStr(note.diagnoses)}
        multiline
        onBlur={(v) => onFieldEdit("diagnoses", v.split(/,\s*/).map((s) => s.trim()).filter(Boolean))}
      />
      {meds.length > 0 && (
        <div className="note-content__section">
          <span className="note-content__label">Medications</span>
          {meds.map((row, idx) => (
            <MedCard
              key={idx}
              idx={idx}
              row={row}
              noteType={noteType}
              onFieldEdit={onMedFieldEdit}
            />
          ))}
        </div>
      )}
      <EditableField
        id="field-prescription-advice"
        label="Advice"
        value={String(note.advice ?? "")}
        multiline
        onBlur={(v) => onFieldEdit("advice", v)}
      />
    </div>
  );
}

export function NotePanel({
  activeTab,
  onTabChange,
  noteStatus,
  noteError,
  mergedNote,
  onFieldEdit,
  onExportFhir,
  canExport,
  pipelinePhase,
}: NotePanelProps) {
  const status = noteStatus[activeTab];

  const handleFieldEdit = (field: string, value: unknown) => {
    onFieldEdit(activeTab, field, value);
  };

  const renderContent = () => {
    // Pipeline still bootstrapping — show a global loading state
    if (pipelinePhase === "running") {
      return (
        <div className="empty-state">
          <span className="empty-state__icon">⏳</span>
          <h3 className="empty-state__title">Initializing…</h3>
          <p className="empty-state__description">
            Seeding transcript and extracting entities. Notes will generate automatically.
          </p>
        </div>
      );
    }

    if (pipelinePhase === "error") {
      return (
        <div className="empty-state">
          <span className="empty-state__icon">⚠️</span>
          <h3 className="empty-state__title">Pipeline Error</h3>
          <p className="empty-state__description">
            Could not connect to the backend. Make sure the FastAPI server is running on port 8000.
          </p>
        </div>
      );
    }

    if (status === "idle" || status === "loading") {
      return (
        <div className="empty-state">
          <span className="empty-state__icon waveform">
            {tabs.find((t) => t.key === activeTab)?.icon}
          </span>
          <h3 className="empty-state__title">Generating note…</h3>
          <p className="empty-state__description">
            Sending transcript to Ollama ({activeTab} template). This may take a moment.
          </p>
        </div>
      );
    }

    if (status === "error") {
      return (
        <div className="empty-state">
          <span className="empty-state__icon">❌</span>
          <h3 className="empty-state__title">Generation failed</h3>
          <p className="empty-state__description">
            {noteError[activeTab] ?? "Unknown error. Check that Ollama is running with qwen3:30b pulled."}
          </p>
        </div>
      );
    }

    // status === "ready"
    if (activeTab === "consultation") {
      return (
        <ConsultationContent
          note={mergedNote}
          onFieldEdit={handleFieldEdit}
        />
      );
    }
    if (activeTab === "discharge") {
      return (
        <DischargeContent
          note={mergedNote}
          onFieldEdit={handleFieldEdit}
          noteType={activeTab}
          onMedFieldEdit={onFieldEdit}
        />
      );
    }
    // prescription
    return (
      <PrescriptionContent
        note={mergedNote}
        onFieldEdit={handleFieldEdit}
        noteType={activeTab}
        onMedFieldEdit={onFieldEdit}
      />
    );
  };

  return (
    <section className="panel" id="note-panel">
      <div className="panel__header">
        <h2 className="panel__title">
          <span className="panel__title-icon">📄</span>
          Generated Note
        </h2>
        <div className="panel__actions">
          <button
            className="btn btn--secondary btn--icon"
            title="Export FHIR Bundle"
            id="btn-export-json"
            onClick={canExport ? onExportFhir : undefined}
            disabled={!canExport}
          >
            ⬇
          </button>
        </div>
      </div>

      {/* Tabs */}
      <nav className="note-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`note-tab ${activeTab === tab.key ? "is-active" : ""}`}
            onClick={() => onTabChange(tab.key)}
            id={`tab-${tab.key}`}
          >
            {tab.icon} {tab.label}
            {noteStatus[tab.key] === "loading" && (
              <span className="tab-spinner"> ⏳</span>
            )}
            {noteStatus[tab.key] === "ready" && (
              <span className="tab-ready"> ✓</span>
            )}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      <div className="panel__body">{renderContent()}</div>
    </section>
  );
}
