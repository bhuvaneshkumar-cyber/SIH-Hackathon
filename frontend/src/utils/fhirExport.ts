/**
 * fhirExport — Build a FHIR R4 Bundle from the active encounter.
 *
 * Bundle contains:
 *  - Patient (pseudo id derived from encounterId; no fabricated real IDs)
 *  - Composition (the note, one section per scalar field)
 *  - MedicationRequest x N (one per medication row, discharge / prescription only)
 *  - Condition x N (one per diagnosis string)
 *
 * Download flow lives in App.tsx — this file only builds the JSON object.
 */

import type { Entities } from "../hooks/useBackend";
import type { NoteType } from "../components/NotePanel";

export interface FhirExportInput {
  tab: NoteType;
  mergedNote: Record<string, unknown> | null;
  entities: Entities | null;
  encounterId: string | null;
}

const NOTE_META: Record<NoteType, { loinc: string; title: string }> = {
  consultation: { loinc: "51852-2", title: "Consultation Note" },
  discharge: { loinc: "18842-5", title: "Discharge Summary" },
  prescription: { loinc: "10160-0", title: "Prescription" },
};

// ponytail: minimal escaper — only used on values rendered into `Composition.text.div`.
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ponytail: builds FHIR Coding blocks. Kept inline rather than a util —
// only one consumer.
const coding = (system: string, code: string, display: string) => ({
  system,
  code,
  display,
});

function sectionFor(title: string, value: string) {
  return {
    title,
    text: {
      status: "generated",
      div: `<div xmlns="http://www.w3.org/1999/xhtml">${escapeHtml(value) || "<em>(empty)</em>"}</div>`,
    },
  };
}

function parseDosage(raw: string): { value?: number; unit?: string } {
  if (!raw) return {};
  const m = raw.match(/(\d+(?:\.\d+)?)\s*([a-zA-Zµ]+)/);
  if (!m) return {};
  const value = Number(m[1]);
  return Number.isFinite(value) ? { value, unit: m[2] } : {};
}

function medRequest(patientRef: string, idx: number, row: Record<string, unknown>) {
  const name = String(row.name ?? "");
  const dosage = String(row.dosage ?? "");
  const frequency = String(row.frequency ?? "");
  const route = String(row.route ?? "");
  const duration = String(row.duration ?? "");

  const combined = [dosage, frequency, route, duration].filter(Boolean).join(", ");

  const dosageInstruction: Record<string, unknown> = { text: combined };
  const { value, unit } = parseDosage(dosage);
  if (value !== undefined && unit) {
    dosageInstruction.doseAndRate = [
      { doseQuantity: { value, unit } },
    ];
  }
  if (route) {
    dosageInstruction.route = {
      coding: [coding("http://snomed.info/sct", "", route)],
      text: route,
    };
  }

  return {
    resourceType: "MedicationRequest",
    id: `med-${idx}`,
    status: "active",
    intent: "order",
    subject: { reference: patientRef },
    medicationCodeableConcept: {
      text: name,
      coding: [coding("http://www.nlm.nih.gov/research/umls/rxnorm", "", name)],
    },
    dosageInstruction: [dosageInstruction],
  };
}

function conditionFor(patientRef: string, idx: number, diagnosis: string) {
  return {
    resourceType: "Condition",
    id: `cond-${idx}`,
    clinicalStatus: {
      coding: [
        coding(
          "http://terminology.hl7.org/CodeSystem/condition-clinical",
          "active",
          "Active",
        ),
      ],
    },
    verificationStatus: {
      coding: [
        coding(
          "http://terminology.hl7.org/CodeSystem/condition-ver-status",
          "unconfirmed",
          "Unconfirmed",
        ),
      ],
    },
    subject: { reference: patientRef },
    code: { text: diagnosis },
  };
}

function readStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((v) => String(v));
  if (typeof value === "string" && value.trim()) {
    return value.split(/,\s*/).map((s) => s.trim()).filter(Boolean);
  }
  return [];
}

