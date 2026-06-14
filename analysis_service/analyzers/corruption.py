import os
from PIL import Image
from analyzers.base import AnalysisResult, BaseAnalyzer


class CorruptionAnalyzer(BaseAnalyzer):
    @property
    def analyzer_type(self) -> str:
        return "corruption"

    def analyze(self, dataset_path: str, config: dict) -> AnalysisResult:
        findings = []
        total = 0

        for root, _, files in os.walk(dataset_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                relative = os.path.relpath(fpath, dataset_path)
                total += 1
                try:
                    with Image.open(fpath) as img:
                        img.verify()
                except Exception as e:
                    findings.append({"file": relative, "error": str(e)})

        corrupted = len(findings)
        valid = total - corrupted
        corruption_rate = round(corrupted / total, 4) if total > 0 else 0.0

        return AnalysisResult(
            analyzer_type=self.analyzer_type,
            status="completed",
            findings=findings,
            summary={
                "total": total,
                "valid": valid,
                "corrupted": corrupted,
                "corruption_rate": corruption_rate,
            },
            metrics={"corruption_rate": corruption_rate},
        )
