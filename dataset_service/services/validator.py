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


SPLIT_NAMES = {"train", "test", "valid", "val", "validation", "training", "testing"}


def _detect_structure(names: list[str]) -> tuple[str, set[str], bool]:
    """
    Returns (root, class_names, is_split_based).
    root = single root folder name, or "" if flat split structure.
    is_split_based = True if root folders are train/test/valid splits.
    """
    root_dirs = set()
    for name in names:
        parts = name.split("/")
        if parts[0]:
            root_dirs.add(parts[0])

    # Case 1: single root folder
    if len(root_dirs) == 1:
        root = next(iter(root_dirs))
        # Check if children of root are splits
        children = set()
        for name in names:
            parts = name.rstrip("/").split("/")
            if len(parts) >= 2 and parts[0] == root and parts[1]:
                children.add(parts[1])
        if children and children <= SPLIT_NAMES:
            # root/train/class/img structure
            class_names = set()
            for name in names:
                parts = name.rstrip("/").split("/")
                if len(parts) >= 3 and parts[0] == root and parts[1] in SPLIT_NAMES and parts[2]:
                    class_names.add(parts[2])
            return root, class_names, True
        return root, children, False

    # Case 2: multiple root folders = splits directly (train/ test/ valid/)
    if root_dirs and root_dirs <= SPLIT_NAMES:
        class_names = set()
        for name in names:
            parts = name.rstrip("/").split("/")
            if len(parts) >= 2 and parts[0] in SPLIT_NAMES and parts[1]:
                class_names.add(parts[1])
        return "", class_names, True

    # Case 3: multiple root folders = classes directly (Potato___Early_blight/ etc.)
    return "", root_dirs, False


def validate_zip_structure(zip_path: str) -> ValidationResult:
    if not zipfile.is_zipfile(zip_path):
        return ValidationResult(valid=False, error_message="File bukan ZIP valid", stats=None)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

    if not names:
        return ValidationResult(valid=False, error_message="ZIP kosong", stats=None)

    root_dirs = set()
    for name in names:
        parts = name.split("/")
        if parts[0]:
            root_dirs.add(parts[0])

    root, class_names, is_split = _detect_structure(names)

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


def _scan_class_dir(class_dir: str, class_name: str, images_per_class: dict, invalid_files: list) -> int:
    total_size = 0
    count = images_per_class.get(class_name, 0)
    for fname in os.listdir(class_dir):
        fpath = os.path.join(class_dir, fname)
        if not os.path.isfile(fpath):
            continue
        total_size += os.path.getsize(fpath)
        if validate_image(fpath):
            count += 1
        else:
            invalid_files.append(f"{class_name}/{fname}")
    images_per_class[class_name] = count
    return total_size


def scan_extracted_dataset(extract_dir: str) -> DatasetStats:
    images_per_class: dict[str, int] = {}
    invalid_files: list[str] = []
    total_size_bytes = 0

    top_entries = [e for e in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, e))]

    # Detect split-based structure at top level
    split_roots = [e for e in top_entries if e.lower() in SPLIT_NAMES]

    if split_roots:
        # Case: extract_dir/train/class/img
        scan_roots = [os.path.join(extract_dir, s) for s in split_roots]
    elif len(top_entries) == 1:
        # Single root folder — check if children are splits or classes
        dataset_root = os.path.join(extract_dir, top_entries[0])
        nested = [e for e in os.listdir(dataset_root) if os.path.isdir(os.path.join(dataset_root, e))]
        nested_splits = [e for e in nested if e.lower() in SPLIT_NAMES]
        if nested_splits:
            scan_roots = [os.path.join(dataset_root, s) for s in nested_splits]
        else:
            scan_roots = [dataset_root]
    else:
        # Multiple root folders = classes directly (Potato___Early_blight/ etc.)
        scan_roots = [extract_dir]

    for split_dir in scan_roots:
        for class_name in sorted(os.listdir(split_dir)):
            class_dir = os.path.join(split_dir, class_name)
            if not os.path.isdir(class_dir):
                continue
            total_size_bytes += _scan_class_dir(class_dir, class_name, images_per_class, invalid_files)

    # Remove classes with 0 images
    images_per_class = {k: v for k, v in images_per_class.items() if v > 0}

    return DatasetStats(
        total_classes=len(images_per_class),
        total_images=sum(images_per_class.values()),
        images_per_class=images_per_class,
        total_size_bytes=total_size_bytes,
        invalid_files=invalid_files,
    )
