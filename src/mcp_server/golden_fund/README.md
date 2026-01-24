# Golden Fund MCP Server 🔱

**Current Version:** 1.0 (Integration v2.4 in AtlasTrinity)
**Tier:** 2 (High Priority / Knowledge Base)

The **Golden Fund** is AtlasTrinity's definitive, persistent knowledge base. It is designed to ingest, validate, and store high-value information ("Golden Records") that persists across sessions and provides deep context for agents.

## 🌟 Key Capabilities

1.  **Semantic Search & Vector Storage**:
    -   Uses **ChromaDB** for semantic similarity search.
    -   Stores embeddings for all ingested content.
    -   Supports hybrid search (Vector + Keyword).

2.  **Recursive Enrichment**:
    -   Automatically queries external Open Data portals (e.g., `data.gov.ua` via CKAN) when local knowledge is insufficient.
    -   Chains ingestion -> parsing -> vectorization in a single flow.

3.  **Blob Storage**:
    -   Manages raw file assets (JSON, CSV, XML) in a local "MinIO-style" structured blob storage.
    -   Located at `~/.config/atlastrinity/data/golden_fund/blobs`.

4.  **Unified Data Transformation**:
    -   Parses diverse formats (CSV, XML, JSON) into a unified schema (`UnifiedSchema`).
    -   Ensures type consistency & metadata normalization.

## 🛠 Tools

| Tool Name | Description | Inputs |
| :--- | :--- | :--- |
| `search_golden_fund` | Search the knowledge base. | `query` (str), `mode` ("semantic"\|"keyword") |
| `ingest_dataset` | Ingest data from a URL or API. | `url` (str), `type` ("web_page"\|"api") |
| `store_blob` | Store raw content as a file. | `content` (str), `filename` (opt) |
| `retrieve_blob` | Retrieve raw content by filename. | `filename` (str) |
| `probe_entity` | Explore graph relationships for an entity. | `entity_id` (str), `depth` (int) |
| `add_knowledge_node` | Manually insert a verified fact. | `content`, `metadata` |

## 📂 Architecture

### Directory Structure

```text
src/mcp_server/golden_fund/
├── server.py              # Main FastMCP entry point
├── lib/
│   ├── connectors/        # External API clients (CKAN, etc.)
│   ├── storage/           # Persistence adapters (Vector, Blob)
│   ├── scraper.py         # Web/API scraping logic
│   ├── parser.py          # Format parsers (XML, CSV, JSON)
│   └── transformer.py     # Schema validation & transformation
└── tools/
    ├── chain.py           # Recursive enrichment logic
    └── ingest.py          # Ingestion pipelines
```

### Configuration

All data is stored in the global configuration directory to ensure persistence during updates:

-   **Vector DB**: `~/.config/atlastrinity/data/golden_fund/chroma_db`
-   **Blob Storage**: `~/.config/atlastrinity/data/golden_fund/blobs`

## 🚀 Usage Example

```python
# Semantic Search (via MCP)
result = await call_tool("golden-fund", "search_golden_fund", {"query": "GDP of Ukraine 2023"})

# Ingest New Data
await call_tool("golden-fund", "ingest_dataset", {
    "url": "https://data.gov.ua/api/3/action/package_show?id=...", 
    "type": "api"
})
```

## ✅ Verification

Run the built-in verification script to test all components:

```bash
python3 scripts/verify_golden_fund.py
```
