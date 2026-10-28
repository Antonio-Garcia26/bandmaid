"""Módulo de persistencia en SQLite para datos oficiales y auditorías."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional
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
                    num_resources INTEGER DEFAULT 1,
                    description TEXT,
                    last_updated TEXT,
                    resource_url TEXT,
                    page INTEGER,
                    extracted_at TEXT NOT NULL
                )
                """
            )
            # Asegurar migración de num_resources si la tabla ya existía
            cursor.execute("PRAGMA table_info(datasets_oficiales)")
            columnas = [info[1] for info in cursor.fetchall()]
            if "num_resources" not in columnas:
                cursor.execute("ALTER TABLE datasets_oficiales ADD COLUMN num_resources INTEGER DEFAULT 1")

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
    """Guarda un DataFrame de Pandas en SQLite evitando duplicados existentes en la base de datos.
    
    Devuelve la cantidad de registros nuevos insertados.
    """
    if df is None or df.empty:
        logger.info("No rows to save in SQLite table '%s'", table_name)
        return 0

    db_path = init_db()
    try:
        with sqlite3.connect(db_path) as conn:
            # Consultar registros ya existentes para no reinsertarlos (idempotencia)
            cursor = conn.cursor()
            cursor.execute(f"SELECT title, resource_url FROM {table_name}")
            existentes = {(str(r[0]), str(r[1])) for r in cursor.fetchall()}

            df_to_save = df.copy()
            if "id" in df_to_save.columns:
                df_to_save = df_to_save.drop(columns=["id"])

            # Filtrar filas que ya existen en la base de datos
            mascara_nuevos = df_to_save.apply(
                lambda row: (str(row.get("title")), str(row.get("resource_url"))) not in existentes,
                axis=1
            )
            df_nuevos = df_to_save[mascara_nuevos]

            if not df_nuevos.empty:
                df_nuevos.to_sql(table_name, conn, if_exists="append", index=False)
                inserted_count = len(df_nuevos)
            else:
                inserted_count = 0

        logger.info("Saved %d new unique rows into SQLite table '%s' (skipped %d duplicates)", inserted_count, table_name, len(df_to_save) - inserted_count)
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


def generar_reporte_sql_analitico() -> dict:
    """Ejecuta consultas analíticas SQL en SQLite y genera archivos CSV y Excel listos para abrir."""
    from datetime import datetime
    db_path = get_db_path()
    output_dir = db_path.parent
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    if not db_path.exists():
        return {"error": "Base de datos SQLite no encontrada."}

    with sqlite3.connect(db_path) as conn:
        # Consulta 1: Resumen agrupado por portal y categoría con conteos
        q_resumen = """
            SELECT portal, category, COUNT(*) AS total_datasets
            FROM datasets_oficiales
            GROUP BY portal, category
            ORDER BY total_datasets DESC
        """
        df_resumen = pd.read_sql_query(q_resumen, conn)

        # Consulta 2: Auditoría estricta de registros duplicados por título y recurso
        q_duplicados = """
            SELECT title, resource_url, COUNT(*) AS repeticiones
            FROM datasets_oficiales
            GROUP BY title, resource_url
            HAVING COUNT(*) > 1
        """
        df_duplicados = pd.read_sql_query(q_duplicados, conn)

        # Consulta 3: Vista de detalle de los registros más recientes
        q_detalle = """
            SELECT id, portal, title, organization, category, last_updated, resource_url, extracted_at
            FROM datasets_oficiales
            ORDER BY id DESC
            LIMIT 50
        """
        df_detalle = pd.read_sql_query(q_detalle, conn)

    # Exportar a CSV con UTF-8 BOM para apertura perfecta en Excel en español
    csv_resumen = output_dir / f"reporte_sql_resumen_{timestamp}.csv"
    csv_detalle = output_dir / f"reporte_sql_detalle_{timestamp}.csv"
    df_resumen.to_csv(csv_resumen, index=False, encoding="utf-8-sig")
    df_detalle.to_csv(csv_detalle, index=False, encoding="utf-8-sig")

    # Exportar a Excel (.xlsx) con hojas múltiples
    excel_path = output_dir / f"reporte_sql_analitico_{timestamp}.xlsx"
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_resumen.to_excel(writer, sheet_name="Resumen por Categoria", index=False)
            df_detalle.to_excel(writer, sheet_name="Detalle Datasets", index=False)
            df_duplicados.to_excel(writer, sheet_name="Auditoria Duplicados", index=False)
    except Exception as exc:
        logger.debug("Excel export error: %s", exc)
        excel_path = None

    return {
        "df_resumen": df_resumen,
        "df_duplicados": df_duplicados,
        "df_detalle": df_detalle,
        "csv_resumen": csv_resumen,
        "csv_detalle": csv_detalle,
        "excel_path": excel_path,
        "total_registros": contar_registros_sqlite("datasets_oficiales"),
        "total_duplicados": len(df_duplicados),
    }


def guardar_en_postgres_opcional(df: pd.DataFrame, table_name: str = "datasets_oficiales", postgres_url: Optional[str] = None) -> Optional[int]:
    """Guarda el DataFrame en PostgreSQL si se suministra una cadena de conexión o variable POSTGRES_URL.
    
    Permite alternar de SQLite a PostgreSQL según los requerimientos de persistencia.
    """
    import os
    url = postgres_url or os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if not url:
        logger.debug("PostgreSQL URL not configured; using local SQLite storage as primary database.")
        return None

    try:
        from sqlalchemy import create_engine  # type: ignore
        engine = create_engine(url)

        df_to_save = df.copy()
        if "id" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["id"])
        df_to_save.to_sql(table_name, engine, if_exists="append", index=False)
        logger.info("Successfully persisted %d rows into PostgreSQL table '%s'", len(df_to_save), table_name)
        return len(df_to_save)
    except Exception as err:
        logger.warning("PostgreSQL sync could not be completed (%s); SQLite remains unaffected.", err)
        return None

