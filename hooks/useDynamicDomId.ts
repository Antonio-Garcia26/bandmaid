"use client";

import { useId, useCallback, useSyncExternalStore } from "react";

// Semilla aleatoria por sesión de usuario en el cliente
let globalSessionSeed = "";
function getGlobalSessionSeed(): string {
  if (!globalSessionSeed && typeof window !== "undefined") {
    globalSessionSeed = Math.random().toString(36).substring(2, 8);
  }
  return globalSessionSeed;
}

const emptySubscribe = () => () => {};

/**
 * Hook para generar IDs y clases dinámicos que cambian por sesión/renderizado,
 * evitando que scripts de scraping con selectores estáticos fijos (ej. By.ID("email"))
 * puedan ubicar elementos sin analizar el árbol dinámico del DOM.
 * 
 * Usa useSyncExternalStore para garantizar consistencia entre SSR e hidratación
 * sin provocar renders en cascada ni advertencias del compilador de React.
 */
export function useDynamicDomId(scope = "field") {
  const reactId = useId().replace(/[:]/g, "");

  // Client snapshot provee la semilla aleatoria; server snapshot provee cadena vacía para evitar mismatch
  const sessionSeed = useSyncExternalStore(
    emptySubscribe,
    getGlobalSessionSeed,
    () => ""
  );

  const getId = useCallback(
    (name: string) => {
      const seed = sessionSeed || reactId;
      return `${scope}-${name}-${seed}`;
    },
    [scope, sessionSeed, reactId]
  );

  const getClass = useCallback(
    (baseClass: string, identifier?: string) => {
      if (!sessionSeed) return baseClass;
      const dyn = identifier ? `_dyn_${identifier}_${sessionSeed}` : `_dyn_${sessionSeed}`;
      return `${baseClass} ${dyn}`;
    },
    [sessionSeed]
  );

  return { getId, getClass, sessionSeed };
}
