"""
Unified Data Format Parsers for Golden Fund
Ported and consolidated from etl_module/src/parsing/formats/
"""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd


class ParseResult:
    """Result container for parsed data."""

    def __init__(self, success: bool, data: Any | None = None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata: dict[str, Any] = {}


class JSONParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            # Try pandas first for clear structure
            try:
                df = pd.read_json(file_path, **kwargs)
                return ParseResult(True, data=df)
            except ValueError:
                # Fallback to standard json
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                return ParseResult(True, data=data)
        except Exception as e:
            return ParseResult(False, error=f"JSON parse error: {e}")


class CSVParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        encodings = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
        last_error = ""

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, **kwargs)
                return ParseResult(True, data=df)
            except UnicodeDecodeError:
                continue
            except Exception as e:
                last_error = str(e)
                break
        
        return ParseResult(False, error=f"CSV parse error: {last_error or 'Unknown encoding'}")


class XMLParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            tree = ET.parse(file_path)  # nosec B314
            root = tree.getroot()
            data = self._element_to_dict(root)
            return ParseResult(True, data=data)
        except Exception as e:
            return ParseResult(False, error=f"XML parse error: {e}")

    def _element_to_dict(self, element: ET.Element) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if element.attrib:
            result["@attributes"] = element.attrib

        for child in element:
            child_data = self._element_to_dict(child)
            if child.tag in result:
                current_val = result[child.tag]
                if isinstance(current_val, list):
                    current_val.append(child_data)
                else:
                    result[child.tag] = [current_val, child_data]
            else:
                result[child.tag] = child_data

        if element.text and element.text.strip():
            if result:
                result["#text"] = element.text.strip()
            else:
                return {"#text": element.text.strip()}
        return result


class ExcelParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            # Read all sheets by default if not specified
            sheet_name = kwargs.get("sheet_name", None)
            df_dict = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

            if isinstance(df_dict, dict):
                # Multiple sheets, return dict of DataFrames
                return ParseResult(True, data=df_dict)
            else:
                # Single DataFrame
                return ParseResult(True, data=df_dict)
        except Exception as e:
            return ParseResult(False, error=f"Excel parse error: {e}")


class ParquetParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            df = pd.read_parquet(file_path, **kwargs)
            return ParseResult(True, data=df)
        except Exception as e:
            return ParseResult(False, error=f"Parquet parse error: {e}")
