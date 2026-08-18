"""
ddi_checker.py — Drug-Drug Interaction prototype safety layer.

⚠️  PROTOTYPE SAFETY LAYER — NOT CLINICALLY VALIDATED.
    Data sourced from a curated subset of high-frequency drug pairs based on
    published clinical guidance. Always consult a licensed pharmacist or
    clinical decision support system before acting on these alerts.

Dataset rationale:
    DDInter 2.0 has no public REST API (confirmed August 2026).
    This module ships a static JSON of ~90 commonly prescribed Indian
    drug pairs with severity grades (Major / Moderate / Minor) and a brief
    mechanism note. Pairs are normalised to lowercase for case-insensitive
    matching.

Severity grades mirror DDInter / Drugs.com conventions:
    Major    — potentially life-threatening; avoid combination if possible
    Moderate — may exacerbate condition or require monitoring / dose adjustment
    Minor    — limited clinical effect; monitor if used together
"""

from __future__ import annotations
import json
from typing import Literal

Severity = Literal["Major", "Moderate", "Minor"]


# ---------------------------------------------------------------------------
# Interaction dataset (static, offline-safe)
# Key: frozenset of two canonical lowercase drug names → interaction record
# ---------------------------------------------------------------------------
_RAW: list[dict] = [
    # ── Anticoagulants ──────────────────────────────────────────────────────
    {"drugs": ["aspirin", "warfarin"], "severity": "Major",
     "description": "Increased bleeding risk; combined antiplatelet + anticoagulant effect."},
    {"drugs": ["ibuprofen", "warfarin"], "severity": "Major",
     "description": "NSAIDs displace warfarin from protein binding and inhibit platelet aggregation."},
    {"drugs": ["naproxen", "warfarin"], "severity": "Major",
     "description": "NSAID potentiates anticoagulant effect; GI bleed risk."},
    {"drugs": ["aspirin", "clopidogrel"], "severity": "Moderate",
     "description": "Dual antiplatelet increases bleed risk; used intentionally post-ACS but requires monitoring."},
    {"drugs": ["heparin", "aspirin"], "severity": "Major",
     "description": "Additive anticoagulation and platelet inhibition; major bleed risk."},

    # ── Antidiabetics ───────────────────────────────────────────────────────
    {"drugs": ["metformin", "contrast media"], "severity": "Major",
     "description": "Contrast-induced nephropathy can accumulate metformin → lactic acidosis. Hold 48 h before/after."},
    {"drugs": ["glipizide", "fluconazole"], "severity": "Major",
     "description": "Fluconazole inhibits CYP2C9, markedly elevating sulfonylurea levels → hypoglycaemia."},
    {"drugs": ["glibenclamide", "fluconazole"], "severity": "Major",
     "description": "CYP2C9 inhibition raises glibenclamide → severe hypoglycaemia."},
    {"drugs": ["insulin", "alcohol"], "severity": "Major",
     "description": "Alcohol potentiates insulin hypoglycaemia and masks warning signs."},
    {"drugs": ["metformin", "alcohol"], "severity": "Moderate",
     "description": "Alcohol increases lactic acidosis risk with metformin."},
    {"drugs": ["glipizide", "aspirin"], "severity": "Moderate",
     "description": "Salicylates can potentiate hypoglycaemic effect of sulfonylureas."},

    # ── Cardiovascular ──────────────────────────────────────────────────────
    {"drugs": ["amlodipine", "simvastatin"], "severity": "Moderate",
     "description": "Amlodipine inhibits CYP3A4 metabolism of simvastatin; myopathy risk. Limit simvastatin to 20 mg."},
    {"drugs": ["amlodipine", "atorvastatin"], "severity": "Minor",
     "description": "Mild CYP3A4 interaction; atorvastatin levels may rise slightly."},
    {"drugs": ["metoprolol", "verapamil"], "severity": "Major",
     "description": "Additive negative chronotropy and inotropy; risk of heart block and severe bradycardia."},
    {"drugs": ["metoprolol", "diltiazem"], "severity": "Major",
     "description": "Additive AV nodal blockade; bradycardia and heart block risk."},
    {"drugs": ["enalapril", "spironolactone"], "severity": "Major",
     "description": "Combined potassium-sparing effect → life-threatening hyperkalaemia."},
    {"drugs": ["lisinopril", "potassium chloride"], "severity": "Major",
     "description": "ACE inhibitor + potassium supplement → hyperkalaemia."},
    {"drugs": ["digoxin", "amiodarone"], "severity": "Major",
     "description": "Amiodarone raises digoxin levels 50–100%; reduce digoxin dose by 50%, monitor levels."},
    {"drugs": ["digoxin", "clarithromycin"], "severity": "Major",
     "description": "P-gp inhibition raises digoxin → toxicity (nausea, arrhythmia, vision changes)."},
    {"drugs": ["furosemide", "gentamicin"], "severity": "Major",
     "description": "Additive ototoxicity and nephrotoxicity."},
    {"drugs": ["hydrochlorothiazide", "lithium"], "severity": "Major",
     "description": "Thiazides reduce renal lithium excretion → lithium toxicity."},
    {"drugs": ["atenolol", "insulin"], "severity": "Moderate",
     "description": "Beta-blockers mask hypoglycaemia symptoms (tachycardia); prolonged hypoglycaemia."},
    {"drugs": ["metoprolol", "insulin"], "severity": "Moderate",
     "description": "Beta-blockade masks adrenergic hypoglycaemia warning signs."},
    {"drugs": ["amlodipine", "rifampicin"], "severity": "Major",
     "description": "Rifampicin is a potent CYP3A4 inducer; amlodipine levels drop dramatically."},

    # ── Antibiotics ─────────────────────────────────────────────────────────
    {"drugs": ["ciprofloxacin", "antacid"], "severity": "Moderate",
     "description": "Antacid chelates ciprofloxacin → markedly reduced absorption. Separate by 2 h."},
    {"drugs": ["ciprofloxacin", "theophylline"], "severity": "Major",
     "description": "Ciprofloxacin inhibits CYP1A2 → theophylline toxicity (seizures, arrhythmia)."},
    {"drugs": ["clarithromycin", "simvastatin"], "severity": "Major",
     "description": "CYP3A4 inhibition → rhabdomyolysis risk. Use alternative statin."},
    {"drugs": ["erythromycin", "simvastatin"], "severity": "Major",
     "description": "CYP3A4 inhibition; rhabdomyolysis reported."},
    {"drugs": ["metronidazole", "alcohol"], "severity": "Major",
     "description": "Disulfiram-like reaction: flushing, nausea, vomiting, hypotension."},
    {"drugs": ["tetracycline", "iron"], "severity": "Moderate",
     "description": "Iron chelates tetracycline; reduced antibiotic absorption. Separate by 2 h."},
    {"drugs": ["tetracycline", "antacid"], "severity": "Moderate",
     "description": "Divalent cations (Ca, Mg, Al) chelate tetracycline; separate by 2 h."},
    {"drugs": ["fluconazole", "warfarin"], "severity": "Major",
     "description": "Potent CYP2C9 inhibition → warfarin accumulation; significant bleed risk."},
    {"drugs": ["rifampicin", "oral contraceptive"], "severity": "Major",
     "description": "CYP3A4 induction reduces contraceptive efficacy; contraception failure."},
    {"drugs": ["rifampicin", "warfarin"], "severity": "Major",
     "description": "CYP2C9/2C19 induction → markedly reduced warfarin effect; INR will drop."},

    # ── CNS / Psychotropics ─────────────────────────────────────────────────
    {"drugs": ["tramadol", "ssri"], "severity": "Major",
     "description": "Serotonin syndrome risk: agitation, hyperthermia, clonus, tachycardia."},
    {"drugs": ["tramadol", "sertraline"], "severity": "Major",
     "description": "Serotonin syndrome and lowered seizure threshold."},
    {"drugs": ["tramadol", "fluoxetine"], "severity": "Major",
     "description": "Serotonin syndrome; fluoxetine also inhibits CYP2D6 metabolism of tramadol."},
    {"drugs": ["diazepam", "alcohol"], "severity": "Major",
     "description": "Additive CNS depression; respiratory depression, coma risk."},
    {"drugs": ["alprazolam", "alcohol"], "severity": "Major",
     "description": "Additive sedation and respiratory depression."},
    {"drugs": ["phenytoin", "carbamazepine"], "severity": "Moderate",
     "description": "Mutual induction; unpredictable serum levels of both drugs. Monitor levels."},
    {"drugs": ["phenytoin", "warfarin"], "severity": "Major",
     "description": "Bidirectional: phenytoin initially inhibits then induces warfarin metabolism. Monitor INR closely."},
    {"drugs": ["lithium", "ibuprofen"], "severity": "Major",
     "description": "NSAIDs reduce renal lithium clearance → lithium toxicity (tremor, confusion, seizure)."},
    {"drugs": ["lithium", "diclofenac"], "severity": "Major",
     "description": "NSAID-induced lithium accumulation."},
    {"drugs": ["haloperidol", "lithium"], "severity": "Major",
     "description": "Risk of irreversible neurotoxicity at normal lithium levels."},

    # ── Analgesics / Pain ───────────────────────────────────────────────────
    {"drugs": ["paracetamol", "alcohol"], "severity": "Major",
     "description": "Chronic alcohol use increases hepatotoxic NAPQI metabolite from paracetamol."},
    {"drugs": ["paracetamol", "warfarin"], "severity": "Moderate",
     "description": "Regular high-dose paracetamol enhances anticoagulant effect; monitor INR."},
    {"drugs": ["ibuprofen", "lisinopril"], "severity": "Moderate",
     "description": "NSAIDs blunt ACE inhibitor antihypertensive effect and impair renal function."},
    {"drugs": ["ibuprofen", "aspirin"], "severity": "Moderate",
     "description": "Ibuprofen competitively blocks aspirin's irreversible platelet COX-1 binding."},
    {"drugs": ["codeine", "clarithromycin"], "severity": "Moderate",
     "description": "CYP3A4 inhibition reduces codeine clearance; raised opioid effect."},
    {"drugs": ["morphine", "diazepam"], "severity": "Major",
     "description": "Additive CNS and respiratory depression."},

    # ── GI / Ulcer drugs ────────────────────────────────────────────────────
    {"drugs": ["pantoprazole", "clopidogrel"], "severity": "Moderate",
     "description": "Pantoprazole may reduce CYP2C19-mediated clopidogrel activation; consider rabeprazole."},
    {"drugs": ["omeprazole", "clopidogrel"], "severity": "Moderate",
     "description": "CYP2C19 competition; reduced clopidogrel antiplatelet effect documented."},
    {"drugs": ["sucralfate", "ciprofloxacin"], "severity": "Moderate",
     "description": "Sucralfate chelates ciprofloxacin; reduced absorption. Separate doses by 2 h."},

    # ── Hormones / Endocrine ────────────────────────────────────────────────
    {"drugs": ["levothyroxine", "calcium carbonate"], "severity": "Moderate",
     "description": "Calcium impairs levothyroxine absorption; separate by 4 h."},
    {"drugs": ["levothyroxine", "iron"], "severity": "Moderate",
     "description": "Iron chelates levothyroxine; significantly reduced absorption. Separate by 4 h."},
    {"drugs": ["dexamethasone", "insulin"], "severity": "Moderate",
     "description": "Glucocorticoids raise blood glucose; insulin requirements increase."},
    {"drugs": ["prednisolone", "insulin"], "severity": "Moderate",
     "description": "Steroid-induced hyperglycaemia; monitor glucose and adjust insulin."},
    {"drugs": ["prednisolone", "ibuprofen"], "severity": "Major",
     "description": "Additive GI ulceration and bleeding risk; avoid combination without gastroprotection."},
    {"drugs": ["prednisolone", "aspirin"], "severity": "Moderate",
     "description": "Increased GI ulcer risk; corticosteroids reduce salicylate levels."},

    # ── Anti-TB ─────────────────────────────────────────────────────────────
    {"drugs": ["rifampicin", "isoniazid"], "severity": "Moderate",
     "description": "Rifampicin induces CYP2E1 metabolism of isoniazid → hepatotoxic hydrazine metabolite."},
    {"drugs": ["isoniazid", "phenytoin"], "severity": "Major",
     "description": "Isoniazid inhibits CYP2C19 → phenytoin toxicity (ataxia, nystagmus)."},
    {"drugs": ["isoniazid", "carbamazepine"], "severity": "Major",
     "description": "Isoniazid inhibits carbamazepine metabolism; toxicity (diplopia, ataxia, drowsiness)."},

    # ── Antiretrovirals / Antivirals ────────────────────────────────────────
    {"drugs": ["tenofovir", "ibuprofen"], "severity": "Moderate",
     "description": "Additive nephrotoxicity; avoid NSAIDs in patients on tenofovir."},
    {"drugs": ["lopinavir", "simvastatin"], "severity": "Major",
     "description": "CYP3A4 inhibition → massive statin accumulation; rhabdomyolysis."},

    # ── Miscellaneous ────────────────────────────────────────────────────────
    {"drugs": ["cetirizine", "alcohol"], "severity": "Moderate",
     "description": "Additive CNS sedation."},
    {"drugs": ["ondansetron", "tramadol"], "severity": "Moderate",
     "description": "Both inhibit/agonise serotonin pathways; serotonin syndrome risk."},
    {"drugs": ["allopurinol", "azathioprine"], "severity": "Major",
     "description": "Allopurinol inhibits xanthine oxidase → azathioprine accumulation → severe myelosuppression."},
    {"drugs": ["sildenafil", "nitrate"], "severity": "Major",
     "description": "Catastrophic hypotension; absolute contraindication."},
    {"drugs": ["sildenafil", "isosorbide mononitrate"], "severity": "Major",
     "description": "Potentiated nitrate vasodilation; severe hypotension, MI, death reported."},
]

