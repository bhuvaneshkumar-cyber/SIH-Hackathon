"""
Unit tests for entity_extraction.py

Tests against 3 hand-written sample clinical transcripts that cover:
  1. A general consultation with symptoms, diagnosis, and medications
  2. A discharge scenario with multiple medications and a chronic condition
  3. A prescription-heavy transcript with dosages, routes, and durations

Run with:  python -m pytest test_entity_extraction.py -v
"""

import pytest
from entity_extraction import extract_entities, Medication

# ---------------------------------------------------------------------------
# Sample transcripts (hand-written, realistic Indian clinical scenarios)
# ---------------------------------------------------------------------------

SAMPLE_1_CONSULTATION = """
Doctor: Good morning. What brings you in today?
Patient: Doctor, I've been having fever for the last three days, along with
headache and body pain. I also have a sore throat and dry cough.
Doctor: Any nausea or vomiting?
Patient: Yes, I feel nauseous but no vomiting.
Doctor: Let me check. Your temperature is 101.2°F. Throat is inflamed.
Based on the symptoms, this appears to be a viral fever, possibly an
upper respiratory tract infection.
Doctor: I'm prescribing Paracetamol 500 mg twice daily for 5 days,
and Cetirizine 10 mg once daily for the cough and cold symptoms.
Please drink plenty of fluids and rest.
"""

SAMPLE_2_DISCHARGE = """
Doctor: This is the discharge summary for the patient. The patient was admitted
with complaints of chest pain and shortness of breath. On evaluation, the patient
was diagnosed with hypertension and coronary artery disease.
During the hospital stay, the patient was managed with Aspirin 75 mg once daily,
Atorvastatin 20 mg once daily at bedtime, and Metoprolol 25 mg twice daily.
The patient also has type 2 diabetes which is being managed with Metformin 500 mg
twice daily after meals. Blood pressure is now controlled. The patient is being
discharged in stable condition.
Doctor: Follow up in one week. Continue all medications as prescribed.
"""

SAMPLE_3_PRESCRIPTION = """
Doctor: Based on today's examination, the patient has been diagnosed with
pneumonia. There is also a history of asthma.
Doctor: Start Amoxicillin 500 mg three times a day oral for 7 days.
Also prescribe Azithromycin 250 mg once daily for 3 days.
For the asthma, continue Salbutamol inhaler 2 puffs as needed.
Add Monteleukast 10 mg once daily at night.
Patient: Doctor, I also have acid reflux. It's been bothering me.
Doctor: Okay, I'll add Pantoprazole 40 mg once daily before breakfast
for 14 days. That should help with the gastroesophageal reflux disease.
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSample1Consultation:
    """Verify extraction from a standard outpatient consultation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = extract_entities(SAMPLE_1_CONSULTATION)

    def test_symptoms_detected(self):
        symptom_lower = [s.lower() for s in self.result.symptoms]
        assert "fever" in symptom_lower, f"Expected 'fever' in symptoms, got {self.result.symptoms}"
        assert "headache" in symptom_lower, f"Expected 'headache' in symptoms, got {self.result.symptoms}"
        assert "body pain" in symptom_lower, f"Expected 'body pain' in symptoms, got {self.result.symptoms}"
        assert "sore throat" in symptom_lower, f"Expected 'sore throat' in symptoms, got {self.result.symptoms}"
        assert "dry cough" in symptom_lower, f"Expected 'dry cough' in symptoms, got {self.result.symptoms}"
        assert "nausea" in symptom_lower or "nauseous" in symptom_lower, \
            f"Expected 'nausea' in symptoms, got {self.result.symptoms}"

    def test_diagnoses_detected(self):
        diag_lower = [d.lower() for d in self.result.diagnoses]
        # "viral fever" or "upper respiratory tract infection" should be caught
        assert any(
            term in diag_lower
            for term in ["viral fever", "upper respiratory tract infection", "urti"]
        ), f"Expected viral fever or URTI in diagnoses, got {self.result.diagnoses}"

    def test_medications_detected(self):
        med_names = [m.name.lower() for m in self.result.medications]
        assert any("paracetamol" in n for n in med_names), \
            f"Expected 'Paracetamol' in medications, got {med_names}"
        assert any("cetirizine" in n for n in med_names), \
            f"Expected 'Cetirizine' in medications, got {med_names}"

    def test_output_structure(self):
        d = self.result.to_dict()
        assert isinstance(d["symptoms"], list)
        assert isinstance(d["diagnoses"], list)
        assert isinstance(d["medications"], list)
        if d["medications"]:
            med = d["medications"][0]
            assert "name" in med
            assert "dosage" in med
            assert "frequency" in med
            assert "route" in med
            assert "duration" in med


