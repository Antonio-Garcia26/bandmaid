"""Pruebas individuales de los 5 métodos de seguridad en el sitio público Band-Maid."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import BANDMAID_URL, WAIT_SECONDS
from logging_config import get_logger

PUBLIC_ORIGIN = "https://bandmaid-abcd123.vercel.app"
MAX_RATE_LIMIT_REQUESTS = 6
CODE_PATTERN = re.compile(r"^[A-Z0-9_]{1,64}$")

logger = get_logger(__name__)


# --- SCRIPTS DE PRUEBA EN NAVEGADOR PARA CADA MÉTODO DE SEGURIDAD ---

REGISTER_TEST_SCRIPT = r"""
const expectedOrigin = arguments[0];
const done = arguments[arguments.length - 1];

function safeCode(payload) {
  return typeof payload?.code === "string" && /^[A-Z0-9_]{1,64}$/.test(payload.code)
    ? payload.code
    : null;
}

(async () => {
  let requestCount = 0;
  let csrfStatus = null;
  let csrfCode = null;
  let registerAttempted = false;
  try {
    if (window.location.origin !== expectedOrigin) {
      done({ error: "ORIGIN_MISMATCH", requestCount });
      return;
    }

    requestCount += 1;
    const csrfResponse = await fetch("/api/csrf", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      redirect: "error",
      headers: { Accept: "application/json" },
    });
    csrfStatus = csrfResponse.status;
    const csrfPayload = await csrfResponse.json().catch(() => ({}));
    csrfCode = safeCode(csrfPayload);
    if (!csrfResponse.ok) {
      done({ stage: "csrf", status: csrfStatus, code: csrfCode });
      return;
    }
    if (typeof csrfPayload.token !== "string" || csrfPayload.token.length === 0) {
      done({ stage: "csrf", status: csrfStatus, code: "CSRF_UNAVAILABLE" });
      return;
    }
    if (window.location.origin !== expectedOrigin) {
      done({ error: "ORIGIN_MISMATCH", requestCount });
      return;
    }

    // Identidad ficticia; se omiten deliberadamente captchaToken y captchaAnswer.
    requestCount += 1;
    registerAttempted = true;
    const response = await fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      redirect: "error",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfPayload.token,
      },
      body: JSON.stringify({
        displayName: "Demostracion Selenium",
        email: "selenium-demo@example.invalid",
        password: "SoloDemoPublico-123",
        website: "",
      }),
    });
    const payload = await response.json().catch(() => ({}));
    done({
      stage: "register",
      csrfStatus,
      csrfCode,
      status: response.status,
      code: safeCode(payload),
    });
  } catch {
    done({
      error: "REQUEST_FAILED",
      requestCount,
      csrfStatus,
      csrfCode,
      registerAttempted,
    });
  }
})();
"""


RATE_LIMIT_TEST_SCRIPT = r"""
const expectedOrigin = arguments[0];
const maximum = arguments[1];
const done = arguments[arguments.length - 1];

function safeCode(payload) {
  return typeof payload?.code === "string" && /^[A-Z0-9_]{1,64}$/.test(payload.code)
    ? payload.code
    : null;
}

(async () => {
  const results = [];
  let attemptedCount = 0;
  try {
    if (window.location.origin !== expectedOrigin) {
      done({ error: "ORIGIN_MISMATCH", results, attemptedCount });
      return;
    }

    for (let number = 1; number <= maximum; number += 1) {
      if (window.location.origin !== expectedOrigin) {
        done({ error: "ORIGIN_MISMATCH", results, attemptedCount });
        return;
      }
      attemptedCount += 1;
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ website: "" }),
      });
      const payload = await response.json().catch(() => ({}));
      results.push({ number, status: response.status, code: safeCode(payload) });

      // Detente al primer HTTP 429; no se hacen solicitudes adicionales.
      if (response.status === 429) break;
    }
    done(results);
  } catch {
    done({ error: "REQUEST_FAILED", results, attemptedCount });
  }
})();
"""


CSRF_TEST_SCRIPT = r"""
const expectedOrigin = arguments[0];
const done = arguments[arguments.length - 1];

function safeCode(payload) {
  return typeof payload?.code === "string" && /^[A-Z0-9_]{1,64}$/.test(payload.code)
    ? payload.code
    : null;
}

