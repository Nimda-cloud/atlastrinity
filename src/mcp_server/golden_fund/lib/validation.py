"""
Data Validation Module for Golden Fund
Implements intermediate validation checkpoints in the data pipeline
to inspect extracted data for completeness.
"""

import logging
from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO, encoding="utf-8")
logger = logging.getLogger("golden_fund.validation")


class ValidationResult:
    """Result container for validation operations."""

    def __init__(
        self,
        success: bool,
        data: Any | None = None,
        error: str | None = None,
        warnings: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.warnings = warnings or []
        self.metadata = metadata or {}


class CompletenessCheck(BaseModel):
    """
    Validation checkpoint for data completeness.
    Specifically checks for at least one named employee with a role/position.
    """

    check_name: str = Field(..., description="Name of the validation checkpoint")
    timestamp: datetime = Field(default_factory=datetime.now)
    passed: bool = Field(default=False)
    message: str = Field(default="")
    details: dict[str, Any] = Field(default_factory=dict)


class DataValidator:
    """
    Main validation class for implementing intermediate validation checkpoints.
    """

    def __init__(self):
        logger.info("DataValidator initialized")

    def validate_data_completeness(
        self, data: dict[str, Any] | list[dict[str, Any]], context: str = "unknown"
    ) -> ValidationResult:
        """
        Validate that extracted data contains at least one named employee with a role/position.

        Args:
            data: The data to validate (can be dict or list of dicts)
            context: Context for validation (e.g., 'company_dataset', 'director_dataset')

        Returns:
            ValidationResult with success status and details
        """
        try:
            # Initialize validation metadata
            metadata = {
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "check_type": "completeness",
                "check_name": "employee_role_completeness",
            }

            # Convert single dict to list for uniform processing
            if isinstance(data, dict):
                data_list = [data]
            elif isinstance(data, list):
                data_list = data
            else:
                return ValidationResult(
                    False, error=f"Unsupported data type: {type(data)}", metadata=metadata
                )

            # Check for empty data
            if not data_list:
                return ValidationResult(
                    False, error="Empty dataset - no records to validate", metadata=metadata
                )

            # Define what constitutes a valid employee with role
            employee_fields = {
                "name_fields": ["name", "director", "employee", "person", "full_name"],
                "role_fields": ["position", "role", "title", "job_title", "occupation"],
            }

            found_valid_employee = False
            employee_details = []

            # Check each record for valid employee with role
            for i, record in enumerate(data_list):
                if not isinstance(record, dict):
                    continue

                # Look for name and role in this record
                name_found = None
                role_found = None

                # Check for name fields
                for name_field in employee_fields["name_fields"]:
                    if record.get(name_field):
                        name_found = str(record[name_field])
                        break

                # Check for role fields
                for role_field in employee_fields["role_fields"]:
                    if record.get(role_field):
                        role_found = str(record[role_field])
                        break

                # If we found both name and role, this is a valid employee
                if name_found and role_found:
                    found_valid_employee = True
                    employee_details.append(
                        {
                            "record_index": i,
                            "name": name_found,
                            "role": role_found,
                            "record": record,
                        }
                    )

            # Determine validation result
            if found_valid_employee:
                metadata["validation_passed"] = True
                metadata["valid_employees_found"] = len(employee_details)
                metadata["employee_samples"] = [
                    {"name": emp["name"], "role": emp["role"]}
                    for emp in employee_details[:3]  # Limit to 3 samples
                ]

                return ValidationResult(
                    True,
                    data={
                        "valid_employees": employee_details,
                        "total_records": len(data_list),
                        "validation_type": "employee_role_completeness",
                    },
                    metadata=metadata,
                )
            else:
                # Validation failed - no valid employees found
                metadata["validation_passed"] = False
                metadata["valid_employees_found"] = 0

                return ValidationResult(
                    False,
                    error="Data completeness check failed: No named employees with roles/positions found",
                    warnings=[
                        "Dataset may be incomplete or missing employee information",
                        f"Checked {len(data_list)} records but found no valid employee-role pairs",
                    ],
                    metadata=metadata,
                )

        except Exception as e:
            return ValidationResult(
                False,
                error=f"Validation error: {e!s}",
                metadata={
                    "context": context,
                    "timestamp": datetime.now().isoformat(),
                    "exception_type": type(e).__name__,
                },
            )

    def validate_schema_compatibility(
        self, data: dict[str, Any] | list[dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate that data conforms to expected schema structure.

        Args:
            data: The data to validate

        Returns:
            ValidationResult with schema compatibility status
        """
        try:
            # Basic schema validation - check if data is structured properly
            if isinstance(data, (dict, list)):
                return ValidationResult(
                    True,
                    data={"message": "Data structure is valid"},
                    metadata={"schema_check": "passed"},
                )
            else:
                return ValidationResult(
                    False,
                    error=f"Invalid data structure: expected dict or list, got {type(data)}",
                    metadata={"schema_check": "failed"},
                )
        except Exception as e:
            return ValidationResult(
                False, error=f"Schema validation error: {e!s}", metadata={"exception": str(e)}
            )

    def create_validation_checkpoint(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        checkpoint_name: str = "completeness",
        context: str = "data_pipeline",
    ) -> ValidationResult:
        """
        Create an intermediate validation checkpoint in the data pipeline.

        Args:
            data: The data to validate
            checkpoint_name: Type of validation checkpoint
            context: Context for the validation

        Returns:
            ValidationResult with checkpoint results
        """
        logger.info(f"Running validation checkpoint: {checkpoint_name}")

        if checkpoint_name == "completeness":
            return self.validate_data_completeness(data, context)
        elif checkpoint_name == "schema":
            return self.validate_schema_compatibility(data)
        else:
            return ValidationResult(
                False,
                error=f"Unknown validation checkpoint: {checkpoint_name}",
                metadata={"available_checkpoints": ["completeness", "schema"]},
            )
