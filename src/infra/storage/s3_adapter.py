"""S3/MinIO adapter implementing ObjectStoragePort.

Milestone: I3-3
Layer: Infrastructure

Provides presigned URL generation, object deletion, and metadata
retrieval via S3-compatible API (MinIO for dev, AWS S3 for production).

See: docs/architecture/00-*.md Section 12.3.1 (ObjectStoragePort)
     docs/architecture/06-基础设施层 Section 9 (media DDL)
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.ports.object_storage_port import ObjectStoragePort
from src.shared.types import (
    BatchDeleteResult,
    ObjectMetadata,
    PresignedDownloadURL,
    PresignedUploadURL,
)

logger = logging.getLogger(__name__)


class S3Adapter(ObjectStoragePort):
    """ObjectStoragePort implementation using S3/MinIO.

    All 5 port methods implemented:
    - generate_upload_url
    - generate_download_url
    - delete_object
    - delete_objects
    - head_object
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        self._endpoint_url = endpoint_url or os.environ.get(
            "MINIO_ENDPOINT", "http://localhost:9000"
        )
        self._access_key = access_key or os.environ.get(
            "MINIO_ACCESS_KEY", os.environ.get("AWS_ACCESS_KEY_ID", "")
        )
        self._secret_key = secret_key or os.environ.get(
            "MINIO_SECRET_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        )
        self._region = region
        self._client: Any = None

    def connect(self) -> None:
        """Create S3 client (synchronous — boto3 is not async)."""
        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
            config=Config(signature_version="s3v4"),
        )
        logger.info("S3 adapter connected: %s", self._endpoint_url)

    @property
    def client(self) -> Any:
        if self._client is None:
            msg = "S3 not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._client

    async def generate_upload_url(
        self,
        bucket: str,
        key: str,
        mime_type: str,
        max_size: int,
        checksum_sha256: str,
        expires_in: int = 3600,
    ) -> PresignedUploadURL:
        """Generate presigned URL for object upload."""
        conditions: dict[str, Any] = {
            "content_type": mime_type,
            "max_size": max_size,
            "checksum_sha256": checksum_sha256,
        }

        url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": mime_type,
            },
            ExpiresIn=expires_in,
        )

        return PresignedUploadURL(
            url=url,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            conditions=conditions,
        )

    async def generate_download_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 900,
    ) -> PresignedDownloadURL:
        """Generate presigned URL for object download."""
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )

        return PresignedDownloadURL(
            url=url,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete a single object."""
        self.client.delete_object(Bucket=bucket, Key=key)

    async def delete_objects(
        self,
        bucket: str,
        keys: list[str],
    ) -> BatchDeleteResult:
        """Delete multiple objects in batch."""
        if not keys:
            return BatchDeleteResult()

        response = self.client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in keys], "Quiet": False},
        )

        deleted = [obj["Key"] for obj in response.get("Deleted", [])]
        errors = [
            {"key": err["Key"], "error": err.get("Message", "Unknown")}
            for err in response.get("Errors", [])
        ]

        return BatchDeleteResult(deleted=deleted, errors=errors)

    async def head_object(self, bucket: str, key: str) -> ObjectMetadata:
        """Retrieve object metadata."""
        try:
            resp = self.client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                msg = f"Object not found: {bucket}/{key}"
                raise FileNotFoundError(msg) from e
            raise

        checksum = resp.get("ChecksumSHA256", "")
        if not checksum:
            # Fall back to ETag (MD5) if no SHA256 available
            checksum = resp.get("ETag", "").strip('"')

        return ObjectMetadata(
            size_bytes=resp["ContentLength"],
            mime_type=resp.get("ContentType", "application/octet-stream"),
            checksum_sha256=checksum,
            last_modified=resp["LastModified"],
            storage_class=resp.get("StorageClass", "STANDARD"),
        )
