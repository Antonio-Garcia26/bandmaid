import "server-only";

import { jsonError } from "@/lib/security/responses";

export type HumanTelemetryPayload = {
  mouseMoves?: number;
  keyStrokes?: number;
  keyIntervalsAverageMs?: number;
  minKeyIntervalMs?: number;
  timeToSubmitMs?: number;
  clickCount?: number;
  curvatureCount?: number;
  isWebdriver?: boolean;
};

/**
 * Valida la telemetría de comportamiento humano enviada desde el cliente.
 * Detecta automatizaciones por Selenium/Webdriver, envíos inhumanamente veloces (<1200 ms),
 * ausencia de eventos de mouse/teclado y cadencia de tecleo sintética (<15 ms promedio).
 */
export function validateHumanInteraction(telemetry: unknown): Response | null {
  if (!telemetry || typeof telemetry !== "object" || Array.isArray(telemetry)) {
    return jsonError(
      "Comportamiento automatizado detectado. Falta telemetría de interacción humana.",
      400,
      "BOT_BEHAVIOR_DETECTED"
    );
  }

  const data = telemetry as HumanTelemetryPayload;

  // 1. Detección directa de Webdriver o navegador automatizado
  if (data.isWebdriver === true) {
    return jsonError(
      "Automatización de navegador detectada.",
      400,
      "BOT_BEHAVIOR_DETECTED"
    );
  }

  // 2. Tiempo mínimo de llenado/envío de formulario (humano no llena y envía en < 1.2 segundos)
  const timeToSubmit = Number(data.timeToSubmitMs);
  if (!Number.isFinite(timeToSubmit) || timeToSubmit < 1200) {
    return jsonError(
      "Velocidad de interacción sobrehumana detectada.",
      400,
      "BOT_BEHAVIOR_DETECTED"
    );
  }

  // 3. Verificación de actividad física mínima (movimiento de cursor o teclado)
  const mouseMoves = Number(data.mouseMoves) || 0;
  const keyStrokes = Number(data.keyStrokes) || 0;
  if (mouseMoves === 0 && keyStrokes === 0) {
    return jsonError(
      "No se registró actividad física del usuario.",
      400,
      "BOT_BEHAVIOR_DETECTED"
    );
  }

  // 4. Cadencia de tecleo: detectar inyección instantánea de texto (send_keys artificiales < 15 ms)
  const avgKeyInterval = Number(data.keyIntervalsAverageMs);
  if (keyStrokes > 1 && Number.isFinite(avgKeyInterval) && avgKeyInterval < 15) {
    return jsonError(
      "Cadencia de escritura artificial detectada.",
      400,
      "BOT_BEHAVIOR_DETECTED"
    );
  }

  return null;
}
