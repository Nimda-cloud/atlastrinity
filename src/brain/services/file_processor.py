
import io
import logging
from typing import List, Optional
from fastapi import UploadFile

logger = logging.getLogger("brain.services.file_processor")

class FileProcessor:
    """Service to process uploaded files and extract text content."""

    @staticmethod
    async def process_files(files: List[UploadFile]) -> str:
        """Process a list of uploaded files and return a combined text summary."""
        if not files:
            return ""

        context_parts = []
        for file in files:
            try:
                content = await FileProcessor._extract_content(file)
                if content:
                    context_parts.append(f"--- [START FILE: {file.filename}] ---\n{content}\n--- [END FILE: {file.filename}] ---")
            except Exception as e:
                logger.error(f"Failed to process file {file.filename}: {e}")
                context_parts.append(f"[ERROR] Could not process file {file.filename}: {str(e)}")

        return "\n\n".join(context_parts)

    @staticmethod
    async def _extract_content(file: UploadFile) -> str:
        """Extract text content based on file type."""
        content_type = file.content_type or ""
        filename = file.filename.lower() if file.filename else ""
        
        # Read file content safely
        file_bytes = await file.read()
        
        # 1. Text / Code Files
        if content_type.startswith("text/") or any(filename.endswith(ext) for ext in [".txt", ".py", ".js", ".ts", ".tsx", ".md", ".json", ".html", ".css", ".csv", ".xml", ".yml", ".yaml"]):
            try:
                return file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1", errors="replace")

        # 2. PDF Files
        if content_type == "application/pdf" or filename.endswith(".pdf"):
            return FileProcessor._read_pdf(file_bytes)

        # 3. Word Documents (DOCX)
        if "wordprocessingml" in content_type or filename.endswith(".docx"):
            return FileProcessor._read_docx(file_bytes)

        # 4. Excel Files (XLSX)
        if "spreadsheetml" in content_type or filename.endswith(".xlsx"):
            return FileProcessor._read_excel(file_bytes)

        # 5. Images (OCR placeholder)
        if content_type.startswith("image/"):
            return FileProcessor._process_image(file_bytes, filename)

        return f"[Binary or Unsupported File Type: {content_type} / {len(file_bytes)} bytes]"

    @staticmethod
    def _read_pdf(data: bytes) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        except ImportError:
            return "[ERROR] pypdf not installed. Cannot read PDF."
        except Exception as e:
            return f"[ERROR] Failed to read PDF: {e}"

    @staticmethod
    def _read_docx(data: bytes) -> str:
        try:
            import docx
            doc = docx.Document(io.BytesIO(data))
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            return "[ERROR] python-docx not installed. Cannot read DOCX."
        except Exception as e:
            return f"[ERROR] Failed to read DOCX: {e}"

    @staticmethod
    def _read_excel(data: bytes) -> str:
        try:
            import pandas as pd
            # Read first sheet, limited rows to avoid token explosion
            df = pd.read_excel(io.BytesIO(data), nrows=50) 
            return f"[First 50 rows of Excel Sheet]\n{df.to_markdown(index=False)}"
        except ImportError:
            return "[ERROR] pandas/openpyxl not installed. Cannot read Excel."
        except Exception as e:
            return f"[ERROR] Failed to read Excel: {e}"

    @staticmethod
    def _process_image(data: bytes, filename: str) -> str:
        # Placeholder for OCR
        # We could use pytesseract here if requested
        return f"[Image Attachment: {filename} - OCR not yet implemented]"
