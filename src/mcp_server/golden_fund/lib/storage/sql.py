
import logging
import sqlite3
from pathlib import Path
from typing import Any, Literal, Optional

import pandas as pd

from .types import StorageResult

logger = logging.getLogger("golden_fund.storage.sql")


class SQLStorage:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default location: global config directory
            config_root = Path.home() / ".config" / "atlastrinity"
            self.db_dir = config_root / "data" / "golden_fund"
            self.db_path = self.db_dir / "golden.db"
        else:
            self.db_path = db_path
            self.db_dir = db_path.parent

        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database connection and ensure basic structure."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL;")
                # Create a metadata table to track datasets
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS datasets_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dataset_name TEXT UNIQUE,
                        table_name TEXT,
                        source_url TEXT,
                        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        row_count INTEGER
                    )
                    """
                )
            logger.info(f"Initialized SQL storage at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def store_dataset(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        source_url: str = "",
        if_exists: Literal["fail", "replace", "append"] = "append",
    ) -> StorageResult:
        """
        Store a DataFrame as a table in SQLite.
        
        Args:
            df: The DataFrame to store
            dataset_name: Name of the dataset (used for metadata)
            source_url: Where the data came from
            if_exists: 'fail', 'replace', or 'append'
        """
        table_name = self._sanitize_table_name(dataset_name)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store actual data
                df.to_sql(table_name, conn, if_exists=if_exists, index=False)
                
                # Update metadata
                conn.execute(
                    """
                    INSERT INTO datasets_metadata (dataset_name, table_name, source_url, row_count)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(dataset_name) DO UPDATE SET
                        row_count = row_count + ?,
                        ingested_at = CURRENT_TIMESTAMP
                    """,
                    (dataset_name, table_name, source_url, len(df), len(df)),
                )
            
            return StorageResult(
                success=True,
                target=table_name,
                data={
                    "table_name": table_name,
                    "rows": len(df),
                    "db_path": str(self.db_path)
                },
            )
        except Exception as e:
            logger.error(f"Failed to store dataset {dataset_name}: {e}")
            return StorageResult(success=False, target=table_name, error=str(e))

    def query(self, query: str, params: tuple = ()) -> StorageResult:
        """Execute a raw SQL query."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return StorageResult(success=True, target="query", data=df.to_dict(orient="records"))
        except Exception as e:
            return StorageResult(success=False, target="query", error=str(e))

    def _sanitize_table_name(self, name: str) -> str:
        """Sanitize string to be a valid SQL table name."""
        return "".join(c if c.isalnum() else "_" for c in name).lower()
