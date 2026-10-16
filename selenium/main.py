"""CLI para extraer y procesar datos públicos de Band-Maid."""

import argparse
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from data_processor import guardar_captura, guardar_resultados, procesar_datos
from driver_manager import cerrar_driver, iniciar_driver
from logging_config import configure_logging, get_logger
from scraper import HumanVerificationDetected, extraer_miembros
from security_tests import run_public_security_test

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


def _show_menu():
    while True:
        print("\n=== Herramientas Band-Maid ===")
        print("1. Extraer información de la web (scraping)")
        print("2. Intentar registro sin CAPTCHA (se espera que falle)")
        print("3. Enviar hasta seis solicitudes para probar el rate limit")
        print("0. Salir")
        try:
            choice = input("Seleccione una opción: ").strip()
        except EOFError:
            logger.warning("Interactive input ended while waiting for a menu choice")
            print("\nNo se recibió una opción; saliendo.")
            return "0"
        if choice in {"0", "1", "2", "3"}:
            return choice
        logger.warning("Invalid menu option rejected")
        print("Opción no válida. Intente de nuevo.")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    configure_logging()
    logger.info(
        "Application started: browser=%s offset=%d limit=%s screenshot=%s",
        args.browser,
        args.offset,
        args.limit,
        args.screenshot,
    )

    while True:
        choice = _show_menu()
        menu_actions = {
            "0": "exit",
            "1": "scraping",
            "2": "registration_without_captcha",
            "3": "rate_limit_check",
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
        else:
            result = _run_security_test(args, "rate-limit")

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