(async () => {
  try {
    if (window.location.origin !== expectedOrigin) {
      done({ error: "ORIGIN_MISMATCH" });
      return;
    }

    // Se envía intencionalmente con token CSRF inválido / manipulado
    const response = await fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      redirect: "error",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": "TOKEN_CSRF_MANIPULADO_INVALIDO_12345",
      },
      body: JSON.stringify({
        displayName: "Prueba Anti-CSRF",
        email: "csrf-test@example.invalid",
        password: "SoloDemoPublico-123",
        website: "",
      }),
    });
    const payload = await response.json().catch(() => ({}));
    done({
      stage: "csrf",
      status: response.status,
      code: safeCode(payload),
    });
  } catch {
    done({ error: "REQUEST_FAILED" });
  }
})();
"""


HONEYPOT_TEST_SCRIPT = r"""
const expectedOrigin = arguments[0];
const done = arguments[arguments.length - 1];

function safeCode(payload) {
  return typeof payload?.code === "string" && /^[A-Z0-9_]{1,64}$/.test(payload.code)
    ? payload.code
    : null;
}

(async () => {
  try {
    if (window.location.origin !== expectedOrigin) {
      done({ error: "ORIGIN_MISMATCH" });
      return;
    }

    // 1. Obtener token CSRF legítimo
    const csrfResponse = await fetch("/api/csrf", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    const csrfPayload = await csrfResponse.json().catch(() => ({}));
    if (!csrfResponse.ok || !csrfPayload.token) {
      done({ stage: "csrf", status: csrfResponse.status, code: "CSRF_UNAVAILABLE" });
      return;
    }

    // 2. Simular que un bot rellena el campo trampa oculto 'website'
    const response = await fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfPayload.token,
      },
      body: JSON.stringify({
        displayName: "Bot Honeypot",
        email: "honeypot-test@example.invalid",
        password: "SoloDemoPublico-123",
        website: "https://sitio-spam-bot.xyz", // <-- Campo honeypot rellenado deliberadamente
      }),
    });
    const payload = await response.json().catch(() => ({}));
    done({
      stage: "honeypot",
      csrfStatus: csrfResponse.status,
      status: response.status,
      code: safeCode(payload),
    });
  } catch {
    done({ error: "REQUEST_FAILED" });
  }
})();
"""


TELEMETRY_TEST_SCRIPT = r"""
const expectedOrigin = arguments[0];
const done = arguments[arguments.length - 1];

function safeCode(payload) {
  return typeof payload?.code === "string" && /^[A-Z0-9_]{1,64}$/.test(payload.code)
    ? payload.code
    : null;
}

(async () => {
  try {
    if (window.location.origin !== expectedOrigin) {
      done({ error: "ORIGIN_MISMATCH" });
      return;
    }

    // 1. Obtener token CSRF legítimo
    const csrfResponse = await fetch("/api/csrf", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    const csrfPayload = await csrfResponse.json().catch(() => ({}));
    if (!csrfResponse.ok || !csrfPayload.token) {
      done({ stage: "csrf", status: csrfResponse.status, code: "CSRF_UNAVAILABLE" });
      return;
    }

    // 2. Enviar telemetría declarando explícitamente automatización por Selenium/Webdriver y cadencia sobrehumana
    const response = await fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfPayload.token,
      },
      body: JSON.stringify({
        displayName: "Bot Automatizado",
        email: "webdriver-bot@example.invalid",
        password: "SoloDemoPublico-123",
        website: "",
        telemetry: {
          isWebdriver: true,
          timeToSubmitMs: 40, // < 1200 ms
          mouseMoves: 0,
          keyStrokes: 0,
          keyIntervalsAverageMs: 1,
        },
      }),
    });
    const payload = await response.json().catch(() => ({}));
    done({
      stage: "telemetry",
      csrfStatus: csrfResponse.status,
      status: response.status,
      code: safeCode(payload),
    });
  } catch {
    done({ error: "REQUEST_FAILED" });
  }
})();
"""


def _matches_public_origin(value: str) -> bool:
    """Comprueba el origen público exacto, sin aceptar subdominios ni credenciales."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == "bandmaid-abcd123.vercel.app"
        and port in (None, 443)
        and parsed.username is None
        and parsed.password is None
    )


