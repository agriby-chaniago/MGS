def calculate_health_score(results: list[dict]) -> dict:
    """
    Score = 0.30*I + 0.25*U + 0.25*D + 0.20*Q

    I = 1 - corruption_rate     (CorruptionAnalyzer.metrics)
    U = uniqueness_rate          (DuplicateAnalyzer.metrics)
    D = 1 - gini_coefficient     (DistributionAnalyzer.metrics)
    Q = images_in_normal_range   (ResolutionAnalyzer.metrics)

    Jika analyzer selesai tapi metrics kosong, default ke nilai netral (1.0).
    """
    metrics = {
        r["analyzer_type"]: (r.get("result_payload") or {}).get("metrics", {})
        for r in results
    }

    # EmptyAnalyzer tidak berkontribusi langsung ke formula Health Score.
    # Hasilnya (empty_rate, empty_count) tersedia di full report sebagai
    # informasi tambahan. Rationale: empty images sudah tercover sebagian
    # oleh Integrity (corruption) dan Quality (resolution outlier).
    I = 1.0 - metrics.get("corruption", {}).get("corruption_rate", 0.0)
    U = metrics.get("duplicate", {}).get("uniqueness_rate", 1.0)
    D = 1.0 - metrics.get("distribution", {}).get("gini_coefficient", 0.0)
    Q = metrics.get("resolution", {}).get("images_in_normal_range", 1.0)

    score = round(0.30 * I + 0.25 * U + 0.25 * D + 0.20 * Q, 4)
    grade = "A" if score >= 0.80 else "B" if score >= 0.60 else "C" if score >= 0.40 else "D"

    return {
        "score": score,
        "grade": grade,
        "components": {
            "I": round(I, 4),
            "U": round(U, 4),
            "D": round(D, 4),
            "Q": round(Q, 4),
        },
    }
