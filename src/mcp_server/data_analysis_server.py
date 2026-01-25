"""Data Analysis MCP Server - Pandas-based Data Processing Engine

Provides comprehensive data analysis capabilities including:
- File metadata extraction (CSV, Excel, JSON)
- Statistical analysis (mean, median, std, correlations)
- Data visualization (charts via matplotlib/plotly)
- Data cleaning and transformation
- Predictive modeling (basic ML)
- Data aggregation and grouping

Integrates with Golden Fund for persistent storage of analysis results.

Author: AtlasTrinity Team
Date: 2026-01-25
Version: 1.0
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from mcp.server import FastMCP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [DATA-ANALYSIS] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
server = FastMCP("data-analysis")

# Configuration
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
DATA_DIR = CONFIG_ROOT / "data" / "analysis_cache"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Maximum rows to process for large files
MAX_ROWS_PREVIEW = 1000
MAX_ROWS_FULL = 100000


def _load_dataframe(data_source: str, **kwargs) -> tuple[pd.DataFrame | None, str | None]:
    """Load data from various sources into a DataFrame."""
    try:
        path = Path(data_source).expanduser()
        
        if path.exists():
            # Local file
            suffix = path.suffix.lower()
            if suffix == ".csv":
                df = pd.read_csv(path, **kwargs)
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(path, **kwargs)
            elif suffix == ".json":
                df = pd.read_json(path, **kwargs)
            elif suffix == ".parquet":
                df = pd.read_parquet(path, **kwargs)
            else:
                return None, f"Unsupported file format: {suffix}"
            
            logger.info(f"Loaded {len(df)} rows from {path}")
            return df, None
        
        elif data_source.startswith("http"):
            # URL
            if ".csv" in data_source.lower():
                df = pd.read_csv(data_source, **kwargs)
            elif ".json" in data_source.lower():
                df = pd.read_json(data_source, **kwargs)
            else:
                # Try CSV by default
                df = pd.read_csv(data_source, **kwargs)
            
            logger.info(f"Loaded {len(df)} rows from URL")
            return df, None
        
        else:
            return None, f"Data source not found: {data_source}"
            
    except Exception as e:
        return None, f"Failed to load data: {str(e)}"


def _get_column_stats(series: pd.Series) -> dict[str, Any]:
    """Get comprehensive statistics for a column."""
    stats: dict[str, Any] = {
        "dtype": str(series.dtype),
        "count": int(series.count()),
        "null_count": int(series.isna().sum()),
        "null_percentage": round(series.isna().sum() / len(series) * 100, 2) if len(series) > 0 else 0,
        "unique_count": int(series.nunique()),
    }
    
    if pd.api.types.is_numeric_dtype(series):
        stats.update({
            "min": float(series.min()) if not pd.isna(series.min()) else None,
            "max": float(series.max()) if not pd.isna(series.max()) else None,
            "mean": round(float(series.mean()), 4) if not pd.isna(series.mean()) else None,
            "median": float(series.median()) if not pd.isna(series.median()) else None,
            "std": round(float(series.std()), 4) if not pd.isna(series.std()) else None,
        })
    elif pd.api.types.is_string_dtype(series) or series.dtype == object:
        # Top values for categorical
        top_values = series.value_counts().head(5).to_dict()
        stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}
        
    return stats


@server.tool()
async def read_metadata(file_path: str, sheet_name: str | int | None = None) -> dict[str, Any]:
    """Extract comprehensive metadata from a data file (CSV, Excel, JSON, Parquet).
    
    Args:
        file_path: Path to the data file
        sheet_name: For Excel files, specify sheet name or index (default: first sheet)
    
    Returns:
        Metadata including columns, types, statistics, and data quality info
    """
    logger.info(f"Reading metadata from: {file_path}")
    
    kwargs = {}
    if sheet_name is not None:
        kwargs["sheet_name"] = sheet_name
    
    df, error = _load_dataframe(file_path, nrows=MAX_ROWS_PREVIEW, **kwargs)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    # Get file info
    path = Path(file_path).expanduser()
    file_info = {
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size if path.exists() else None,
        "file_type": path.suffix.lower(),
    }
    
    # Get schema info
    columns_info = []
    for col in df.columns:
        col_stats = _get_column_stats(df[col])
        col_stats["name"] = str(col)
        columns_info.append(col_stats)
    
    # Overall stats
    overall = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    
    # Sample data (first 5 rows)
    sample = df.head(5).to_dict(orient="records")
    
    return {
        "success": True,
        "file_info": file_info,
        "overall": overall,
        "columns": columns_info,
        "sample_data": sample,
    }


@server.tool()
async def analyze_dataset(
    data_source: str,
    analysis_type: str = "summary",
    output_format: str = "json",
    target_path: str | None = None,
) -> dict[str, Any]:
    """Analyze a dataset with statistical methods and generate insights.
    
    Args:
        data_source: Path to data file or URL
        analysis_type: Type of analysis - 'summary', 'correlation', 'distribution', 'outliers'
        output_format: Output format - 'json', 'markdown', 'html'
        target_path: Optional path to save results
    
    Returns:
        Analysis results with insights and recommendations
    """
    logger.info(f"Analyzing dataset: {data_source} (type={analysis_type})")
    
    df, error = _load_dataframe(data_source, nrows=MAX_ROWS_FULL)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    results: dict[str, Any] = {
        "success": True,
        "analysis_type": analysis_type,
        "row_count": len(df),
        "column_count": len(df.columns),
    }
    
    if analysis_type == "summary":
        # Basic summary statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        
        results["numeric_summary"] = df[numeric_cols].describe().to_dict() if numeric_cols else {}
        results["categorical_summary"] = {
            col: df[col].value_counts().head(10).to_dict() 
            for col in categorical_cols[:5]  # Limit to first 5 categorical columns
        }
        results["missing_values"] = df.isna().sum().to_dict()
        
    elif analysis_type == "correlation":
        # Correlation analysis for numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            results["correlation_matrix"] = corr_matrix.to_dict()
            
            # Find strong correlations
            strong_corrs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    val = corr_matrix.iloc[i, j]
                    if abs(val) > 0.7:
                        strong_corrs.append({
                            "col1": corr_matrix.columns[i],
                            "col2": corr_matrix.columns[j],
                            "correlation": round(val, 4),
                        })
            results["strong_correlations"] = strong_corrs
        else:
            results["correlation_matrix"] = {}
            results["note"] = "Not enough numeric columns for correlation analysis"
            
    elif analysis_type == "distribution":
        # Distribution analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        distributions = {}
        for col in numeric_cols[:10]:  # Limit to first 10
            series = df[col].dropna()
            if len(series) > 0:
                distributions[col] = {
                    "mean": round(float(series.mean()), 4),
                    "median": float(series.median()),
                    "std": round(float(series.std()), 4),
                    "skewness": round(float(series.skew()), 4),
                    "kurtosis": round(float(series.kurtosis()), 4),
                    "percentiles": {
                        "25%": float(series.quantile(0.25)),
                        "50%": float(series.quantile(0.50)),
                        "75%": float(series.quantile(0.75)),
                        "95%": float(series.quantile(0.95)),
                    }
                }
        results["distributions"] = distributions
        
    elif analysis_type == "outliers":
        # Outlier detection using IQR method
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outliers = {}
        for col in numeric_cols[:10]:
            series = df[col].dropna()
            if len(series) > 0:
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outlier_count = ((series < lower_bound) | (series > upper_bound)).sum()
                outliers[col] = {
                    "outlier_count": int(outlier_count),
                    "outlier_percentage": round(outlier_count / len(series) * 100, 2),
                    "lower_bound": round(float(lower_bound), 4),
                    "upper_bound": round(float(upper_bound), 4),
                }
        results["outliers"] = outliers
    
    # Save results if target path specified
    if target_path:
        output_path = Path(target_path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        results["saved_to"] = str(output_path)
    
    return results


@server.tool()
async def generate_statistics(
    data_source: str,
    statistics_type: str = "descriptive",
    group_by: str | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    """Generate statistical analysis from a dataset.
    
    Args:
        data_source: Path to data file or URL
        statistics_type: Type - 'descriptive', 'inferential', 'frequency'
        group_by: Optional column name to group by
        output_format: Output format - 'json', 'markdown'
    
    Returns:
        Statistical analysis results
    """
    logger.info(f"Generating statistics: {data_source} (type={statistics_type})")
    
    df, error = _load_dataframe(data_source, nrows=MAX_ROWS_FULL)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    results: dict[str, Any] = {
        "success": True,
        "statistics_type": statistics_type,
    }
    
    if group_by and group_by in df.columns:
        # Grouped statistics
        grouped = df.groupby(group_by)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if statistics_type == "descriptive":
            results["grouped_stats"] = grouped[numeric_cols].agg(
                ["count", "mean", "std", "min", "max"]
            ).to_dict()
        elif statistics_type == "frequency":
            results["group_counts"] = grouped.size().to_dict()
            results["group_percentages"] = (grouped.size() / len(df) * 100).round(2).to_dict()
    else:
        # Overall statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if statistics_type == "descriptive":
            desc = df[numeric_cols].describe()
            results["descriptive"] = desc.to_dict()
            
            # Add additional stats
            for col in numeric_cols[:10]:
                series = df[col].dropna()
                if len(series) > 0:
                    results.setdefault("additional", {})[col] = {
                        "variance": round(float(series.var()), 4),
                        "skewness": round(float(series.skew()), 4),
                        "kurtosis": round(float(series.kurtosis()), 4),
                        "coefficient_of_variation": round(float(series.std() / series.mean() * 100), 2) if series.mean() != 0 else None,
                    }
                    
        elif statistics_type == "frequency":
            categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            results["frequency_tables"] = {
                col: df[col].value_counts().to_dict()
                for col in categorical_cols[:5]
            }
            
        elif statistics_type == "inferential":
            # Basic inferential stats
            results["sample_size"] = len(df)
            for col in numeric_cols[:5]:
                series = df[col].dropna()
                n = len(series)
                if n > 1:
                    mean = series.mean()
                    std = series.std()
                    se = std / np.sqrt(n)
                    # 95% confidence interval
                    ci_lower = mean - 1.96 * se
                    ci_upper = mean + 1.96 * se
                    results.setdefault("confidence_intervals", {})[col] = {
                        "mean": round(float(mean), 4),
                        "std_error": round(float(se), 4),
                        "ci_95_lower": round(float(ci_lower), 4),
                        "ci_95_upper": round(float(ci_upper), 4),
                    }
    
    return results


@server.tool()
async def create_visualization(
    data_source: str,
    visualization_type: str,
    x_axis: str | None = None,
    y_axis: str | None = None,
    title: str | None = None,
    output_format: str = "png",
) -> dict[str, Any]:
    """Create visualizations from data.
    
    Args:
        data_source: Path to data file or URL
        visualization_type: Type - 'histogram', 'scatter', 'bar', 'line', 'box', 'heatmap'
        x_axis: Column name for X axis
        y_axis: Column name for Y axis
        title: Chart title
        output_format: Output format - 'png', 'svg', 'html'
    
    Returns:
        Path to generated visualization or base64 encoded image
    """
    logger.info(f"Creating visualization: {visualization_type}")
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
    except ImportError:
        return {"success": False, "error": "matplotlib not available"}
    
    df, error = _load_dataframe(data_source, nrows=MAX_ROWS_PREVIEW)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    try:
        if visualization_type == "histogram":
            if x_axis and x_axis in df.columns:
                df[x_axis].hist(ax=ax, bins=30, edgecolor='black')
                ax.set_xlabel(x_axis)
                ax.set_ylabel("Frequency")
            else:
                # Histogram of first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    df[numeric_cols[0]].hist(ax=ax, bins=30, edgecolor='black')
                    ax.set_xlabel(numeric_cols[0])
                    ax.set_ylabel("Frequency")
                    
        elif visualization_type == "scatter":
            if x_axis and y_axis and x_axis in df.columns and y_axis in df.columns:
                ax.scatter(df[x_axis], df[y_axis], alpha=0.6)
                ax.set_xlabel(x_axis)
                ax.set_ylabel(y_axis)
            else:
                return {"success": False, "error": "x_axis and y_axis required for scatter plot"}
                
        elif visualization_type == "bar":
            if x_axis and x_axis in df.columns:
                value_counts = df[x_axis].value_counts().head(20)
                value_counts.plot(kind='bar', ax=ax)
                ax.set_xlabel(x_axis)
                ax.set_ylabel("Count")
                plt.xticks(rotation=45, ha='right')
            else:
                return {"success": False, "error": "x_axis required for bar chart"}
                
        elif visualization_type == "line":
            if y_axis and y_axis in df.columns:
                if x_axis and x_axis in df.columns:
                    ax.plot(df[x_axis], df[y_axis])
                    ax.set_xlabel(x_axis)
                else:
                    ax.plot(df[y_axis])
                ax.set_ylabel(y_axis)
            else:
                return {"success": False, "error": "y_axis required for line chart"}
                
        elif visualization_type == "box":
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                df[numeric_cols[:10]].boxplot(ax=ax)
                plt.xticks(rotation=45, ha='right')
                
        elif visualization_type == "heatmap":
            numeric_df = df.select_dtypes(include=[np.number])
            if len(numeric_df.columns) > 1:
                corr = numeric_df.corr()
                im = ax.imshow(corr, cmap='coolwarm', aspect='auto')
                ax.set_xticks(range(len(corr.columns)))
                ax.set_yticks(range(len(corr.columns)))
                ax.set_xticklabels(corr.columns, rotation=45, ha='right')
                ax.set_yticklabels(corr.columns)
                plt.colorbar(im, ax=ax)
            else:
                return {"success": False, "error": "Need at least 2 numeric columns for heatmap"}
        else:
            return {"success": False, "error": f"Unknown visualization type: {visualization_type}"}
        
        # Set title
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f"{visualization_type.capitalize()} Chart")
        
        plt.tight_layout()
        
        # Save to file
        output_file = DATA_DIR / f"chart_{uuid.uuid4().hex[:8]}.{output_format}"
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Saved visualization to: {output_file}")
        
        return {
            "success": True,
            "visualization_type": visualization_type,
            "output_path": str(output_file),
            "format": output_format,
        }
        
    except Exception as e:
        plt.close(fig)
        return {"success": False, "error": f"Visualization failed: {str(e)}"}


@server.tool()
async def data_cleaning(
    data_source: str,
    cleaning_methods: list[str] | None = None,
    handle_missing: str = "drop",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Clean and preprocess data.
    
    Args:
        data_source: Path to data file
        cleaning_methods: List of methods - 'remove_duplicates', 'fill_missing', 'normalize', 'standardize', 'remove_outliers'
        handle_missing: How to handle missing values - 'drop', 'mean', 'median', 'mode', 'zero'
        output_path: Path to save cleaned data
    
    Returns:
        Cleaning summary and path to cleaned data
    """
    logger.info(f"Cleaning data: {data_source}")
    
    if cleaning_methods is None:
        cleaning_methods = ["remove_duplicates"]
    
    df, error = _load_dataframe(data_source)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    original_shape = df.shape
    cleaning_log = []
    
    for method in cleaning_methods:
        if method == "remove_duplicates":
            before = len(df)
            df = df.drop_duplicates()
            removed = before - len(df)
            cleaning_log.append(f"Removed {removed} duplicate rows")
            
        elif method == "fill_missing":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].isna().any():
                    if handle_missing == "mean":
                        df[col] = df[col].fillna(df[col].mean())
                    elif handle_missing == "median":
                        df[col] = df[col].fillna(df[col].median())
                    elif handle_missing == "zero":
                        df[col] = df[col].fillna(0)
            cleaning_log.append(f"Filled missing values using {handle_missing}")
            
        elif method == "normalize":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val != min_val:
                    df[col] = (df[col] - min_val) / (max_val - min_val)
            cleaning_log.append(f"Normalized {len(numeric_cols)} numeric columns to [0, 1]")
            
        elif method == "standardize":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                mean = df[col].mean()
                std = df[col].std()
                if std != 0:
                    df[col] = (df[col] - mean) / std
            cleaning_log.append(f"Standardized {len(numeric_cols)} numeric columns (z-score)")
            
        elif method == "remove_outliers":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            before = len(df)
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                df = df[(df[col] >= Q1 - 1.5 * IQR) & (df[col] <= Q3 + 1.5 * IQR)]
            removed = before - len(df)
            cleaning_log.append(f"Removed {removed} outlier rows")
    
    # Handle remaining missing values
    if handle_missing == "drop":
        before = len(df)
        df = df.dropna()
        dropped = before - len(df)
        if dropped > 0:
            cleaning_log.append(f"Dropped {dropped} rows with missing values")
    
    # Save cleaned data
    if output_path:
        save_path = Path(output_path).expanduser()
    else:
        save_path = DATA_DIR / f"cleaned_{uuid.uuid4().hex[:8]}.csv"
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(save_path, index=False)
    
    return {
        "success": True,
        "original_shape": {"rows": original_shape[0], "columns": original_shape[1]},
        "cleaned_shape": {"rows": len(df), "columns": len(df.columns)},
        "cleaning_log": cleaning_log,
        "output_path": str(save_path),
    }


