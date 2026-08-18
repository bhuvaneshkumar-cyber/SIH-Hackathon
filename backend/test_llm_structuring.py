import pytest
import requests
import json
from unittest.mock import patch, MagicMock
from llm_structuring import generate_note

# Dummy data
TRANSCRIPT = "Patient comes in with a headache and fever. Diagnosed with viral fever. Prescribed Paracetamol 500mg twice a day for 3 days."
ENTITIES = {
    "symptoms": ["headache", "fever"],
    "diagnoses": ["viral fever"],
    "medications": [
        {"name": "Paracetamol", "dosage": "500mg", "frequency": "twice a day", "duration": "for 3 days", "route": ""}
    ]
}

@patch('llm_structuring.requests.post')
def test_generate_note_success(mock_post):
    # Mock successful Ollama response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": json.dumps({
            "chief_complaint": "headache and fever",
            "history_of_present_illness": "Patient has a headache and fever.",
            "assessment": "viral fever",
            "plan": "Paracetamol 500mg twice a day for 3 days."
        })
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    result = generate_note("consultation", TRANSCRIPT, ENTITIES)
    
    assert result["chief_complaint"] == "headache and fever"
    assert result["assessment"] == "viral fever"
    assert mock_post.call_count == 1

@patch('llm_structuring.requests.post')
def test_generate_note_retry_on_bad_json(mock_post):
    # Mock first response bad JSON, second response good JSON
    bad_response = MagicMock()
    bad_response.json.return_value = {"response": "This is not JSON"}
    bad_response.raise_for_status = MagicMock()

    good_response = MagicMock()
    good_response.json.return_value = {
        "response": json.dumps({
            "diagnoses": ["viral fever"],
            "medications": [{"name": "Paracetamol", "dosage": "500mg"}],
            "advice": "Rest"
        })
    }
    good_response.raise_for_status = MagicMock()

    mock_post.side_effect = [bad_response, good_response]

    result = generate_note("prescription", TRANSCRIPT, ENTITIES)
    
    assert result["diagnoses"] == ["viral fever"]
    assert mock_post.call_count == 2 # Verify retry happened

@patch('llm_structuring.requests.post')
def test_generate_note_fails_after_retries(mock_post):
    # Mock bad JSON consistently
    bad_response = MagicMock()
    bad_response.json.return_value = {"response": "Still not JSON"}
    bad_response.raise_for_status = MagicMock()

    mock_post.side_effect = [bad_response, bad_response]

    with pytest.raises(RuntimeError, match="Failed to parse LLM output"):
        generate_note("discharge", TRANSCRIPT, ENTITIES)
    
    assert mock_post.call_count == 2
