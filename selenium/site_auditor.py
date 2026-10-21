"""Módulo de auditoría y categorización de seguridad de sitios web externos (Fase 2)."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import urllib.parse

import pandas as pd
import requests

from config import AUDIT_TARGETS, OUTPUT_DIR_NAME, WAIT_SECONDS
from database import guardar_en_sqlite, init_db
from driver_manager import cerrar_driver, iniciar_driver
from logging_config import get_logger
from scraper import detectar_desafio

logger = get_logger(__name__)


def _auditar_robots_txt(robots_url: str) -> Dict[str, Any]:
    """Inspecciona el archivo robots.txt de un sitio web público."""
    resultado = {
        "disponible": False,
        "status_code": None,
        "disallow_count": 0,
        "allow_count": 0,
        "crawl_delay": None,
        "sitemap_presente": False,
        "resumen": "No disponible",
    }
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(robots_url, headers=headers, timeout=10)
        resultado["status_code"] = resp.status_code
        if resp.status_code == 200:
            resultado["disponible"] = True
            lines = resp.text.splitlines()
            disallows = [l for l in lines if l.strip().lower().startswith("disallow:")]
            allows = [l for l in lines if l.strip().lower().startswith("allow:")]
            sitemaps = [l for l in lines if l.strip().lower().startswith("sitemap:")]
            delays = [l for l in lines if l.strip().lower().startswith("crawl-delay:")]

            resultado["disallow_count"] = len(disallows)
            resultado["allow_count"] = len(allows)
            resultado["sitemap_presente"] = len(sitemaps) > 0
            if delays:
                resultado["crawl_delay"] = delays[0].split(":", 1)[1].strip()

            resultado["resumen"] = (
                f"Permite indexación con {len(disallows)} reglas restrictivas"
                if len(disallows) < 50
                else f"Altamente restrictivo ({len(disallows)} directivas Disallow)"
            )
        else:
            resultado["resumen"] = f"Respuesta HTTP {resp.status_code} al solicitar robots.txt"
    except Exception as err:
        logger.warning("Error fetching robots.txt from %s: %s", robots_url, err)
        resultado["resumen"] = f"Error al consultar robots.txt ({type(err).__name__})"
    return resultado


def _auditar_cabeceras_http(url: str) -> Dict[str, Any]:
    """Analiza cabeceras HTTP de respuesta para detectar WAF, Cloudflare y seguridad perimetral."""
    resultado = {
        "status_code": None,
        "server": "No especificado",
        "waf_detectado": "Ninguno detectado",
        "cloudflare": False,
        "hsts": False,
        "csp": False,
        "x_frame_options": False,
        "rate_limit_headers": False,
    }
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        resultado["status_code"] = resp.status_code
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}

        resultado["server"] = resp_headers.get("server", "No expuesto")
        if "cf-ray" in resp_headers or "cloudflare" in resultado["server"].lower():
            resultado["cloudflare"] = True
            resultado["waf_detectado"] = "Cloudflare WAF / CDN"
        elif "x-amz-cf-id" in resp_headers or "cloudfront" in resultado["server"].lower():
            resultado["waf_detectado"] = "AWS CloudFront WAF"
        elif "x-azure-ref" in resp_headers:
            resultado["waf_detectado"] = "Azure Front Door WAF"

        resultado["hsts"] = "strict-transport-security" in resp_headers
        resultado["csp"] = "content-security-policy" in resp_headers
        resultado["x_frame_options"] = "x-frame-options" in resp_headers
        resultado["rate_limit_headers"] = any("ratelimit" in k or "retry-after" in k for k in resp_headers)
    except Exception as err:
        logger.warning("Error fetching headers from %s: %s", url, err)
        resultado["waf_detectado"] = f"Inaccesible vía requests ({type(err).__name__})"
    return resultado


def _auditar_con_selenium(driver, url: str) -> Dict[str, Any]:
    """Carga el sitio mediante Selenium y analiza renderizado dinámico, frameworks y retos."""
    resultado = {
        "titulo": "",
        "render_dinamico_js": False,
        "frameworks_detectados": [],
        "captcha_detectado": "Ninguno",
        "desafio_bloqueante": False,
        "elementos_dom": 0,
        "tiempo_carga_ms": 0,
    }
    try:
        inicio = datetime.now()
        driver.get(url)
        resultado["titulo"] = driver.title
        duracion = (datetime.now() - inicio).total_seconds() * 1000
        resultado["tiempo_carga_ms"] = round(duracion)

        # Detectar frameworks o scripts dinámicos
        page_source = driver.page_source.lower()
        if "__next" in page_source or "_next/static" in page_source:
            resultado["frameworks_detectados"].append("Next.js")
            resultado["render_dinamico_js"] = True
        if "react" in page_source or "data-reactroot" in page_source:
            resultado["frameworks_detectados"].append("React")
            resultado["render_dinamico_js"] = True
        if "vue" in page_source or "data-v-" in page_source:
            resultado["frameworks_detectados"].append("Vue.js")
            resultado["render_dinamico_js"] = True
        if "ckan" in page_source or "select-switch" in page_source:
            resultado["frameworks_detectados"].append("CKAN OpenData")
            resultado["render_dinamico_js"] = True
        if "jquery" in page_source:
            resultado["frameworks_detectados"].append("jQuery")

        # Detectar presencia de CAPTCHA o retos de acceso
        if "turnstile" in page_source or "challenges.cloudflare.com" in page_source:
            resultado["captcha_detectado"] = "Cloudflare Turnstile"
        elif "recaptcha" in page_source or "google.com/recaptcha" in page_source:
            resultado["captcha_detectado"] = "Google reCAPTCHA"
        elif "hcaptcha" in page_source:
            resultado["captcha_detectado"] = "hCaptcha"

        # Verificar si saltó un desafío bloqueante
        resultado["desafio_bloqueante"] = detectar_desafio(driver)

        # Contar complejidad del DOM
        resultado["elementos_dom"] = driver.execute_script("return document.getElementsByTagName('*').length;")
    except Exception as err:
        logger.warning("Selenium audit encountered an issue on %s: %s", url, err)
        resultado["desafio_bloqueante"] = False
        resultado["captcha_detectado"] = "Ninguno"
    return resultado


def _clasificar_nivel_proteccion(http_data: Dict[str, Any], sel_data: Dict[str, Any]) -> str:
    """Clasifica el nivel de protección de acuerdo a la rúbrica (Básico, Intermedio, Avanzado)."""
    # Avanzado: Cloudflare WAF activo, Turnstile/CAPTCHA v3 o bloqueo de bot estándar
    if (
        (http_data.get("cloudflare") and http_data.get("rate_limit_headers"))
        or "turnstile" in str(sel_data.get("captcha_detectado")).lower()
        or sel_data.get("desafio_bloqueante")
    ):
        return "Avanzado"

    # Intermedio: Renderizado dinámico (React/Vue/Next/CKAN AJAX) o Cloudflare CDN sin bloqueo agresivo
    if (
        sel_data.get("render_dinamico_js")
        or http_data.get("cloudflare")
        or sel_data.get("captcha_detectado") != "Ninguno"
        or len(sel_data.get("frameworks_detectados", [])) > 0
    ):
        return "Intermedio"

    # Básico: Estructura HTML tradicional, sin WAF bloqueante, paginación por URL
    return "Básico"


def ejecutar_auditoria_completa(browser: str = "edge") -> List[Dict[str, Any]]:
    """Ejecuta la auditoría comparativa de los 5 sitios web objetivo y genera los reportes."""
    logger.info("Starting complete security audit for 5 target websites using browser=%s", browser)
    init_db()

    resultados = []
    driver = None
    try:
        driver, _ = iniciar_driver(browser, timeout=10)
        for target in AUDIT_TARGETS:
            print(f"\n[Auditoría] Analizando: {target['nombre']} ({target['url']})...")
            # 1. Inspeccionar robots.txt
            robots_info = _auditar_robots_txt(target["robots_url"])
            # 2. Inspeccionar cabeceras HTTP
            http_info = _auditar_cabeceras_http(target["url"])
            # 3. Inspeccionar DOM y comportamiento en Selenium
            sel_info = _auditar_con_selenium(driver, target["url"])
            # 4. Clasificación técnica
            nivel_calculado = _clasificar_nivel_proteccion(http_info, sel_info)

            tecnologias_str = ", ".join(sel_info.get("frameworks_detectados", [])) or "HTML5 / Vanilla JS"

            registro = {
                "id": target["id"],
                "nombre": target["nombre"],
                "url": target["url"],
                "tipo_fuente": target["tipo_fuente"],
                "nivel_asignado": nivel_calculado,
                "nivel_esperado": target["nivel_esperado"],
                "status_http": http_info.get("status_code"),
                "server_header": http_info.get("server"),
                "waf_detectado": http_info.get("waf_detectado"),
                "seguridad_cabeceras": f"HSTS: {http_info.get('hsts')}, CSP: {http_info.get('csp')}, X-Frame: {http_info.get('x_frame_options')}",
                "robots_txt_disponible": robots_info.get("disponible"),
                "robots_txt_resumen": robots_info.get("resumen"),
                "tecnologias_js": tecnologias_str,
                "captcha_detectado": sel_info.get("captcha_detectado"),
                "desafio_bloqueante": sel_info.get("desafio_bloqueante"),
                "elementos_dom": sel_info.get("elementos_dom"),
                "tiempo_carga_ms": sel_info.get("tiempo_carga_ms"),
                "viabilidad_legal": target["viabilidad_legal"],
                "auditado_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            resultados.append(registro)
            print(f"  -> Nivel asignado: {nivel_calculado} | WAF: {registro['waf_detectado']} | CAPTCHA: {registro['captcha_detectado']}")
    finally:
        if driver is not None:
            cerrar_driver(driver)

    df_auditoria = pd.DataFrame(resultados)

    # Guardar en SQLite
    try:
        guardar_en_sqlite(
            df_auditoria[[
                "nombre", "url", "nivel_asignado", "status_http", "robots_txt_resumen",
                "waf_detectado", "captcha_detectado", "tecnologias_js", "viabilidad_legal", "auditado_at"
            ]].rename(columns={"nivel_asignado": "nivel", "robots_txt_resumen": "robots_txt_status"}),
            table_name="auditoria_sitios",
        )
    except Exception as err:
        logger.warning("Could not persist audit results into SQLite: %s", err)

    # Guardar en JSON y CSV para el informe de la Fase 2
    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "auditoria_5_sitios.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    csv_path = output_dir / "auditoria_5_sitios.csv"
    df_auditoria.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 90)
    print("RESUMEN DE AUDITORÍA COMPARATIVA DE LOS 5 SITIOS (FASE 2)")
    print("=" * 90)
    cols_vista = ["nombre", "nivel_asignado", "waf_detectado", "captcha_detectado", "tecnologias_js"]
    print(df_auditoria[cols_vista].to_string(index=False))
    print("=" * 90)
    print(f"Archivos de auditoría generados exitosamente:")
    print(f"  • JSON detallado: {json_path}")
    print(f"  • CSV estructurado: {csv_path}")
    print(f"  • SQLite persistido en: salida/datos_oficiales.db (tabla 'auditoria_sitios')")

    return resultados
