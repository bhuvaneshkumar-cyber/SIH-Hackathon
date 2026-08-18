/**
 * TopBar — Application header with branding, backend status, user badge, and logout.
 * Phase 6: accepts currentUser + onLogout props.
 */

import type { BackendStatus, AuthUser } from "../hooks/useBackend";

interface TopBarProps {
  backendStatus: BackendStatus;
  isRecording: boolean;
  currentUser: AuthUser | null;
  onLogout: () => void;
}

export function TopBar({ backendStatus, isRecording, currentUser, onLogout }: TopBarProps) {
  return (
    <header className="top-bar">
      <div className="top-bar__brand">
        <div className="top-bar__logo" aria-hidden="true">
          C
        </div>
        <div>
          <div className="top-bar__title">ClinDoc AI</div>
          <div className="top-bar__subtitle">
            Ambient Clinical Documentation Assistant
          </div>
        </div>
      </div>

      <div className="top-bar__status">
        {isRecording && (
          <span className="status-badge status-badge--recording animate-fade-in">
            <span className="status-dot status-dot--pulse" />
            Recording
          </span>
        )}

        <a
          href="/compare.html"
          target="_blank"
          rel="noopener noreferrer"
          className="top-bar__compare-link"
          title="ClinDoc AI vs Nuance DAX / Abridge"
        >
          📊 Compare
        </a>

        <span
          className={`status-badge ${
            backendStatus === "connected"
              ? "status-badge--connected"
              : "status-badge--disconnected"
          }`}
        >
          <span
            className={`status-dot ${
              backendStatus === "connected" ? "status-dot--pulse" : ""
            }`}
          />
          {backendStatus === "checking"
            ? "Connecting…"
            : backendStatus === "connected"
            ? "Backend Online"
            : "Backend Offline"}
        </span>

        {currentUser && (
          <div className="top-bar__user">
            <span className="top-bar__user-name">
              👨‍⚕️ {currentUser.full_name}
            </span>
            <button
              className="btn btn--ghost btn--sm"
              onClick={onLogout}
              id="btn-logout"
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
