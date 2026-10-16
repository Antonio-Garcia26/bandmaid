"""Pruebas de registro y límite de solicitudes en el sitio público Band-Maid."""

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
    logger.info(
        "Public origin confirmed: phase=%s origin=%s",
        phase,
        PUBLIC_ORIGIN,
    )


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
    logger.info("Opening registration dialog for CAPTCHA omission test")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    try:
        join_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.nav-join"))
        )
        join_button.click()
        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'dialog.auth-dialog[open] .captcha-image')
            )
        )
    except Exception:
        logger.exception("Registration dialog with CAPTCHA indicator could not be opened")
        raise
    logger.info("Registration dialog opened; CAPTCHA indicator is visible")


def _log_register_result(result: object) -> None:
    if not isinstance(result, dict):
        logger.error(
            "Registration test returned an unusable result: result_type=%s",
            type(result).__name__,
        )
        return

    csrf_status = _safe_status(result.get("csrfStatus"))
    csrf_code = _safe_code(result.get("csrfCode"))
    if result.get("stage") == "csrf":
        csrf_status = _safe_status(result.get("status"))
        csrf_code = _safe_code(result.get("code"))
    if csrf_status is not None:
        logger.info(
            "Security test response: method=GET endpoint=csrf http_status=%d response_code=%s",
            csrf_status,
            csrf_code or "unavailable",
        )

    stage = result.get("stage")
    if stage == "register":
        logger.info(
            "Security test response: method=POST endpoint=register http_status=%s response_code=%s",
            _safe_status(result.get("status")),
            _safe_code(result.get("code")) or "unavailable",
        )
    elif stage == "csrf":
        logger.warning("Registration test stopped before POST because CSRF was unavailable")

    error = result.get("error")
    if error == "ORIGIN_MISMATCH" or error == "REQUEST_FAILED":
        request_count = _safe_count(result.get("requestCount"), 2)
        logger.error(
            "Registration test script reported an error: code=%s request_count=%s register_attempted=%s",
            error,
            request_count if request_count is not None else "unknown",
            result.get("registerAttempted") is True,
        )
    elif stage not in ("csrf", "register"):
        logger.error("Registration test returned an unrecognized result stage")


def _log_rate_limit_results(result: object) -> None:
    error = result.get("error") if isinstance(result, dict) else None
    responses = result.get("results") if isinstance(result, dict) else result
    if not isinstance(responses, list):
        logger.error(
            "Rate-limit test returned an unusable result: result_type=%s",
            type(result).__name__,
        )
        return

    rate_limited_at = None
    for index, item in enumerate(responses[:MAX_RATE_LIMIT_REQUESTS], start=1):
        if not isinstance(item, dict):
            logger.warning("Rate-limit result entry skipped: sequence_position=%d", index)
            continue
        number = item.get("number")
        request_number = (
            number
            if isinstance(number, int)
            and not isinstance(number, bool)
            and 1 <= number <= MAX_RATE_LIMIT_REQUESTS
            else "unknown"
        )
        status = _safe_status(item.get("status"))
        code = _safe_code(item.get("code"))
        logger.info(
            "Sequential login result: request_number=%s http_status=%s response_code=%s",
            request_number,
            status,
            code or "unavailable",
        )
        if status == 429 and rate_limited_at is None:
            rate_limited_at = request_number
            logger.warning(
                "HTTP 429 observed during rate-limit test: request_number=%s",
                request_number,
            )

    if rate_limited_at is not None:
        logger.warning(
            "Rate-limit test stopped after HTTP 429: request_number=%s",
            rate_limited_at,
        )

    if error == "ORIGIN_MISMATCH" or error == "REQUEST_FAILED":
        attempted_count = _safe_count(
            result.get("attemptedCount"),
            MAX_RATE_LIMIT_REQUESTS,
        )
        logger.error(
            "Rate-limit test script reported an error: code=%s attempted_requests=%d",
            error,
            attempted_count
            if attempted_count is not None
            else min(len(responses), MAX_RATE_LIMIT_REQUESTS),
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
    mode_label = (
        mode
        if isinstance(mode, str) and mode in ("register", "rate-limit")
        else "invalid"
    )
    logger.info("Public security test started: mode=%s", mode_label)
    if mode not in {"register", "rate-limit"}:
        logger.error("Public security test rejected: invalid mode")
        raise ValueError("El modo debe ser 'register' o 'rate-limit'.")
    if not _matches_public_origin(BANDMAID_URL):
        logger.error(
            "Public security test rejected: configured URL does not match expected origin=%s",
            PUBLIC_ORIGIN,
        )
        raise RuntimeError("La URL configurada no coincide con el origen público autorizado.")

    logger.info("Navigating to public security-test origin: origin=%s", PUBLIC_ORIGIN)
    try:
        driver.get(BANDMAID_URL)
    except Exception:
        logger.exception(
            "Security-test navigation failed: mode=%s expected_origin=%s",
            mode,
            PUBLIC_ORIGIN,
        )
        raise
    _ensure_public_origin(driver, phase="after_navigation")

    if mode == "register":
        _open_registration_dialog(driver)
        _ensure_public_origin(driver, phase="before_register")
        try:
            result = driver.execute_async_script(REGISTER_TEST_SCRIPT, PUBLIC_ORIGIN)
        except Exception:
            logger.exception(
                "Registration test script execution failed: endpoint=register"
            )
            raise
        _log_register_result(result)
        _print_register_result(result)
    else:
        logger.info(
            "Starting sequential login checks: maximum_requests=%d",
            MAX_RATE_LIMIT_REQUESTS,
        )
        try:
            result = driver.execute_async_script(
                RATE_LIMIT_TEST_SCRIPT,
                PUBLIC_ORIGIN,
                MAX_RATE_LIMIT_REQUESTS,
            )
        except Exception:
            logger.exception(
                "Rate-limit test script execution failed: endpoint=login maximum_requests=%d",
                MAX_RATE_LIMIT_REQUESTS,
            )
            raise
        _log_rate_limit_results(result)
        _print_rate_limit_results(result)

    return result