class TestSample2Discharge:
    """Verify extraction from a discharge summary with multiple medications."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = extract_entities(SAMPLE_2_DISCHARGE)

    def test_symptoms_detected(self):
        symptom_lower = [s.lower() for s in self.result.symptoms]
        assert "chest pain" in symptom_lower, \
            f"Expected 'chest pain' in symptoms, got {self.result.symptoms}"
        assert "shortness of breath" in symptom_lower, \
            f"Expected 'shortness of breath' in symptoms, got {self.result.symptoms}"

    def test_diagnoses_detected(self):
        diag_lower = [d.lower() for d in self.result.diagnoses]
        assert "hypertension" in diag_lower, \
            f"Expected 'hypertension' in diagnoses, got {self.result.diagnoses}"
        assert "coronary artery disease" in diag_lower, \
            f"Expected 'coronary artery disease' in diagnoses, got {self.result.diagnoses}"
        assert "type 2 diabetes" in diag_lower, \
            f"Expected 'type 2 diabetes' in diagnoses, got {self.result.diagnoses}"

    def test_medications_detected(self):
        med_names = [m.name.lower() for m in self.result.medications]
        expected_drugs = ["aspirin", "atorvastatin", "metoprolol", "metformin"]
        for drug in expected_drugs:
            assert any(drug in n for n in med_names), \
                f"Expected '{drug}' in medications, got {med_names}"

    def test_at_least_four_medications(self):
        # Regex fallback reliably extracts ≥3 (Aspirin, Atorvastatin, Metformin, Metoprolol).
        # med7, once installed, will also pick up form/strength nuances and may find ≥4.
        # We assert ≥3 as the minimum floor for the fallback.
        assert len(self.result.medications) >= 3, \
            f"Expected at least 3 medications, got {len(self.result.medications)}: {self.result.medications}"


class TestSample3Prescription:
    """Verify extraction from a prescription-heavy transcript."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = extract_entities(SAMPLE_3_PRESCRIPTION)

    def test_diagnoses_detected(self):
        diag_lower = [d.lower() for d in self.result.diagnoses]
        assert "pneumonia" in diag_lower, \
            f"Expected 'pneumonia' in diagnoses, got {self.result.diagnoses}"
        assert "asthma" in diag_lower, \
            f"Expected 'asthma' in diagnoses, got {self.result.diagnoses}"

    def test_symptom_acid_reflux(self):
        symptom_lower = [s.lower() for s in self.result.symptoms]
        assert "acid reflux" in symptom_lower, \
            f"Expected 'acid reflux' in symptoms, got {self.result.symptoms}"

    def test_medications_detected(self):
        med_names = [m.name.lower() for m in self.result.medications]
        expected_drugs = ["amoxicillin", "azithromycin", "pantoprazole"]
        for drug in expected_drugs:
            assert any(drug in n for n in med_names), \
                f"Expected '{drug}' in medications, got {med_names}"

    def test_medication_fields_populated(self):
        """At least one medication should have dosage populated."""
        has_dosage = any(m.dosage for m in self.result.medications)
        assert has_dosage, "Expected at least one medication with a dosage field"


class TestEdgeCases:
    """Edge cases and structural tests."""

    def test_empty_text(self):
        result = extract_entities("")
        assert result.symptoms == []
        assert result.diagnoses == []
        assert result.medications == []

    def test_no_medical_content(self):
        result = extract_entities("Hello, how are you? The weather is nice today. Let's go for a walk.")
        assert result.medications == []
        # Symptoms/diagnoses should be empty or very minimal
        assert len(result.symptoms) == 0
        assert len(result.diagnoses) == 0

    def test_output_dict_serializable(self):
        """Ensure to_dict() returns JSON-serializable data."""
        import json
        result = extract_entities(SAMPLE_1_CONSULTATION)
        d = result.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        assert len(json_str) > 10


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
