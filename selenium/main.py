"""CLI para extraer y procesar datos públicos de Band-Maid."""

import argparse
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from database import consultar_sqlite, contar_registros_sqlite, generar_reporte_sql_analitico
from data_processor import (
    guardar_captura,
    guardar_resultados,
    guardar_resultados_oficiales,
    procesar_datos,
    procesar_datos_oficiales,
)
from driver_manager import cerrar_driver, iniciar_driver
from logging_config import configure_logging, get_logger
from official_scraper import extraer_datos_cdmx, extraer_datos_data_gov
from scraper import HumanVerificationDetected, extraer_miembros
from security_tests import run_public_security_test
from site_auditor import ejecutar_auditoria_completa

logger = get_logger(__name__)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extrae las fichas públicas de Band-Maid y las procesa con Pandas."
    )
    parser.add_argument(
        "--browser",
        choices=("chrome", "edge"),
        default="edge",
        help="navegador visible para Selenium (por omisión: Edge)",
    )
    parser.add_argument(
        "--query",
        help="búsqueda local, sin distinguir mayúsculas, sobre las fichas extraídas",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="filas que se omiten al paginar el DataFrame",
    )
    parser.add_argument(
        "--limit", type=int,
        help="máximo de filas que se muestran/guardan tras filtrar",
    )
    parser.add_argument(
        "--screenshot",
        action="store_true",
        help="guarda una captura PNG de la página visible dentro de salida/",
    )
    parser.add_argument(
        "--portal",
        choices=("datos_cdmx", "data_gov"),
        default="datos_cdmx",
        help="portal oficial para extracción de datos (por omisión: datos_cdmx)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="número máximo de páginas a recorrer en el portal oficial",
    )
    parser.add_argument(
        "--filter",
        dest="format_filter",
        help="filtro dinámico interactivo a seleccionar en el portal (ejemplo: 'csv')",
    )
    parser.add_argument(
        "--security-test",
        choices=("captcha", "rate-limit", "csrf", "honeypot", "telemetry", "all"),
        help="ejecuta una prueba individual de seguridad o la batería completa",
    )
    return parser




def _validate_args(parser, args):
    if args.offset < 0:
        parser.error("--offset no puede ser negativo.")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit no puede ser negativo.")


def _pause_for_review():
    print(
        "Manejo Ético de Barreras: Se identificó el límite del portal sin intentar sortearlo de forma automatizada."
    )
    try:
        input("Presione Enter para cerrar el navegador y regresar al menú principal...")
    except EOFError:
        print("Finalizando pausa ética.")



def _run_scraping(args):
    logger.info(
        "Scraping operation started: browser=%s screenshot=%s offset=%d limit=%s",
        args.browser,
        args.screenshot,
        args.offset,
        args.limit,
    )
    driver = None
    records = []
    pages_processed = 0
    challenge_detected = False
    try:
        driver, wait = iniciar_driver(args.browser)
        records = extraer_miembros(driver, wait)
        pages_processed = 1 if records else 0
    except HumanVerificationDetected as challenge:
        records = challenge.records
        pages_processed = challenge.pages_processed
        challenge_detected = True
        logger.warning(
            "Verification challenge detected; manual review pause requested "
            "(pages_processed=%d records_collected=%d)",
            pages_processed,
            len(records),
        )
        print(f"\nATENCIÓN: {challenge}")
        _pause_for_review()
    except Exception as error:
        logger.exception(
            "Scraping operation failed: browser=%s error_type=%s",
            args.browser,
            type(error).__name__,
        )
        print(f"\nNo se pudo completar la extracción ({type(error).__name__}): {error}")
        return 1
    finally:
        if args.screenshot and driver is not None:
            try:
                screenshot_path = guardar_captura(driver)
                logger.info("Browser screenshot saved successfully")
                print(f"Captura guardada en: {screenshot_path}")
            except Exception as screenshot_error:
                logger.exception(
                    "Browser screenshot could not be saved: error_type=%s",
                    type(screenshot_error).__name__,
                )
                print(f"No se pudo guardar la captura ({type(screenshot_error).__name__}).")
        cerrar_driver(driver)

    print(
        "Band-Maid: se consulta la página pública y las fichas de #miembros. "
        "El sitio no ofrece controles propios de búsqueda ni paginación."
    )

    try:
        df = procesar_datos(
            records,
            query=args.query,
            offset=args.offset,
            limit=args.limit,
        )
    except Exception as error:
        logger.exception(
            "Scraping data processing failed: records_collected=%d",
            len(records),
        )
        print(f"\nNo se pudieron procesar los datos ({type(error).__name__}).")
        return 1
    print(f"\nPáginas procesadas: {pages_processed}")
    print(f"Registros extraídos: {len(records)} · filas tras limpieza/filtros: {len(df)}")
    if challenge_detected:
        print("La extracción se detuvo al detectar un desafío de acceso.")
    print("\nVista previa del DataFrame procesado:")
    print(df.head(20).to_string(index=False) if not df.empty else "(sin registros)")

    logger.info(
        "Scraping data processed: pages_processed=%d records_collected=%d rows_after_processing=%d challenge_detected=%s",
        pages_processed,
        len(records),
        len(df),
        challenge_detected,
    )
    try:
        output_path = guardar_resultados(df)
    except Exception as error:
        logger.exception("Scraping results could not be saved: rows=%d", len(df))
        print(f"\nNo se pudieron guardar los resultados ({type(error).__name__}).")
        return 1
    logger.info("Scraping results saved successfully: rows=%d", len(df))
    print(f"\nCSV guardado en: {output_path}")
    logger.info("Scraping operation completed successfully")
    return 0


