"""CLI para extraer y procesar datos públicos de Band-Maid."""

import argparse
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from database import consultar_sqlite, contar_registros_sqlite
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
    return parser


def _validate_args(parser, args):
    if args.offset < 0:
        parser.error("--offset no puede ser negativo.")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit no puede ser negativo.")


def _pause_for_review():
    print(
        "Revise el navegador manualmente. El programa no resolverá ni sorteará el desafío; "
        "la extracción se detendrá al cerrar esta pausa."
    )
    try:
        input("Presione Enter cuando termine la revisión para detener y cerrar el navegador...")
    except EOFError:
        print("No hay entrada interactiva; se detiene la extracción.")


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
        test_result = run_public_security_test(driver, mode)
        if mode == "register":
            stage = (
                test_result.get("stage")
                if isinstance(test_result, dict)
                and test_result.get("stage") in {"csrf", "register"}
                else "unavailable"
            )
            status = (
                test_result.get("status")
                if isinstance(test_result, dict)
                and isinstance(test_result.get("status"), int)
                and not isinstance(test_result.get("status"), bool)
                else None
            )
            logger.info(
                "Security test result: mode=%s stage=%s http_status=%s",
                mode,
                stage,
                status,
            )
        else:
            responses = (
                test_result.get("results")
                if isinstance(test_result, dict)
                else test_result
            )
            responses = responses if isinstance(responses, list) else []
            statuses = [
                item.get("status")
                for item in responses
                if isinstance(item, dict)
                and isinstance(item.get("status"), int)
                and not isinstance(item.get("status"), bool)
            ]
            logger.info(
                "Security test result: mode=%s responses_received=%d rate_limit_observed=%s",
                mode,
                len(statuses),
                429 in statuses,
            )
        logger.info("Security test operation completed: mode=%s", mode)
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

    print("\n" + "=" * 60)
    print("EXTRACCIÓN DE DATOS OFICIALES CON SELENIUM (FASE 3)")
    print(f"Portal objetivo: {portal_choice} | Búsqueda: '{search_query}' | Páginas: {max_pages}")
    print("=" * 60)

    driver = None
    records = []
    challenge_detected = False
    try:
        driver, wait = iniciar_driver(args.browser)
        if portal_choice == "datos_cdmx":
            records = extraer_datos_cdmx(driver, wait, query=search_query, max_pages=max_pages)
        else:
            records = extraer_datos_data_gov(driver, wait, query=search_query, max_pages=max_pages)
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

    print(f"\nProcesando y limpiando {len(records)} registros con Pandas...")
    df = procesar_datos_oficiales(records, query=args.query, offset=args.offset, limit=args.limit)

    print(f"\nRegistros procesados y estructurados: {len(df)}")
    if challenge_detected:
        print("(La extracción se pausó preventivamente por desafío de verificación)")

    print("\nVista previa del Dataset Oficial estructurado:")
    cols_preview = ["title", "organization", "category", "last_updated"]
    cols_exist = [c for c in cols_preview if c in df.columns]
    print(df[cols_exist].head(15).to_string(index=False) if not df.empty else "(sin registros)")

    # Guardar en SQLite y CSV
    try:
        storage_info = guardar_resultados_oficiales(df, portal_tag=portal_choice)
        print("\n" + "-" * 60)
        print("ALMACENAMIENTO PERSISTENTE COMPLETADO:")
        print(f"  • Base de Datos SQLite: salida/datos_oficiales.db (filas añadidas: {storage_info['sqlite_rows']})")
        print(f"  • Archivo CSV estructurado: {storage_info['csv_path'].name}")
        if storage_info.get("excel_path"):
            print(f"  • Archivo Excel: {storage_info['excel_path'].name}")
        print("-" * 60)
    except Exception as error:
        logger.exception("Could not save official data results: %s", error)
        print(f"No se pudieron guardar los resultados oficiales ({type(error).__name__}).")
        return 1

    return 0


def _run_db_view():
    """Consulta y muestra los registros almacenados en la base de datos SQLite."""
    total = contar_registros_sqlite("datasets_oficiales")
    total_audit = contar_registros_sqlite("auditoria_sitios")
    print("\n" + "=" * 60)
    print("CONSULTA DE BASE DE DATOS SQLITE (salida/datos_oficiales.db)")
    print(f"Total registros datasets_oficiales: {total} | Total auditorías registradas: {total_audit}")
    print("=" * 60)

    if total == 0:
        print("La tabla 'datasets_oficiales' aún no tiene registros.")
        print("Ejecute la opción 5 para extraer y almacenar datos de un portal oficial.")
        return 0

    df = consultar_sqlite("datasets_oficiales", limit=15)
    cols = ["id", "portal", "title", "category", "last_updated"]
    cols_exist = [c for c in cols if c in df.columns]
    print(df[cols_exist].to_string(index=False))
    return 0


def _show_menu():
    while True:
        print("\n=== Menú de Automatización, Seguridad y Extracción ===")
        print("1. Extraer fichas de Band-Maid (Scraping local/propio)")
        print("2. Intentar registro sin CAPTCHA (Seguridad Band-Maid)")
        print("3. Enviar solicitudes para probar rate limit (Band-Maid)")
        print("4. [Fase 2] Auditar y clasificar los 5 sitios web (Básico, Intermedio, Avanzado)")
        print("5. [Fase 3] Extraer datos de Portal Oficial (Búsqueda + Filtros + SQLite + CSV)")
        print("6. [Fase 3] Consultar base de datos SQLite de datos oficiales")
        print("0. Salir")
        try:
            choice = input("Seleccione una opción: ").strip()
        except EOFError:
            logger.warning("Interactive input ended while waiting for a menu choice")
            print("\nNo se recibió una opción; saliendo.")
            return "0"
        if choice in {"0", "1", "2", "3", "4", "5", "6"}:
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

    while True:
        choice = _show_menu()
        menu_actions = {
            "0": "exit",
            "1": "scraping_bandmaid",
            "2": "registration_without_captcha",
            "3": "rate_limit_check",
            "4": "audit_5_sites",
            "5": "official_scraping",
            "6": "sqlite_database_view",
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
            result = _run_security_test(args, "register")
        elif choice == "3":
            result = _run_security_test(args, "rate-limit")
        elif choice == "4":
            result = _run_audit(args)
        elif choice == "5":
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
