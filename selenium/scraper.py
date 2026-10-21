"""Extracción de fichas públicas de la página de Band-Maid."""

from __future__ import annotations

import re
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from config import (
    BANDMAID_SELECTORS,
    BANDMAID_URL,
)
from logging_config import get_logger

logger = get_logger(__name__)


class HumanVerificationDetected(RuntimeError):
    """Señaliza un desafío que requiere revisión manual y detención."""

    def __init__(self, message, records=None, pages_processed=0):
        super().__init__(message)
        self.records = records or []
        self.pages_processed = pages_processed


def clean_text(value):
    """Normaliza espacios y convierte textos vacíos en None."""
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or None


def detectar_desafio(driver):
    """Detecta señales comunes de CAPTCHA, bloqueo o verificación humana."""
    try:
        title = (driver.title or "").casefold()
        body = driver.find_element(By.TAG_NAME, "body").text.casefold()
    except Exception:
        logger.exception(
            "Challenge detection could not inspect the page title or body; "
            "continuing with no text-based challenge detected"
        )
        return False

    indicators = (
        "captcha",
        "access denied",
        "verify you are human",
        "human verification",
        "checking your browser",
        "security check",
        "too many requests",
        "rate limit exceeded",
        "one more step",
        "attention required",
        "you have been blocked",
    )
    if any(term in title or term in body for term in indicators):
        return True

    challenge_selectors = (
        'iframe[src*="captcha"]',
        '[id*="captcha"]',
        '[class*="captcha"]',
    )
    return any(driver.find_elements(By.CSS_SELECTOR, selector) for selector in challenge_selectors)


def manejar_barrera_etica(driver, records=None, pages_processed=0, permitir_continuar=True):
    """Manejo Ético de Barreras: Si se detecta un CAPTCHA o desafío de acceso,
    se pausa respetuosamente solicitando la intervención del operador humano
    para continuar con la extracción."""
    if not detectar_desafio(driver):
        return True

    logger.warning(
        "Manejo Ético: Desafío de verificación humana detectado. Pausando script para intervención manual (pages=%d, records=%d)",
        pages_processed,
        len(records) if records else 0,
    )
    print("\n" + "=" * 75)
    print(" [MANEJO ÉTICO DE BARRERAS - INTERVENCIÓN MANUAL REQUERIDA]")
    print(" Se ha identificado un límite de acceso en el sitio (CAPTCHA / Verificación).")
    print(" Por respeto a las políticas del sitio y límites éticos, el script se")
    print(" pausa respetuosamente para que el operador humano intervenga en el navegador.")
    print("=" * 75)

    if not permitir_continuar:
        raise HumanVerificationDetected(
            "Desafío de acceso detectado; extracción detenida conforme a política ética.",
            records=records,
            pages_processed=pages_processed,
        )

    while True:
        try:
            resp = input(
                "\nPor favor complete el CAPTCHA en la ventana de Selenium y presione ENTER para continuar (o 'q' para cancelar): "
            ).strip().lower()
        except EOFError:
            resp = "q"

        if resp in {"q", "cancelar", "salir"}:
            logger.info("Human operator cancelled challenge resolution; stopping extraction")
            raise HumanVerificationDetected(
                "Extracción cancelada por el operador durante el desafío de verificación.",
                records=records,
                pages_processed=pages_processed,
            )

        # Verificar si el desafío ya fue resuelto
        if not detectar_desafio(driver):
            logger.info("Human operator successfully cleared challenge. Resuming dynamic navigation.")
            print(">> Verificación humana superada exitosamente. Continuando extracción dinámicamente...")
            return True
        else:
            print(">> El desafío aún se detecta activo en el navegador. Por favor resuélvalo antes de continuar.")


def _ensure_no_challenge(driver, records=None, pages_processed=0):
    manejar_barrera_etica(driver, records=records, pages_processed=pages_processed, permitir_continuar=True)



def extraer_miembros(driver, wait):
    """Lee las cinco fichas públicas de miembros disponibles en #miembros."""
    logger.info("Starting navigation to configured public page: url=%s", BANDMAID_URL)
    try:
        driver.get(BANDMAID_URL)
    except Exception:
        logger.exception("Navigation to configured public page failed")
        raise
    logger.info("Configured public page loaded")
    _ensure_no_challenge(driver)
    logger.info(
        "Starting navigation through members anchor: selector=%s",
        BANDMAID_SELECTORS["members_link"],
    )
    try:
        members_link = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, BANDMAID_SELECTORS["members_link"])
            )
        )
        old_url = driver.current_url
        members_link.click()
        wait.until(EC.url_changes(old_url))
        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, BANDMAID_SELECTORS["members_section"])
            )
        )
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, BANDMAID_SELECTORS["cards"])
            )
        )
    except Exception:
        logger.exception(
            "Members anchor navigation failed: anchor_selector=%s section_selector=%s",
            BANDMAID_SELECTORS["members_link"],
            BANDMAID_SELECTORS["members_section"],
        )
        raise
    logger.info(
        "Members anchor navigation completed: section_selector=%s",
        BANDMAID_SELECTORS["members_section"],
    )
    _ensure_no_challenge(driver)
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, BANDMAID_SELECTORS["cards"])
    except Exception:
        logger.exception(
            "Member card lookup failed: selector=%s",
            BANDMAID_SELECTORS["cards"],
        )
        raise
    logger.info(
        "Member cards found: count=%d selector=%s",
        len(cards),
        BANDMAID_SELECTORS["cards"],
    )
    records = []
    skipped_cards = 0

    try:
        for card in cards:
            try:
                name = clean_text(
                    card.find_element(By.CSS_SELECTOR, BANDMAID_SELECTORS["name"]).text
                )
                role = clean_text(
                    card.find_element(By.CSS_SELECTOR, BANDMAID_SELECTORS["role"]).text
                )
                image_alt = clean_text(
                    card.find_element(
                        By.CSS_SELECTOR,
                        BANDMAID_SELECTORS["image"],
                    ).get_attribute("alt")
                )
            except (NoSuchElementException, StaleElementReferenceException):
                skipped_cards += 1
                continue
            records.append(
                {
                    "name": name,
                    "role": role,
                    "image_alt": image_alt,
                    "page": 1,
                    "url": driver.current_url,
                }
            )
    except Exception:
        logger.exception(
            "Member card extraction failed: cards_found=%d records_collected=%d cards_skipped=%d",
            len(cards),
            len(records),
            skipped_cards,
        )
        raise

    logger.info(
        "Member card extraction completed: records_collected=%d cards_skipped=%d cards_found=%d",
        len(records),
        skipped_cards,
        len(cards),
    )
    return records
