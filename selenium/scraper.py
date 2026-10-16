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


def _ensure_no_challenge(driver, records=None, pages_processed=0):
    if detectar_desafio(driver):
        raise HumanVerificationDetected(
            "Se detectó una posible verificación humana o bloqueo de acceso.",
            records=records,
            pages_processed=pages_processed,
        )


def extraer_miembros(driver, wait):
    """Lee las cinco fichas públicas de miembros disponibles en #miembros."""
    driver.get(BANDMAID_URL)
    _ensure_no_challenge(driver)
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
        EC.presence_of_element_located((By.CSS_SELECTOR, BANDMAID_SELECTORS["cards"]))
    )
    _ensure_no_challenge(driver)
    cards = driver.find_elements(By.CSS_SELECTOR, BANDMAID_SELECTORS["cards"])
    records = []

    for card in cards:
        try:
            name = clean_text(card.find_element(By.CSS_SELECTOR, BANDMAID_SELECTORS["name"]).text)
            role = clean_text(card.find_element(By.CSS_SELECTOR, BANDMAID_SELECTORS["role"]).text)
            image_alt = clean_text(
                card.find_element(By.CSS_SELECTOR, BANDMAID_SELECTORS["image"]).get_attribute("alt")
            )
        except (NoSuchElementException, StaleElementReferenceException):
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
    return records
