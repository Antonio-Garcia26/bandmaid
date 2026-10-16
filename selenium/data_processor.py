"""Limpieza, filtrado, vista previa y almacenamiento de los datos."""

from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from config import OUTPUT_DIR_NAME


COLUMNS = ["name", "role", "image_alt", "page", "url", "extracted_at"]


def _clean_text(value):
    if pd.isna(value):
        return pd.NA
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned if cleaned else pd.NA


def procesar_datos(records, query=None, offset=0, limit=None):
    """Limpia los registros, aplica filtros locales y pagina el DataFrame."""
    if offset < 0:
        raise ValueError("--offset no puede ser negativo.")
    if limit is not None and limit < 0:
        raise ValueError("--limit no puede ser negativo.")

    df = pd.DataFrame(records)
    for column in COLUMNS:
        if column not in df.columns and column != "extracted_at":
            df[column] = pd.NA

    for column in ("name", "role", "image_alt", "url"):
        df[column] = df[column].map(_clean_text)
    df["page"] = pd.to_numeric(df["page"], errors="coerce")
    df = df.dropna(subset=["name", "page", "url"])
    df["role"] = df["role"].fillna("")
    df["image_alt"] = df["image_alt"].fillna("")

    if query:
        needle = query.casefold()
        text_columns = [column for column in df.columns if column != "extracted_at"]
        matches = df[text_columns].fillna("").astype(str).apply(
            lambda column: column.map(lambda value: needle in value.casefold())
        ).any(axis=1)
        df = df[matches]

    extracted_at = datetime.now().astimezone().isoformat(timespec="seconds")
    df["extracted_at"] = extracted_at
    df = df.iloc[offset:] if limit is None else df.iloc[offset:offset + limit]
    return df.reindex(columns=COLUMNS).reset_index(drop=True)


def guardar_resultados(df):
    """Guarda un CSV con nombre único dentro de la nueva carpeta salida/."""
    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"bandmaid_{timestamp}.csv"
    suffix = 2
    while output_path.exists():
        output_path = output_dir / f"bandmaid_{timestamp}_{suffix}.csv"
        suffix += 1
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path

def guardar_captura(driver):
    """Guarda una captura PNG de la página visible dentro de salida/."""
    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"bandmaid_{timestamp}.png"
    suffix = 2
    while output_path.exists():
        output_path = output_dir / f"bandmaid_{timestamp}_{suffix}.png"
        suffix += 1
    if not driver.save_screenshot(str(output_path)):
        raise RuntimeError("Selenium no pudo guardar la captura.")
    return output_path
