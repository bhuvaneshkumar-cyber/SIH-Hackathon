# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClinDoc AI — Ambient Clinical Documentation Assistant (SIH 2026, PS #43).
Multilingual doctor-patient audio → diarized transcript → medical entities → structured clinical note.

Two subprojects, separate dependency trees:

| Subproject | Path     | Stack                                |
|------------|----------|--------------------------------------|
| Backend    | `backend/`  | FastAPI + spaCy (med7) + Ollama      |
| Frontend   | `frontend/` | React 19 + TypeScript + Vite + Oxlint|

## Commands

### Backend (`backend/`)

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# med7 wheel is checked in — install locally instead of from PyPI:
pip install en_core_med7_lg-1.1.0-py3-none-any.whl --no-deps

# Run dev server (Phase 0 / 2 / 3 endpoints)
uvicorn main:app --reload --port 8000

# Tests
python -m pytest test_entity_extraction.py -v
python -m pytest test_llm_structuring.py -v
python -m pytest -v                            # both files

# Ollama (required for /generate-note in Phase 3)
ollama pull qwen3:30b                          # matches MODEL_NAME in llm_structuring.py
ollama serve                                   # default :11434
```

### Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev        # vite dev server, http://localhost:5173
npm run build      # tsc -b && vite build (type-checks first)
npm run lint       # oxlint
npm run preview    # serve production build
```

The Vite dev server (`:5173`) is the only origin allowed by the backend CORS config — don't change one without the other.

## Architecture

### Backend pipeline (per encounter)

```
upload-audio ──► encounter{} in-memory store ──► (Phase 1: ASR fills transcript)
                                                ──► /extract-entities  (entity_extraction.py)
                                                ──► /generate-note     (llm_structuring.py, calls Ollama)
```

- `main.py` — FastAPI app. Endpoints: `GET /health`, `POST /upload-audio`, `POST /extract-entities`, `GET /encounter/{id}`, `POST /generate-note`, `WS /ws/transcribe`. Encounters live in a module-level `dict` (no DB yet).
- `entity_extraction.py` — Layer 2. Dual extractor:
  - Medications: `med7` spaCy model if installed, else regex fallback (handles list-style sentences like "Asp 75mg OD and Met 25mg BD"). Lazy-loaded via the `_models` singleton. Falls back gracefully — if med7 wheel is missing, regex still works.
  - Symptoms/diagnoses: spaCy `en_core_web_sm` + curated `PhraseMatcher` lists (`SYMPTOM_TERMS`, `DIAGNOSIS_TERMS`).
  - `normalize_to_english()` is a pass-through stub — wire to Ollama later.
- `llm_structuring.py` — Layer 3. Calls Ollama at `localhost:11434` with `MODEL_NAME = "qwen3:30b"`. Returns one of three Pydantic-validated schemas: `consultation` (SOAP), `discharge`, or `prescription`. Strips ` ```json ` fences, parses, retries once on failure.

### Frontend layout

```
main.tsx → App.tsx
            ├─ TopBar             (brand + backend status pill)
            ├─ AudioControls      (record button + drag/drop upload)
            ├─ TranscriptPanel    (left column, speaker-labeled lines)
            └─ NotePanel          (right column, tabbed SOAP/Discharge/Prescription)
```

- State is local to `App.tsx` (transcript entries, active note tab, recording flag, uploaded filename). No global store.
- `hooks/useBackend.ts` is the only network layer:
  - Polls `GET /health` every 5 s → `backendStatus` (connected/disconnected/checking).
  - `uploadAudio(file)` → POST `/upload-audio` (multipart).
  - `connectWs(onMessage)` returns the raw `WebSocket` (caller wires `onopen`/`onmessage`); `disconnectWs()` closes it.
- On record-start, frontend opens `ws://localhost:8000/ws/transcribe` and pushes any incoming `transcript_chunk` objects into the transcript array. Today the backend just echoes input — `App.tsx` already maps `speaker` to doctor/patient/unknown, so when real ASR lands nothing changes here.
- Styling is plain CSS (`src/index.css`) using BEM-ish class names (`panel`, `audio-controls__buttons`, `status-badge--connected`). No CSS framework.

### Conventions

- Python: type hints with `from __future__ import annotations`, dataclasses for entity containers, module-level logger.
- Frontend: `verbatimModuleSyntax` and `allowImportraryExtensions` on — use `import type { Foo }` for type-only imports. Hooks live under `src/hooks/`, components under `src/components/`; component files export the component and any small types it owns.
- Oxlint rules in `.oxlintrc.json`: `react/rules-of-hooks` is an error; `react/only-export-components` warns (constants allowed).
- Tests are co-located in `backend/test_*.py`. `test_llm_structuring.py` mocks `requests.post` — the Ollama call is unit-tested without a live daemon.

## Phase status

| Phase | Scope                                | State                           |
|-------|--------------------------------------|---------------------------------|
| 0     | Scaffolding, health, upload, WS stub | Done                            |
| 1     | ASR + diarization                    | Not wired (WS still echoes)     |
| 2     | NLP entity extraction                | Done (`entity_extraction.py`)   |
| 3     | LLM structuring → EHR note           | Done (`llm_structuring.py`, needs Ollama running) |

When working in phases that aren't done yet, the placeholder stubs are the right places to extend — don't fork new files.
