"""Módulo de persistencia en SQLite para datos oficiales y auditorías."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from config import OUTPUT_DIR_NAME
from logging_config import get_logger

logger = get_logger(__name__)

DB_NAME = "datos_oficiales.db"


def get_db_path() -> Path:
    """Devuelve la ruta absoluta al archivo SQLite en la carpeta de salida."""
    output_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / DB_NAME


def init_db() -> Path:
    """Inicializa la base de datos SQLite y crea las tablas necesarias si no existen."""
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Tabla para datasets oficiales extraídos
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets_oficiales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portal TEXT NOT NULL,
                    title TEXT NOT NULL,
                    organization TEXT,
                    category TEXT,
                    description TEXT,
                    last_updated TEXT,
                    resource_url TEXT,
                    page INTEGER,
                    extracted_at TEXT NOT NULL
                )
                """
            )
            # Índices para búsquedas rápidas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portal ON datasets_oficiales(portal)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON datasets_oficiales(category)")

            # Tabla para el registro de auditoría de sitios (Fase 2)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auditoria_sitios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    url TEXT NOT NULL,
                    nivel TEXT NOT NULL,
                    status_http INTEGER,
                    robots_txt_status TEXT,
                    waf_detectado TEXT,
                    captcha_detectado TEXT,
                    tecnologias_js TEXT,
                    viabilidad_legal TEXT,
                    auditado_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        logger.info("SQLite database initialized successfully at %s", db_path)
    except Exception:
        logger.exception("Failed to initialize SQLite database at %s", db_path)
        raise
    return db_path


def guardar_en_sqlite(df: pd.DataFrame, table_name: str = "datasets_oficiales") -> int:
    """Guarda un DataFrame de Pandas en la base de datos SQLite.
    
    Devuelve la cantidad de registros insertados.
    """
    if df is None or df.empty:
        logger.info("No rows to save in SQLite table '%s'", table_name)
        return 0

    db_path = init_db()
    try:
        with sqlite3.connect(db_path) as conn:
            # Excluir columna 'id' si ya viene en el DataFrame para dejar que SQLite autoincremente
            df_to_save = df.copy()
            if "id" in df_to_save.columns:
                df_to_save = df_to_save.drop(columns=["id"])
            df_to_save.to_sql(table_name, conn, if_exists="append", index=False)
        inserted_count = len(df)
        logger.info("Saved %d rows into SQLite table '%s'", inserted_count, table_name)
        return inserted_count
    except Exception:
        logger.exception("Error saving DataFrame into SQLite table '%s'", table_name)
        raise


def consultar_sqlite(table_name: str = "datasets_oficiales", limit: int = 20) -> pd.DataFrame:
    """Consulta los últimos registros guardados en la tabla especificada."""
    db_path = get_db_path()
    if not db_path.exists():
        return pd.DataFrame()

    try:
        with sqlite3.connect(db_path) as conn:
            query = f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ?"
            return pd.read_sql_query(query, conn, params=(limit,))
    except Exception:
        logger.exception("Error querying SQLite table '%s'", table_name)
        return pd.DataFrame()


def contar_registros_sqlite(table_name: str = "datasets_oficiales") -> int:
    """Devuelve el total de filas registradas en una tabla."""
    db_path = get_db_path()
    if not db_path.exists():
        return 0
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception:
        return 0