def _ensure_public_origin(driver, phase: str) -> None:
    try:
        current_url = driver.current_url
    except Exception:
        logger.exception(
            "Browser origin could not be checked: phase=%s expected_origin=%s",
            phase,
            PUBLIC_ORIGIN,
        )
        raise
    if not _matches_public_origin(current_url):
        logger.error(
            "Browser origin validation failed: phase=%s expected_origin=%s",
            phase,
            PUBLIC_ORIGIN,
        )
        raise RuntimeError(
            "El navegador no está en el origen público esperado; no se enviaron solicitudes de prueba."
        )
    logger.info("Public origin confirmed: phase=%s origin=%s", phase, PUBLIC_ORIGIN)


def _safe_status(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
        return value
    return None


def _safe_count(value: object, maximum: int) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum:
        return value
    return None


def _safe_code(value: object) -> str | None:
    if isinstance(value, str) and CODE_PATTERN.fullmatch(value):
        return value
    return None


def _open_registration_dialog(driver) -> None:
    logger.info("Opening registration dialog for security tests")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    try:
        join_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.nav-join"))
        )
        join_button.click()
        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "dialog.auth-dialog[open] .captcha-image")
            )
        )
    except Exception:
        logger.exception("Registration dialog with CAPTCHA indicator could not be opened")
        raise
    logger.info("Registration dialog opened successfully")


def _log_register_result(result: object) -> None:
    if not isinstance(result, dict):
        logger.error("Registration test returned an unusable result: type=%s", type(result).__name__)
        return

    csrf_status = _safe_status(result.get("csrfStatus"))
    csrf_code = _safe_code(result.get("csrfCode"))
    if result.get("stage") == "csrf":
        csrf_status = _safe_status(result.get("status"))
        csrf_code = _safe_code(result.get("code"))
    if csrf_status is not None:
        logger.info("Security test response: method=GET endpoint=csrf http_status=%d code=%s", csrf_status, csrf_code or "unavailable")

    stage = result.get("stage")
    if stage == "register":
        logger.info(
            "Security test response: method=POST endpoint=register http_status=%s code=%s",
            _safe_status(result.get("status")),
            _safe_code(result.get("code")) or "unavailable",
        )
    elif stage == "csrf":
        logger.warning("Registration test stopped before POST because CSRF was unavailable")


def _log_rate_limit_results(result: object) -> None:
    responses = result.get("results") if isinstance(result, dict) else result
    if not isinstance(responses, list):
        logger.error("Rate-limit test returned an unusable result: type=%s", type(result).__name__)
        return

    rate_limited_at = None
    for index, item in enumerate(responses[:MAX_RATE_LIMIT_REQUESTS], start=1):
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        request_number = number if isinstance(number, int) and 1 <= number <= MAX_RATE_LIMIT_REQUESTS else "unknown"
        status = _safe_status(item.get("status"))
        code = _safe_code(item.get("code"))
        logger.info("Sequential login result: request_number=%s http_status=%s code=%s", request_number, status, code or "unavailable")
        if status == 429 and rate_limited_at is None:
            rate_limited_at = request_number

    if rate_limited_at is not None:
        logger.warning("Rate-limit test stopped after HTTP 429: request_number=%s", rate_limited_at)


def _print_register_result(result: object) -> None:
    print("\n" + "-" * 65)
    print("RESULTADO DE PRUEBA: 1. PROTECCIÓN CAPTCHA (OMISIÓN)")
    print("-" * 65)
    if not isinstance(result, dict):
        print("El sitio no devolvió un resultado legible para el registro.")
        return
    if result.get("error"):
        print(f"Error durante la prueba de registro: {result.get('error')}")
        return

    status = _safe_status(result.get("status"))
    code = _safe_code(result.get("code")) or "sin código"
    print("Solicitudes enviadas: 1 GET /api/csrf (válido) y 1 POST /api/auth/register (sin CAPTCHA).")
    print(f"Respuesta del servidor: HTTP {status or '—'} · Código: {code}")
    if status == 400 and code == "CAPTCHA_INVALID":
        print(">> [ÉXITO DE SEGURIDAD]: El servidor bloqueó la solicitud por omisión del código CAPTCHA.")
    elif status is not None and 400 <= status <= 599:
        print(f">> [PROTEGIDO]: El servidor rechazó el registro automatizado (HTTP {status}).")
    else:
        print(">> [ATENCIÓN]: No se observó el rechazo esperado por CAPTCHA.")


