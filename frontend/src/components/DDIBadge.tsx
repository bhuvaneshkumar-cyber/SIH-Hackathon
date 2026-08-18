/**
 * DDIBadge — Drug-Drug Interaction alert panel.
 *
 * Shown below the NotePanel when the DDI check returns interactions.
 * Clearly labeled as a PROTOTYPE SAFETY LAYER, NOT CLINICALLY VALIDATED.
 *
 * Severity color coding:
 *   Major    → red
 *   Moderate → amber
 *   Minor    → blue/muted
 */

import type { DDIInteraction } from "../hooks/useBackend";

interface DDIBadgeProps {
  interactions: DDIInteraction[];
  loading: boolean;
  onDismiss: () => void;
}

const SEVERITY_CLASS: Record<DDIInteraction["severity"], string> = {
  Major: "ddi-row--major",
  Moderate: "ddi-row--moderate",
  Minor: "ddi-row--minor",
};

const SEVERITY_ICON: Record<DDIInteraction["severity"], string> = {
  Major: "🔴",
  Moderate: "🟡",
  Minor: "🔵",
};

export function DDIBadge({ interactions, loading, onDismiss }: DDIBadgeProps) {
  if (loading) {
    return (
      <div className="ddi-panel animate-fade-in">
        <div className="ddi-panel__header">
          <span className="ddi-panel__title">⏳ Checking interactions…</span>
        </div>
      </div>
    );
  }

  if (interactions.length === 0) {
    return (
      <div className="ddi-panel ddi-panel--clear animate-fade-in">
        <div className="ddi-panel__header">
          <span className="ddi-panel__title">✅ No known interactions detected</span>
          <button className="ddi-panel__dismiss" onClick={onDismiss} id="btn-ddi-dismiss">
            ✕
          </button>
        </div>
        <p className="ddi-panel__disclaimer">
          ⚠️ PROTOTYPE SAFETY LAYER — NOT CLINICALLY VALIDATED. Consult a pharmacist before acting on this result.
        </p>
      </div>
    );
  }

  const majorCount = interactions.filter((i) => i.severity === "Major").length;

  return (
    <div className="ddi-panel animate-fade-in">
      <div className="ddi-panel__header">
        <span className="ddi-panel__title">
          💊 {interactions.length} interaction{interactions.length !== 1 ? "s" : ""} found
          {majorCount > 0 && (
            <span className="ddi-panel__major-badge"> · {majorCount} Major</span>
          )}
        </span>
        <button className="ddi-panel__dismiss" onClick={onDismiss} id="btn-ddi-dismiss">
          ✕
        </button>
      </div>

      <div className="ddi-rows">
        {interactions.map((ix, idx) => (
          <div key={idx} className={`ddi-row ${SEVERITY_CLASS[ix.severity]}`}>
            <div className="ddi-row__header">
              <span className="ddi-row__icon">{SEVERITY_ICON[ix.severity]}</span>
              <strong className="ddi-row__drugs">
                {ix.drug_a} + {ix.drug_b}
              </strong>
              <span className="ddi-row__severity">{ix.severity}</span>
            </div>
            <p className="ddi-row__desc">{ix.description}</p>
          </div>
        ))}
      </div>

      <p className="ddi-panel__disclaimer">
        ⚠️ PROTOTYPE SAFETY LAYER — NOT CLINICALLY VALIDATED.
        Data sourced from curated clinical references. Consult a licensed pharmacist or clinical decision support system before acting on these alerts.
      </p>
    </div>
  );
}