# Build lookup index: frozenset({drug_a, drug_b}) → interaction dict
_INDEX: dict[frozenset, dict] = {
    frozenset(r["drugs"]): r for r in _RAW
}

# Severity sort order for ranking
_SEVERITY_ORDER = {"Major": 0, "Moderate": 1, "Minor": 2}


def _normalise(name: str) -> str:
    """Lowercase, strip whitespace, collapse multiple spaces."""
    return " ".join(name.lower().split())


def check_interactions(drug_names: list[str]) -> list[dict]:
    """
    Given a list of drug names (from entity extraction), return all known
    pairwise interactions sorted by severity (Major first).

    Returns a list of dicts:
        {
            "drug_a": str,
            "drug_b": str,
            "severity": "Major" | "Moderate" | "Minor",
            "description": str,
            "disclaimer": str,
        }
    """
    normed = [_normalise(d) for d in drug_names if d]
    found: list[dict] = []

    for i in range(len(normed)):
        for j in range(i + 1, len(normed)):
            key = frozenset({normed[i], normed[j]})
            if key in _INDEX:
                record = _INDEX[key]
                found.append({
                    "drug_a": drug_names[i],
                    "drug_b": drug_names[j],
                    "severity": record["severity"],
                    "description": record["description"],
                    "disclaimer": (
                        "PROTOTYPE SAFETY LAYER — NOT CLINICALLY VALIDATED. "
                        "Consult a pharmacist or clinical decision support "
                        "system before acting on this alert."
                    ),
                })

    found.sort(key=lambda x: _SEVERITY_ORDER.get(x["severity"], 99))
    return found
