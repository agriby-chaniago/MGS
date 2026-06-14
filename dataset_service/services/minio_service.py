import os
from minio import Minio


class MinIOService:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.bucket = os.getenv("MINIO_BUCKET", "modelgate-datasets")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, object_name: str, file_path: str) -> str:
        self.client.fput_object(self.bucket, object_name, file_path)
        return f"{self.bucket}/{object_name}"

    def upload_directory(self, dataset_id: str, directory: str) -> str:
        """Upload semua file di directory ke MinIO. Return prefix path."""
        # directory berisi: root_folder/class_name/image.jpg
        entries = [e for e in os.listdir(directory) if os.path.isdir(os.path.join(directory, e))]
        root = entries[0] if entries else ""
        dataset_root = os.path.join(directory, root) if root else directory

        for class_name in os.listdir(dataset_root):
            class_dir = os.path.join(dataset_root, class_name)
            if not os.path.isdir(class_dir):
                continue
            for fname in os.listdir(class_dir):
                fpath = os.path.join(class_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                object_name = f"{dataset_id}/{class_name}/{fname}"
                self.client.fput_object(self.bucket, object_name, fpath)

        return f"{self.bucket}/{dataset_id}/"

    def delete_prefix(self, prefix: str):
        """Hapus semua object dengan prefix tertentu (rollback)."""
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        for obj in objects:
            self.client.remove_object(self.bucket, obj.object_name)


minio_service = MinIOService()