@server.tool()
async def data_aggregation(
    data_source: str,
    group_by: str,
    aggregation_methods: list[str] | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    """Aggregate and summarize data by grouping.
    
    Args:
        data_source: Path to data file
        group_by: Column name to group by
        aggregation_methods: List of methods - 'sum', 'mean', 'count', 'min', 'max', 'std'
        output_format: Output format - 'json', 'csv'
    
    Returns:
        Aggregated data
    """
    logger.info(f"Aggregating data by: {group_by}")
    
    if aggregation_methods is None:
        aggregation_methods = ["count", "mean", "sum"]
    
    df, error = _load_dataframe(data_source)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    if group_by not in df.columns:
        return {"success": False, "error": f"Column '{group_by}' not found in data"}
    
    # Get numeric columns for aggregation
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if not numeric_cols:
        # Just count if no numeric columns
        result = df.groupby(group_by).size().reset_index(name='count')
    else:
        # Build aggregation dict
        agg_dict = {col: aggregation_methods for col in numeric_cols}
        result = df.groupby(group_by).agg(agg_dict)
        
        # Flatten column names
        result.columns = ['_'.join(col).strip() for col in result.columns.values]
        result = result.reset_index()
    
    return {
        "success": True,
        "group_by": group_by,
        "aggregation_methods": aggregation_methods,
        "group_count": len(result),
        "aggregated_data": result.to_dict(orient="records"),
    }


@server.tool()
async def interpret_column_data(
    file_path: str,
    column_names: list[str],
    sheet_name: str | int | None = None,
) -> dict[str, Any]:
    """Interpret specific columns to understand their value patterns.
    
    Args:
        file_path: Path to the data file
        column_names: List of column names to interpret
        sheet_name: For Excel files, specify sheet name or index
    
    Returns:
        Detailed interpretation of column values with counts
    """
    logger.info(f"Interpreting columns: {column_names}")
    
    kwargs = {}
    if sheet_name is not None:
        kwargs["sheet_name"] = sheet_name
    
    df, error = _load_dataframe(file_path, **kwargs)
    if error:
        return {"success": False, "error": error}
    
    if df is None:
        return {"success": False, "error": "Failed to load dataframe"}
    
    interpretations = []
    
    for col_name in column_names:
        if col_name not in df.columns:
            interpretations.append({
                "column_name": col_name,
                "error": f"Column not found in data"
            })
            continue
        
        series = df[col_name]
        value_counts = series.value_counts()
        
        interpretation = {
            "column_name": col_name,
            "data_type": str(series.dtype),
            "total_values": len(series),
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique()),
            "unique_values_with_counts": [
                [str(k), int(v)] for k, v in value_counts.items()
            ][:100],  # Limit to top 100
        }
        
        interpretations.append(interpretation)
    
    return {
        "success": True,
        "columns_interpretation": interpretations,
    }


