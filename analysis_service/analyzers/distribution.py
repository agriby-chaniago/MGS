import os
from analyzers.base import AnalysisResult, BaseAnalyzer


def gini(counts: list[int]) -> float:
    n = len(counts)
    if n == 0 or sum(counts) == 0:
        return 0.0
    counts = sorted(counts)
    total = sum(counts)
    return sum((2 * i - n - 1) * x for i, x in enumerate(counts, 1)) / (n * total)


class DistributionAnalyzer(BaseAnalyzer):
    @property
    def analyzer_type(self) -> str:
        return "distribution"

    def analyze(self, dataset_path: str, config: dict) -> AnalysisResult:
        class_counts: dict[str, int] = {}

        for entry in os.scandir(dataset_path):
            if entry.is_dir():
                count = sum(1 for _ in os.scandir(entry.path))
                class_counts[entry.name] = count

        counts = list(class_counts.values())
        gini_coeff = round(gini(counts), 4)

        return AnalysisResult(
            analyzer_type=self.analyzer_type,
            status="completed",
            findings=[],
            summary={
                "total_classes": len(class_counts),
                "total_images": sum(counts),
                "images_per_class": class_counts,
                "gini_coefficient": gini_coeff,
            },
            metrics={"gini_coefficient": gini_coeff},
        )
