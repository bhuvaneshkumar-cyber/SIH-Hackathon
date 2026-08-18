"""
Entity Extraction — Layer 2

Dual-extractor pipeline:
  1. med7 (spaCy model)  → medication fields (drug, dosage, strength, route, frequency, form, duration)
  2. Symptom/Diagnosis extractor → clinical term matching via spaCy NER + rule-based PhraseMatcher

Both extractors output a single merged entity list:
{
  "symptoms": ["string", ...],
  "diagnoses": ["string", ...],
  "medications": [{"name": "", "dosage": "", "frequency": "", "route": "", "duration": ""}, ...]
}

Translation normalization for non-English text is stubbed (TODO: wire to Ollama in Phase 3).
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

import spacy
from spacy.matcher import PhraseMatcher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Medication:
    name: str = ""
    dosage: str = ""
    frequency: str = ""
    route: str = ""
    duration: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ExtractedEntities:
    symptoms: list[str] = field(default_factory=list)
    diagnoses: list[str] = field(default_factory=list)
    medications: list[Medication] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symptoms": self.symptoms,
            "diagnoses": self.diagnoses,
            "medications": [m.to_dict() for m in self.medications],
        }


# ---------------------------------------------------------------------------
# Curated clinical term lists for rule-based matching
# (supplements NER — catches common terms that general models miss)
# ---------------------------------------------------------------------------

# Common symptoms seen in Indian clinical settings
SYMPTOM_TERMS = [
    "fever", "cough", "cold", "headache", "body ache", "body pain",
    "chest pain", "shortness of breath", "breathlessness", "wheezing",
    "nausea", "vomiting", "diarrhea", "diarrhoea", "constipation",
    "abdominal pain", "stomach pain", "back pain", "joint pain",
    "muscle pain", "fatigue", "weakness", "dizziness", "lightheadedness",
    "palpitations", "swelling", "edema", "oedema", "rash", "itching",
    "burning sensation", "numbness", "tingling", "blurred vision",
    "loss of appetite", "weight loss", "weight gain", "insomnia",
    "difficulty sleeping", "anxiety", "depression", "sore throat",
    "runny nose", "nasal congestion", "ear pain", "eye pain",
    "difficulty swallowing", "blood in stool", "blood in urine",
    "frequent urination", "painful urination", "chest tightness",
    "night sweats", "chills", "rigors", "malaise", "lethargy",
    "excessive thirst", "excessive hunger", "dry mouth", "dry cough",
    "productive cough", "cough with sputum", "hemoptysis",
    "loss of consciousness", "seizures", "tremors", "cramps",
    "bloating", "heartburn", "acid reflux", "hiccups",
]

# Common diagnoses / conditions
DIAGNOSIS_TERMS = [
    "hypertension", "high blood pressure", "diabetes", "diabetes mellitus",
    "type 2 diabetes", "type 1 diabetes", "asthma", "bronchitis",
    "pneumonia", "tuberculosis", "tb", "copd",
    "chronic obstructive pulmonary disease", "coronary artery disease",
    "myocardial infarction", "heart attack", "heart failure",
    "congestive heart failure", "atrial fibrillation", "stroke",
    "cerebrovascular accident", "hyperlipidemia", "dyslipidemia",
    "hypothyroidism", "hyperthyroidism", "anemia", "anaemia",
    "iron deficiency anemia", "urinary tract infection", "uti",
    "upper respiratory tract infection", "urti", "gastritis",
    "peptic ulcer", "gastroesophageal reflux disease", "gerd",
    "irritable bowel syndrome", "ibs", "chronic kidney disease",
    "acute kidney injury", "liver cirrhosis", "hepatitis",
    "dengue", "malaria", "typhoid", "chikungunya",
    "covid-19", "influenza", "migraine", "epilepsy",
    "rheumatoid arthritis", "osteoarthritis", "osteoporosis",
    "depression", "anxiety disorder", "bipolar disorder",
    "schizophrenia", "skin infection", "cellulitis",
    "fungal infection", "viral fever", "bacterial infection",
]

# ---------------------------------------------------------------------------
# Singleton model loader (lazy init — loads on first extraction call)
# ---------------------------------------------------------------------------

class _Models:
    """Lazy-loaded NLP model container."""

    def __init__(self) -> None:
        self._med7 = None
        self._general_nlp = None
        self._symptom_matcher = None
        self._diagnosis_matcher = None
        self._med7_available = False

    @property
    def med7(self):
        if self._med7 is None:
            try:
                self._med7 = spacy.load("en_core_med7_lg")
                self._med7_available = True
                logger.info("med7 model loaded successfully")
            except OSError:
                logger.warning(
                    "med7 model not found — medication extraction will use "
                    "regex fallback. Install with: pip install the med7 wheel."
                )
                self._med7_available = False
        return self._med7

    @property
    def med7_available(self) -> bool:
        # Trigger lazy load
        _ = self.med7
        return self._med7_available

    @property
    def general_nlp(self):
        if self._general_nlp is None:
            self._general_nlp = spacy.load("en_core_web_sm")
            # Build phrase matchers
            self._symptom_matcher = PhraseMatcher(self._general_nlp.vocab, attr="LOWER")
            symptom_patterns = [self._general_nlp.make_doc(t) for t in SYMPTOM_TERMS]
            self._symptom_matcher.add("SYMPTOM", symptom_patterns)

            self._diagnosis_matcher = PhraseMatcher(self._general_nlp.vocab, attr="LOWER")
            diagnosis_patterns = [self._general_nlp.make_doc(t) for t in DIAGNOSIS_TERMS]
            self._diagnosis_matcher.add("DIAGNOSIS", diagnosis_patterns)

            logger.info("General NLP model + phrase matchers loaded")
        return self._general_nlp

    @property
    def symptom_matcher(self):
        _ = self.general_nlp  # ensure initialized
        return self._symptom_matcher

    @property
    def diagnosis_matcher(self):
        _ = self.general_nlp  # ensure initialized
        return self._diagnosis_matcher


_models = _Models()


# ---------------------------------------------------------------------------
# Translation normalization stub
# ---------------------------------------------------------------------------

def normalize_to_english(text: str) -> str:
    """
    Translate / normalize non-English clinical text to English.
    TODO: Wire to Ollama local model in Phase 3.
    For now, pass through unchanged (assumes English input).
    """
    # Placeholder — in Phase 3 this will call the local LLM
    return text


# ---------------------------------------------------------------------------
# Medication extraction
# ---------------------------------------------------------------------------

# Regex patterns for fallback medication extraction
_DOSAGE_PATTERN = re.compile(
    r'\b(\d+(?:\.\d+)?)\s*(mg|g|mcg|µg|ml|mL|iu|units?|tablet|tab|capsule|cap|drops?|puffs?)\b',
    re.IGNORECASE
)
_FREQUENCY_PATTERN = re.compile(
    r'\b(once|twice|thrice|'
    r'(?:one|two|three|four)\s*times?\s*(?:a|per)\s*day|'
    r'daily|bid|tid|qid|prn|'
    r'every\s*\d+\s*hours?|'
    r'(?:od|bd|tds|qds|sos|hs)|'
    r'(?:morning|evening|night|bedtime)|'
    r'(?:before|after)\s*(?:meals?|food|breakfast|lunch|dinner))\b',
    re.IGNORECASE
)
_ROUTE_PATTERN = re.compile(
    r'\b(oral|orally|iv|intravenous|im|intramuscular|'
    r'sc|subcutaneous|topical|inhaled|inhalation|'
    r'sublingual|rectal|nasal|ophthalmic|otic|'
    r'by\s*mouth|per\s*oral)\b',
    re.IGNORECASE
)
_DURATION_PATTERN = re.compile(
    r'\b(?:for\s+)?(\d+)\s*(days?|weeks?|months?|years?)\b',
    re.IGNORECASE
)


def _extract_medications_med7(text: str) -> list[Medication]:
    """Extract medications using the med7 NER model."""
    nlp = _models.med7
    if nlp is None:
        return []

    doc = nlp(text)
    medications: list[Medication] = []

    # med7 entity labels: DRUG, DOSAGE, STRENGTH, ROUTE, FREQUENCY, FORM, DURATION
    # Group entities into medications — heuristic: each DRUG label starts a new med
    current_med: dict[str, str] = {}

    for ent in doc.ents:
        label = ent.label_.upper()
        value = ent.text.strip()

        if label == "DRUG":
            # If we already have a drug in progress, save it
            if current_med.get("name"):
                medications.append(Medication(**current_med))
            current_med = {"name": value, "dosage": "", "frequency": "", "route": "", "duration": ""}
        elif label in ("DOSAGE", "STRENGTH"):
            current_med["dosage"] = (current_med.get("dosage", "") + " " + value).strip()
        elif label == "FREQUENCY":
            current_med["frequency"] = value
        elif label == "ROUTE":
            current_med["route"] = value
        elif label in ("DURATION",):
            current_med["duration"] = value
        elif label == "FORM":
            # Form (e.g. "tablet", "syrup") — append to dosage for context
            current_med["dosage"] = (current_med.get("dosage", "") + " " + value).strip()

    # Don't forget the last medication
    if current_med.get("name"):
        medications.append(Medication(**current_med))

    return medications


# Pattern to find a candidate drug name immediately before a dosage.
# Matches 1–3 capitalized words optionally preceded by "and", commas, or conjunctions.
_DRUG_NAME_BEFORE_DOSAGE = re.compile(
    r'(?:(?:and|,|with|also|plus|start|prescrib(?:e|ing)?)\s+)?'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})'
    r'\s*(?:tablet|tab|capsule|cap|syrup|syp|injection|inj|inhaler)?\s*$',
    re.IGNORECASE,
)


def _extract_medications_regex(text: str) -> list[Medication]:
    """
    Regex-based fallback for medication extraction when med7 is unavailable.

    Strategy:
      1. Split into clause-like segments (by period, newline, semicolon).
      2. For each segment containing a dosage pattern, scan *backwards* from
         the dosage position to find the nearest capitalised drug name,
         allowing for conjunctions ("and", ",") between the prior drug and
         the new one in list-style sentences.
    """
    medications: list[Medication] = []
    # Split into individual clauses — commas kept within each clause
    segments = re.split(r'[.\n;]', text)

    for segment in segments:
        # A segment can contain multiple dosage references (e.g. "Asp 75mg OD and Met 25mg BD")
        # Find all dosage positions and handle each independently
        dosage_iter = list(_DOSAGE_PATTERN.finditer(segment))
        if not dosage_iter:
            continue

        freq_match = _FREQUENCY_PATTERN.search(segment)
        route_match = _ROUTE_PATTERN.search(segment)
        dur_match = _DURATION_PATTERN.search(segment)

        for dosage_match in dosage_iter:
            before = segment[:dosage_match.start()]

            # Walk backwards token-by-token to collect the drug name.
            # Stop at stop-words that indicate the drug name ended.
            stop_words = {
                "with", "the", "of", "is", "was", "are", "for",
                "a", "an", "in", "on", "at", "by", "to", "prescribed",
                "start", "continue", "add", "prescribing",
            }
            tokens = re.split(r'[\s,]+', before.strip())
            name_parts: list[str] = []
            for tok in reversed(tokens):
                clean = tok.strip(",.;:()\"'")
                if not clean:
                    continue
                lower = clean.lower()
                # Conjunction like "and" separates list items — stop collecting
                if lower in ("and", "also", "plus"):
                    break
                # Stop-word encountered and we already have a name — done
                if lower in stop_words and name_parts:
                    break
                # Accept capitalized words, short abbreviations (Tab, Cap, Inj)
                if clean[0].isupper() or lower in ("tab", "cap", "inj", "syp"):
                    name_parts.insert(0, clean)
                elif name_parts:
                    # Lower-case word after we have name parts → stop
                    break

            drug_name = " ".join(name_parts).strip()
            if not drug_name:
                continue

            medications.append(Medication(
                name=drug_name,
                dosage=dosage_match.group(0),
                frequency=freq_match.group(0) if freq_match else "",
                route=route_match.group(0) if route_match else "",
                duration=dur_match.group(0) if dur_match else "",
            ))

    return medications


# ---------------------------------------------------------------------------
# Symptom & diagnosis extraction
# ---------------------------------------------------------------------------

def _extract_symptoms_diagnoses(text: str) -> tuple[list[str], list[str]]:
    """
    Extract symptoms and diagnoses using:
      1. spaCy general NER (catches some medical entities)
      2. PhraseMatcher with curated clinical term lists
    Deduplicates and returns (symptoms, diagnoses).
    """
    nlp = _models.general_nlp
    doc = nlp(text)

    symptoms: set[str] = set()
    diagnoses: set[str] = set()

    # --- PhraseMatcher ---
    symptom_matches = _models.symptom_matcher(doc)
    for _match_id, start, end in symptom_matches:
        span_text = doc[start:end].text.strip()
        if span_text:
            symptoms.add(span_text.lower())

    diagnosis_matches = _models.diagnosis_matcher(doc)
    for _match_id, start, end in diagnosis_matches:
        span_text = doc[start:end].text.strip()
        if span_text:
            diagnoses.add(span_text.lower())

    # --- spaCy general NER (DISEASE-like labels from en_core_web_sm are limited,
    #     but we can catch terms flagged as conditions from context) ---
    # en_core_web_sm doesn't have DISEASE labels, but can help with deduplication

    # Normalize: capitalize for readability
    return (
        sorted(s.title() for s in symptoms),
        sorted(d.title() for d in diagnoses),
    )


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_entities(transcript_text: str) -> ExtractedEntities:
    """
    Run the full entity extraction pipeline on a transcript.

    Steps:
      1. Normalize to English (stub for now)
      2. Extract medications (med7 if available, else regex fallback)
      3. Extract symptoms & diagnoses (PhraseMatcher + NER)
      4. Merge into a single ExtractedEntities object

    Args:
        transcript_text: The full transcript text (may be multi-speaker).

    Returns:
        ExtractedEntities with symptoms, diagnoses, and medications.
    """
    # Step 1: Normalize
    english_text = normalize_to_english(transcript_text)

    # Step 2: Medications
    if _models.med7_available:
        medications = _extract_medications_med7(english_text)
        logger.info("Extracted %d medications via med7", len(medications))
    else:
        medications = _extract_medications_regex(english_text)
        logger.info("Extracted %d medications via regex fallback", len(medications))

    # Step 3: Symptoms & diagnoses
    symptoms, diagnoses = _extract_symptoms_diagnoses(english_text)
    logger.info("Extracted %d symptoms, %d diagnoses", len(symptoms), len(diagnoses))

    # Step 4: Merge
    return ExtractedEntities(
        symptoms=symptoms,
        diagnoses=diagnoses,
        medications=medications,
    )
