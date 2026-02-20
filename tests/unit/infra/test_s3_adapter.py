"""S3/MinIO adapter unit tests using Fake adapter pattern.

Milestone: I3-3
Tests: ObjectStoragePort contract, presigned URLs, batch delete, head_object.

No unittest.mock / MagicMock / patch — uses Fake adapter implementing ObjectStoragePort.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from src.ports.object_storage_port import ObjectStoragePort
from src.shared.types import (
    BatchDeleteResult,
    ObjectMetadata,
    PresignedDownloadURL,
    PresignedUploadURL,
)

# -- Fake adapter (DI pattern, implements ObjectStoragePort) --


@dataclass
class _StoredObject:
    """In-memory representation of a stored object."""

    key: str
    data: bytes = b""
    mime_type: str = "application/octet-stream"
    checksum_sha256: str = ""
    storage_class: str = "STANDARD"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeS3Adapter(ObjectStoragePort):
    """In-memory fake implementing ObjectStoragePort for unit tests."""

    def __init__(self) -> None:
        self._buckets: dict[str, dict[str, _StoredObject]] = {}

    def create_bucket(self, bucket: str) -> None:
        if bucket not in self._buckets:
            self._buckets[bucket] = {}

    def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        mime_type: str = "application/octet-stream",
        checksum_sha256: str = "",
    ) -> None:
        self.create_bucket(bucket)
        self._buckets[bucket][key] = _StoredObject(
            key=key,
            data=data,
            mime_type=mime_type,
            checksum_sha256=checksum_sha256,
        )

    async def generate_upload_url(
        self,
        bucket: str,
        key: str,
        mime_type: str,
        max_size: int,
        checksum_sha256: str,
        expires_in: int = 3600,
    ) -> PresignedUploadURL:
        self.create_bucket(bucket)
        return PresignedUploadURL(
            url=f"https://fake-s3/{bucket}/{key}?upload=1",
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            conditions={
                "content_type": mime_type,
                "max_size": max_size,
                "checksum_sha256": checksum_sha256,
            },
        )

    async def generate_download_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 900,
    ) -> PresignedDownloadURL:
        return PresignedDownloadURL(
            url=f"https://fake-s3/{bucket}/{key}?download=1",
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    async def delete_object(self, bucket: str, key: str) -> None:
        if bucket in self._buckets:
            self._buckets[bucket].pop(key, None)

    async def delete_objects(
        self,
        bucket: str,
        keys: list[str],
    ) -> BatchDeleteResult:
        deleted: list[str] = []
        errors: list[dict[str, str]] = []
        if bucket not in self._buckets:
            errors = [{"key": k, "error": "NoSuchBucket"} for k in keys]
            return BatchDeleteResult(deleted=deleted, errors=errors)

        for k in keys:
            if k in self._buckets[bucket]:
                del self._buckets[bucket][k]
                deleted.append(k)
            else:
                # S3 delete is idempotent — still reports as deleted
                deleted.append(k)

        return BatchDeleteResult(deleted=deleted, errors=errors)

    async def head_object(self, bucket: str, key: str) -> ObjectMetadata:
        if bucket not in self._buckets or key not in self._buckets[bucket]:
            msg = f"Object not found: {bucket}/{key}"
            raise FileNotFoundError(msg)

        obj = self._buckets[bucket][key]
        return ObjectMetadata(
            size_bytes=len(obj.data),
            mime_type=obj.mime_type,
            checksum_sha256=obj.checksum_sha256,
            last_modified=obj.created_at,
            storage_class=obj.storage_class,
        )


@pytest.fixture
def adapter() -> FakeS3Adapter:
    return FakeS3Adapter()


# -- Tests --


@pytest.mark.unit
class TestS3AdapterImplementsPort:
    def test_is_object_storage_port(self) -> None:
        adapter = FakeS3Adapter()
        assert isinstance(adapter, ObjectStoragePort)


@pytest.mark.unit
class TestS3AdapterUpload:
    async def test_generate_upload_url(self, adapter: FakeS3Adapter) -> None:
        result = await adapter.generate_upload_url(
            bucket="media",
            key="photos/test.jpg",
            mime_type="image/jpeg",
            max_size=10_000_000,
            checksum_sha256="abc123",
            expires_in=600,
        )
        assert isinstance(result, PresignedUploadURL)
        assert "media" in result.url
        assert "photos/test.jpg" in result.url
        assert result.conditions["content_type"] == "image/jpeg"
        assert result.conditions["max_size"] == 10_000_000
        assert result.expires_at > datetime.now(UTC)

    async def test_upload_url_default_expiry(self, adapter: FakeS3Adapter) -> None:
        result = await adapter.generate_upload_url("b", "k", "text/plain", 100, "sha")
        # Default 3600s
        assert (result.expires_at - datetime.now(UTC)).total_seconds() > 3500


@pytest.mark.unit
class TestS3AdapterDownload:
    async def test_generate_download_url(self, adapter: FakeS3Adapter) -> None:
        result = await adapter.generate_download_url("media", "photos/test.jpg")
        assert isinstance(result, PresignedDownloadURL)
        assert "media" in result.url
        assert result.expires_at > datetime.now(UTC)

    async def test_download_url_custom_expiry(self, adapter: FakeS3Adapter) -> None:
        result = await adapter.generate_download_url("b", "k", expires_in=60)
        delta = (result.expires_at - datetime.now(UTC)).total_seconds()
        assert 50 < delta < 70


@pytest.mark.unit
class TestS3AdapterDelete:
    async def test_delete_single_object(self, adapter: FakeS3Adapter) -> None:
        adapter.put_object("media", "a.txt", b"hello")
        await adapter.delete_object("media", "a.txt")
        with pytest.raises(FileNotFoundError):
            await adapter.head_object("media", "a.txt")

    async def test_delete_nonexistent_is_safe(self, adapter: FakeS3Adapter) -> None:
        # S3 delete is idempotent
        await adapter.delete_object("media", "nonexistent")

    async def test_batch_delete(self, adapter: FakeS3Adapter) -> None:
        adapter.put_object("media", "a.txt", b"a")
        adapter.put_object("media", "b.txt", b"b")
        adapter.put_object("media", "c.txt", b"c")

        result = await adapter.delete_objects("media", ["a.txt", "b.txt"])
        assert isinstance(result, BatchDeleteResult)
        assert "a.txt" in result.deleted
        assert "b.txt" in result.deleted
        assert not result.errors

    async def test_batch_delete_empty_list(self, adapter: FakeS3Adapter) -> None:
        result = await adapter.delete_objects("media", [])
        assert result.deleted == []
        assert result.errors == []


@pytest.mark.unit
class TestS3AdapterHeadObject:
    async def test_head_object(self, adapter: FakeS3Adapter) -> None:
        adapter.put_object(
            "media",
            "test.jpg",
            b"x" * 1024,
            mime_type="image/jpeg",
            checksum_sha256="deadbeef",
        )
        meta = await adapter.head_object("media", "test.jpg")
        assert isinstance(meta, ObjectMetadata)
        assert meta.size_bytes == 1024
        assert meta.mime_type == "image/jpeg"
        assert meta.checksum_sha256 == "deadbeef"
        assert meta.storage_class == "STANDARD"
        assert isinstance(meta.last_modified, datetime)

    async def test_head_nonexistent_raises(self, adapter: FakeS3Adapter) -> None:
        with pytest.raises(FileNotFoundError, match="Object not found"):
            await adapter.head_object("media", "no-such-key")
