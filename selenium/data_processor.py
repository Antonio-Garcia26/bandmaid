"""Limpieza, filtrado, vista previa y almacenamiento de los datos."""

from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import pandas as pd


from config import OUTPUT_DIR_NAME
from logging_config import get_logger

logger = get_logger(__name__)


COLUMNS = ["name", "role", "image_alt", "page", "url", "extracted_at"]


def _clean_text(value):
    if pd.isna(value):
        return pd.NA
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned if cleaned else pd.NA


def procesar_datos(records, query=None, offset=0, limit=None):
    """Limpia los registros, aplica filtros locales y pagina el DataFrame."""
    try:
        records_received = len(records)
    except TypeError:
        records_received = None
    except Exception:
        logger.exception("Data processing failed while counting input records")
        raise
    try:
        query_filter_applied = bool(query)
    except Exception:
        logger.exception("Data processing failed while evaluating the local query filter")
        raise
    logger.info(
        "Data processing started: records_received=%s offset=%s limit=%s query_filter=%s",
        records_received if records_received is not None else "unknown",
        offset,
        limit,
        query_filter_applied,
    )

    try:
        if offset < 0:
            raise ValueError("--offset no puede ser negativo.")
        if limit is not None and limit < 0:
            raise ValueError("--limit no puede ser negativo.")

        df = pd.DataFrame(records)
        rows_before_cleaning = len(df)
        for column in COLUMNS:
            if column not in df.columns and column != "extracted_at":
                df[column] = pd.NA

        for column in ("name", "role", "image_alt", "url"):
            df[column] = df[column].map(_clean_text)
        df["page"] = pd.to_numeric(df["page"], errors="coerce")
        df = df.dropna(subset=["name", "page", "url"])
        df["role"] = df["role"].fillna("")
        df["image_alt"] = df["image_alt"].fillna("")
        rows_after_cleaning = len(df)
        logger.info(
            "Data cleaning completed: rows_before=%d rows_after=%d rows_removed=%d",
            rows_before_cleaning,
            rows_after_cleaning,
            rows_before_cleaning - rows_after_cleaning,
        )

        rows_before_filter = len(df)
        if query_filter_applied:
            needle = query.casefold()
            text_columns = [column for column in df.columns if column != "extracted_at"]
            matches = df[text_columns].fillna("").astype(str).apply(
                lambda column: column.map(lambda value: needle in value.casefold())
            ).any(axis=1)
            df = df[matches]
        rows_after_filter = len(df)
        logger.info(
            "Data filtering completed: query_filter=%s rows_before=%d rows_after=%d",
            query_filter_applied,
            rows_before_filter,
            rows_after_filter,
        )

        extracted_at = datetime.now().astimezone().isoformat(timespec="seconds")
        df["extracted_at"] = extracted_at
        df = df.iloc[offset:] if limit is None else df.iloc[offset:offset + limit]
        result = df.reindex(columns=COLUMNS).reset_index(drop=True)
        logger.info(
            "Data processing completed: rows_before_pagination=%d rows_after_pagination=%d",
            rows_after_filter,
            len(result),
        )
        return result
    except Exception:
        logger.exception(
            "Data processing failed: records_received=%s offset=%s limit=%s query_filter=%s",
            records_received if records_received is not None else "unknown",
            offset,
            limit,
            query_filter_applied,
        )
        raise

def guardar_resultados(df):
    """Guarda un CSV con nombre único dentro de la nueva carpeta salida/."""
    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    row_count = None
    try:
        row_count = len(df)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"bandmaid_{timestamp}.csv"
        suffix = 2
        while output_path.exists():
            output_path = output_dir / f"bandmaid_{timestamp}_{suffix}.csv"
            suffix += 1
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    except Exception:
        logger.exception(
            "CSV save failed: output_directory=%s rows=%s",
            OUTPUT_DIR_NAME,
            row_count,
        )
        raise
    logger.info(
        "CSV saved successfully: path=%s rows=%d",
        output_path.relative_to(Path(__file__).resolve().parent),
        row_count,
    )
    return output_path


def guardar_captura(driver):
    """Guarda una captura PNG de la página visible dentro de salida/."""
    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"bandmaid_{timestamp}.png"
        suffix = 2
        while output_path.exists():
            output_path = output_dir / f"bandmaid_{timestamp}_{suffix}.png"
            suffix += 1
        if not driver.save_screenshot(str(output_path)):
            raise RuntimeError("Selenium no pudo guardar la captura.")
    except Exception:
        logger.exception("Screenshot save failed: output_directory=%s", OUTPUT_DIR_NAME)
        raise
    logger.info(
        "Screenshot saved successfully: path=%s",
        output_path.relative_to(Path(__file__).resolve().parent),
    )
    return output_path


# --- FASE 3: Limpieza y persistencia para datos de portales oficiales ---
OFFICIAL_COLUMNS = [
    "portal",
    "title",
    "organization",
    "category",
    "num_resources",
    "description",
    "last_updated",
    "resource_url",
    "page",
    "extracted_at",
]

_MESES_ES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "setiembre": "09", "octubre": "10",
    "noviembre": "11", "diciembre": "12"
}


def _limpiar_caracteres_especiales(texto: Any) -> str:
    """Elimina caracteres no imprimibles, de control y normaliza espacios en blanco."""
    if texto is None or pd.isna(texto):
        return ""
    s = str(texto)
    # Eliminar caracteres de control ASCII (excepto espacios normales)
    s = re.sub(r"[\x00-\x1f\x7f-\x9f]+", " ", s)
    # Reemplazar múltiples espacios, tabs y saltos de línea por un único espacio
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalizar_numero(valor: Any, default: int = 1) -> int:
    """Transformación y normalización de valores numéricos crudos.
    
    Elimina caracteres especiales, separadores de miles y extrae el valor numérico.
    Ejemplos: '1,250 descargas' -> 1250, '3 recursos' -> 3, '5' -> 5, None -> default.
    """
    if valor is None or pd.isna(valor):
        return default
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return int(valor)
    s = str(valor).replace(",", "").strip()
    m = re.search(r"(\d+)", s)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, OverflowError):
            return default
    return default


