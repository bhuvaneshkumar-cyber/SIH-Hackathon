"""
AI Clinical Documentation Assistant — Backend
SIH 2026 (PS #43)

FastAPI application entry point.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from entity_extraction import extract_entities
from llm_structuring import generate_note
from ddi_checker import check_interactions
from auth import authenticate_user, create_login_token, get_current_user

app = FastAPI(
    title="Clinical Documentation Assistant",
    description="AI-powered ambient clinical documentation — SIH 2026",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server on localhost:5173
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory encounter store (no DB for MVP)
# ---------------------------------------------------------------------------
encounters: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    return {
        "status": "ok",
        "service": "clinical-doc-assistant",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate with demo credentials and return a JWT access token.
    Demo:  email=doctor@clindoc.ai  password=demo2026
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_login_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }


@app.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Return current user profile (requires valid JWT)."""
    return {
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
    }


@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Accept an audio file upload.
    Phase 0: just acknowledge receipt and return a new encounter ID.
    Actual ASR processing will be wired in Phase 1.
    """
    encounter_id = str(uuid.uuid4())
    encounters[encounter_id] = {
        "id": encounter_id,
        "filename": file.filename,
        "status": "received",
        "transcript": None,
        "entities": None,
        "note": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "encounter_id": encounter_id,
        "filename": file.filename,
        "status": "received",
        "message": "Audio received. ASR processing not yet implemented.",
    }

# ---------------------------------------------------------------------------
# Entity extraction endpoint
# ---------------------------------------------------------------------------

class TranscriptRequest(BaseModel):
    transcript: str
    encounter_id: str | None = None


@app.post("/extract-entities")
async def extract_entities_endpoint(
    body: TranscriptRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Run entity extraction on a transcript string.
    Called automatically after ASR produces a full transcript.
    Also callable standalone (e.g., after upload + manual transcript entry).
    """
    entities = extract_entities(body.transcript)
    entity_dict = entities.to_dict()

    # If an encounter_id was provided, attach entities to that encounter
    if body.encounter_id and body.encounter_id in encounters:
        encounters[body.encounter_id]["entities"] = entity_dict
        encounters[body.encounter_id]["status"] = "entities_extracted"

    return {
        "encounter_id": body.encounter_id,
        "entities": entity_dict,
    }


@app.get("/encounter/{encounter_id}")
async def get_encounter(encounter_id: str):
    """Retrieve the current state of an encounter by ID."""
    if encounter_id not in encounters:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounters[encounter_id]

# ---------------------------------------------------------------------------
# Transcript attachment (Phase 4 — unblocks /generate-note when real ASR
# isn't wired; Phase 1 will use the same endpoint once it lands)
# ---------------------------------------------------------------------------

class AttachTranscriptRequest(BaseModel):
    transcript: str


@app.post("/encounter/{encounter_id}/transcript")
async def attach_transcript(encounter_id: str, body: AttachTranscriptRequest):
    """
    Attach a finalized transcript string to an existing encounter.

    Phase 0/1 status: /upload-audio only stores the filename — ASR isn't wired.
    Phase 1 will populate the transcript here directly.
    For Phase 4 demos, the frontend seeds a sample transcript through this
    endpoint so /generate-note has both transcript and entities to work with.
    """
    from fastapi import HTTPException
    if encounter_id not in encounters:
        raise HTTPException(status_code=404, detail="Encounter not found")
    encounters[encounter_id]["transcript"] = body.transcript
    encounters[encounter_id]["status"] = "transcript_attached"
    return {
        "encounter_id": encounter_id,
        "status": "transcript_attached",
        "transcript_length": len(body.transcript),
    }


# ---------------------------------------------------------------------------
# Note generation endpoint (LLM Structuring)
# ---------------------------------------------------------------------------

class NoteRequest(BaseModel):
    encounter_id: str
    note_type: str  # "consultation", "discharge", or "prescription"

@app.post("/generate-note")
async def generate_note_endpoint(
    body: NoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a structured clinical note using the LLM based on extracted entities.
    Requires an encounter with extracted entities.
    """
    if body.encounter_id not in encounters:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Encounter not found")

    encounter = encounters[body.encounter_id]

    if not encounter.get("transcript"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Encounter has no transcript. Cannot generate note.")

    if not encounter.get("entities"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Encounter has no extracted entities. Run entity extraction first.")

    try:
        note_json = generate_note(body.note_type, encounter["transcript"], encounter["entities"])
        encounter["note"] = note_json
        encounter["status"] = "note_generated"
        return {
            "encounter_id": body.encounter_id,
            "note_type": body.note_type,
            "note": note_json
        }
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Drug-Drug Interaction check  (Phase 6)
# ---------------------------------------------------------------------------

class DDIRequest(BaseModel):
    medications: list[str]  # list of drug name strings


@app.post("/check-interactions")
async def check_drug_interactions(
    body: DDIRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Check pairwise drug-drug interactions for a list of medication names.

    Returns a list of interaction records sorted by severity (Major first).
    Each record carries a disclaimer that this is a PROTOTYPE SAFETY LAYER
    and NOT CLINICALLY VALIDATED.
    """
    interactions = check_interactions(body.medications)
    return {
        "checked_drugs": body.medications,
        "interaction_count": len(interactions),
        "interactions": interactions,
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming / transcript updates.
    Phase 0: echo back any text message received, wrapped in a status envelope.
    Phase 1 will replace this with actual ASR streaming logic.
    """
    await websocket.accept()
    encounter_id = str(uuid.uuid4())
    try:
        while True:
            data = await websocket.receive_text()
            # Phase 0: echo back as a transcript-chunk stub
            await websocket.send_json({
                "type": "transcript_chunk",
                "encounter_id": encounter_id,
                "text": data,
                "speaker": "unknown",
                "is_final": False,
                "message": "Echo stub — ASR not yet connected.",
            })
    except WebSocketDisconnect:
        # Client disconnected — clean up
        pass