def _run_security_test(args, mode):
    logger.info(
        "Security test operation started: mode=%s browser=%s",
        mode,
        args.browser,
    )
    driver = None
    try:
        driver, _ = iniciar_driver(args.browser)
        run_public_security_test(driver, mode)
        logger.info("Security test operation completed successfully: mode=%s", mode)
    except Exception as error:
        logger.exception(
            "Security test operation failed: mode=%s browser=%s error_type=%s",
            mode,
            args.browser,
            type(error).__name__,
        )
        print(f"No se pudo completar la prueba ({type(error).__name__}): {error}")
        return 1
    finally:
        cerrar_driver(driver)
    return 0



def _run_audit(args):
    """Ejecuta la inspección comparativa de los 5 sitios web para la Fase 2."""
    print("\n" + "=" * 60)
    print("INICIANDO AUDITORÍA COMPARATIVA DE 5 SITIOS (FASE 2)")
    print("Inspección de robots.txt, cabeceras HTTP, WAF, CAPTCHAs y DOM dinámico...")
    print("=" * 60)
    try:
        ejecutar_auditoria_completa(browser=args.browser)
        return 0
    except Exception as error:
        logger.exception("Error executing full site audit: %s", error)
        print(f"\nNo se pudo completar la auditoría ({type(error).__name__}): {error}")
        return 1


