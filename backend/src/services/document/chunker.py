"""
Document chunking using LangChain text splitters.
"""
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.core.config import settings


class DocumentChunker:
    """Chunker for splitting documents into smaller pieces."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[list[str]] = None,
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks
            separators: List of separator strings
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.separators = separators or ["\n\n", "\n", ".", "!", "?", ",", " ", ""]

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks.

        Args:
            text: Input text to split

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        return self._splitter.split_text(text)

    def chunk_with_metadata(
        self,
        text: str,
        document_id: str,
        filename: str,
    ) -> list[dict]:
        """
        Split text and add metadata to each chunk.

        Args:
            text: Input text to split
            document_id: Document ID
            filename: Source filename

        Returns:
            List of dicts with chunk text and metadata
        """
        chunks = self.chunk_text(text)

        return [
            {
                "text": chunk,
                "metadata": {
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                },
            }
            for i, chunk in enumerate(chunks)
        ]

    def chunk_pages(
        self,
        pages: list[dict],
        document_id: str,
        filename: str,
    ) -> list[dict]:
        """
        Chunk text from pages while preserving page information.

        Args:
            pages: List of page dicts with page_num and text
            document_id: Document ID
            filename: Source filename

        Returns:
            List of chunks with page metadata
        """
        all_chunks = []
        chunk_index = 0

        for page in pages:
            page_text = page.get("text", "")
            page_num = page.get("page_num", 0)

            if not page_text.strip():
                continue

            page_chunks = self.chunk_text(page_text)

            for chunk in page_chunks:
                all_chunks.append({
                    "text": chunk,
                    "metadata": {
                        "document_id": document_id,
                        "filename": filename,
                        "page_num": page_num,
                        "chunk_index": chunk_index,
                    },
                })
                chunk_index += 1

        # Add total chunk count to all chunks
        for chunk in all_chunks:
            chunk["metadata"]["chunk_count"] = len(all_chunks)

        return all_chunks


def chunk_document(
    text: str,
    document_id: str,
    filename: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[dict]:
    """
    Convenience function to chunk a document.

    Args:
        text: Document text
        document_id: Document ID
        filename: Source filename
        chunk_size: Optional chunk size
        chunk_overlap: Optional overlap

    Returns:
        List of chunks with metadata
    """
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_with_metadata(text, document_id, filename)
