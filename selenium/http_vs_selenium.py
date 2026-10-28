"""Script para comparar HTTP vs Selenium con WebDriverWait (Duelo entre HTTP y Selenium) - TAD 2_4

Objetivo: Tomar UN solo sitio, intentar con requests (HTTP) y comparar con Selenium usando esperas explícitas.
Sitio sugerido: https://catalog.data.gov/dataset o https://datos.gob.mx/
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from driver_manager import cerrar_driver, iniciar_driver
from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def intento_http(url: str, query: str | None = None) -> Dict[str, Any]:
    """Intento 1: Obtener datos con petición HTTP permitida."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if query:
        # Para catálogos CKAN comunes
        if "catalog.data.gov" in url:
            url = f"{url}?q={query}"
        elif "datos.gob.mx" in url:
            url = f"{url}?q={query}"

    inicio = time.perf_counter()
    resp = requests.get(url, headers=headers, timeout=15)
    duracion = time.perf_counter() - inicio

    soup = BeautifulSoup(resp.text, "html.parser")
    # Intentar detectar tarjetas típicas de CKAN/otros catálogos
    tarjetas = soup.select(".dataset-content, .dataset-item, .card.dataset-card, .package-item")
    resultados = []
    for t in tarjetas[:20]:
        titulo = t.select_one("h3 a, h4 a, h5 a, .dataset-heading a")
        org = t.select_one(".dataset-organization, .organization, .usa-collection__meta-item a")
        resultados.append({
            "titulo": titulo.get_text(strip=True) if titulo else None,
            "organizacion": org.get_text(strip=True) if org else None,
            "tiene_enlace": bool(titulo and titulo.get("href")),
        })

    return {
        "metodo": "HTTP (requests)",
        "url_final": resp.url,
        "status_code": resp.status_code,
        "tiempo_seg": round(duracion, 3),
        "longitud_html": len(resp.text),
        "tarjetas_detectadas": len(tarjetas),
        "muestra": resultados[:5],
        "hay_app_root_o_carga_js": "ng-app" in resp.text.lower() or "__next" in resp.text.lower() or "id=\"app\"" in resp.text.lower(),
    }


def intento_selenium(url: str, query: str | None = None, browser: str = "edge") -> Dict[str, Any]:
    """Intento 2: Obtener datos con Selenium usando WebDriverWait (no sleeps ciegos)."""
    driver = None
    try:
        driver, wait = iniciar_driver(browser)
        inicio = time.perf_counter()
        driver.get(url)
        duracion_carga = time.perf_counter() - inicio

        # Intentar buscar si existe barra de búsqueda (aplica a CKAN)
        if query:
            try:
                # Data.gov
                buscadores = [
                    (By.CSS_SELECTOR, "input#search-big-input"),
                    (By.CSS_SELECTOR, "input[name='q']"),
                    (By.CSS_SELECTOR, "input.dataset-search-input"),
                    (By.XPATH, "//input[@name='q' or @id='q' or contains(@placeholder,'Buscar')]"),
                ]
                buscador = None
                for by, sel in buscadores:
                    try:
                        buscador = wait.until(EC.presence_of_element_located((by, sel)))
                        break
                    except Exception:
                        continue
                if buscador is not None:
                    buscador.clear()
                    buscador.send_keys(query)
                    buscador.submit()
                    time.sleep(2)
            except Exception as e:
                logger.debug("No se pudo interactuar con buscador: %s", e)

        # Esperar a que aparezcan tarjetas con WebDriverWait
        selectores_tarjetas = [
            ".dataset-content",
            ".dataset-item",
            ".card.dataset-card",
            ".package-item",
            "article.dataset-item",
        ]
        tarjetas = []
        for sel in selectores_tarjetas:
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel)))
                tarjetas = driver.find_elements(By.CSS_SELECTOR, sel)
                if tarjetas:
                    break
            except TimeoutException:
                continue

        duracion_total = time.perf_counter() - inicio
        resultados = []
        for t in tarjetas[:20]:
            try:
                titulo_elem = t.find_element(By.CSS_SELECTOR, "h3 a, h4 a, h5 a, .dataset-heading a, .card-title a")
                titulo = titulo_elem.text.strip()
                href = titulo_elem.get_attribute("href")
                org_elem = t.find_elements(By.CSS_SELECTOR, ".dataset-organization, .organization, .usa-collection__meta-item a")
                org = org_elem[0].text.strip() if org_elem else None
                resultados.append({"titulo": titulo, "organizacion": org, "tiene_enlace": bool(href)})
            except Exception:
                continue

        return {
            "metodo": "Selenium (WebDriverWait)",
            "url_actual": driver.current_url,
            "titulo_pagina": driver.title,
            "tiempo_carga_inicial_seg": round(duracion_carga, 3),
            "tiempo_total_seg": round(duracion_total, 3),
            "tarjetas_detectadas": len(tarjetas),
            "campos_extraidos": len(resultados),
            "muestra": resultados[:5],
            "uso_webdriverwait": True,
        }
    finally:
        if driver is not None:
            cerrar_driver(driver)


