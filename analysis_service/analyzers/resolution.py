import os
import numpy as np
from PIL import Image
from analyzers.base import AnalysisResult, BaseAnalyzer


class ResolutionAnalyzer(BaseAnalyzer):
    @property
    def analyzer_type(self) -> str:
        return "resolution"

    def analyze(self, dataset_path: str, config: dict) -> AnalysisResult:
        widths = []
        heights = []

        for root, _, files in os.walk(dataset_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with Image.open(fpath) as img:
                        w, h = img.size
                    widths.append(w)
                    heights.append(h)
                except Exception:
                    pass

        total = len(widths)
        if total == 0:
            return AnalysisResult(
                analyzer_type=self.analyzer_type,
                status="completed",
                findings=[],
                summary={"total": 0},
                metrics={"images_in_normal_range": 0.0},
            )

        w_arr = np.array(widths, dtype=np.float64)
        h_arr = np.array(heights, dtype=np.float64)

        median_w = float(np.median(w_arr))
        median_h = float(np.median(h_arr))
        std_w = float(np.std(w_arr))
        std_h = float(np.std(h_arr))

        in_range = sum(
            1 for w, h in zip(widths, heights)
            if abs(w - median_w) <= std_w and abs(h - median_h) <= std_h
        )
        images_in_normal_range = round(in_range / total, 4)

        return AnalysisResult(
            analyzer_type=self.analyzer_type,
            status="completed",
            findings=[],
            summary={
                "total": total,
                "median_width": round(median_w, 2),
                "median_height": round(median_h, 2),
                "std_width": round(std_w, 2),
                "std_height": round(std_h, 2),
                "min_res": f"{int(min(widths))}x{int(min(heights))}",
                "max_res": f"{int(max(widths))}x{int(max(heights))}",
            },
            metrics={"images_in_normal_range": images_in_normal_range},
        )
