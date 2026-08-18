/**
 * seedTranscript — Demo transcript for Phase 4.
 *
 * Phase 1 (real ASR) isn't wired; the frontend seeds a realistic Indian-clinical
 * sample on mount to exercise the full transcript → entities → note → FHIR
 * pipeline that judges will see live.
 *
 * Content intentionally stresses all three note templates and triggers the
 * standard medication + symptom + diagnosis extractors.
 */

import type { TranscriptEntry } from "../components/TranscriptPanel";

export const SEED_TRANSCRIPT: TranscriptEntry[] = [
  {
    id: "seed-1",
    speaker: "doctor",
    text: "Good morning. What brings you in today?",
  },
  {
    id: "seed-2",
    speaker: "patient",
    text: "Doctor, I've had a fever and headache for the last three days, along with body ache and a dry cough.",
  },
  {
    id: "seed-3",
    speaker: "doctor",
    text: "Any nausea, vomiting, or sore throat?",
  },
  {
    id: "seed-4",
    speaker: "patient",
    text: "Yes, I feel nauseous but no vomiting. No sore throat either. I'm also feeling more tired than usual.",
  },
  {
    id: "seed-5",
    speaker: "doctor",
    text: "Let me check. Temperature is 101.2 Fahrenheit, throat mildly inflamed, and blood pressure is 140 over 90, slightly elevated.",
  },
  {
    id: "seed-6",
    speaker: "doctor",
    text: "I'm diagnosing this as a viral fever with mild hypertension. I'm prescribing Paracetamol 500 mg twice daily for 5 days and Cetirizine 10 mg once daily at night for the cough. Continue your existing Amlodipine 5 mg once daily for the blood pressure.",
  },
  {
    id: "seed-7",
    speaker: "doctor",
    text: "I'd also like a CBC and dengue NS1 test to rule anything else out. Please drink plenty of fluids and rest.",
  },
  {
    id: "seed-8",
    speaker: "patient",
    text: "Should I be worried, doctor?",
  },
  {
    id: "seed-9",
    speaker: "doctor",
    text: "No, this looks viral. If the fever persists beyond five days, or you develop a rash or severe headache, come back immediately.",
  },
  {
    id: "seed-10",
    speaker: "patient",
    text: "Thank you, doctor.",
  },
];

export const SEED_TRANSCRIPT_TEXT = SEED_TRANSCRIPT.map((e) => e.text).join(" ");
