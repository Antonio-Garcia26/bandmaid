"use client";

import { useEffect, useRef, useState } from "react";
import { RotateCw, ShieldCheck, AlertCircle } from "lucide-react";
import { ApiError, requestJson } from "@/lib/api-client";

type CaptchaApiResponse = {
  captchaToken: string;
  captchaImage: string;
  expiresInSeconds: number;
};

export type CaptchaValue = {
  token: string;
  answer: string;
  isFilled: boolean;
};

type TextCaptchaProps = {
  onChange: (value: CaptchaValue) => void;
  disabled?: boolean;
  refreshTrigger?: number;
};

function getErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.code === "RATE_LIMITED") {
    return "Demasiadas recargas seguidas. Espera unos segundos antes de pedir otra.";
  }
  return "No se pudo cargar el código de seguridad. Pulsa para reintentar.";
}

export function TextCaptcha({ onChange, disabled = false, refreshTrigger = 0 }: TextCaptchaProps) {
  const [captchaData, setCaptchaData] = useState<CaptchaApiResponse | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // Carga inicial y actualización al cambiar refreshTrigger
  useEffect(() => {
    let active = true;

    async function loadChallenge() {
      try {
        const response = await requestJson<CaptchaApiResponse>("/api/auth/captcha");
        if (!active) return;
        setCaptchaData(response);
        setAnswer("");
        setError(null);
        setLoading(false);
        onChangeRef.current({ token: response.captchaToken, answer: "", isFilled: false });
      } catch (err) {
        if (!active) return;
        setError(getErrorMessage(err));
        setCaptchaData(null);
        setAnswer("");
        setLoading(false);
        onChangeRef.current({ token: "", answer: "", isFilled: false });
      }
    }

    void loadChallenge();

    return () => {
      active = false;
    };
  }, [refreshTrigger]);

  async function handleManualRefresh() {
    setLoading(true);
    setError(null);
    setAnswer("");
    try {
      const response = await requestJson<CaptchaApiResponse>("/api/auth/captcha");
      setCaptchaData(response);
      onChangeRef.current({ token: response.captchaToken, answer: "", isFilled: false });
    } catch (err) {
      setError(getErrorMessage(err));
      // Si ya teníamos una imagen previa, la conservamos para que el usuario no vea un recuadro vacío
      onChangeRef.current({ token: "", answer: "", isFilled: false });
    } finally {
      setLoading(false);
    }
  }

  function handleAnswerChange(val: string) {
    const cleaned = val.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
    setAnswer(cleaned);
    onChangeRef.current({
      token: captchaData?.captchaToken ?? "",
      answer: cleaned,
      isFilled: cleaned.length >= 4,
    });
  }

  return (
    <div className="captcha-block" role="group" aria-label="Verificación de seguridad visual">
      <div className="captcha-header">
        <label htmlFor="captcha-code-input" className="captcha-label">
          <ShieldCheck size={16} aria-hidden="true" className="captcha-shield-icon" />
          <span>Verificación de seguridad</span>
        </label>
      </div>

      <p className="captcha-explanation">
        Escribe los caracteres que ves en la imagen:
      </p>

      <div className="captcha-card">
        <div className="captcha-image-wrapper">
          {loading ? (
            <div className="captcha-skeleton" aria-label="Cargando código borroso…">
              <RotateCw className="captcha-spin" size={20} aria-hidden="true" />
              <span>Generando código…</span>
            </div>
          ) : error && !captchaData ? (
            <div className="captcha-error-display" role="alert">
              <AlertCircle size={18} aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : captchaData?.captchaImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={captchaData.captchaImage}
              alt="Código de caracteres borrosos y distorsionados para verificación de seguridad"
              className="captcha-image"
              width={260}
              height={76}
            />
          ) : null}
        </div>

        <button
          type="button"
          onClick={() => void handleManualRefresh()}
          className="captcha-refresh-btn"
          disabled={loading || disabled}
          aria-label="Generar un nuevo código si este no se puede leer"
          title="Generar nueva imagen si el texto no es claro"
        >
          <RotateCw size={16} className={loading ? "captcha-spin" : ""} aria-hidden="true" />
          <span>Nueva<br />imagen</span>
        </button>
      </div>

      {error && captchaData && (
        <p className="captcha-error-inline" role="alert">
          <AlertCircle size={13} aria-hidden="true" />
          <span>{error}</span>
        </p>
      )}

      <div className="captcha-input-section">
        <input
          id="captcha-code-input"
          type="text"
          name="captchaAnswer"
          value={answer}
          onChange={(e) => handleAnswerChange(e.target.value)}
          placeholder="Ingrese el código"
          className="plain-input captcha-input"
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={8}
          disabled={loading || disabled}
          required
        />
        {answer.length > 0 && (
          <p className="captcha-hint">
            {answer.length} / 5 caracteres
          </p>
        )}
      </div>
    </div>
  );
}