function readMedRows(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v) => v && typeof v === "object") as Record<string, unknown>[];
}

export function buildFhirBundle(input: FhirExportInput): Record<string, unknown> {
  const { tab, mergedNote, entities, encounterId } = input;
  const shortId = (encounterId ?? "no-encounter").replace(/-/g, "").slice(0, 8);
  const patientRef = `Patient/pat-${shortId}`;
  const meta = NOTE_META[tab];
  const now = new Date().toISOString();

  const note = mergedNote ?? {};
  const entries: Record<string, unknown>[] = [];

  // --- Patient (always) ---
  entries.push({
    resource: {
      resourceType: "Patient",
      id: `pat-${shortId}`,
      identifier: [
        {
          system: "urn:ietf:rfc:4122",
          value: encounterId ?? `pseudo-${shortId}`,
        },
      ],
      active: true,
    },
  });

  // --- Composition: per-tab scalar fields become sections ---
  let compositionSections: Record<string, unknown>[] = [];
  let medicationRows: Record<string, unknown>[] = [];
  let diagnoses: string[] = [];

  if (tab === "consultation") {
    compositionSections = [
      sectionFor("Chief Complaint", String(note.chief_complaint ?? "")),
      sectionFor("History of Present Illness", String(note.history_of_present_illness ?? "")),
      sectionFor("Assessment", String(note.assessment ?? "")),
      sectionFor("Plan", String(note.plan ?? "")),
    ];
  } else if (tab === "discharge") {
    const adm = readStringArray(note.admission_diagnoses);
    const dis = readStringArray(note.discharge_diagnoses);
    medicationRows = readMedRows(note.discharge_medications);
    diagnoses = [...adm, ...dis];
    compositionSections = [
      sectionFor("Admission Diagnoses", adm.join(", ")),
      sectionFor("Discharge Diagnoses", dis.join(", ")),
      sectionFor("Hospital Course", String(note.hospital_course ?? "")),
      sectionFor("Discharge Medications", medicationRows.map((m) => String(m.name ?? "")).join(", ")),
      sectionFor("Follow Up", String(note.follow_up ?? "")),
    ];
  } else {
    // prescription
    diagnoses = readStringArray(note.diagnoses);
    medicationRows = readMedRows(note.medications);
    compositionSections = [
      sectionFor("Diagnoses", diagnoses.join(", ")),
      sectionFor("Medications", medicationRows.map((m) => String(m.name ?? "")).join(", ")),
      sectionFor("Advice", String(note.advice ?? "")),
    ];
  }

  // Surface diagnosis strings as Conditions even if the LLM left the
  // diagnosis arrays empty — fall back to entities.diagnoses so the export
  // is always meaningful for the demo.
  const fallbackDiagnoses = diagnoses.length ? diagnoses : (entities?.diagnoses ?? []);

  entries.push({
    resource: {
      resourceType: "Composition",
      id: `note-${tab}`,
      status: "final",
      type: {
        coding: [coding("http://loinc.org", meta.loinc, meta.title)],
        text: meta.title,
      },
      subject: { reference: patientRef },
      date: now,
      title: meta.title,
      section: compositionSections,
    },
  });

  medicationRows.forEach((row, idx) => {
    entries.push({ resource: medRequest(patientRef, idx, row) });
  });

  fallbackDiagnoses.forEach((d, idx) => {
    entries.push({ resource: conditionFor(patientRef, idx, d) });
  });

  return {
    resourceType: "Bundle",
    id: `bundle-${shortId}`,
    type: "collection",
    timestamp: now,
    meta: {
      profile: ["http://hl7.org/fhir/StructureDefinition/Bundle"],
    },
    entry: entries,
  };
}

// ponytail: download helper colocated — single consumer in App.tsx.
export function downloadJson(filename: string, payload: unknown): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/fhir+json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
