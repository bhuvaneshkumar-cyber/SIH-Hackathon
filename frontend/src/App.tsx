/**
 * App — Root component.
 *
 * Phase 6 additions:
 *   - Auth gate: renders LoginScreen if no valid JWT in localStorage
 *   - DDI check: triggered after entity extraction; shown as DDIBadge below NotePanel
 *   - TopBar now shows doctor name + logout button when authenticated
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { useBackend } from "./hooks/useBackend";
import type { Entities, DDIInteraction } from "./hooks/useBackend";
import { TopBar } from "./components/TopBar";
import { AudioControls } from "./components/AudioControls";
import {
  TranscriptPanel,
  type TranscriptEntry,
} from "./components/TranscriptPanel";
import { NotePanel, type NoteType } from "./components/NotePanel";
import { LoginScreen } from "./components/LoginScreen";
import { DDIBadge } from "./components/DDIBadge";
import { SEED_TRANSCRIPT, SEED_TRANSCRIPT_TEXT } from "./data/seedTranscript";
import { buildFhirBundle, downloadJson } from "./utils/fhirExport";

type NoteStatus = "idle" | "loading" | "ready" | "error";
type PipelinePhase = "idle" | "running" | "done" | "error";

// A 10 g dummy audio blob — just enough to satisfy /upload-audio's File param.
function makeDummyFile(): File {
  return new File([new Uint8Array(10)], "seed.wav", { type: "audio/wav" });
}

function App() {
  // --- Backend connection ---
  const {
    backendStatus,
    token,
    currentUser,
    login,
    logout,
    uploadAudio,
    attachTranscript,
    extractEntities,
    generateNote,
    checkInteractions,
    connectWs,
    disconnectWs,
  } = useBackend();

  // --- Recording state ---
  const [isRecording, setIsRecording] = useState(false);

  // --- Transcript state ---
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);

  // --- File info ---
  const [activeFileName, setActiveFileName] = useState<string | null>(null);

  // --- Note tab ---
  const [activeNoteTab, setActiveNoteTab] = useState<NoteType>("consultation");

  // --- Phase 4 pipeline state ---
  const [encounterId, setEncounterId] = useState<string | null>(null);
  const [entities, setEntities] = useState<Entities | null>(null);
  const [notes, setNotes] = useState<Partial<Record<NoteType, Record<string, unknown>>>>({});
  const [noteStatus, setNoteStatus] = useState<Record<NoteType, NoteStatus>>({
    consultation: "idle",
    discharge: "idle",
    prescription: "idle",
  });
  const [noteError, setNoteError] = useState<Partial<Record<NoteType, string>>>({});
  const [pipelinePhase, setPipelinePhase] = useState<PipelinePhase>("idle");

  // Phase 6: DDI state
  const [ddiInteractions, setDdiInteractions] = useState<DDIInteraction[] | null>(null);
  const [ddiLoading, setDdiLoading] = useState(false);
  const [ddiVisible, setDdiVisible] = useState(false);

  // Physician's per-field overrides (frontend-only; merged on render and export)
  const editsRef = useRef<Record<NoteType, Record<string, unknown>>>({
    consultation: {},
    discharge: {},
    prescription: {},
  });

  // Guard against StrictMode double-invoke
  const pipelineStarted = useRef(false);

  // --- Mount: run pipeline once (only when authenticated) ---
  useEffect(() => {
    if (!token) return;                    // wait for auth
    if (pipelineStarted.current) return;
    pipelineStarted.current = true;

    const runPipeline = async () => {
      setPipelinePhase("running");
      try {
        // 1. Bootstrap encounter via dummy upload
        const uploadResult = await uploadAudio(makeDummyFile());
        const eid = uploadResult.encounter_id;
        setEncounterId(eid);

        // 2. Seed transcript into TranscriptPanel and push to backend
        setTranscript(SEED_TRANSCRIPT);
        await attachTranscript(eid, SEED_TRANSCRIPT_TEXT);

        // 3. Extract entities
        const entitiesResult = await extractEntities(SEED_TRANSCRIPT_TEXT, eid);
        setEntities(entitiesResult.entities);

        // 4. Phase 6: DDI check on extracted medication names
        const medNames = entitiesResult.entities.medications.map((m) => m.name);
        if (medNames.length >= 2) {
          setDdiLoading(true);
          setDdiVisible(true);
          try {
            const ddiResult = await checkInteractions(medNames);
            setDdiInteractions(ddiResult.interactions);
          } finally {
            setDdiLoading(false);
          }
        }

        setPipelinePhase("done");
      } catch (err) {
        console.error("Pipeline bootstrap failed:", err);
        setPipelinePhase("error");
      }
    };

    runPipeline();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // --- Auto-generate note when a tab becomes active and is still idle ---
  useEffect(() => {
    if (!encounterId || pipelinePhase !== "done") return;
    if (noteStatus[activeNoteTab] !== "idle") return;

    const tab = activeNoteTab;

    const generateNoteForTab = async (noteType: NoteType) => {
      setNoteStatus((prev) => ({ ...prev, [noteType]: "loading" }));
      try {
        const res = await generateNote(encounterId, noteType);
        setNotes((prev) => ({ ...prev, [noteType]: res.note }));
        setNoteStatus((prev) => ({ ...prev, [noteType]: "ready" }));
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setNoteError((prev) => ({ ...prev, [noteType]: msg }));
        setNoteStatus((prev) => ({ ...prev, [noteType]: "error" }));
      }
    };

    generateNoteForTab(tab);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeNoteTab, encounterId, pipelinePhase]);

  // --- Handle physician field edits ---
  const handleFieldEdit = useCallback(
    (noteType: NoteType, field: string, value: unknown) => {
      editsRef.current[noteType][field] = value;
    },
    []
  );

  // --- Export FHIR Bundle ---
  const handleExportFhir = useCallback(() => {
    const mergedNote = {
      ...(notes[activeNoteTab] ?? {}),
      ...editsRef.current[activeNoteTab],
    };
    const shortId = (encounterId ?? "no-encounter").replace(/-/g, "").slice(0, 8);
    const bundle = buildFhirBundle({
      tab: activeNoteTab,
      mergedNote,
      entities,
      encounterId,
    });
    downloadJson(`clindoc-${activeNoteTab}-${shortId}.fhir.json`, bundle);
  }, [activeNoteTab, notes, entities, encounterId]);

  // --- Handle record toggle ---
  const handleToggleRecord = useCallback(() => {
    if (isRecording) {
      disconnectWs();
      setIsRecording(false);
    } else {
      const ws = connectWs((chunk) => {
        setTranscript((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            speaker:
              chunk.speaker === "unknown"
                ? "doctor"
                : (chunk.speaker as "doctor" | "patient"),
            text: chunk.text,
          },
        ]);
      });
      ws.onopen = () => {
        ws.send("WebSocket connection test — echo from frontend.");
      };
      setIsRecording(true);
      setActiveFileName(null);
    }
  }, [isRecording, connectWs, disconnectWs]);

  // --- Handle file upload ---
  const handleFileSelected = useCallback(
    async (file: File) => {
      setActiveFileName(file.name);
      try {
        const result = await uploadAudio(file);
        setTranscript((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            speaker: "doctor",
            text: `[System] Audio file "${result.filename}" uploaded. Encounter: ${result.encounter_id}. ${result.message}`,
          },
        ]);
      } catch (err) {
        setTranscript((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            speaker: "doctor",
            text: `[Error] Failed to upload audio: ${err instanceof Error ? err.message : String(err)}`,
          },
        ]);
      }
    },
    [uploadAudio]
  );

  // Merged note for the active tab (LLM output + physician edits)
  const mergedActiveNote = {
    ...(notes[activeNoteTab] ?? {}),
    ...editsRef.current[activeNoteTab],
  };

  // --- Auth gate ---
  if (!token) {
    return (
      <LoginScreen
        onLogin={async (email, password) => {
          await login(email, password);
        }}
      />
    );
  }

  return (
    <div className="app-layout">
      <TopBar
        backendStatus={backendStatus}
        isRecording={isRecording}
        currentUser={currentUser}
        onLogout={logout}
      />

      <main className="main-content">
        <AudioControls
          isRecording={isRecording}
          onToggleRecord={handleToggleRecord}
          onFileSelected={handleFileSelected}
          activeFileName={activeFileName}
          backendConnected={backendStatus === "connected"}
        />

        <TranscriptPanel entries={transcript} />

        <NotePanel
          activeTab={activeNoteTab}
          onTabChange={setActiveNoteTab}
          noteStatus={noteStatus}
          noteError={noteError}
          mergedNote={mergedActiveNote}
          onFieldEdit={handleFieldEdit}
          onExportFhir={handleExportFhir}
          canExport={noteStatus[activeNoteTab] === "ready"}
          pipelinePhase={pipelinePhase}
          allNoteStatus={noteStatus}
        />

        {/* Phase 6: DDI alert panel */}
        {ddiVisible && (
          <div style={{ gridColumn: "1 / -1" }}>
            <DDIBadge
              interactions={ddiInteractions ?? []}
              loading={ddiLoading}
              onDismiss={() => setDdiVisible(false)}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
