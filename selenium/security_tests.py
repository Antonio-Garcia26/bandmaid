"""Pruebas de registro y límite de solicitudes en el sitio público Band-Maid."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import BANDMAID_URL, WAIT_SECONDS

PUBLIC_ORIGIN = "https://bandmaid-abcd123.vercel.app"
MAX_RATE_LIMIT_REQUESTS = 6
CODE_PATTERN = re.compile(r"^[A-Z0-9_]{1,64}$")


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
    if (!csrfResponse.ok) {
      done({ stage: "csrf", status: csrfStatus, code: safeCode(csrfPayload) });
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

    // Identidad ficticia .invalid; se omiten captchaToken y captchaAnswer.
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
    done({ stage: "register", status: response.status, code: safeCode(payload) });
  } catch {
    done({ error: "REQUEST_FAILED", requestCount, csrfStatus, registerAttempted });
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


def _ensure_public_origin(driver) -> None:
    if not _matches_public_origin(driver.current_url):
        raise RuntimeError(
            "El navegador no está en el origen público esperado; no se enviaron solicitudes de prueba."
        )


def _safe_status(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
        return value
    return None


def _safe_code(value: object) -> str | None:
    if isinstance(value, str) and CODE_PATTERN.fullmatch(value):
        return value
    return None


def _open_registration_dialog(driver) -> None:
    wait = WebDriverWait(driver, WAIT_SECONDS)
    join_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.nav-join"))
    )
    join_button.click()
    wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'dialog.auth-dialog[open] .captcha-image')
        )
    )


def _print_register_result(result: object) -> None:
    if not isinstance(result, dict):
        print("El sitio no devolvió un resultado legible para el registro.")
        return
    if result.get("error"):
        request_count = result.get("requestCount")
        if not isinstance(request_count, int) or isinstance(request_count, bool):
            request_count = 0
        print(f"Solicitudes de prueba al API intentadas: {request_count}.")
        csrf_status = _safe_status(result.get("csrfStatus"))
        if csrf_status is not None:
            print(f"GET /api/csrf: HTTP {csrf_status}.")
        if result.get("registerAttempted"):
            print("POST /api/auth/register: se intentó; no se recibió un estado HTTP.")
        if result.get("error") == "ORIGIN_MISMATCH":
            print("El origen cambió; no se enviaron más solicitudes de prueba.")
            return
        print("No se completó la prueba de registro.")
        return

    status = _safe_status(result.get("status"))
    code = _safe_code(result.get("code")) or "sin código seguro"
    if result.get("stage") == "csrf":
        print("Solicitudes de prueba al API: 1 GET de CSRF y 0 POST de registro.")
        print(f"GET /api/csrf: HTTP {status or '—'} · {code}.")
        print("No se envió el POST de registro porque no se obtuvo CSRF.")
        return
    if result.get("stage") != "register":
        print("El sitio no devolvió un resultado reconocible para el registro.")
        return

    print("Solicitudes de prueba al API: 1 GET de CSRF y 1 POST de registro.")
    print(f"POST /api/auth/register: HTTP {status or '—'} · {code}.")
    if status == 400 and code == "CAPTCHA_INVALID":
        print("Resultado esperado: el servidor rechazó el registro por CAPTCHA omitido.")
    elif status is not None and 400 <= status <= 599:
        print("El servidor rechazó el registro; se esperaba el rechazo del CAPTCHA omitido.")
    else:
        print("No se observó el rechazo esperado por CAPTCHA; revisa el resultado del servidor.")


def _print_rate_limit_results(result: object) -> None:
    error = result.get("error") if isinstance(result, dict) else None
    results = result.get("results") if isinstance(result, dict) else result
    if not isinstance(results, list):
        print("El sitio no devolvió resultados legibles para el límite de solicitudes.")
        return

    limited_at = None
    for item in results[:MAX_RATE_LIMIT_REQUESTS]:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            number = None
        status = _safe_status(item.get("status"))
        code = _safe_code(item.get("code")) or "sin código seguro"
        print(
            f"POST /api/auth/login {number or '—'}/{MAX_RATE_LIMIT_REQUESTS}: "
            f"HTTP {status or '—'} · {code}."
        )
        if status == 429 and limited_at is None:
            limited_at = number

    attempted_count = (
        result.get("attemptedCount") if isinstance(result, dict) else len(results)
    )
    if not isinstance(attempted_count, int) or isinstance(attempted_count, bool):
        attempted_count = len(results)
    print(
        f"Solicitudes intentadas: {attempted_count} de un máximo de "
        f"{MAX_RATE_LIMIT_REQUESTS}."
    )
    if error == "ORIGIN_MISMATCH":
        print("El origen cambió; la prueba se detuvo.")
        return
    if error:
        print("La prueba se interrumpió antes de recibir todos los estados HTTP.")
        return
    if limited_at is not None:
        print(f"Primer HTTP 429 observado en la solicitud {limited_at}; la prueba se detuvo.")
    else:
        print("No apareció HTTP 429 durante las solicitudes enviadas.")


def run_public_security_test(driver, mode: str) -> object:
    """Ejecuta una prueba pública acotada de registro o de rate limit.

    `mode` debe ser `register` o `rate-limit`. El llamador conserva y cierra
    el driver; este módulo solo navega y ejecuta las solicitudes de prueba.
    """
    if mode not in {"register", "rate-limit"}:
        raise ValueError("El modo debe ser 'register' o 'rate-limit'.")
    if not _matches_public_origin(BANDMAID_URL):
        raise RuntimeError("La URL configurada no coincide con el origen público autorizado.")

    driver.get(BANDMAID_URL)
    _ensure_public_origin(driver)

    if mode == "register":
        _open_registration_dialog(driver)
        _ensure_public_origin(driver)
        result = driver.execute_async_script(REGISTER_TEST_SCRIPT, PUBLIC_ORIGIN)
        _print_register_result(result)
    else:
        result = driver.execute_async_script(
            RATE_LIMIT_TEST_SCRIPT,
            PUBLIC_ORIGIN,
            MAX_RATE_LIMIT_REQUESTS,
        )
        _print_rate_limit_results(result)

    return result
