# ClinDoc AI 🩺

**Ambient Clinical Documentation Assistant — SIH 2026 Prototype (PS #43)**

ClinDoc AI is a prototype ambient listening agent designed to automate structured clinical documentation. By listening to the patient-doctor conversation, it automatically extracts medical entities (symptoms, diagnoses, medications) and structures them into FHIR-compliant clinical notes (Consultations, Discharge Summaries, and Prescriptions). 

Built specifically for the Smart India Hackathon (SIH) 2026, this MVP focuses on a multi-lingual, offline-capable architecture designed for Indian clinical settings.

![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square&logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![Python](https://img.shields.io/badge/Language-Python%203.14-3776AB?style=flat-square&logo=python)

---

## 🚀 Features

* **🎙️ Ambient Audio Capture:** WebSockets interface designed to stream audio from the browser to the backend for ASR (mocked via sample audio clips for demo reliability).
* **🧠 Medical Entity Extraction:** Utilizes `med7` and `scispaCy` to accurately pull symptoms, diagnoses, and detailed medication regimens from the transcript.
* **📝 LLM Structuring:** Structures the extracted facts into three distinct formats using a local-friendly mock LLM layer (for zero-latency demoing):
  * Outpatient Consultation Notes
  * Discharge Summaries
  * Prescriptions
* **💊 Safety Layer (DDI Check):** Bundled prototype Drug-Drug Interaction (DDI) checker based on a static, high-frequency Indian drug dataset. Highlights Major/Moderate/Minor risks directly in the UI.
* **🔒 Doctor Authentication:** JWT-based stateless authentication protecting clinical data endpoints. 
* **🌐 Multilingual Support:** Includes sample clinical scenarios generated in English (Indian Accent) and Tamil, demonstrating the future localized ASR pipeline.
* **🏥 FHIR Export:** One-click export of the finalized note to an HL7 FHIR R4 JSON Bundle.

## 🏗️ Architecture

The app is divided into a **Vite/React frontend** and a **FastAPI backend**. 

```text
ClinDoc AI 
 ├── frontend/         # React SPA (Vite, TypeScript, standard CSS)
 │   ├── public/       # Static assets, demo audio clips, comparison slide
 │   └── src/          # React components, hooks, FHIR exporter
 └── backend/          # FastAPI Python Server
     ├── main.py       # API router
     ├── auth.py       # JWT auth & stateless user management
     ├── entity_*.py   # spaCy/Med7 NLP pipeline
     ├── llm_*.py      # Prompt templates & LLM stub logic
     └── ddi_checker.py# Prototype offline DDI safety lookup
```

## 🛠️ Quick Start

### 1. Backend Setup
Make sure you have Python 3.10+ installed.

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

# Install dependencies (requires C++ build tools for spaCy)
pip install -r requirements.txt

# Run the FastAPI server
fastapi dev main.py
```
*Backend runs on `http://localhost:8000`*

### 2. Frontend Setup
Make sure you have Node.js 18+ installed.

```bash
cd frontend
npm install

# Start the Vite dev server
npm run dev
```
*Frontend runs on `http://localhost:5173`*

## 🎬 Demo Guide

1. Open `http://localhost:5173`.
2. **Log In:** Use the pre-filled demo credentials (`doctor@clindoc.ai` / `demo2026`).
3. **Select a scenario:** In the top bar, click one of the demo clips (e.g., *Consultation (EN)* or *Consultation (TA)*).
4. **Watch the pipeline:** 
   * The transcript populates.
   * Entities (symptoms, medications) are instantly extracted.
   * If interacting medications are found (e.g., Aspirin + Warfarin), the **DDI Safety Alert** will appear.
5. **Review the Note:** The right panel structures the facts into a Consultation, Discharge, or Prescription note. 
6. **Export:** Click "Export FHIR Bundle" to download the structured data.
7. **Positioning:** Click `📊 Compare` in the top bar to view a competitive analysis slide against Nuance DAX / Abridge.

## ⚠️ Disclaimer

This is a **hackathon prototype**. 
- The Drug-Drug Interaction (DDI) alerts are a **PROTOTYPE SAFETY LAYER** and are not clinically validated. 
- Do not use this software for actual patient care. 
- Always consult a licensed pharmacist or clinical decision support system before acting on any medical output.
