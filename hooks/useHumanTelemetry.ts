"use client";

import { useEffect, useRef, useCallback } from "react";

export type HumanTelemetry = {
  mouseMoves: number;
  keyStrokes: number;
  keyIntervalsAverageMs: number;
  minKeyIntervalMs: number;
  timeToSubmitMs: number;
  clickCount: number;
  curvatureCount: number;
  isWebdriver: boolean;
};

/**
 * Hook para recolectar telemetría de interacción física del usuario.
 * Detecta movimientos no lineales de cursor, cadencia de teclado,
 * tiempo de interacción y banderas de automatización (Selenium / Webdriver).
 */
export function useHumanTelemetry(active = true) {
  const mountTimeRef = useRef<number | null>(null);
  const mouseMovesRef = useRef<number>(0);
  const keyStrokesRef = useRef<number>(0);
  const clickCountRef = useRef<number>(0);
  const keyTimestampsRef = useRef<number[]>([]);
  const lastPointerRef = useRef<{ x: number; y: number } | null>(null);
  const lastVectorRef = useRef<{ dx: number; dy: number } | null>(null);
  const curvatureCountRef = useRef<number>(0);

  useEffect(() => {
    if (!active) return;

    mountTimeRef.current = Date.now();
    mouseMovesRef.current = 0;
    keyStrokesRef.current = 0;
    clickCountRef.current = 0;
    keyTimestampsRef.current = [];
    lastPointerRef.current = null;
    lastVectorRef.current = null;
    curvatureCountRef.current = 0;

    const handlePointerMove = (e: MouseEvent | PointerEvent) => {
      mouseMovesRef.current += 1;
      const current = { x: e.clientX, y: e.clientY };

      if (lastPointerRef.current) {
        const dx = current.x - lastPointerRef.current.x;
        const dy = current.y - lastPointerRef.current.y;

        if (lastVectorRef.current) {
          // Detectar trayectoria curva vs saltos rectos o instantáneos
          const dot = dx * lastVectorRef.current.dx + dy * lastVectorRef.current.dy;
          const mag1 = Math.hypot(dx, dy);
          const mag2 = Math.hypot(lastVectorRef.current.dx, lastVectorRef.current.dy);

          if (mag1 > 2 && mag2 > 2) {
            const cosTheta = dot / (mag1 * mag2);
            if (cosTheta < 0.96) {
              curvatureCountRef.current += 1;
            }
          }
        }
        lastVectorRef.current = { dx, dy };
      }
      lastPointerRef.current = current;
    };

    const handleKeyDown = () => {
      keyStrokesRef.current += 1;
      keyTimestampsRef.current.push(Date.now());
      if (keyTimestampsRef.current.length > 60) {
        keyTimestampsRef.current.shift();
      }
    };

    const handleClick = () => {
      clickCountRef.current += 1;
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    window.addEventListener("mousemove", handlePointerMove, { passive: true });
    window.addEventListener("keydown", handleKeyDown, { passive: true });
    window.addEventListener("click", handleClick, { passive: true });

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("mousemove", handlePointerMove);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("click", handleClick);
    };
  }, [active]);

  const getTelemetry = useCallback((): HumanTelemetry => {
    const now = Date.now();
    const timeToSubmitMs = now - (mountTimeRef.current ?? now);

    // Calcular intervalos entre pulsaciones
    const timestamps = keyTimestampsRef.current;
    const intervals: number[] = [];
    for (let i = 1; i < timestamps.length; i++) {
      intervals.push(timestamps[i] - timestamps[i - 1]);
    }

    const keyIntervalsAverageMs =
      intervals.length > 0
        ? Math.round(intervals.reduce((a, b) => a + b, 0) / intervals.length)
        : 0;

    const minKeyIntervalMs =
      intervals.length > 0 ? Math.min(...intervals) : 0;

    // Comprobar indicadores de automatización del navegador
    let isWebdriver = false;
    if (typeof window !== "undefined") {
      const nav = window.navigator as unknown as { webdriver?: boolean };
      const win = window as unknown as Record<string, unknown>;
      const doc = document as unknown as Record<string, unknown>;

      isWebdriver = Boolean(
        nav.webdriver === true ||
          win._phantom ||
          win.__nightmare ||
          win.callPhantom ||
          doc.__selenium_unwrapped ||
          doc.__webdriver_evaluate ||
          doc.__driver_evaluate
      );
    }

    return {
      mouseMoves: mouseMovesRef.current,
      keyStrokes: keyStrokesRef.current,
      keyIntervalsAverageMs,
      minKeyIntervalMs,
      timeToSubmitMs,
      clickCount: clickCountRef.current,
      curvatureCount: curvatureCountRef.current,
      isWebdriver,
    };
  }, []);

  return { getTelemetry };
}
