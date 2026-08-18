"""
Generate 3 sample English clinical audio clips via edge-tts (Microsoft Neural TTS).
Outputs go to frontend/public/samples/ so Vite serves them statically.

Clip design:
  clip_en_consultation.mp3 – Outpatient consultation (fever + hypertension)
  clip_en_discharge.mp3    – Discharge summary scenario (post-MI recovery)
  clip_en_prescription.mp3 – Prescription-only encounter (acid reflux)

Voice: en-IN-NeerjaNeural (Indian English, female — familiar accent for Indian judges)
"""

import asyncio
import os
import edge_tts

OUTPUT_DIR = r"d:\Bhuvanesh\My_Workspace\Projects\SIH_2026\frontend\public\samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICE = "en-IN-NeerjaNeural"

# Use alternating voice for doctor lines to simulate diarisation
VOICE_DOCTOR = "en-IN-PrabhatNeural"   # male, Indian English
VOICE_PATIENT = "en-IN-NeerjaNeural"    # female, Indian English

CLIPS = {
    "clip_en_consultation": """\
Doctor: Good morning. What brings you in today?
Patient: Doctor, I have been having a fever for the past three days, along with a severe headache and body ache.
Doctor: Any cough, cold, or sore throat?
Patient: Yes, I have a dry cough. Also feeling very tired.
Doctor: Let me check. Your temperature is 101 degrees and blood pressure is 145 over 90, which is a little high.
Patient: I have a history of high blood pressure, doctor. I was on Amlodipine earlier.
Doctor: I see. I am diagnosing you with viral fever and mild hypertension.
Doctor: I am prescribing Paracetamol 500 milligrams twice daily for 5 days for the fever, and Amlodipine 5 milligrams once daily for the blood pressure.
Doctor: Drink plenty of fluids, take rest, and come back if the fever does not subside in 5 days.
Patient: Thank you, doctor.""",

    "clip_en_discharge": """\
Doctor: Mr. Sharma, good news — you are ready to be discharged today.
Patient: That is a relief, doctor. What was wrong with me exactly?
Doctor: You came in with chest pain and breathlessness. We confirmed a mild heart attack — what we call a non-ST elevation myocardial infarction — as well as Type 2 diabetes which was poorly controlled.
Patient: I see. What medicines do I need to take?
Doctor: You will continue Aspirin 75 milligrams once daily, Atorvastatin 20 milligrams at night, Metformin 500 milligrams twice daily with food, and Metoprolol 25 milligrams twice daily for the heart.
Doctor: Please avoid strenuous activity for the next two weeks. Follow up with the cardiologist within 7 days, and get an HbA1c test done before your next visit.
Patient: Understood. Thank you, doctor.""",

    "clip_en_prescription": """\
Doctor: What seems to be the problem today?
Patient: I have been having burning in my chest after meals for the past week, doctor. It gets worse when I lie down.
Doctor: Any nausea, vomiting, or difficulty swallowing?
Patient: A little nausea, but no vomiting or swallowing problem.
Doctor: This sounds like gastroesophageal reflux disease — acid reflux. I am going to prescribe Pantoprazole 40 milligrams once daily before breakfast, and Domperidone 10 milligrams three times a day before meals.
Doctor: Avoid spicy food, fried food, and caffeine. Do not lie down immediately after eating. Take the medicines for two weeks and come back if there is no improvement.
Patient: Will do, doctor. Thank you.""",
}


async def generate_clip(name: str, text: str) -> None:
    out_path = os.path.join(OUTPUT_DIR, f"{name}.mp3")
    # For TTS we use the patient voice (female) for the whole clip —
    # real diarisation is Phase 1 ASR work; these clips demonstrate content,
    # not speaker separation.
    communicate = edge_tts.Communicate(text, VOICE_PATIENT, rate="-5%")
    await communicate.save(out_path)
    size_kb = os.path.getsize(out_path) // 1024
    print(f"  [OK] {name}.mp3  ({size_kb} KB)")


async def main() -> None:
    print(f"Generating {len(CLIPS)} audio clips -> {OUTPUT_DIR}\n")
    tasks = [generate_clip(n, t) for n, t in CLIPS.items()]
    await asyncio.gather(*tasks)
    print("\nAll clips generated.")


if __name__ == "__main__":
    asyncio.run(main())
