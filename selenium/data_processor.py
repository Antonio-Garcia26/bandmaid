"""Limpieza, filtrado, vista previa y almacenamiento de los datos."""

from datetime import datetime
from pathlib import Path
import re

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
