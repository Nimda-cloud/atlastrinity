"""
Ingestion Tool for Golden Fund
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from ..lib.parser import DataParser
from ..lib.scraper import DataScraper, ScrapeFormat
from ..lib.storage import SQLStorage, VectorStorage
from ..lib.validation import DataValidator

logger = logging.getLogger("golden_fund.tools.ingest")

# Define storage path (Global config directory)
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
DATA_DIR = CONFIG_ROOT / "data" / "golden_fund"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(exist_ok=True)


async def ingest_dataset(
    url: str, type: str = "web_page", process_pipeline: list[str] | None = None
) -> str:
    """
    Ingest a dataset from a URL.

    Args:
        url: URL to ingest
        type: 'web_page', 'api', 'file', 'csv', 'json', 'excel', 'parquet', etc.
        process_pipeline: List of steps (e.g. ['parse', 'vectorize', 'validate'])
                          If None, defaults to ['parse', 'store_sql']
    """
    scraper = DataScraper()
    parser = DataParser()
    validator = DataValidator()
    sql_storage = SQLStorage()
    vector_storage = VectorStorage()

    if process_pipeline is None:
        process_pipeline = ["parse", "store_sql", "vectorize"]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    logger.info(f"Starting ingestion run {run_id} for {url} ({type})")

    # 1. Scrape / Fetch / Download
    if type == "api":
        result = scraper.scrape_api_endpoint(url)
        save_fmt = ScrapeFormat.JSON
        ext = ".json"
    elif type == "web_page":
        result = scraper.scrape_web_page(url)
        save_fmt = ScrapeFormat.JSON  # Saves soup/text structure
        ext = ".json"
    else:
        # Assume generic file download for csv, excel, parquet, etc.
        result = scraper.download_file(url)
        save_fmt = None  # Raw bytes, Scraper detects this

        # Infer extension from URL or type
        if type in ["csv", "json", "xml", "parquet"]:
            ext = f".{type}"
        elif type in ["excel", "xlsx", "xls"]:
            ext = ".xlsx"
        else:
            # Try to get from URL
            path = Path(url)
            ext = path.suffix if path.suffix else ".bin"

    if not result.success:
        msg = f"Ingestion failed during retrieval: {result.error}"
        logger.error(msg)
        return msg

    # 2. Save Raw Data
    if result.data:
        raw_file = RAW_DIR / f"{run_id}_raw{ext}"

        # If scraper returned dict/list (API/Web), save as JSON
        if isinstance(result.data, (dict, list)):
            save_fmt = ScrapeFormat.JSON

        save_res = scraper.save_data(
            result.data, raw_file, save_fmt if save_fmt else ScrapeFormat.JSON
        )

        if not save_res.success:
            return f"Failed to save raw data: {save_res.error}"

        logger.info(f"Saved raw data to {save_res.data}")
    else:
        return "No data retrieved"

    summary = f"Ingestion {run_id} successful. Raw data: {raw_file.name}."

    # 3. Process Pipeline
    parsed_df = None

    if "parse" in process_pipeline:
        # Determine format hint
        format_hint = ext.lstrip(".").lower()
        if format_hint == "bin":
            # inspect file signature or content? For now rely on user 'type' if provided
            if type not in ["file", "web_page", "api"]:
                format_hint = type

        parse_res = parser.parse(raw_file, format_hint=format_hint)

        if parse_res.success:
            data = parse_res.data
            records_count = 0

            # Normalize to DataFrame if possible
            if isinstance(data, pd.DataFrame):
                parsed_df = data
                records_count = len(parsed_df)
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                parsed_df = pd.DataFrame(data)
                records_count = len(parsed_df)
            elif isinstance(data, dict):
                parsed_df = pd.DataFrame([data])
                records_count = 1

            summary += f" Parsed {records_count} records."
        else:
            summary += f" Parsing failed: {parse_res.error}"

    # 4. Storage (SQL)
    if "store_sql" in process_pipeline and parsed_df is not None:
        dataset_name = f"dataset_{run_id}"
        # Store in SQL
        store_res = sql_storage.store_dataset(parsed_df, dataset_name, source_url=url)

        if store_res.success:
            summary += f" Stored in SQL table '{store_res.target}'."
        else:
            summary += f" SQL Storage failed: {store_res.error}"

    # 5. Vectorize (Semantic Search)
    if "vectorize" in process_pipeline and parsed_df is not None:
        # Create a summary node for the dataset
        desc = f"Dataset from {url} ({type}). Columns: {', '.join(parsed_df.columns[:10])}. Rows: {len(parsed_df)}."

        vector_data = {
            "name": f"dataset_{run_id}",
            "type": "dataset",
            "content": desc,
            "source_url": url,
            "format": ext,
            "sql_table": f"dataset_{run_id}",  # Link to SQL table
        }

        vec_res = vector_storage.store(vector_data)
        if vec_res.success:
            summary += " Indexed for semantic search."
        else:
            summary += f" Vector indexing failed: {vec_res.error}"

    # 6. Validation
    if "validate" in process_pipeline and parsed_df is not None:
        # Connect df back to list of dicts for validator
        # Ensure keys are strings for typing compatibility
        val_data = [
            {str(k): v for k, v in record.items()} for record in parsed_df.to_dict(orient="records")
        ]

        validation_res = validator.validate_data_completeness(
            val_data, context=f"ingestion_{run_id}"
        )
        if validation_res.success:
            summary += " Validation passed."
        else:
            summary += f" Validation warning: {validation_res.error}"

    return summary
