import os
import zipfile
from dataclasses import dataclass, field
from PIL import Image

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_ZIP_SIZE_MB = 2048


@dataclass
class DatasetStats:
    total_classes: int
    total_images: int
    images_per_class: dict[str, int]
    total_size_bytes: int
    invalid_files: list[str]


@dataclass
class ValidationResult:
    valid: bool
    error_message: str | None
    stats: DatasetStats | None


def validate_image(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in VALID_EXTENSIONS:
        return False
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def validate_zip_structure(zip_path: str) -> ValidationResult:
    if not zipfile.is_zipfile(zip_path):
        return ValidationResult(valid=False, error_message="File bukan ZIP valid", stats=None)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

    if not names:
        return ValidationResult(valid=False, error_message="ZIP kosong", stats=None)

    # Cari root folder
    root_dirs = set()
    for name in names:
        parts = name.split("/")
        if parts[0]:
            root_dirs.add(parts[0])

    if len(root_dirs) != 1:
        return ValidationResult(
            valid=False,
            error_message=f"ZIP harus punya tepat 1 root folder, ditemukan: {len(root_dirs)}",
            stats=None,
        )

    root = next(iter(root_dirs))

    # Cari class folders (level 2)
    class_names = set()
    for name in names:
        parts = name.rstrip("/").split("/")
        if len(parts) >= 2 and parts[0] == root and parts[1]:
            class_names.add(parts[1])

    if len(class_names) < 2:
        return ValidationResult(
            valid=False,
            error_message=f"Dataset harus punya minimal 2 class, ditemukan: {len(class_names)}",
            stats=None,
        )

    return ValidationResult(
        valid=True,
        error_message=None,
        stats=None,  # diisi setelah extract
    )


def scan_extracted_dataset(extract_dir: str) -> DatasetStats:
    images_per_class: dict[str, int] = {}
    invalid_files: list[str] = []
    total_size_bytes = 0

    # root folder = satu-satunya subfolder di extract_dir
    entries = [e for e in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, e))]
    root = entries[0] if entries else ""
    dataset_root = os.path.join(extract_dir, root) if root else extract_dir

    for class_name in sorted(os.listdir(dataset_root)):
        class_dir = os.path.join(dataset_root, class_name)
        if not os.path.isdir(class_dir):
            continue

        count = 0
        for fname in os.listdir(class_dir):
            fpath = os.path.join(class_dir, fname)
            if not os.path.isfile(fpath):
                continue
            total_size_bytes += os.path.getsize(fpath)
            if validate_image(fpath):
                count += 1
            else:
                invalid_files.append(f"{class_name}/{fname}")

        if count > 0:
            images_per_class[class_name] = count

    return DatasetStats(
        total_classes=len(images_per_class),
        total_images=sum(images_per_class.values()),
        images_per_class=images_per_class,
        total_size_bytes=total_size_bytes,
        invalid_files=invalid_files,
    )
