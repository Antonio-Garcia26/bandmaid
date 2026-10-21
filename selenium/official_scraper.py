"""Extractor con Selenium para portales oficiales de datos abiertos (Fase 3)."""

from __future__ import annotations

from datetime import datetime
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from config import OFFICIAL_PORTALS, WAIT_SECONDS
from logging_config import get_logger
from scraper import HumanVerificationDetected, clean_text, detectar_desafio

logger = get_logger(__name__)


def _verificar_barreras(driver, records=None, pages_processed=0):
    """Comprueba si el sitio activó una verificación humana o bloqueo."""
    if detectar_desafio(driver):
        logger.warning(
            "Access challenge or CAPTCHA detected on official portal; triggering ethical pause (pages=%d, records=%d)",
            pages_processed,
            len(records) if records else 0,
        )
        raise HumanVerificationDetected(
            "Se detectó un CAPTCHA o desafío de acceso en el portal oficial.",
            records=records,
            pages_processed=pages_processed,
        )


def extraer_datos_cdmx(
    driver,
    wait,
    query: str = "salud",
    max_pages: int = 2,
) -> List[Dict[str, Any]]:
    """Navega en el Portal de Datos Abiertos de la CDMX, aplica búsqueda y extrae datasets."""
    cfg = OFFICIAL_PORTALS["datos_cdmx"]
    url = cfg["url"]
    logger.info("Starting CDMX extraction: query='%s', max_pages=%d, url=%s", query, max_pages, url)
    print(f"\n[Selenium] Conectando a {cfg['nombre']}...")
    driver.get(url)

    records: List[Dict[str, Any]] = []
    pages_processed = 0

    _verificar_barreras(driver, records, pages_processed)

    # 1. Navegación y Localización: interactuar con la barra de búsqueda oficial
    try:
        print(f"[Selenium] Localizando barra de búsqueda e ingresando término: '{query}'...")
        search_box = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, cfg["search_input"]))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)
    except TimeoutException:
        logger.warning("Search input element not found via wait; attempting direct query URL")
        driver.get(f"{url}?q={query}")

    # 2. Recorrido de páginas y extracción
    while pages_processed < max_pages:
        _verificar_barreras(driver, records, pages_processed)

        # Esperar a que los elementos de tarjetas de datos estén visibles en el DOM
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, cfg["cards"])))
        except TimeoutException:
            logger.info("No more dataset cards found on page %d", pages_processed + 1)
            break

        cards = driver.find_elements(By.CSS_SELECTOR, cfg["cards"])
        print(f"[Selenium] Procesando página {pages_processed + 1}: se encontraron {len(cards)} tarjetas de datos.")

        for card in cards:
            try:
                # Título y enlace del dataset
                title_elem = card.find_element(By.CSS_SELECTOR, "h5.card-title a, h3 a")
                title = clean_text(title_elem.text)
                raw_href = title_elem.get_attribute("href") or ""
                resource_url = urljoin(url, raw_href)

                # Metadatos del card
                card_text = card.text
                organization = "Gobierno de la Ciudad de México"
                org_match = re.search(r"Organizaci[oó]n:\s*([^\n\r]+)", card_text, re.IGNORECASE)
                if org_match:
                    organization = clean_text(org_match.group(1))

                category = "General"
                cat_match = re.search(r"Categor[ií]a:\s*([^\n\r]+)", card_text, re.IGNORECASE)
                if cat_match:
                    category = clean_text(cat_match.group(1))
                else:
                    cat_elems = card.find_elements(By.CSS_SELECTOR, "span.text-aqua")
                    if cat_elems:
                        category = clean_text(cat_elems[0].text)

                last_updated = ""
                date_match = re.search(r"Actualizaci[oó]n:\s*([^\n\r]+)", card_text, re.IGNORECASE)
                if date_match:
                    last_updated = clean_text(date_match.group(1))

                desc_elems = card.find_elements(By.CSS_SELECTOR, "p.card-text")
                description = ""
                for p in desc_elems:
                    p_text = clean_text(p.text)
                    if p_text and not any(tag in p_text for tag in ["Organización", "Categoría", "Actualización"]):
                        description = p_text
                        break

                if title:
                    records.append({
                        "portal": "Datos Abiertos CDMX",
                        "title": title,
                        "organization": organization,
                        "category": category,
                        "description": description or "Dataset oficial publicado por Gobierno de la CDMX",
                        "last_updated": last_updated or "2026",
                        "resource_url": resource_url,
                        "page": pages_processed + 1,
                    })
            except (NoSuchElementException, StaleElementReferenceException) as item_err:
                logger.debug("Skipped card item due to DOM transition: %s", item_err)
                continue

        pages_processed += 1

        # Paginación dinámica: verificar si hay siguiente página
        if pages_processed < max_pages:
            try:
                next_buttons = driver.find_elements(By.CSS_SELECTOR, "ul.pagination li a")
                siguiente = None
                for btn in next_buttons:
                    if "»" in btn.text or "siguiente" in btn.text.lower() or "next" in btn.text.lower():
                        siguiente = btn
                        break
                if siguiente and siguiente.is_displayed():
                    print("[Selenium] Navegando a la siguiente página de resultados...")
                    siguiente.click()
                    time.sleep(2)
                else:
                    break
            except Exception as nav_err:
                logger.info("Pagination navigation stopped: %s", nav_err)
                break

    logger.info("Extraction from CDMX completed: collected %d records across %d pages", len(records), pages_processed)
    return records


