import os
import numpy as np
from PIL import Image
from analyzers.base import AnalysisResult, BaseAnalyzer

EMPTY_STD_THRESHOLD = 5.0  # empirical: std < 5 on 0-255 range = near-uniform color


class EmptyAnalyzer(BaseAnalyzer):
    @property
    def analyzer_type(self) -> str:
        return "empty"

    def analyze(self, dataset_path: str, config: dict) -> AnalysisResult:
        findings = []
        total = 0

        for root, _, files in os.walk(dataset_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                relative = os.path.relpath(fpath, dataset_path)
                total += 1

                if os.path.getsize(fpath) < 1024:
                    findings.append({"file": relative, "reason": "file_size_below_1kb"})
                    continue

                try:
                    with Image.open(fpath) as img:
                        arr = np.array(img.convert("RGB"), dtype=np.float32)
                    if np.std(arr) < EMPTY_STD_THRESHOLD:
                        findings.append({"file": relative, "reason": "near_uniform_color"})
                except Exception:
                    pass  # let CorruptionAnalyzer handle broken files

        empty_count = len(findings)
        empty_rate = round(empty_count / total, 4) if total > 0 else 0.0

        return AnalysisResult(
            analyzer_type=self.analyzer_type,
            status="completed",
            findings=findings,
            summary={
                "total": total,
                "empty_count": empty_count,
                "empty_rate": empty_rate,
            },
            metrics={"empty_rate": empty_rate},
        )
