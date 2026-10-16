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
from scraper import HumanVerificationDetected, extraer_miembros


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


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)

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
        print(f"\nATENCIÓN: {challenge}")
        _pause_for_review()
    except Exception as error:
        print(f"\nNo se pudo completar la extracción ({type(error).__name__}): {error}")
        return 1
    finally:
        if args.screenshot and driver is not None:
            try:
                screenshot_path = guardar_captura(driver)
                print(f"Captura guardada en: {screenshot_path}")
            except Exception as screenshot_error:
                print(f"No se pudo guardar la captura ({type(screenshot_error).__name__}).")
        cerrar_driver(driver)

    print(
        "Band-Maid: se consulta la página pública y las fichas de #miembros. "
        "El sitio no ofrece controles propios de búsqueda ni paginación."
    )

    df = procesar_datos(
        records,
        query=args.query,
        offset=args.offset,
        limit=args.limit,
    )
    print(f"\nPáginas procesadas: {pages_processed}")
    print(f"Registros extraídos: {len(records)} · filas tras limpieza/filtros: {len(df)}")
    if challenge_detected:
        print("La extracción se detuvo al detectar un desafío de acceso.")
    print("\nVista previa del DataFrame procesado:")
    print(df.head(20).to_string(index=False) if not df.empty else "(sin registros)")

    output_path = guardar_resultados(df)
    print(f"\nCSV guardado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
