import os
import imagehash
from PIL import Image
from analyzers.base import AnalysisResult, BaseAnalyzer

HAMMING_THRESHOLD = 10  # distance ≤ 10 = duplicate


class DuplicateAnalyzer(BaseAnalyzer):
    @property
    def analyzer_type(self) -> str:
        return "duplicate"

    def analyze(self, dataset_path: str, config: dict) -> AnalysisResult:
        hashes: list[tuple[str, imagehash.ImageHash]] = []

        for root, _, files in os.walk(dataset_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                relative = os.path.relpath(fpath, dataset_path)
                try:
                    with Image.open(fpath) as img:
                        h = imagehash.phash(img)
                    hashes.append((relative, h))
                except Exception:
                    pass

        total = len(hashes)
        findings = []
        seen_duplicates: set[str] = set()

        # O(n²) — acceptable for MVP
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                file_a, hash_a = hashes[i]
                file_b, hash_b = hashes[j]
                distance = hash_a - hash_b
                if distance <= HAMMING_THRESHOLD:
                    findings.append({
                        "file_a": file_a,
                        "file_b": file_b,
                        "distance": distance,
                    })
                    seen_duplicates.add(file_a)
                    seen_duplicates.add(file_b)

        duplicate_pairs_count = len(findings)
        unique_images = total - len(seen_duplicates)
        uniqueness_rate = round(unique_images / total, 4) if total > 0 else 1.0

        return AnalysisResult(
            analyzer_type=self.analyzer_type,
            status="completed",
            findings=findings,
            summary={
                "total_images": total,
                "duplicate_pairs_count": duplicate_pairs_count,
                "unique_images": unique_images,
            },
            metrics={"uniqueness_rate": uniqueness_rate},
        )
