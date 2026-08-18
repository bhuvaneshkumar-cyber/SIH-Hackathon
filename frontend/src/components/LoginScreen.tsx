/**
 * LoginScreen — Demo doctor login form.
 *
 * Renders a full-page login UI with:
 *  - Email + password fields
 *  - Shows demo credentials hint prominently
 *  - Error message on bad credentials
 *  - Loading state during POST /auth/login
 *
 * On success, calls onLogin() so App.tsx can switch to the main UI.
 */

import { useState, useCallback, type FormEvent } from "react";

interface LoginScreenProps {
  onLogin: (email: string, password: string) => Promise<void>;
}

const HINT_EMAIL = "doctor@clindoc.ai";
const HINT_PASS = "demo2026";

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [email, setEmail] = useState(HINT_EMAIL);
  const [password, setPassword] = useState(HINT_PASS);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      setLoading(true);
      try {
        await onLogin(email.trim(), password);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Login failed");
      } finally {
        setLoading(false);
      }
    },
    [email, password, onLogin]
  );

  return (
    <div className="login-screen">
      <div className="login-card animate-fade-in">
        {/* Branding */}
        <div className="login-card__brand">
          <div className="top-bar__logo login-card__logo">C</div>
          <h1 className="login-card__title">ClinDoc AI</h1>
          <p className="login-card__subtitle">Ambient Clinical Documentation Assistant</p>
        </div>

        {/* Demo hint */}
        <div className="login-card__hint">
          <span className="login-card__hint-label">🔑 Demo credentials</span>
          <code>{HINT_EMAIL}</code> / <code>{HINT_PASS}</code>
        </div>

        {/* Form */}
        <form className="login-card__form" onSubmit={handleSubmit} id="login-form">
          <div className="login-field">
            <label className="login-field__label" htmlFor="login-email">
              Email
            </label>
            <input
              id="login-email"
              className="login-field__input"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="doctor@clindoc.ai"
            />
          </div>

          <div className="login-field">
            <label className="login-field__label" htmlFor="login-password">
              Password
            </label>
            <input
              id="login-password"
              className="login-field__input"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="login-card__error" role="alert">
              ⚠ {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn--primary login-card__submit"
            disabled={loading}
            id="btn-login"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="login-card__footer">
          SIH 2026 · PS #43 · Not for clinical use
        </p>
      </div>
    </div>
  );
}