def _normalizar_fecha(fecha_str: str) -> str:
    """Transforma fechas con texto informal o en español a formato ISO YYYY-MM-DD."""
    if not fecha_str or pd.isna(fecha_str):
        return datetime.now().astimezone().strftime("%Y-%m-%d")
    s = str(fecha_str).strip().lower()

    # Patrón: "28 de agosto 2026" o "28 de agosto de 2026"
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de)?\s+(\d{4})", s)
    if m:
        dia, mes_nombre, anio = m.groups()
        mes_num = _MESES_ES.get(mes_nombre, "01")
        return f"{anio}-{mes_num}-{int(dia):02d}"

    # Patrón YYYY-MM-DD estándar
    m2 = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m2:
        anio, mes, dia = m2.groups()
        return f"{anio}-{int(mes):02d}-{int(dia):02d}"

    # Solo año
    m3 = re.search(r"\b(20\d{2})\b", s)
    if m3:
        return f"{m3.group(1)}-01-01"

    return datetime.now().astimezone().strftime("%Y-%m-%d")


def procesar_datos_oficiales(records, query=None, offset=0, limit=None) -> pd.DataFrame:
    """Limpia, normaliza con Pandas y valida registros de portales oficiales.
    
    Aplica:
    1. Eliminación de caracteres especiales y no imprimibles.
    2. Normalización de fechas a formato ISO (YYYY-MM-DD).
    3. Normalización y tipado de valores numéricos (num_resources, page).
    4. Filtrado y paginación estructurada.
    """
    if not records:
        logger.warning("Empty records received in procesar_datos_oficiales")
        return pd.DataFrame(columns=OFFICIAL_COLUMNS)

    logger.info("Processing official portal records: total_received=%d query='%s'", len(records), query)
    df = pd.DataFrame(records)

    # 1. Asegurar todas las columnas necesarias
    for col in OFFICIAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # 2. Limpieza de texto (eliminación de caracteres no imprimibles y normalización de espacios)
    for col in ("title", "organization", "category", "description", "resource_url"):
        df[col] = df[col].map(_limpiar_caracteres_especiales)

    # 3. Normalización de fechas a ISO YYYY-MM-DD
    df["last_updated"] = df["last_updated"].map(_normalizar_fecha)

    # 4. Normalización y transformación de valores numéricos con Pandas
    df["num_resources"] = df["num_resources"].map(lambda v: _normalizar_numero(v, default=1)).astype(int)
    df["page"] = pd.to_numeric(df["page"], errors="coerce").fillna(1).astype(int)

    # 5. Descartar filas sin título o URL válida
    df = df[df["title"].str.len() > 2]
    df = df[df["resource_url"].str.startswith("http")]

    # 6. Filtrado local por query si fue suministrado
    if query:
        needle = str(query).strip().casefold()
        coincide = (
            df["title"].str.casefold().str.contains(needle, na=False)
            | df["description"].str.casefold().str.contains(needle, na=False)
            | df["category"].str.casefold().str.contains(needle, na=False)
            | df["organization"].str.casefold().str.contains(needle, na=False)
        )
        df = df[coincide]

    # 7. Timestamp de extracción y paginación
    extracted_at = datetime.now().astimezone().isoformat(timespec="seconds")
    df["extracted_at"] = extracted_at

    # Paginación
    if offset > 0:
        df = df.iloc[offset:]
    if limit is not None and limit > 0:
        df = df.iloc[:limit]

    df = df.reindex(columns=OFFICIAL_COLUMNS).reset_index(drop=True)
    logger.info("Official data processing completed: final_rows=%d", len(df))
    return df


def guardar_resultados_oficiales(df: pd.DataFrame, portal_tag: str = "portal_oficial") -> dict:
    """Guarda el dataset estructurado en SQLite (persistente) y en archivos CSV, JSON y Excel."""
    from database import guardar_en_sqlite, guardar_en_postgres_opcional

    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    # 1. Base de datos relacional SQLite
    filas_sqlite = guardar_en_sqlite(df, table_name="datasets_oficiales")

    # Opcional: Sincronizar con PostgreSQL si existe configuración
    guardar_en_postgres_opcional(df, table_name="datasets_oficiales")

    # 2. Archivo estructurado CSV
    csv_filename = f"{portal_tag}_{timestamp}.csv"
    csv_path = output_dir / csv_filename
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 3. Archivo estructurado JSON
    json_filename = f"{portal_tag}_{timestamp}.json"
    json_path = output_dir / json_filename
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)

    # 4. Archivo estructurado Excel (.xlsx)
    excel_path = None
    try:
        excel_filename = f"{portal_tag}_{timestamp}.xlsx"
        excel_path = output_dir / excel_filename
        df.to_excel(excel_path, index=False, engine="openpyxl")
    except Exception as exc:
        logger.warning("Excel export skipped: %s", exc)

    logger.info("Official data stored: sqlite_rows=%d csv=%s json=%s excel=%s",
                filas_sqlite, csv_path.name, json_path.name, excel_path.name if excel_path else "none")
    return {
        "sqlite_rows": filas_sqlite,
        "csv_path": csv_path,
        "json_path": json_path,
        "excel_path": excel_path,
    }

