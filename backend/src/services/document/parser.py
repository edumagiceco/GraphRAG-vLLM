"""
PDF document parser using pdfplumber.
"""
import logging
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)


class EmptyPDFError(Exception):
    """Raised when PDF has no extractable text."""
    pass


class PDFParser:
    """Parser for extracting text from PDF documents."""

    def __init__(self, file_path: str | Path):
        """
        Initialize PDF parser.

        Args:
            file_path: Path to PDF file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

    def extract_text(self, raise_if_empty: bool = False) -> str:
        """
        Extract all text from PDF.

        Args:
            raise_if_empty: If True, raise EmptyPDFError when no text found

        Returns:
            Extracted text content

        Raises:
            EmptyPDFError: If raise_if_empty is True and PDF has no text
        """
        text_parts = []

        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        # Check if PDF is empty or has no extractable text
        if raise_if_empty and not full_text.strip():
            logger.warning(f"Empty PDF detected: {self.file_path}")
            raise EmptyPDFError(
                "PDF has no extractable text. The file may be scanned images, "
                "corrupted, or password protected."
            )

        return full_text

    def is_empty(self) -> bool:
        """
        Check if PDF has no extractable text.

        Returns:
            True if PDF has no text content
        """
        try:
            text = self.extract_text()
            return not text.strip()
        except Exception as e:
            logger.error(f"Error checking PDF: {e}")
            return True

    def extract_pages(self) -> list[dict]:
        """
        Extract text with page information.

        Returns:
            List of dicts with page_num and text
        """
        pages = []

        with pdfplumber.open(self.file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    pages.append({
                        "page_num": i,
                        "text": page_text,
                        "width": page.width,
                        "height": page.height,
                    })

        return pages

    def get_metadata(self) -> dict:
        """
        Get PDF metadata.

        Returns:
            PDF metadata dict
        """
        with pdfplumber.open(self.file_path) as pdf:
            return {
                "page_count": len(pdf.pages),
                "metadata": pdf.metadata or {},
            }

    def extract_tables(self) -> list[dict]:
        """
        Extract tables from PDF.

        Returns:
            List of tables with page information
        """
        tables = []

        with pdfplumber.open(self.file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                page_tables = page.extract_tables()
                for j, table in enumerate(page_tables):
                    if table:
                        tables.append({
                            "page_num": i,
                            "table_num": j + 1,
                            "data": table,
                        })

        return tables


def parse_pdf(file_path: str | Path) -> dict:
    """
    Parse PDF and return structured content.

    Args:
        file_path: Path to PDF file

    Returns:
        Dict with text, pages, metadata, and tables
    """
    parser = PDFParser(file_path)

    return {
        "text": parser.extract_text(),
        "pages": parser.extract_pages(),
        "metadata": parser.get_metadata(),
        "tables": parser.extract_tables(),
    }


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Simple function to extract text from PDF.

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text
    """
    parser = PDFParser(file_path)
    return parser.extract_text()
