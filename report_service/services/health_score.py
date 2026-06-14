# TODO (Agriby - Fase 4):
# Score = 0.30*I + 0.25*U + 0.25*D + 0.20*Q
# I: valid_images / total_images
# U: 1 - (duplicate_count / total_images), PHash hamming ≤ 10
# D: 1 - gini_coefficient(class_counts)
# Q: % gambar dalam ±1σ dari median resolution
# Threshold lulus: ≥ 0.80
