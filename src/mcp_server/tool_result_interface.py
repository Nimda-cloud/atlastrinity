from abc import ABC, abstractmethod
from typing import Any


class ToolResult(ABC):
    """
    Abstract base class for all tool result objects.
    Enforces standardized attribute-based access.
    """

    @property
    @abstractmethod
    def success(self) -> bool:
        """Indicates whether the tool execution was successful."""

    @property
    @abstractmethod
    def data(self) -> Any:
        """The main data returned by the tool."""

    @property
    @abstractmethod
    def error(self) -> str | None:
        """Error message if the tool execution failed."""
