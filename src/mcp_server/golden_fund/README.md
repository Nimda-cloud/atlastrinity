# Golden Fund MCP Server 🔱

**Current Version:** 2.0 (Integration v4.5 in AtlasTrinity)
**Tier:** 2 (High Priority / Knowledge Base)

The **Golden Fund** is AtlasTrinity's definitive, persistent knowledge base. It is designed to ingest, validate, and store high-value information ("Golden Records") that persists across sessions and provides deep context for agents.

## 🌟 Key Capabilities

1.  **Semantic Search & Vector Storage**:
    -   Uses **ChromaDB** for semantic similarity search.
    -   Stores embeddings for all ingested content.
    -   Supports hybrid search (Vector + Keyword + Recursive).

2.  **Entity Probing & Relationship Exploration**:
    -   Deep entity exploration with configurable depth (1-3 levels).
    -   Automatic extraction of related entities from metadata.
    -   Recursive relationship traversal.

3.  **Data Analysis Integration**:
    -   Bridge between `data-analysis` server and knowledge persistence.
    -   Analyze CSV/Excel/JSON files and store insights.
    -   Retrieve stored dataset insights on demand.

4.  **Recursive Enrichment**:
    -   Automatically queries external Open Data portals (e.g., `data.gov.ua` via CKAN) when local knowledge is insufficient.
    -   Chains ingestion -> parsing -> vectorization in a single flow.

5.  **Blob Storage**:
    -   Manages raw file assets (JSON, CSV, XML) in a local "MinIO-style" structured blob storage.
    -   Located at `~/.config/atlastrinity/data/golden_fund/blobs`.

6.  **Unified Data Transformation**:
    -   Parses diverse formats (CSV, XML, JSON) into a unified schema (`UnifiedSchema`).
    -   Ensures type consistency & metadata normalization.

## 🛠 Tools (8 Total)

| Tool Name | Description | Inputs |
| :--- | :--- | :--- |
| `search_golden_fund` | Search the knowledge base. | `query` (str), `mode` ("semantic"\|"keyword"\|"hybrid"\|"recursive") |
| `probe_entity` | Explore entity relationships with depth traversal. | `entity_id` (str), `depth` (int, 1-3) |
| `ingest_dataset` | Ingest data from a URL or API. | `url` (str), `type` ("web_page"\|"api"\|"csv_url") |
| `add_knowledge_node` | Manually insert a verified fact with links. | `content` (str), `metadata` (dict), `links` (list, opt) |
| `analyze_and_store` | Analyze a data file and store insights. | `file_path` (str), `dataset_name` (str), `analysis_type` (opt) |
| `get_dataset_insights` | Retrieve stored insights for a dataset. | `dataset_name` (str) |
| `store_blob` | Store raw content as a file. | `content` (str), `filename` (opt) |
| `retrieve_blob` | Retrieve raw content by filename. | `filename` (str) |

## 📂 Architecture

### Directory Structure

```text
src/mcp_server/golden_fund/
├── server.py              # Main FastMCP entry point (8 tools)
├── lib/
│   ├── connectors/        # External API clients (CKAN, etc.)
│   ├── storage/           # Persistence adapters (Vector, Blob, Search)
│   ├── scraper.py         # Web/API scraping logic
│   ├── parser.py          # Format parsers (XML, CSV, JSON)
│   ├── transformer.py     # Schema validation & transformation
│   └── validation.py      # Data completeness validation
└── tools/
    ├── chain.py           # Recursive enrichment logic
    └── ingest.py          # Ingestion pipelines
```

### Configuration

All data is stored in the global configuration directory to ensure persistence during updates:

-   **Vector DB**: `~/.config/atlastrinity/data/golden_fund/chroma_db`
-   **Blob Storage**: `~/.config/atlastrinity/data/golden_fund/blobs`
-   **Analysis Cache**: `~/.config/atlastrinity/data/golden_fund/analysis_cache`

## 🚀 Usage Examples

### Semantic Search
```python
result = await call_tool("golden-fund", "search_golden_fund", {
    "query": "GDP of Ukraine 2023",
    "mode": "semantic"  # or "keyword", "hybrid", "recursive"
})
```

### Entity Probing
```python
result = await call_tool("golden-fund", "probe_entity", {
    "entity_id": "Ukraine",
    "depth": 2  # Explore 2 levels of relationships
})
```

### Analyze and Store Dataset
```python
# First analyze with data-analysis server, then persist to Golden Fund
result = await call_tool("golden-fund", "analyze_and_store", {
    "file_path": "/path/to/sales_data.csv",
    "dataset_name": "Q4_Sales_2025",
    "analysis_type": "summary"  # or "correlation", "distribution"
})
```

### Retrieve Dataset Insights
```python
result = await call_tool("golden-fund", "get_dataset_insights", {
    "dataset_name": "Q4_Sales_2025"
})
```

### Ingest External Data
```python
await call_tool("golden-fund", "ingest_dataset", {
    "url": "https://data.gov.ua/api/3/action/package_show?id=...", 
    "type": "api",
    "process_pipeline": ["parse", "validate"]
})
```

## 🔗 Integration with Data Analysis

Golden Fund works seamlessly with the `data-analysis` MCP server:

1. **Raw Analysis**: Use `data-analysis` tools (`analyze_dataset`, `generate_statistics`, `create_visualization`) for immediate data processing.
2. **Persist Insights**: Use `analyze_and_store` to save analysis results to Golden Fund for future retrieval.
3. **Retrieve Later**: Use `get_dataset_insights` to recall stored analysis without re-processing.

## ✅ Verification

Run the built-in verification script to test all components:

```bash
python3 scripts/verify_golden_fund.py
```