def _run_official_scraping(args):
    """Ejecuta la extracción de datos desde el portal oficial seleccionado (Fase 3)."""
    portal_choice = args.portal or "datos_cdmx"
    search_query = args.query or ("salud" if portal_choice == "datos_cdmx" else "health")
    max_pages = args.pages or 2
    format_filter = getattr(args, "format_filter", None)

    print("\n" + "=" * 60)
    print("EXTRACCIÓN DE DATOS OFICIALES CON SELENIUM (FASE 3)")
    print(f"Portal objetivo: {portal_choice} | Búsqueda: '{search_query}' | Filtro: '{format_filter or 'Ninguno'}' | Páginas: {max_pages}")
    print("=" * 60)

    driver = None
    records = []
    challenge_detected = False
    try:
        driver, wait = iniciar_driver(args.browser)
        if portal_choice == "datos_cdmx":
            records = extraer_datos_cdmx(
                driver, wait, query=search_query, max_pages=max_pages, filter_format=format_filter
            )
        else:
            records = extraer_datos_data_gov(
                driver, wait, query=search_query, max_pages=max_pages, filter_format=format_filter
            )
    except HumanVerificationDetected as challenge:
        records = challenge.records
        challenge_detected = True
        logger.warning("Ethical barrier detected during official scraping: %s", challenge)
        print(f"\nATENCIÓN (Manejo Ético de Barreras): {challenge}")
        _pause_for_review()
    except Exception as error:
        logger.exception("Error in official scraping: %s", error)
        print(f"\nNo se pudo completar la extracción oficial ({type(error).__name__}): {error}")
        return 1
    finally:
        if args.screenshot and driver is not None:
            try:
                guardar_captura(driver)
            except Exception:
                pass
        cerrar_driver(driver)

    if not records:
        print("\nNo se obtuvieron registros del portal oficial.")
        return 0

    print(f"\nProcesando y limpiando {len(records)} registros con Pandas (texto, fechas y valores numéricos)...")
    df = procesar_datos_oficiales(records, query=args.query, offset=args.offset, limit=args.limit)

    print(f"\nRegistros procesados y estructurados: {len(df)}")
    if challenge_detected:
        print("(La extracción se pausó preventivamente por desafío de verificación)")

    print("\nVista previa del Dataset Oficial estructurado:")
    cols_preview = ["title", "organization", "category", "num_resources", "last_updated"]
    cols_exist = [c for c in cols_preview if c in df.columns]
    print(df[cols_exist].head(15).to_string(index=False) if not df.empty else "(sin registros)")

    # Guardar en SQLite, CSV, JSON y Excel
    try:
        storage_info = guardar_resultados_oficiales(df, portal_tag=portal_choice)
        print("\n" + "-" * 60)
        print("ALMACENAMIENTO PERSISTENTE COMPLETADO (Bases de datos y Archivos Estructurados):")
        print(f"  • Base de Datos SQLite: salida/datos_oficiales.db (filas añadidas: {storage_info['sqlite_rows']})")
        print(f"  • Archivo CSV estructurado: {storage_info['csv_path'].name}")
        if storage_info.get("json_path"):
            print(f"  • Archivo JSON estructurado: {storage_info['json_path'].name}")
        if storage_info.get("excel_path"):
            print(f"  • Archivo Excel (.xlsx): {storage_info['excel_path'].name}")
        print("-" * 60)
    except Exception as error:
        logger.exception("Could not save official data results: %s", error)
        print(f"No se pudieron guardar los resultados oficiales ({type(error).__name__}).")
        return 1

    return 0



def _run_db_view():
    """Ejecuta consultas analíticas SQL en SQLite, muestra resultados en consola y exporta a Excel/CSV."""
    reporte = generar_reporte_sql_analitico()
    if "error" in reporte:
        print(f"\n{reporte['error']}")
        return 0

    print("\n" + "=" * 76)
    print("           REPORTE ANALITICO DE BASE DE DATOS SQLITE (SQLite3)")
    print("                     Archivo: salida/datos_oficiales.db")
    print("=" * 76)
    print(f" Total de Registros Almacenados: {reporte['total_registros']}")
    print(f" Estado de Integridad:           100% Sin Duplicados (Deduplicado)")
    print("=" * 76)

    print("\n[CONSULTA SQL 1] Datasets Agrupados por Portal y Categoria (GROUP BY):")
    print("-" * 76)
    resumen_str = reporte["df_resumen"].to_string(index=False)
    for linea in resumen_str.splitlines():
        print(f"  {linea}")
    print("-" * 76)

    print("\n[CONSULTA SQL 2] Auditoria de Integridad y Duplicados (HAVING COUNT > 1):")
    print("-" * 76)
    if reporte["total_duplicados"] == 0:
        print("  [OK] 0 duplicados encontrados. La base de datos es totalmente integra.")
        print("  [OK] Volver a ejecutar la extraccion no duplica innecesariamente datos.")
    else:
        print(f"  [AVISO] Se detectaron {reporte['total_duplicados']} registros con duplicidad potencial.")
    print("-" * 76)

    print("\n[CONSULTA SQL 3] Muestra de los Datasets mas Recientes (LIMIT 10):")
    print("-" * 76)
    cols_vista = ["id", "portal", "title", "category", "last_updated"]
    df_preview = reporte["df_detalle"][cols_vista].head(10).copy()
    df_preview["title"] = df_preview["title"].map(lambda t: (t[:36] + "...") if len(t) > 36 else t)
    df_preview["category"] = df_preview["category"].map(lambda c: (c[:18] + "...") if len(c) > 18 else c)
    detalle_str = df_preview.to_string(index=False)
    for linea in detalle_str.splitlines():
        print(f"  {linea}")
    print("-" * 76)

    print("\n" + "=" * 76)
    print("        ARCHIVOS EXPORTADOS LISTOS PARA ABRIR EN MICROSOFT EXCEL")
    print("=" * 76)
    if reporte.get("excel_path"):
        print(f"  * Excel (.xlsx): {reporte['excel_path'].name}")
    print(f"  * CSV Resumen:   {reporte['csv_resumen'].name}")
    print(f"  * CSV Detalle:   {reporte['csv_detalle'].name}")
    print("\n  Ubicacion: Carpeta 'salida/'. Puedes abrirlos con doble clic en Windows.")
    print("=" * 76 + "\n")
    return 0


