"use client";

import { Eye, EyeOff, KeyRound, UserRound } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { ApiError, mutateJson } from "@/lib/api-client";
import { useAuth } from "@/components/auth/AuthContext";
import { Turnstile } from "@/components/security/Turnstile";
import { Dialog } from "@/components/ui/Dialog";
import type { FanUser } from "@/lib/types";

type AuthMode = "login" | "register";
type AuthModalProps = { open: boolean; onClose: () => void; initialMode?: AuthMode };
type AuthResponse = { user: FanUser };

export function AuthModal({ open, onClose, initialMode = "login" }: AuthModalProps) {
  const auth = useAuth();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState("");
  const [turnstileAttempt, setTurnstileAttempt] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const honeypotRef = useRef<HTMLInputElement>(null);

  const turnstileKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim();
  const infrastructureReady = auth.configured === true && Boolean(turnstileKey && turnstileKey.toUpperCase() !== "PENDIENDTE");
  const title = mode === "register" ? "Tu lugar empieza aquí." : "Qué bueno verte.";

  function selectMode(nextMode: AuthMode) {
    setFormError(null);
    if (nextMode === mode) return;
    setMode(nextMode);
    setTurnstileToken("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (!infrastructureReady || !turnstileToken || submitting) return;

    setSubmitting(true);
    try {
      const response = await mutateJson<AuthResponse>(`/api/auth/${mode === "register" ? "register" : "login"}`, {
        ...(mode === "register" ? { displayName: displayName.trim() } : {}),
        email: email.trim(),
        password,
        website: honeypotRef.current?.value ?? "",
        turnstileToken,
      });
      auth.acceptUser(response.user);
      setPassword("");
      onClose();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "No se pudo conectar. Revisa tu conexión e inténtalo de nuevo.");
    } finally {
      setTurnstileToken("");
      setTurnstileAttempt((attempt) => attempt + 1);
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={title} eyebrow="O-MEI-SYU-SAMA · CLUB DE FANS" className="auth-dialog">
      <div className="auth-tabs" role="tablist" aria-label="Acceso a la comunidad">
        <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "auth-tab active" : "auth-tab"} onClick={() => selectMode("login")}>
          Iniciar sesión
        </button>
        <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "auth-tab active" : "auth-tab"} onClick={() => selectMode("register")}>
          Crear cuenta
        </button>
      </div>

      <p className="auth-intro">Un rincón hecho por fans, para fans. Esta comunidad escolar no está afiliada oficialmente a BAND-MAID.</p>

      {auth.loading && <p className="auth-loading-message" role="status">Comprobando la conexión segura…</p>}
      {auth.configured === false && (
        <div className="pending-panel" role="status">
          <KeyRound size={18} aria-hidden="true" />
          <p><strong>PENDIENDTE: conectar Firebase.</strong> El acceso estará disponible cuando se configure el servicio.</p>
        </div>
      )}
      {auth.error && (
        <div className="form-message form-message-error" role="alert">
          <p>{auth.error}</p>
          <button type="button" className="text-action" onClick={() => void auth.refresh()}>Reintentar</button>
        </div>
      )}

      <form className="auth-form" onSubmit={handleSubmit}>
        {mode === "register" && (
          <label className="field-label">
            Nombre para mostrar
            <span className="input-wrap"><UserRound size={17} aria-hidden="true" /><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} name="displayName" autoComplete="name" minLength={2} maxLength={50} required disabled={submitting} /></span>
          </label>
        )}
        <label className="field-label">
          Correo electrónico
          <input className="plain-input" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" maxLength={254} required disabled={submitting} />
        </label>
        <label className="field-label">
          Contraseña
          <span className="password-wrap">
            <input className="plain-input" type={showPassword ? "text" : "password"} name="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={mode === "register" ? 8 : 1} maxLength={128} required disabled={submitting} />
            <button className="password-toggle" type="button" onClick={() => setShowPassword((show) => !show)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}>
              {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
            </button>
          </span>
        </label>
        <input ref={honeypotRef} className="honeypot-field" name="website" type="text" autoComplete="off" tabIndex={-1} aria-hidden="true" />

        <div className="turnstile-space">
        {open && <Turnstile key={`${mode}-${turnstileAttempt}`} action={mode} onToken={setTurnstileToken} />}
        </div>
        {formError && <p className="form-message form-message-error" role="alert">{formError}</p>}

        <button className="button button-red auth-submit" type="submit" disabled={!infrastructureReady || !turnstileToken || submitting}>
          {submitting ? "Un momento…" : mode === "register" ? "Crear mi cuenta" : "Entrar a la comunidad"}
        </button>
        <p className="form-footnote">Tu cuenta es solo para esta comunidad de fans.</p>
      </form>
    </Dialog>
  );
}
