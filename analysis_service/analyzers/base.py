from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    analyzer_type: str
    status: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, dataset_path: str, config: dict) -> AnalysisResult:
        pass

    @property
    @abstractmethod
    def analyzer_type(self) -> str:
        pass