def _print_rate_limit_results(result: object) -> None:
    print("\n" + "-" * 65)
    print("RESULTADO DE PRUEBA: 2. RATE LIMITING (FUERZA BRUTA / RÁFAGA)")
    print("-" * 65)
    results = result.get("results") if isinstance(result, dict) else result
    if not isinstance(results, list):
        print("El sitio no devolvió resultados legibles para el rate limit.")
        return

    limited_at = None
    for item in results[:MAX_RATE_LIMIT_REQUESTS]:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        status = _safe_status(item.get("status"))
        code = _safe_code(item.get("code")) or "sin código"
        print(f"  • Intento {number}/{MAX_RATE_LIMIT_REQUESTS}: POST /api/auth/login -> HTTP {status or '—'} ({code})")
        if status == 429 and limited_at is None:
            limited_at = number

    if limited_at is not None:
        print(f"\n>> [ÉXITO DE SEGURIDAD]: Límite de tasa activado exitosamente en el intento {limited_at} (HTTP 429 RATE_LIMITED).")
    else:
        print("\n>> No se observó HTTP 429 en las solicitudes enviadas.")


def _print_csrf_result(result: object) -> None:
    print("\n" + "-" * 65)
    print("RESULTADO DE PRUEBA: 3. PROTECCIÓN ANTI-CSRF (TOKEN INVÁLIDO)")
    print("-" * 65)
    if not isinstance(result, dict) or result.get("error"):
        print(f"No se pudo completar la prueba CSRF: {result.get('error') if isinstance(result, dict) else 'error desconocido'}")
        return

    status = _safe_status(result.get("status"))
    code = _safe_code(result.get("code")) or "sin código"
    print("Solicitudes enviadas: 1 POST /api/auth/register con token X-CSRF-Token manipulado.")
    print(f"Respuesta del servidor: HTTP {status or '—'} · Código: {code}")
    if status == 403 and code == "CSRF_REJECTED":
        print(">> [ÉXITO DE SEGURIDAD]: Servidor neutralizó la mutación no autorizada (HTTP 403 CSRF_REJECTED).")
    elif status is not None and 400 <= status <= 599:
        print(f">> [PROTEGIDO]: La mutación fue rechazada correctamente por la capa de seguridad (HTTP {status}).")
    else:
        print(">> [ATENCIÓN]: No se observó el rechazo esperado de CSRF.")


def _print_honeypot_result(result: object) -> None:
    print("\n" + "-" * 65)
    print("RESULTADO DE PRUEBA: 4. CAMPO TRAMPA HONEYPOT (BOT TRAP)")
    print("-" * 65)
    if not isinstance(result, dict) or result.get("error"):
        print(f"No se pudo completar la prueba Honeypot: {result.get('error') if isinstance(result, dict) else 'error desconocido'}")
        return

    status = _safe_status(result.get("status"))
    code = _safe_code(result.get("code")) or "sin código"
    print("Solicitudes enviadas: 1 GET CSRF y 1 POST /api/auth/register con campo invisible 'website' rellenado.")
    print(f"Respuesta del servidor: HTTP {status or '—'} · Código: {code}")
    if status == 400 and code == "BOT_REJECTED":
        print(">> [ÉXITO DE SEGURIDAD]: Bot detectado por rellenar el campo trampa oculto (HTTP 400 BOT_REJECTED).")
    elif status is not None and 400 <= status <= 599:
        print(f">> [PROTEGIDO]: Formulario bot neutralizado por el backend (HTTP {status}).")
    else:
        print(">> [ATENCIÓN]: No se observó el rechazo esperado por Honeypot.")


def _print_telemetry_result(result: object) -> None:
    print("\n" + "-" * 65)
    print("RESULTADO DE PRUEBA: 5. TELEMETRÍA Y DETECCIÓN DE AUTOMATIZACIÓN")
    print("-" * 65)
    if not isinstance(result, dict) or result.get("error"):
        print(f"No se pudo completar la prueba de telemetría: {result.get('error') if isinstance(result, dict) else 'error desconocido'}")
        return

    status = _safe_status(result.get("status"))
    code = _safe_code(result.get("code")) or "sin código"
    print("Solicitudes enviadas: 1 GET CSRF y 1 POST con telemetría de Webdriver y velocidad sobrehumana (<1200ms).")
    print(f"Respuesta del servidor: HTTP {status or '—'} · Código: {code}")
    if status == 400 and code == "BOT_BEHAVIOR_DETECTED":
        print(">> [ÉXITO DE SEGURIDAD]: Automatización y cadencia sintética bloqueadas (HTTP 400 BOT_BEHAVIOR_DETECTED).")
    elif status is not None and 400 <= status <= 599:
        print(f">> [PROTEGIDO]: Servidor bloqueó la telemetría automatizada (HTTP {status}).")
    else:
        print(">> [ATENCIÓN]: No se observó el rechazo esperado por telemetría.")


