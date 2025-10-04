"""MinIO/S3 storage client for artifact management."""

import hashlib
import io
import logging
import os
from typing import Optional, BinaryIO

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# MinIO configuration from environment
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Bucket names
BUCKET_ARTIFACTS = "pr-telemetry-artifacts"
BUCKET_CHUNKS = "pr-telemetry-chunks"
BUCKET_TRACES = "pr-telemetry-traces"

# Initialize MinIO client
storage_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)


def ensure_buckets():
    """Ensure required buckets exist."""
    buckets = [BUCKET_ARTIFACTS, BUCKET_CHUNKS, BUCKET_TRACES]
    for bucket in buckets:
        try:
            if not storage_client.bucket_exists(bucket):
                storage_client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket {bucket}: {e}")
            raise


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


def upload_blob(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream"
) -> tuple[str, str, int]:
    """
    Upload a blob to storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
        data: Binary data to upload
        content_type: MIME type
    
    Returns:
        Tuple of (uri, sha256, size_bytes)
    """
    try:
        # Compute hash
        sha256 = compute_sha256(data)
        size_bytes = len(data)
        
        # Upload
        storage_client.put_object(
            bucket,
            object_name,
            io.BytesIO(data),
            length=size_bytes,
            content_type=content_type
        )
        
        # Construct URI
        protocol = "https" if MINIO_SECURE else "http"
        uri = f"{protocol}://{MINIO_ENDPOINT}/{bucket}/{object_name}"
        
        logger.info(f"Uploaded blob: {uri} (SHA-256: {sha256[:8]}..., {size_bytes} bytes)")
        return uri, sha256, size_bytes
    
    except S3Error as e:
        logger.error(f"Error uploading blob to {bucket}/{object_name}: {e}")
        raise


def download_blob(bucket: str, object_name: str) -> bytes:
    """
    Download a blob from storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
    
    Returns:
        Binary data
    """
    try:
        response = storage_client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        logger.error(f"Error downloading blob from {bucket}/{object_name}: {e}")
        raise


def get_blob_info(bucket: str, object_name: str) -> Optional[dict]:
    """
    Get information about a blob.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
    
    Returns:
        Dictionary with blob metadata or None if not found
    """
    try:
        stat = storage_client.stat_object(bucket, object_name)
        return {
            "size": stat.size,
            "etag": stat.etag,
            "last_modified": stat.last_modified,
            "content_type": stat.content_type,
        }
    except S3Error as e:
        if e.code == "NoSuchKey":
            return None
        logger.error(f"Error getting blob info for {bucket}/{object_name}: {e}")
        raise


def upload_text(
    bucket: str,
    object_name: str,
    text: str,
    content_type: str = "text/plain"
) -> tuple[str, str, int]:
    """
    Upload text content to storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
        text: Text content
        content_type: MIME type
    
    Returns:
        Tuple of (uri, sha256, size_bytes)
    """
    data = text.encode("utf-8")
    return upload_blob(bucket, object_name, data, content_type)


def upload_json(
    bucket: str,
    object_name: str,
    json_str: str
) -> tuple[str, str, int]:
    """
    Upload JSON content to storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
        json_str: JSON string
    
    Returns:
        Tuple of (uri, sha256, size_bytes)
    """
    return upload_text(bucket, object_name, json_str, content_type="application/json")

