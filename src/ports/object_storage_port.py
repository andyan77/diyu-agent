"""ObjectStoragePort - Object storage operations interface.

v3.6 Extension Port. Not a Day-1 Port (Section 12.3 Day-1 = 6 ports).
Encapsulates object storage primitives without business logic, security
scanning, or permission checks.

Underlying implementation: S3 / MinIO / OSS / GCS (swappable).

See: docs/architecture/00-*.md Section 12.3.1
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import (
        BatchDeleteResult,
        ObjectMetadata,
        PresignedDownloadURL,
        PresignedUploadURL,
    )


class ObjectStoragePort(ABC):
    """Port: Object storage operation primitives.

    5 methods (aligned with architecture doc 00:578):
    - generate_upload_url
    - generate_download_url
    - delete_object
    - delete_objects
    - head_object
    """

    @abstractmethod
    async def generate_upload_url(
        self,
        bucket: str,
        key: str,
        mime_type: str,
        max_size: int,
        checksum_sha256: str,
        expires_in: int = 3600,
    ) -> PresignedUploadURL:
        """Generate a presigned URL for object upload.

        Args:
            bucket: Target bucket name.
            key: Object key (path within bucket).
            mime_type: Expected MIME type of the upload.
            max_size: Maximum allowed size in bytes.
            checksum_sha256: Expected SHA-256 checksum for integrity.
            expires_in: URL expiry in seconds (default 1 hour).

        Returns:
            PresignedUploadURL with url, expires_at, and conditions.
        """

    @abstractmethod
    async def generate_download_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 900,
    ) -> PresignedDownloadURL:
        """Generate a presigned URL for object download.

        Args:
            bucket: Source bucket name.
            key: Object key.
            expires_in: URL expiry in seconds (default 15 minutes).

        Returns:
            PresignedDownloadURL with url and expires_at.
        """

    @abstractmethod
    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete a single object.

        Args:
            bucket: Bucket name.
            key: Object key to delete.
        """

    @abstractmethod
    async def delete_objects(
        self,
        bucket: str,
        keys: list[str],
    ) -> BatchDeleteResult:
        """Delete multiple objects in batch.

        Args:
            bucket: Bucket name.
            keys: List of object keys to delete.

        Returns:
            BatchDeleteResult with deleted keys and any errors.
        """

    @abstractmethod
    async def head_object(self, bucket: str, key: str) -> ObjectMetadata:
        """Retrieve object metadata without downloading the object.

        Args:
            bucket: Bucket name.
            key: Object key.

        Returns:
            ObjectMetadata with size, mime_type, checksum, etc.
        """
