"""
Monitoring Configuration Loader

Loads and manages monitoring configuration for Prometheus, Grafana, and OpenSearch integration.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional, cast

import yaml

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


class MonitoringConfig:
    """
    Monitoring configuration loader and manager.
    
    This class handles loading monitoring configuration from the main config.yaml
    and provides access to monitoring settings.
    """

    def __init__(self):
        """
        Initialize the monitoring configuration loader.
        Uses the global SystemConfig singleton to access merged configuration.
        """
        # Lazy import to avoid circular dependencies if any
        from .config_loader import config
        self.system_config = config

    def _get_config_section(self) -> dict[str, Any]:
        """
        Get monitoring configuration section.

        Returns:
            Dictionary containing monitoring configuration
        """
        return cast(dict[str, Any], self.system_config.get("monitoring", {}))

    def get_prometheus_config(self) -> dict[str, Any]:
        """Get Prometheus configuration."""
        return cast(dict[str, Any], self._get_config_section().get("prometheus", {}))

    def get_grafana_config(self) -> dict[str, Any]:
        """Get Grafana configuration."""
        return cast(dict[str, Any], self._get_config_section().get("grafana", {}))

    def get_opensearch_config(self) -> dict[str, Any]:
        """Get OpenSearch configuration."""
        return cast(dict[str, Any], self._get_config_section().get("opensearch", {}))

    def get_tracing_config(self) -> dict[str, Any]:
        """Get tracing configuration."""
        return cast(dict[str, Any], self._get_config_section().get("tracing", {}))

    def get_etl_config(self) -> dict[str, Any]:
        """Get ETL monitoring configuration."""
        return cast(dict[str, Any], self._get_config_section().get("etl", {}))

    def get_alerts_config(self) -> dict[str, Any]:
        """Get alerts configuration."""
        return cast(dict[str, Any], self._get_config_section().get("alerts", {}))

    def is_prometheus_enabled(self) -> bool:
        """Check if Prometheus monitoring is enabled."""
        return cast(bool, self.get_prometheus_config().get("enabled", True))

    def is_grafana_enabled(self) -> bool:
        """Check if Grafana logging is enabled."""
        return cast(bool, self.get_grafana_config().get("enabled", True))

    def is_opensearch_enabled(self) -> bool:
        """Check if OpenSearch integration is enabled."""
        return cast(bool, self.get_opensearch_config().get("enabled", True))

    def is_tracing_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return cast(bool, self.get_tracing_config().get("enabled", True))

    def save_config(self, config: dict[str, Any]) -> bool:
        """
        Save monitoring configuration to file.
        Note: This now updates the main config.yaml file via manual load/dump 
        since SystemConfig is read-only for now.
        """
        from .config_loader import CONFIG_ROOT
        import yaml
        
        config_path = CONFIG_ROOT / "config.yaml"
        
        try:
            # Load full config
            full_config = {}
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    full_config = yaml.safe_load(f) or {}
            
            # Update monitoring section
            if "monitoring" not in full_config:
                full_config["monitoring"] = {}
                
            # Deep merge or replace? Replace specific sections provided
            if "monitoring" in config:
                full_config["monitoring"] = config["monitoring"]
            else:
                # Assume passed config IS the monitoring block
                full_config["monitoring"] = config

            # Save back
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(full_config, f, sort_keys=False)

            logger.info(f"Monitoring configuration saved to {config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving monitoring config: {e}")
            return False


# Global monitoring config instance
monitoring_config = MonitoringConfig()
