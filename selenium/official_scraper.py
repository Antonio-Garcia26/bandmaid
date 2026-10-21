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
from scraper import HumanVerificationDetected, clean_text, detectar_desafio, manejar_barrera_etica

logger = get_logger(__name__)


def _verificar_barreras(driver, records=None, pages_processed=0) -> bool:
    """Manejo Ético de Barreras: Si se detecta un CAPTCHA o desafío de acceso,
    se pausa respetuosamente solicitando la intervención del operador humano
    para continuar con la extracción dinámicamente."""
    return manejar_barrera_etica(
        driver,
        records=records,
        pages_processed=pages_processed,
        permitir_continuar=True,
    )


def _buscar_elem_robusto(parent, css_selector: str, xpath_selector: Optional[str] = None):
    """Localizador robusto híbrido: busca por CSS Selector y tiene fallback a XPath."""
    try:
        return parent.find_element(By.CSS_SELECTOR, css_selector)
    except (NoSuchElementException, Exception):
        if xpath_selector:
            return parent.find_element(By.XPATH, xpath_selector)
        raise


def _buscar_elems_robustos(parent, css_selector: str, xpath_selector: Optional[str] = None):
    """Localizador robusto múltiple: busca por CSS Selector y tiene fallback a XPath."""
    elems = parent.find_elements(By.CSS_SELECTOR, css_selector)
    if not elems and xpath_selector:
        elems = parent.find_elements(By.XPATH, xpath_selector)
    return elems


def _aplicar_filtro_interactivo(driver, wait, portal_key: str, filtro: str = "csv") -> bool:
    """Navegación y Localización: Selecciona dinámicamente un filtro en la interfaz web oficial.
    
    Localiza la faceta correspondiente usando XPath y CSS Selectors, hace scroll e interactúa
    con Selenium WebDriver esperando la actualización del DOM.
    """
    cfg = OFFICIAL_PORTALS[portal_key]
    xpath_filtro = cfg.get("filter_format_xpath")
    logger.info("Applying dynamic filter '%s' in portal '%s'", filtro, portal_key)
    print(f"[Selenium - Filtros] Localizando y aplicando filtro de formato '{filtro.upper()}'...")

    # Intento 1: Interacción directa con el elemento en la interfaz vía XPath / CSS
    if xpath_filtro:
        try:
            elementos = driver.find_elements(By.XPATH, xpath_filtro)
            for elem in elementos:
                if elem.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(1)
                    elem.click()
                    time.sleep(2)
                    logger.info("Filter '%s' clicked successfully via XPath in %s", filtro, portal_key)
                    print(f"[Selenium - Filtros] Filtro '{filtro.upper()}' seleccionado exitosamente en el DOM.")
                    return True
        except Exception as filter_err:
            logger.debug("Interactive filter click via XPath encountered an issue: %s", filter_err)

    # Intento 2: Fallback controlado por parámetro de navegación en la URL
    current_url = driver.current_url
    param = "res_format=CSV" if portal_key == "data_gov" else "format=CSV"
    if param.split("=")[0] not in current_url:
        sep = "&" if "?" in current_url else "?"
        url_filtrada = f"{current_url}{sep}{param}"
        print(f"[Selenium - Filtros] Navegando con filtro de formato: {url_filtrada}")
        driver.get(url_filtrada)
        time.sleep(2)
        return True

    return False