def extraer_datos_data_gov(
    driver,
    wait,
    query: str = "health",
    max_pages: int = 2,
) -> List[Dict[str, Any]]:
    """Navega en el Catálogo Federal Data.gov, aplica búsqueda y extrae datasets."""
    cfg = OFFICIAL_PORTALS["data_gov"]
    url = cfg["url"]
    logger.info("Starting Data.gov extraction: query='%s', max_pages=%d, url=%s", query, max_pages, url)
    print(f"\n[Selenium] Conectando a {cfg['nombre']}...")
    driver.get(url)

    records: List[Dict[str, Any]] = []
    pages_processed = 0

    _verificar_barreras(driver, records, pages_processed)

    # 1. Búsqueda
    try:
        print(f"[Selenium] Localizando barra de búsqueda en Data.gov para: '{query}'...")
        search_box = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, cfg["search_input"]))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)
    except TimeoutException:
        logger.warning("Search input element not found; loading direct query URL")
        driver.get(f"{url}?q={query}")

    # 2. Extracción estructurada
    while pages_processed < max_pages:
        _verificar_barreras(driver, records, pages_processed)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, cfg["cards"])))
        except TimeoutException:
            logger.info("No dataset cards found on Data.gov page %d", pages_processed + 1)
            break

        cards = driver.find_elements(By.CSS_SELECTOR, cfg["cards"])
        print(f"[Selenium] Procesando página {pages_processed + 1}: se encontraron {len(cards)} datasets.")

        for card in cards:
            try:
                title_elem = card.find_element(By.CSS_SELECTOR, "h3.usa-collection__heading a, .dataset-heading a")
                title = clean_text(title_elem.text)
                raw_href = title_elem.get_attribute("href") or ""
                resource_url = urljoin(url, raw_href)

                organization = "U.S. Federal Government"
                org_elems = card.find_elements(By.CSS_SELECTOR, ".usa-collection__meta-item a, .dataset-organization")
                if org_elems:
                    organization = clean_text(org_elems[0].text)

                description = ""
                desc_elems = card.find_elements(By.CSS_SELECTOR, ".dataset-description, .usa-collection__description")
                if desc_elems:
                    description = clean_text(desc_elems[0].text)

                tag_elems = card.find_elements(By.CSS_SELECTOR, ".usa-tag, .tag")
                category = clean_text(tag_elems[0].text) if tag_elems else "Open Data"

                if title:
                    records.append({
                        "portal": "Data.gov (Federal Open Data)",
                        "title": title,
                        "organization": organization,
                        "category": category,
                        "description": description or "Dataset oficial publicado en el catálogo federal de datos abiertos",
                        "last_updated": "2026",
                        "resource_url": resource_url,
                        "page": pages_processed + 1,
                    })
            except (NoSuchElementException, StaleElementReferenceException) as item_err:
                logger.debug("Skipped Data.gov item due to DOM change: %s", item_err)
                continue

        pages_processed += 1

        if pages_processed < max_pages:
            try:
                next_btn = driver.find_elements(By.CSS_SELECTOR, cfg["pagination_next"])
                if next_btn and next_btn[0].is_displayed():
                    print("[Selenium] Navegando a la siguiente página en Data.gov...")
                    next_btn[0].click()
                    time.sleep(2)
                else:
                    break
            except Exception as nav_err:
                logger.info("Pagination navigation stopped on Data.gov: %s", nav_err)
                break

    logger.info("Extraction from Data.gov completed: %d records across %d pages", len(records), pages_processed)
    return records
