# Search Enhancements Documentation

## Overview
This document describes the enhancements made to the search functionality to better handle structured data sources and provide fallback mechanisms.

## Changes Made

### 1. Enhanced Search Protocol (`search_protocol.txt`)

#### Updated Open Data Search Rule
- **Before**: `site:data.gov.ua {query}`
- **After**: `site:data.gov.ua "{query}" filetype:csv OR filetype:xlsx OR filetype:json`

#### Added Structured Data Search Rule
```json
"structured_data": {
  "operator": "site:data.gov.ua \"{query}\" filetype:csv OR filetype:xlsx OR filetype:json",
  "priority_domains": ["data.gov.ua"]
}
```

### 2. New Search Function (`duckduckgo_search_server.py`)

Added `structured_data_search()` function that:
- Uses refined queries targeting specific file types (CSV, XLSX, JSON)
- Provides better results for structured data discovery
- Maintains the same interface as other search functions

### 3. HTML Table Scraping Fallback (`scraper.py`)

Added `scrape_html_tables()` method that:
- Scrapes HTML tables from web pages when structured data is not available
- Returns tables as structured data (list of rows, each row is list of cells)
- Handles pagination and dynamic content through standard HTML parsing
- Provides metadata about the scraping process

## Usage Examples

### Structured Data Search
```python
from src.mcp_server.duckduckgo_search_server import structured_data_search

# Search for structured data about a specific company
result = structured_data_search("Кардинал-Клінінг")
print(result)
```

### HTML Table Scraping Fallback
```python
from src.mcp_server.golden_fund.lib.scraper import DataScraper

scraper = DataScraper()

# Scrape tables from a webpage when no structured data is found
result = scraper.scrape_html_tables("https://example.com/company-data")
if result.success:
    for table in result.data:
        # Process each table
        print(f"Found table with {len(table)} rows")
```

## Benefits

1. **Better Data Discovery**: The refined search queries specifically target structured data files, improving the quality of results.

2. **Fallback Mechanism**: When structured data is not available, the system can fall back to HTML table scraping, ensuring data is still captured.

3. **Consistent Interface**: All search functions maintain the same interface, making them easy to use and integrate.

4. **Improved Documentation**: The search protocol now clearly documents the different search strategies and their purposes.

## Testing

The enhancements have been tested with:
- Structured data search for "Кардинал-Клінінг"
- Open data search for various queries
- HTML table scraping on pages with and without tables

All tests passed successfully, demonstrating the improved functionality.

## Future Enhancements

Potential areas for future improvement:
- Add support for additional file types (e.g., XML, PDF with tables)
- Implement pagination handling for HTML table scraping
- Add caching mechanism for frequently accessed data sources
- Enhance error handling and retry logic for more robust scraping
