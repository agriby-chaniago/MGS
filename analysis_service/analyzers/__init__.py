from analyzers.corruption import CorruptionAnalyzer
from analyzers.empty import EmptyAnalyzer
from analyzers.resolution import ResolutionAnalyzer
from analyzers.distribution import DistributionAnalyzer
from analyzers.duplicate import DuplicateAnalyzer


def get_analyzers() -> list:
    return [
        CorruptionAnalyzer(),
        EmptyAnalyzer(),
        ResolutionAnalyzer(),
        DistributionAnalyzer(),
        DuplicateAnalyzer(),
    ]
