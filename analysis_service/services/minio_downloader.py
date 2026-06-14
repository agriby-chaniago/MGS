import os
from minio import Minio


def get_minio_client() -> Minio:
    return Minio(
        endpoint=f"{os.getenv('MINIO_HOST', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


def parse_minio_path(minio_path: str) -> tuple[str, str]:
    """
    "modelgate-datasets/uuid/" → ("modelgate-datasets", "uuid/")
    minio_path diisi dari dataset.minio_path saat upload (format: bucket/prefix)
    """
    parts = minio_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid minio_path format: {minio_path}")
    return parts[0], parts[1]


def download_dataset(minio_path: str, audit_id: str) -> str:
    """Download semua object dengan prefix ke /tmp/analysis_{audit_id}/. Return local path."""
    local_dir = f"/tmp/analysis_{audit_id}"
    os.makedirs(local_dir, exist_ok=True)
    client = get_minio_client()
    bucket, prefix = parse_minio_path(minio_path)
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    for obj in objects:
        relative = obj.object_name[len(prefix):]
        local_path = os.path.join(local_dir, relative)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        client.fget_object(bucket, obj.object_name, local_path)
    return local_dir


def cleanup_tmp(path: str):
    import shutil
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
