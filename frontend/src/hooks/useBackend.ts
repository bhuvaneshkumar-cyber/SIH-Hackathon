/**
 * useBackend — hook for talking to the FastAPI backend.
 *
 * Provides:
 *  - backendStatus: "connected" | "disconnected" (based on /health poll)
 *  - token / user: JWT auth state (Phase 6)
 *  - login(email, password): POST to /auth/login
 *  - logout(): clear token
 *  - uploadAudio(file): POST file to /upload-audio
 *  - attachTranscript(id, transcript): POST to /encounter/{id}/transcript (Phase 4)
 *  - extractEntities(transcript, encounterId?): POST to /extract-entities (Phase 4)
 *  - generateNote(encounterId, noteType): POST to /generate-note (Phase 4)
 *  - checkInteractions(medications): POST to /check-interactions (Phase 6)
 *  - wsRef: React ref to the WebSocket (connect/disconnect managed by caller)
 */

import { useState, useEffect, useRef, useCallback } from "react";
import type { NoteType } from "../components/NotePanel";

const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";
const TOKEN_KEY = "clindoc_token";

export type BackendStatus = "connected" | "disconnected" | "checking";

export interface UploadResult {
  encounter_id: string;
  filename: string;
  status: string;
  message: string;
}

// ponytail: mirrored from the backend Medication dataclass exactly.
export interface MedicationRow {
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  duration: string;
}

export interface Entities {
  symptoms: string[];
  diagnoses: string[];
  medications: MedicationRow[];
}

export interface EntitiesResult {
  encounter_id: string | null;
  entities: Entities;
}

export interface AttachTranscriptResult {
  encounter_id: string;
  status: string;
  transcript_length: number;
}

export interface NoteResponse {
  encounter_id: string;
  note_type: NoteType;
  // The note payload is a Pydantic-validated record whose shape depends on
  // note_type. The looseness mirrors the backend: `discharge_medications` and
  // `prescription.medications` are free-form `Dict[str, str]`, so we widen to
  // `unknown` here and let NotePanel narrow per tab.
  note: Record<string, unknown>;
}

export interface TranscriptChunk {
  type: string;
  encounter_id: string;
  text: string;
  speaker: string;
  is_final: boolean;
  message: string;
}

// Phase 6 auth
export interface AuthUser {
  email: string;
  full_name: string;
  role: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

// Phase 6 DDI
export interface DDIInteraction {
  drug_a: string;
  drug_b: string;
  severity: "Major" | "Moderate" | "Minor";
  description: string;
  disclaimer: string;
}

export interface DDIResult {
  checked_drugs: string[];
  interaction_count: number;
  interactions: DDIInteraction[];
}

export function useBackend() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const wsRef = useRef<WebSocket | null>(null);

  // --- Auth state ---
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_KEY)
  );
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  // --- Health check poll (every 5 s) ---
  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (!cancelled) setBackendStatus(res.ok ? "connected" : "disconnected");
      } catch {
        if (!cancelled) setBackendStatus("disconnected");
      }
    };

    check();
    const interval = setInterval(check, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // --- Shared error helper that surfaces the backend `detail` message ---
  const postJson = useCallback(async <T,>(path: string, body: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) headers["Authorization"] = `Bearer ${storedToken}`;
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = (await res.json()) as { detail?: string };
        if (err?.detail) detail = err.detail;
      } catch {
        /* ignore JSON parse failure on error body */
      }
      throw new Error(detail);
    }
    return res.json() as Promise<T>;
  }, []);

  // --- Upload audio file ---
  const uploadAudio = useCallback(async (file: File): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/upload-audio`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  }, []);

  // --- Phase 4 helpers ---
  const attachTranscript = useCallback(
    (encounterId: string, transcript: string) =>
      postJson<AttachTranscriptResult>(`/encounter/${encounterId}/transcript`, { transcript }),
    [postJson],
  );

  const extractEntities = useCallback(
    (transcript: string, encounterId?: string) =>
      postJson<EntitiesResult>("/extract-entities", {
        transcript,
        encounter_id: encounterId ?? null,
      }),
    [postJson],
  );

  const generateNote = useCallback(
    (encounterId: string, noteType: NoteType) =>
      postJson<NoteResponse>("/generate-note", {
        encounter_id: encounterId,
        note_type: noteType,
      }),
    [postJson],
  );

  // --- Phase 6: Auth helpers ---
  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    // /auth/login uses OAuth2 form encoding, not JSON
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(err.detail ?? `Login failed: HTTP ${res.status}`);
    }
    const result = (await res.json()) as LoginResult;
    localStorage.setItem(TOKEN_KEY, result.access_token);
    setToken(result.access_token);
    setCurrentUser(result.user);
    return result;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setCurrentUser(null);
  }, []);

  // --- Phase 6: DDI check ---
  const checkInteractions = useCallback(
    (medications: string[]) =>
      postJson<DDIResult>("/check-interactions", { medications }),
    [postJson],
  );

  // --- WebSocket connect/disconnect ---
  const connectWs = useCallback(
    (onMessage: (data: TranscriptChunk) => void) => {
      if (wsRef.current) wsRef.current.close();

      const ws = new WebSocket(`${WS_BASE}/ws/transcribe`);
      ws.onmessage = (ev) => {
        try {
          const parsed = JSON.parse(ev.data) as TranscriptChunk;
          onMessage(parsed);
        } catch {
          /* ignore non-JSON messages */
        }
      };
      wsRef.current = ws;
      return ws;
    },
    []
  );

  const disconnectWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return {
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
    wsRef,
  };
}
