import json
import requests
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# Ollama Endpoint Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:30b"

class ConsultationNote(BaseModel):
    chief_complaint: str = Field(description="Primary reason for the visit", default="")
    history_of_present_illness: str = Field(description="Details of the current problem", default="")
    assessment: str = Field(description="Medical assessment and diagnoses", default="")
    plan: str = Field(description="Treatment plan, medications, and next steps", default="")

class DischargeSummary(BaseModel):
    admission_diagnoses: List[str] = Field(description="Diagnoses at the time of admission", default_factory=list)
    discharge_diagnoses: List[str] = Field(description="Diagnoses at the time of discharge", default_factory=list)
    hospital_course: str = Field(description="Summary of the patient's stay and treatments", default="")
    discharge_medications: List[Dict[str, str]] = Field(description="List of medications on discharge", default_factory=list)
    follow_up: str = Field(description="Follow up instructions", default="")

class Prescription(BaseModel):
    diagnoses: List[str] = Field(description="Patient's diagnoses", default_factory=list)
    medications: List[Dict[str, str]] = Field(description="Prescribed medications with dosage, frequency, route, duration", default_factory=list)
    advice: str = Field(description="General advice or instructions for the patient", default="")

NOTE_SCHEMAS = {
    "consultation": ConsultationNote,
    "discharge": DischargeSummary,
    "prescription": Prescription,
}

SYSTEM_PROMPT = """You are a highly capable AI medical assistant. 
Your task is to generate a structured clinical note based on the provided transcript and extracted entities.
You must strictly output ONLY valid JSON matching the exact schema requested. 
Do not include markdown blocks like ```json or any other conversational text. Just the raw JSON object.
Use ONLY the given facts. Do not fabricate or hallucinate information. If a field cannot be filled using the provided information, leave it empty (or an empty list if it's a list).
"""

def generate_note(note_type: str, transcript: str, entities: dict) -> dict:
    if note_type not in NOTE_SCHEMAS:
        raise ValueError(f"Invalid note_type. Must be one of {list(NOTE_SCHEMAS.keys())}")
    
    schema_model = NOTE_SCHEMAS[note_type]
    schema_json = schema_model.model_json_schema()

    prompt = f"""
Transcript:
{transcript}

Extracted Entities:
{json.dumps(entities, indent=2)}

Please generate a {note_type} note.
Expected JSON Schema:
{json.dumps(schema_json, indent=2)}
"""

    payload = {
        "model": MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "format": "json" # Force JSON output if supported by model
    }

    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            # The API returns 'response' field with the generated text
            generated_text = result.get("response", "").strip()
            
            # Ollama might wrap in ```json ... ``` despite instructions
            if generated_text.startswith("```json"):
                generated_text = generated_text[7:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
            
            generated_text = generated_text.strip()
            
            parsed_json = json.loads(generated_text)
            
            # Validate with Pydantic
            validated_data = schema_model(**parsed_json)
            return validated_data.model_dump()
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise RuntimeError(f"Ollama API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            if attempt == max_retries:
                raise RuntimeError(f"Failed to parse LLM output as JSON: {str(e)}\nOutput was: {generated_text}")
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"Failed to validate LLM output against schema: {str(e)}\nOutput was: {generated_text}")
            
    raise RuntimeError("Unexpected failure during LLM generation.")
