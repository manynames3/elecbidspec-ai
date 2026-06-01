from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import boto3

from app.core.config import get_settings


def store_upload(content: bytes, filename: str | None, content_type: str | None = None) -> dict:
    settings = get_settings()
    safe_name = Path(filename or "upload").name
    storage_name = f"{uuid4()}-{safe_name}"

    if settings.upload_bucket:
        key = f"{settings.upload_prefix.strip('/')}/{storage_name}" if settings.upload_prefix else storage_name
        put_args = {
            "Bucket": settings.upload_bucket,
            "Key": key,
            "Body": content,
            "ServerSideEncryption": "AES256",
        }
        if content_type:
            put_args["ContentType"] = content_type
        boto3.client("s3").put_object(**put_args)
        return {
            "name": filename,
            "storage": "s3",
            "bucket": settings.upload_bucket,
            "key": key,
            "stored_path": f"s3://{settings.upload_bucket}/{key}",
        }

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = settings.upload_dir / storage_name
    storage_path.write_bytes(content)
    return {"name": filename, "storage": "local", "stored_path": str(storage_path)}