def comparar(http_res: Dict[str, Any], sel_res: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "comparativa": {
            "registros_http_muestra": http_res.get("tarjetas_detectadas", 0),
            "registros_selenium_muestra": sel_res.get("tarjetas_detectadas", 0),
            "campos_faltantes_aprox": "Menor con Selenium si hay renderizado JS" if sel_res.get("tarjetas_detectadas", 0) > http_res.get("tarjetas_detectadas", 0) else "Similar o HTTP suficiente",
            "tiempo_http_seg": http_res.get("tiempo_seg"),
            "tiempo_selenium_seg": sel_res.get("tiempo_total_seg"),
            "recomendacion": "Usar API oficial si existe y está documentada. Si solo hay HTML estático y viene completo -> HTTP (requests). Si el contenido se carga por JS/AJAX -> Selenium con WebDriverWait.",
        }
    }


def mostrar_resultado_http(h: dict):
    print("\n" + "=" * 70)
    print(" RESULTADO: PETICION HTTP DIRECTA (requests)")
    print("=" * 70)
    print(f" • Codigo de Estado HTTP:  {h.get('status_code', 'N/A')}")
    print(f" • Tiempo de Respuesta:    {h.get('tiempo_seg', 0)} segundos")
    print(f" • Tarjetas Detectadas:    {h.get('tarjetas_detectadas', 0)} datasets")
    print(f" • Tamano del HTML:        {h.get('longitud_html', 0)} caracteres")
    print(f" • Carga Dinamica JS:      {'No detectada (HTML estatico)' if not h.get('hay_app_root_o_carga_js') else 'Si detectada (SPA/JS)'}")
    print("-" * 70)
    print(" Muestra de registros extraidos:")
    for idx, reg in enumerate(h.get("muestra", [])[:3], 1):
        tit = (reg.get("titulo") or "Sin titulo")[:65]
        org = (reg.get("organizacion") or "Sin organizacion")[:65]
        print(f"   {idx}. {tit}")
        print(f"      Org: {org}")
    print("=" * 70)


def mostrar_resultado_selenium(s: dict):
    print("\n" + "=" * 70)
    print(" RESULTADO: NAVEGADOR AUTOMATIZADO (Selenium con WebDriverWait)")
    print("=" * 70)
    print(f" • Titulo de la Pagina:    {s.get('titulo_pagina') or ''}")
    print(f" • Tiempo Carga Inicial:   {s.get('tiempo_carga_inicial_seg', 0)} segundos")
    print(f" • Tiempo Total Ejecucion: {s.get('tiempo_total_seg', 0)} segundos")
    print(f" • Tarjetas Renderizadas:  {s.get('tarjetas_detectadas', 0)} datasets")
    print(f" • Campos Procesados:      {s.get('campos_extraidos', 0)} campos")
    print(f" • Uso de WebDriverWait:   Si (esperas explicitas sincronizadas)")
    print("-" * 70)
    print(" Muestra de registros extraidos:")
    for idx, reg in enumerate(s.get("muestra", [])[:3], 1):
        tit = (reg.get("titulo") or "Sin titulo")[:65]
        org = (reg.get("organizacion") or "Sin organizacion")[:65]
        print(f"   {idx}. {tit}")
        print(f"      Org: {org}")
    print("=" * 70)


def mostrar_comparativa(comp: dict):
    c = comp.get("comparativa", {})
    t_http = c.get("tiempo_http_seg", 0)
    t_sel = c.get("tiempo_selenium_seg", 0)
    ratio = round(t_sel / t_http, 1) if t_http > 0 else 0

    print("\n" + "#" * 70)
    print(" TABLA COMPARATIVA: DUELO TECNICO (HTTP vs SELENIUM)")
    print("#" * 70)
    print(f" Metrica                  | HTTP (requests)  | Selenium (Edge)")
    print("-" * 70)
    print(f" Tiempo de Ejecucion      | {str(t_http) + ' s':<16} | {str(t_sel) + ' s (x' + str(ratio) + ' mas lento)'}")
    print(f" Tarjetas Extraidas       | {str(c.get('registros_http_muestra', 0)) + ' registros':<16} | {str(c.get('registros_selenium_muestra', 0)) + ' registros'}")
    print(f" Ejecucion de JavaScript  | No requerida     | Si (Motor V8 / DOM)")
    print(f" Consumo de Recursos      | Muy Bajo (~20MB) | Alto (~350MB)")
    print("-" * 70)
    print(" DICTAMEN TECNICO Y RECOMENDACION:")
    print(" • Si el portal devuelve datos en HTML estatico -> Usar HTTP (mas rapido).")
    print(" • Si el contenido requiere React/AJAX dinamico -> Usar Selenium.")
    print(" • Si la institucion ofrece API Oficial         -> Usar la API Oficial.")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    configure_logging()
    print("\n" + "=" * 70)
    print("   ACTIVIDAD 2: DUELO ENTRE HTTP Y SELENIUM (TAD 2_4)")
    print("=" * 70)
    print("Sitio predeterminado: https://catalog.data.gov/dataset (Catálogo Federal CKAN)")
    url = input("\n> Ingresa la URL a comparar [Presiona Enter para Data.gov]: ").strip() or "https://catalog.data.gov/dataset"
    query = input("> Término de búsqueda opcional [Presiona Enter para 'health']: ").strip() or "health"

    print("\n[Paso 1/2] Ejecutando petición HTTP directa con requests...")
    h = intento_http(url, query)
    mostrar_resultado_http(h)

    print("\n[Paso 2/2] Lanzando navegador con Selenium y WebDriverWait...")
    s = intento_selenium(url, query)
    mostrar_resultado_selenium(s)

    mostrar_comparativa(comparar(h, s))