def extraer_datos_cdmx(
    driver,
    wait,
    query: str = "salud",
    max_pages: int = 2,
    filter_format: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Navega en el Portal de Datos Abiertos de la CDMX, aplica búsqueda, filtros y extrae datasets."""
    cfg = OFFICIAL_PORTALS["datos_cdmx"]
    url = cfg["url"]
    logger.info(
        "Starting CDMX extraction: query='%s', filter='%s', max_pages=%d, url=%s",
        query, filter_format, max_pages, url
    )
    print(f"\n[Selenium] Conectando al portal oficial: {cfg['nombre']}...")
    driver.get(url)

    records: List[Dict[str, Any]] = []
    pages_processed = 0

    _verificar_barreras(driver, records, pages_processed)

    # 1. Navegación y Localización: Búsqueda dinámica con Selenium WebDriver
    try:
        print(f"[Selenium - Búsqueda] Localizando barra de búsqueda e ingresando término: '{query}'...")
        try:
            search_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, cfg["search_input"]))
            )
        except TimeoutException:
            search_box = wait.until(
                EC.presence_of_element_located((By.XPATH, cfg["search_input_xpath"]))
            )

        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)
    except TimeoutException:
        logger.warning("Search input element not found via wait; falling back to direct query URL")
        driver.get(f"{url}?q={query}")

    # 2. Selección de Filtros (si fue solicitado)
    if filter_format:
        _aplicar_filtro_interactivo(driver, wait, "datos_cdmx", filtro=filter_format)

    # 3. Recorrido dinámico de páginas y extracción estructurada con CSS y XPath
    while pages_processed < max_pages:
        _verificar_barreras(driver, records, pages_processed)

        # Espera explícita para la aparición de tarjetas en el DOM
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, cfg["cards"])))
        except TimeoutException:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, cfg["cards_xpath"])))
            except TimeoutException:
                logger.info("No more dataset cards found on page %d", pages_processed + 1)
                break

        # Uso de localizadores robustos híbridos (CSS + XPath fallback)
        cards = _buscar_elems_robustos(driver, cfg["cards"], cfg.get("cards_xpath"))
        print(f"[Selenium] Procesando página {pages_processed + 1}: se encontraron {len(cards)} tarjetas de datos.")

        for card in cards:
            try:
                # Título y enlace del dataset usando CSS / XPath
                try:
                    title_elem = _buscar_elem_robusto(card, cfg["title"], cfg.get("title_xpath"))
                    title = clean_text(title_elem.text)
                    raw_href = title_elem.get_attribute("href") or ""
                    resource_url = urljoin(url, raw_href)
                except Exception:
                    continue

                card_text = card.text

                # Organización
                organization = "Gobierno de la Ciudad de México"
                org_match = re.search(r"Organizaci[oó]n:\s*([^\n\r]+)", card_text, re.IGNORECASE)
                if org_match:
                    organization = clean_text(org_match.group(1))

                # Categoría
                category = "General"
                cat_match = re.search(r"Categor[ií]a:\s*([^\n\r]+)", card_text, re.IGNORECASE)
                if cat_match:
                    category = clean_text(cat_match.group(1))
                else:
                    cat_elems = _buscar_elems_robustos(card, cfg["category"], cfg.get("category_xpath"))
                    if cat_elems:
                        category = clean_text(cat_elems[0].text)

                # Fecha de última actualización
                last_updated = ""
                date_match = re.search(r"Actualizaci[oó]n:\s*([^\n\r]+)", card_text, re.IGNORECASE)
                if date_match:
                    last_updated = clean_text(date_match.group(1))

                # Descripción
                desc_elems = _buscar_elems_robustos(card, cfg["description"], cfg.get("description_xpath"))
                description = ""
                for p in desc_elems:
                    p_text = clean_text(p.text)
                    if p_text and not any(tag in p_text for tag in ["Organización", "Categoría", "Actualización"]):
                        description = p_text
                        break

                # Métrica numérica cruda (cantidad de recursos/formatos disponibles en el dataset)
                res_elems = _buscar_elems_robustos(card, cfg.get("resources", ".badge"), cfg.get("resources_xpath"))
                num_resources_val = len(res_elems) if res_elems else 1
                res_match = re.search(r"(\d+)\s+recursos?", card_text, re.IGNORECASE)
                if res_match:
                    num_resources_val = int(res_match.group(1))

                if title:
                    records.append({
                        "portal": "Datos Abiertos CDMX",
                        "title": title,
                        "organization": organization,
                        "category": category,
                        "num_resources": num_resources_val,
                        "description": description or "Dataset oficial publicado por Gobierno de la CDMX",
                        "last_updated": last_updated or "2026",
                        "resource_url": resource_url,
                        "page": pages_processed + 1,
                    })
            except (NoSuchElementException, StaleElementReferenceException) as item_err:
                logger.debug("Skipped card item due to DOM transition: %s", item_err)
                continue

        pages_processed += 1

        # Paginación dinámica: verificar botón de siguiente página con CSS y XPath
        if pages_processed < max_pages:
            try:
                next_buttons = _buscar_elems_robustos(
                    driver,
                    cfg["pagination_next"],
                    cfg.get("pagination_next_xpath"),
                )
                siguiente = None
                for btn in next_buttons:
                    btn_text = (btn.text or "").lower()
                    rel_attr = (btn.get_attribute("rel") or "").lower()
                    if "»" in btn.text or "siguiente" in btn_text or "next" in btn_text or rel_attr == "next":
                        siguiente = btn
                        break

                if siguiente and siguiente.is_displayed():
                    print("[Selenium - Paginación] Navegando a la siguiente página dinámicamente...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", siguiente)
                    time.sleep(1)
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
    filter_format: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Navega en el Catálogo Federal Data.gov, aplica búsqueda, filtros y extrae datasets."""
    cfg = OFFICIAL_PORTALS["data_gov"]
    url = cfg["url"]
    logger.info(
        "Starting Data.gov extraction: query='%s', filter='%s', max_pages=%d, url=%s",
        query, filter_format, max_pages, url
    )
    print(f"\n[Selenium] Conectando al portal federal: {cfg['nombre']}...")
    driver.get(url)

    records: List[Dict[str, Any]] = []
    pages_processed = 0

    _verificar_barreras(driver, records, pages_processed)

    # 1. Búsqueda con Selenium WebDriver
    try:
        print(f"[Selenium - Búsqueda] Localizando barra de búsqueda en Data.gov para: '{query}'...")
        try:
            search_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, cfg["search_input"]))
            )
        except TimeoutException:
            search_box = wait.until(
                EC.presence_of_element_located((By.XPATH, cfg["search_input_xpath"]))
            )

        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)
    except TimeoutException:
        logger.warning("Search input element not found; loading direct query URL")
        driver.get(f"{url}?q={query}")

    # 2. Selección de Filtros (si fue solicitado)
    if filter_format:
        _aplicar_filtro_interactivo(driver, wait, "data_gov", filtro=filter_format)

    # 3. Extracción estructurada con CSS y XPath
    while pages_processed < max_pages:
        _verificar_barreras(driver, records, pages_processed)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, cfg["cards"])))
        except TimeoutException:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, cfg["cards_xpath"])))
            except TimeoutException:
                logger.info("No dataset cards found on Data.gov page %d", pages_processed + 1)
                break

        cards = _buscar_elems_robustos(driver, cfg["cards"], cfg.get("cards_xpath"))
        print(f"[Selenium] Procesando página {pages_processed + 1}: se encontraron {len(cards)} datasets.")

        for card in cards:
            try:
                title_elem = _buscar_elem_robusto(card, cfg["title"], cfg.get("title_xpath"))
                title = clean_text(title_elem.text)
                raw_href = title_elem.get_attribute("href") or ""
                resource_url = urljoin(url, raw_href)

                organization = "U.S. Federal Government"
                org_elems = _buscar_elems_robustos(card, cfg["organization"], cfg.get("organization_xpath"))
                if org_elems:
                    organization = clean_text(org_elems[0].text)

                description = ""
                desc_elems = _buscar_elems_robustos(card, cfg["description"], cfg.get("description_xpath"))
                if desc_elems:
                    description = clean_text(desc_elems[0].text)

                tag_elems = _buscar_elems_robustos(card, cfg["category"], cfg.get("category_xpath"))
                category = clean_text(tag_elems[0].text) if tag_elems else "Open Data"

                # Métrica numérica cruda (formatos/recursos disponibles)
                res_elems = _buscar_elems_robustos(card, cfg.get("resources", ".format-label"), cfg.get("resources_xpath"))
                num_resources_val = len(res_elems) if res_elems else 1

                if title:
                    records.append({
                        "portal": "Data.gov (Federal Open Data)",
                        "title": title,
                        "organization": organization,
                        "category": category,
                        "num_resources": num_resources_val,
                        "description": description or "Dataset oficial publicado en el catálogo federal de datos abiertos",
                        "last_updated": "2026",
                        "resource_url": resource_url,
                        "page": pages_processed + 1,
                    })
            except (NoSuchElementException, StaleElementReferenceException) as item_err:
                logger.debug("Skipped Data.gov item due to DOM change: %s", item_err)
                continue

        pages_processed += 1

        # Paginación dinámica con XPath y CSS
        if pages_processed < max_pages:
            try:
                next_btns = _buscar_elems_robustos(
                    driver,
                    cfg["pagination_next"],
                    cfg.get("pagination_next_xpath"),
                )
                if next_btns and next_btns[0].is_displayed():
                    print("[Selenium - Paginación] Navegando a la siguiente página en Data.gov...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btns[0])
                    time.sleep(1)
                    next_btns[0].click()
                    time.sleep(2)
                else:
                    break
            except Exception as nav_err:
                logger.info("Pagination navigation stopped on Data.gov: %s", nav_err)
                break

    logger.info("Extraction from Data.gov completed: %d records across %d pages", len(records), pages_processed)
    return records
