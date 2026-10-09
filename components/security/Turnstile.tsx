"use client";

import Script from "next/script";
import { useCallback, useEffect, useRef, useState } from "react";

type TurnstileAction = "register" | "login" | "create-post";
type TurnstileOptions = {
  sitekey: string;
  action: TurnstileAction;
  theme?: "light" | "dark" | "auto";
  callback: (token: string) => void;
  "expired-callback": () => void;
  "error-callback": () => void;
};

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, options: TurnstileOptions) => string;
      remove: (widgetId: string) => void;
    };
  }
}

type TurnstileProps = {
  action: TurnstileAction;
  onToken: (token: string) => void;
};

export function Turnstile({ action, onToken }: TurnstileProps) {
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim();
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const onTokenRef = useRef(onToken);
  const [widgetState, setWidgetState] = useState<"loading" | "ready" | "verified" | "error" | "script-error">("loading");

  useEffect(() => {
    onTokenRef.current = onToken;
  }, [onToken]);

  const renderWidget = useCallback(() => {
    if (!siteKey || !window.turnstile || !containerRef.current || widgetId.current) return;
    try {
      widgetId.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        action,
        theme: "light",
        callback: (token) => {
          setWidgetState("verified");
          onTokenRef.current(token);
        },
        "expired-callback": () => {
          setWidgetState("ready");
          onTokenRef.current("");
        },
        "error-callback": () => {
          setWidgetState("error");
          onTokenRef.current("");
        },
      });
      setWidgetState("ready");
    } catch {
      setWidgetState("error");
      onTokenRef.current("");
    }
  }, [action, siteKey]);

  useEffect(() => {
    if (typeof window !== "undefined" && window.turnstile) {
      queueMicrotask(renderWidget);
    }
  }, [renderWidget]);

  const retryWidget = useCallback(() => {
    if (!window.turnstile) {
      setWidgetState("script-error");
      return;
    }
    if (widgetId.current) window.turnstile.remove(widgetId.current);
    widgetId.current = null;
    if (containerRef.current) containerRef.current.replaceChildren();
    setWidgetState("loading");
    onTokenRef.current("");
    window.requestAnimationFrame(renderWidget);
  }, [renderWidget]);

  useEffect(() => {
    return () => {
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
    };
  }, []);

  if (!siteKey || siteKey.toUpperCase() === "PENDIENDTE") {
    return <p className="pending-note" role="status">PENDIENDTE: configurar Turnstile para continuar.</p>;
  }

  return (
    <div className="turnstile-wrap">
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
        strategy="afterInteractive"
        onReady={renderWidget}
        onError={() => setWidgetState("script-error")}
      />
      <div className="turnstile-slot" ref={containerRef} aria-label="Verificación de seguridad" />
      {widgetState === "loading" && <p className="turnstile-status" role="status">Cargando verificación segura…</p>}
      {widgetState === "ready" && <p className="turnstile-status" role="status">Completa la verificación para continuar.</p>}
      {widgetState === "verified" && <p className="turnstile-status turnstile-verified" role="status">Verificación completada.</p>}
      {(widgetState === "error" || widgetState === "script-error") && (
        <div className="turnstile-error" role="status">
          <p>{widgetState === "script-error" ? "No se pudo cargar Turnstile. Actualiza la página e inténtalo de nuevo." : "La verificación no se completó."}</p>
          {widgetState === "error" && <button className="text-action" type="button" onClick={retryWidget}>Reintentar verificación</button>}
        </div>
      )}
    </div>
  );
}
