"""
Unified Data Format Parsers for Golden Fund
Ported and consolidated from etl_module/src/parsing/formats/
"""

import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import xml.etree.ElementTree as ET
import pandas as pd

class ParseResult:
    """Result container for parsed data."""
    def __init__(self, success: bool, data: Any | None = None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = {}

class JSONParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            # Try pandas first for clear structure
            try:
                df = pd.read_json(file_path, **kwargs)
                return ParseResult(True, data=df)
            except ValueError:
                # Fallback to standard json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ParseResult(True, data=data)
        except Exception as e:
            return ParseResult(False, error=f"JSON parse error: {e}")

class CSVParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            df = pd.read_csv(file_path, **kwargs)
            return ParseResult(True, data=df)
        except Exception as e:
            return ParseResult(False, error=f"CSV parse error: {e}")

class XMLParser:
    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            data = self._xml_to_dict(root)
            return ParseResult(True, data=data) 
        except Exception as e:
            return ParseResult(False, error=f"XML parse error: {e}")

    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        result = {}
        if element.attrib:
            result["@attributes"] = element.attrib
        
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if isinstance(result[child.tag], list):
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = [result[child.tag], child_data]
            else:
                result[child.tag] = child_data
        
        if element.text and element.text.strip():
            if result:
                result["#text"] = element.text.strip()
            else:
                return element.text.strip()
        return result
