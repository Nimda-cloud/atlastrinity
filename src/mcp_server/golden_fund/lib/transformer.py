"""
Data Transformation Layer for Golden Fund
Ported from etl_module/src/transformation/data_transformer.py
"""

import logging
from datetime import datetime
from typing import Any, Optional, Union, cast

from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO, encoding="utf-8")
logger = logging.getLogger("golden_fund.transformer")

# Import validation module for integration
try:
    from .validation import DataValidator as ImportedDataValidator
    from .validation import ValidationResult as ImportedValidationResult
    DataValidator = ImportedDataValidator
    ValidationResult = ImportedValidationResult
except ImportError:
    # Fallback for when validation module is not available
    DataValidator: type[Any] | None = None
    ValidationResult: type[Any] | None = None


class TransformResult:
    def __init__(self, success: bool, data: Any | None = None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error


class UnifiedSchema(BaseModel):
    """
    Unified conceptual schema for Golden Fund entities.
    Flexible enough to hold diverse data but enforced key metadata.
    """

    name: str = Field(..., description="Entity name or title")
    type: str = Field(default="unknown", description="Entity type (e.g. person, company, dataset)")
    content: Any = Field(default=None, description="Main content or payload")
    source_format: str = Field(..., description="Original format")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataTransformer:
    def __init__(self):
        self.schema = UnifiedSchema
        self.validator = DataValidator() if DataValidator is not None else None
        logger.info("DataTransformer initialized")

    def transform(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        source_format: str = "unknown",
        validate_completeness: bool = False,
    ) -> TransformResult:
        try:
            if isinstance(data, list):
                transformed = []
                for item in data:
                    res = self._transform_item(item, source_format)
                    if res:
                        transformed.append(res)

                # Add validation checkpoint if requested
                if validate_completeness and self.validator is not None and DataValidator is not None:
                    validation_res = self.validator.validate_data_completeness(
                        transformed, context="transformation"
                    )
                    if not validation_res.success:
                        logger.warning(
                            f"Data completeness validation failed: {validation_res.error}"
                        )
                        # Continue with transformed data but add warning
                        return TransformResult(
                            True,
                            data=transformed,
                            error=f"Validation warning: {validation_res.error}",
                        )

                return TransformResult(True, data=transformed)
            else:
                res = self._transform_item(data, source_format)
                return TransformResult(
                    True if res else False, data=res, error="Validation failed" if not res else None
                )
        except Exception as e:
            return TransformResult(False, error=f"Transformation error: {e}")

    def _transform_item(self, item: dict[str, Any], source_format: str) -> dict[str, Any] | None:
        try:
            # Heuristic mapping flexibility
            name = item.get("name") or item.get("title") or item.get("id") or "Untitled"

            # Construct unified record
            record = {
                "name": str(name),
                "type": item.get("type", "entity"),
                "content": item,  # Store full original
                "source_format": source_format,
                "metadata": {k: v for k, v in item.items() if k not in ["name", "title"]},
            }

            # Validate
            validated = self.schema(**record)
            return cast(dict[str, Any] | None, validated.model_dump())
        except ValidationError as e:
            logger.warning(f"Validation failed for item: {e}")
            return None
