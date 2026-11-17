"""Hifadhi ya picha na faili kwenye Cloudflare R2 (inatumia itifaki ya S3)."""
import mimetypes
import uuid

import boto3
from botocore.config import Config as BotoConfig

from config import Config

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}

_client = None


def _get_client():
    global _client
    if _client is None:
        if not (Config.R2_ACCOUNT_ID and Config.R2_ACCESS_KEY_ID and Config.R2_SECRET_ACCESS_KEY):
            raise RuntimeError("Mipangilio ya R2 haijakamilika kwenye .env")
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{Config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=Config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=Config.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=BotoConfig(signature_version="s3v4"),
        )
    return _client


def public_url(key):
    return f"{Config.R2_PUBLIC_URL}/{key}"


def _sniff(stream):
    """Hutambua aina halisi ya picha kwa baiti za mwanzo, si kwa jina la faili."""
    head = stream.read(12)
    stream.seek(0)
    if head.startswith(b"\xff\xd8\xff"):
        return {"jpg", "jpeg"}
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"png"}
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return {"gif"}
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return {"webp"}
    return set()


def upload_image(file_storage, folder="uploads"):
    """Pakia picha kutoka kwenye fomu (request.files[...]). Inarudisha URL ya umma."""
    name = file_storage.filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise ValueError("Aina ya picha hairuhusiwi. Tumia jpg, png, webp au gif.")
    if ext not in _sniff(file_storage.stream):
        raise ValueError("Faili hili si picha halali.")
    key = f"{folder}/{uuid.uuid4().hex}.{ext}"
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    _get_client().upload_fileobj(
        file_storage.stream,
        Config.R2_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return public_url(key)


def delete_key(key):
    _get_client().delete_object(Bucket=Config.R2_BUCKET, Key=key)


def ping():
    _get_client().head_bucket(Bucket=Config.R2_BUCKET)
    return True
