"""
Document storage service for PDF file management.
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from src.core.config import settings


class DocumentStorage:
    """Service for managing document file storage."""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize document storage.

        Args:
            base_path: Base storage path (default: from settings)
        """
        self.base_path = Path(base_path or settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_chatbot_path(self, chatbot_id: str) -> Path:
        """Get storage path for a chatbot."""
        path = self.base_path / "documents" / chatbot_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_document_path(self, chatbot_id: str, document_id: str, filename: str) -> Path:
        """Get full path for a document file."""
        # Use document_id as folder to avoid filename conflicts
        doc_path = self._get_chatbot_path(chatbot_id) / document_id
        doc_path.mkdir(parents=True, exist_ok=True)
        return doc_path / filename

    async def save_file(
        self,
        chatbot_id: str,
        document_id: str,
        file: UploadFile,
    ) -> tuple[str, int]:
        """
        Save uploaded file to storage.

        Args:
            chatbot_id: Chatbot ID
            document_id: Document ID
            file: Uploaded file

        Returns:
            Tuple of (file_path, file_size)

        Raises:
            ValueError: If file is too large or invalid type
        """
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are supported")

        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Seek back to start

        max_size = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            raise ValueError(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
                f"maximum allowed ({settings.max_file_size_mb}MB)"
            )

        # Generate safe filename
        safe_filename = self._sanitize_filename(file.filename)
        file_path = self._get_document_path(chatbot_id, document_id, safe_filename)

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        return str(file_path), file_size

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = os.path.basename(filename)

        # Replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, "_")

        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 100:
            name = name[:100]

        return f"{name}{ext}"

    def get_file_path(self, chatbot_id: str, document_id: str, filename: str) -> Optional[Path]:
        """
        Get path to stored file.

        Args:
            chatbot_id: Chatbot ID
            document_id: Document ID
            filename: Original filename

        Returns:
            Path to file or None if not exists
        """
        file_path = self._get_document_path(chatbot_id, document_id, filename)
        return file_path if file_path.exists() else None

    async def delete_file(self, chatbot_id: str, document_id: str) -> bool:
        """
        Delete document folder and contents.

        Args:
            chatbot_id: Chatbot ID
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        doc_path = self._get_chatbot_path(chatbot_id) / document_id
        if doc_path.exists():
            shutil.rmtree(doc_path)
            return True
        return False

    async def delete_chatbot_files(self, chatbot_id: str) -> bool:
        """
        Delete all files for a chatbot.

        Args:
            chatbot_id: Chatbot ID

        Returns:
            True if deleted, False if not found
        """
        chatbot_path = self._get_chatbot_path(chatbot_id)
        if chatbot_path.exists():
            shutil.rmtree(chatbot_path)
            return True
        return False

    def get_storage_stats(self, chatbot_id: str) -> dict:
        """
        Get storage statistics for a chatbot.

        Args:
            chatbot_id: Chatbot ID

        Returns:
            Dict with file_count and total_size
        """
        chatbot_path = self._get_chatbot_path(chatbot_id)

        file_count = 0
        total_size = 0

        for root, _, files in os.walk(chatbot_path):
            for file in files:
                file_path = Path(root) / file
                file_count += 1
                total_size += file_path.stat().st_size

        return {
            "file_count": file_count,
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
        }


# Singleton instance
_storage_instance: Optional[DocumentStorage] = None


def get_document_storage() -> DocumentStorage:
    """Get or create the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = DocumentStorage()
    return _storage_instance