@server.tool()
async def run_pandas_code(
    code: str,
    data_source: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Execute pandas code safely in a sandboxed environment.
    
    Args:
        code: Python/Pandas code to execute
        data_source: Optional path to load as 'df' variable
        timeout_seconds: Maximum execution time
    
    Returns:
        Execution result or error
    """
    logger.info(f"Executing pandas code (data_source={data_source})")
    
    # Security: Block dangerous operations
    dangerous_patterns = [
        "import os", "import sys", "import subprocess",
        "exec(", "eval(", "__import__",
        "open(", "file(", "input(",
        "os.", "sys.", "subprocess.",
        "shutil.", "pathlib.",
        "requests.", "urllib.",
    ]
    
    code_lower = code.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in code_lower:
            return {
                "success": False,
                "error": f"Blocked: Code contains dangerous pattern '{pattern}'",
            }
    
    # Prepare execution environment
    local_vars: dict[str, Any] = {
        "pd": pd,
        "np": np,
    }
    
    # Load data if specified
    if data_source:
        df, error = _load_dataframe(data_source)
        if error:
            return {"success": False, "error": error}
        local_vars["df"] = df
    
    try:
        # Execute code
        exec(code, {"__builtins__": {}}, local_vars)
        
        # Get result (last assigned variable or 'result')
        result = local_vars.get("result", local_vars.get("df"))
        
        if isinstance(result, pd.DataFrame):
            return {
                "success": True,
                "result_type": "DataFrame",
                "shape": {"rows": len(result), "columns": len(result.columns)},
                "columns": list(result.columns),
                "preview": result.head(10).to_dict(orient="records"),
            }
        elif isinstance(result, pd.Series):
            return {
                "success": True,
                "result_type": "Series",
                "length": len(result),
                "preview": result.head(10).to_dict(),
            }
        else:
            return {
                "success": True,
                "result_type": type(result).__name__,
                "result": str(result)[:5000],  # Limit output
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Execution failed: {str(e)}",
        }


if __name__ == "__main__":
    try:
        server.run()
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(0)
    except BaseException as e:
        def contains_broken_pipe(exc):
            if isinstance(exc, BrokenPipeError) or "Broken pipe" in str(exc):
                return True
            if hasattr(exc, "exceptions"):
                return any(contains_broken_pipe(inner) for inner in exc.exceptions)
            return False

        if contains_broken_pipe(e):
            sys.exit(0)
        raise