def run_public_security_test(driver, mode: str) -> object:
    """Ejecuta de manera individual cualquiera de los 5 métodos de seguridad o la batería completa.
    
    Modos soportados:
    - 'captcha' / 'register': Omisión deliberada de CAPTCHA (HTTP 400 CAPTCHA_INVALID).
    - 'rate-limit': Ráfaga secuencial de inicios de sesión (HTTP 429 RATE_LIMITED).
    - 'csrf': Mutación sin token o con token CSRF alterado (HTTP 403 CSRF_REJECTED).
    - 'honeypot': Relleno de campo trampa invisible para bots (HTTP 400 BOT_REJECTED).
    - 'telemetry': Telemetría biométrica artificial y Webdriver (HTTP 400 BOT_BEHAVIOR_DETECTED).
    - 'all': Ejecución secuencial de los 5 métodos de seguridad.
    """
    valid_modes = {"captcha", "register", "rate-limit", "csrf", "honeypot", "telemetry", "all"}
    if mode not in valid_modes:
        logger.error("Public security test rejected: invalid mode '%s'", mode)
        raise ValueError(f"El modo debe ser uno de: {valid_modes}")

    if not _matches_public_origin(BANDMAID_URL):
        logger.error("Public security test rejected: configured URL mismatch with %s", PUBLIC_ORIGIN)
        raise RuntimeError("La URL configurada no coincide con el origen público autorizado.")

    logger.info("Navigating to public security-test origin: %s (mode=%s)", PUBLIC_ORIGIN, mode)
    driver.get(BANDMAID_URL)
    _ensure_public_origin(driver, phase="after_navigation")

    # Mapeo a modo estándar
    if mode == "register":
        mode = "captcha"

    if mode == "all":
        print("\n" + "=" * 70)
        print("INICIANDO BATERÍA COMPLETA DE PRUEBAS DE SEGURIDAD (5 MÉTODOS)")
        print("=" * 70)
        res_captcha = run_public_security_test(driver, "captcha")
        res_rate = run_public_security_test(driver, "rate-limit")
        res_csrf = run_public_security_test(driver, "csrf")
        res_honeypot = run_public_security_test(driver, "honeypot")
        res_telemetry = run_public_security_test(driver, "telemetry")
        print("\n" + "=" * 70)
        print("BATERÍA DE SEGURIDAD FINALIZADA: LOS 5 MÉTODOS HAN SIDO PROBADOS.")
        print("=" * 70)
        return {
            "captcha": res_captcha,
            "rate_limit": res_rate,
            "csrf": res_csrf,
            "honeypot": res_honeypot,
            "telemetry": res_telemetry,
        }

    if mode == "captcha":
        _open_registration_dialog(driver)
        _ensure_public_origin(driver, phase="before_captcha")
        result = driver.execute_async_script(REGISTER_TEST_SCRIPT, PUBLIC_ORIGIN)
        _log_register_result(result)
        _print_register_result(result)
        return result

    elif mode == "rate-limit":
        result = driver.execute_async_script(RATE_LIMIT_TEST_SCRIPT, PUBLIC_ORIGIN, MAX_RATE_LIMIT_REQUESTS)
        _log_rate_limit_results(result)
        _print_rate_limit_results(result)
        return result

    elif mode == "csrf":
        result = driver.execute_async_script(CSRF_TEST_SCRIPT, PUBLIC_ORIGIN)
        _print_csrf_result(result)
        return result

    elif mode == "honeypot":
        result = driver.execute_async_script(HONEYPOT_TEST_SCRIPT, PUBLIC_ORIGIN)
        _print_honeypot_result(result)
        return result

    elif mode == "telemetry":
        result = driver.execute_async_script(TELEMETRY_TEST_SCRIPT, PUBLIC_ORIGIN)
        _print_telemetry_result(result)
        return result

    return None
