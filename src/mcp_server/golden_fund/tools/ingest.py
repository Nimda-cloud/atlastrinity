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


def _get_scrape_result(url: str, type: str, scraper: DataScraper):
    """Helper to handle the first stage of ingestion: scraping."""
    if type == "api":
        return scraper.scrape_api_endpoint(url), ".json"
    elif type == "web_page":
        return scraper.scrape_web_page(url), ".json"
    
    # Generic file download
    result = scraper.download_file(url)
    if type in ["csv", "json", "xml", "parquet"]:
        ext = f".{type}"
    elif type in ["excel", "xlsx", "xls"]:
        ext = ".xlsx"
    else:
        path = Path(url)
        ext = path.suffix if path.suffix else ".bin"
    return result, ext


def _parse_raw_data(raw_file: Path, ext: str, type: str, parser: DataParser):
    """Helper to handle the second stage: parsing."""
    format_hint = ext.lstrip(".").lower()
    if format_hint == "bin" and type not in ["file", "web_page", "api"]:
        format_hint = type
    
    return parser.parse(raw_file, format_hint=format_hint)


async def ingest_dataset(
    url: str, type: str = "web_page", process_pipeline: list[str] | None = None
) -> str:
    """Ingest a dataset from a URL."""
    scraper = DataScraper()
    parser = DataParser()
    validator = DataValidator()
    sql_storage = SQLStorage()
    vector_storage = VectorStorage()

    if process_pipeline is None:
        process_pipeline = ["parse", "store_sql", "vectorize"]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    logger.info(f"Starting ingestion run {run_id} for {url} ({type})")

    result, ext = _get_scrape_result(url, type, scraper)
    if not result.success:
        msg = f"Ingestion failed during retrieval: {result.error}"
        logger.error(msg)
        return msg

    if not result.data:
        return "No data retrieved"

    raw_file = RAW_DIR / f"{run_id}_raw{ext}"
    save_res = scraper.save_data(result.data, raw_file)
    if not save_res.success:
        return f"Failed to save raw data: {save_res.error}"

    summary = f"Ingestion {run_id} successful. Raw data: {raw_file.name}."
    parsed_df = None

    if "parse" in process_pipeline:
        parse_res = _parse_raw_data(raw_file, ext, type, parser)
        if parse_res.success:
            data = parse_res.data
            if isinstance(data, pd.DataFrame):
                parsed_df = data
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                parsed_df = pd.DataFrame(data)
            elif isinstance(data, dict):
                parsed_df = pd.DataFrame([data])
            summary += f" Parsed {len(parsed_df) if parsed_df is not None else 0} records."
        else:
            summary += f" Parsing failed: {parse_res.error}"

    if "store_sql" in process_pipeline and parsed_df is not None:
        store_res = sql_storage.store_dataset(parsed_df, f"dataset_{run_id}", source_url=url)
        summary += f" Stored in SQL table '{store_res.target}'." if store_res.success else f" SQL Storage failed: {store_res.error}"

    if "vectorize" in process_pipeline and parsed_df is not None:
        desc = f"Dataset from {url} ({type}). Columns: {', '.join(parsed_df.columns[:10])}. Rows: {len(parsed_df)}."
        vector_data = {"name": f"dataset_{run_id}", "type": "dataset", "content": desc, "source_url": url, "format": ext, "sql_table": f"dataset_{run_id}"}
        vec_res = vector_storage.store(vector_data)
        summary += " Indexed for semantic search." if vec_res.success else f" Vector indexing failed: {vec_res.error}"

    if "validate" in process_pipeline and parsed_df is not None:
        val_data = [{str(k): v for k, v in record.items()} for record in parsed_df.to_dict(orient="records")]
        validation_res = validator.validate_data_completeness(val_data, context=f"ingestion_{run_id}")
        summary += " Validation passed." if validation_res.success else f" Validation warning: {validation_res.error}"

    return summary