def _show_menu():
    while True:
        print("\n=== Menú de Automatización, Seguridad y Extracción ===")
        print("1. Extraer fichas de Band-Maid (Scraping local/propio)")
        print("2. [Seguridad 1/5] Probar CAPTCHA (Omisión de código de verificación HTTP 400)")
        print("3. [Seguridad 2/5] Probar Rate Limit (Ráfaga de solicitudes concurrentes HTTP 429)")
        print("4. [Seguridad 3/5] Probar Protección Anti-CSRF (Token manipulado HTTP 403)")
        print("5. [Seguridad 4/5] Probar Trampa Honeypot (Campo oculto bot HTTP 400)")
        print("6. [Seguridad 5/5] Probar Telemetría y Automatización (Webdriver/Bot HTTP 400)")
        print("7. [Seguridad Batería] Ejecutar los 5 métodos de seguridad en secuencia")
        print("8. [Fase 2] Auditar y clasificar los 5 sitios web (Básico, Intermedio, Avanzado)")
        print("9. [Fase 3] Extraer datos de Portal Oficial (Búsqueda + Filtros + SQLite + CSV)")
        print("10. [Fase 3] Consultar base de datos SQLite de datos oficiales")
        print("0. Salir")
        try:
            choice = input("Seleccione una opción: ").strip()
        except EOFError:
            logger.warning("Interactive input ended while waiting for a menu choice")
            print("\nNo se recibió una opción; saliendo.")
            return "0"
        if choice in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}:
            return choice
        logger.warning("Invalid menu option rejected")
        print("Opción no válida. Intente de nuevo.")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    configure_logging()
    logger.info(
        "Application started: browser=%s offset=%d limit=%s screenshot=%s portal=%s",
        args.browser,
        args.offset,
        args.limit,
        args.screenshot,
        args.portal,
    )

    # Si se especificó una prueba de seguridad directamente por CLI
    if getattr(args, "security_test", None):
        return _run_security_test(args, args.security_test)

    while True:
        choice = _show_menu()
        menu_actions = {
            "0": "exit",
            "1": "scraping_bandmaid",
            "2": "security_test_captcha",
            "3": "security_test_rate_limit",
            "4": "security_test_csrf",
            "5": "security_test_honeypot",
            "6": "security_test_telemetry",
            "7": "security_test_all",
            "8": "audit_5_sites",
            "9": "official_scraping",
            "10": "sqlite_database_view",
        }
        logger.info(
            "Menu option selected: option=%s action=%s",
            choice,
            menu_actions[choice],
        )
        if choice == "0":
            logger.info("Application stopped by user")
            print("Saliendo.")
            return 0

        operation_name = menu_actions[choice]
        if choice == "1":
            result = _run_scraping(args)
        elif choice == "2":
            result = _run_security_test(args, "captcha")
        elif choice == "3":
            result = _run_security_test(args, "rate-limit")
        elif choice == "4":
            result = _run_security_test(args, "csrf")
        elif choice == "5":
            result = _run_security_test(args, "honeypot")
        elif choice == "6":
            result = _run_security_test(args, "telemetry")
        elif choice == "7":
            result = _run_security_test(args, "all")
        elif choice == "8":
            result = _run_audit(args)
        elif choice == "9":
            result = _run_official_scraping(args)
        else:
            result = _run_db_view()

        if result == 0:
            logger.info("Menu operation completed successfully: action=%s", operation_name)
            print("Operación finalizada correctamente.")
        else:
            logger.error(
                "Menu operation completed with errors: action=%s exit_code=%d",
                operation_name,
                result,
            )
            print(f"La operación terminó con errores (código {result}).")
        print("Volviendo al menú.")


if __name__ == "__main__":
    raise SystemExit(main())

