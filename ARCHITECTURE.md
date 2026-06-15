# ModelGate — Arsitektur Teknis

## Gambaran Umum

ModelGate dibangun dengan pola **microservices** — setiap domain fungsional berjalan sebagai proses independen dengan database schema sendiri. Komunikasi antar service menggunakan dua jalur: **HTTP sinkron** (via Nginx) untuk operasi user-facing, dan **RabbitMQ asinkron** untuk proses berat yang berjalan di background.

```
                        ┌─────────────┐
                        │  Streamlit  │  UI (port 8501)
                        └──────┬──────┘
                               │ HTTP
                        ┌──────▼──────┐
                        │    Nginx    │  API Gateway (port 8080)
                        └──┬──┬──┬───┘
              ┌────────────┘  │  │  └────────────┐
              │               │  │               │
      ┌───────▼──────┐ ┌──────▼──▼──────┐ ┌──────▼──────┐
      │   dataset    │ │     audit      │ │   report    │
      │   service   │ │    service     │ │   service   │
      │   (8001)    │ │    (8002)      │ │   (8004)    │
      └───────┬──────┘ └──────┬─────────┘ └──────┬──────┘
              │               │ publish            │ read
              │          ┌────▼────┐               │
              │          │Rabbit MQ│               │
              │          │audit.   │               │
              │          │jobs     │               │
              │          └────┬────┘               │
              │               │ consume            │
              │        ┌──────▼──────┐             │
              │        │  analysis   │             │
              │        │  service   │             │
              │        │  (8003)    │             │
              │        └──────┬──────┘             │
              │               │ publish            │
              │          ┌────▼────┐               │
              │          │Rabbit MQ│               │
              │          │analysis.│               │
              │          │results  │               │
              │          └────┬────┘               │
              │               │ consume            │
              │        ┌──────▼──────┐             │
              │        │   audit     │ ←───────────┘
              │        │  service   │   read-only
              │        │(consumer)  │
              │        └─────────────┘
              │
      ┌───────▼─────────────────────────────────────┐
      │                 PostgreSQL                   │
      │  dataset_svc  audit_svc  analysis_svc  ...  │
      └─────────────────────────────────────────────┘
              │
      ┌───────▼──────┐
      │    MinIO     │  Object Storage (gambar)
      └──────────────┘
```

---

## Service Breakdown

### 1. dataset_service (port 8001)

**Tanggung jawab:** Menerima upload dataset, validasi struktur ZIP, menyimpan metadata ke DB, dan mengunggah gambar ke MinIO.

**Flow upload:**
```
Client → POST /upload
  1. Baca bytes, cek size ≤ 2GB
  2. Hitung SHA-256 hash → cek dedup di DB
  3. Validasi struktur ZIP (minimal 2 kelas)
  4. Extract ke /tmp
  5. Scan gambar per kelas
  6. Upload ke MinIO: modelgate-datasets/{dataset_id}/{class}/{file}
  7. Simpan metadata ke dataset_svc.datasets
  8. Return dataset_id
```

**Deduplication:** File yang sama (hash identik) langsung return `cached: true` tanpa re-upload. SHA-256 disimpan di kolom `file_hash`.

**Owned tables:** `dataset_svc.datasets`, `dataset_svc.dataset_classes`

---

### 2. audit_service (port 8002)

**Tanggung jawab:** Membuat audit job, mempublikasikan ke RabbitMQ, melacak status, dan menyediakan endpoint retry.

**State machine audit:**
```
pending → queued → processing → completed
                             ↘ failed → queued (retry)
```

Transisi divalidasi oleh `state_machine.py` — kode tidak bisa melompat state sembarangan.

**Flow create audit:**
```
POST /api/v1/audits
  1. Validasi dataset_id ada dan aktif
  2. Cek cache: ada audit completed untuk dataset ini? → return cached
  3. Buat record Audit (status: pending)
  4. Commit ke DB (supaya audit_id tersedia sebelum message diterima consumer)
  5. Publish ke RabbitMQ queue "audit.jobs"
  6. Transisi status → queued
  7. Return audit_id
```

**Deduplication:** Satu dataset hanya punya satu hasil audit aktif. Audit kedua untuk dataset yang sama langsung return hasil yang sudah ada (`cached: true`). Bisa di-bypass dengan `force: true` (retry).

**Owned tables:** `audit_svc.audits`
**Read-only mirror:** `dataset_svc.datasets` (untuk validasi dataset_id)

---

### 3. analysis_service (port 8003)

**Tanggung jawab:** Consumer RabbitMQ yang menjalankan 5 analyzer secara berurutan, menyimpan hasil per analyzer, dan mempublikasikan hasil ke queue berikutnya.

**Flow analisis:**
```
Consume dari "audit.jobs"
  1. Cek force=True → hapus semua result lama (retry path)
  2. Idempotency check: semua analyzer sudah selesai? → skip
  3. Validasi audit.status == "queued"
  4. Download dataset dari MinIO ke /tmp/analysis_{audit_id}/
  5. Set audit.status = "processing"
  6. Loop 5 analyzer:
     a. Run analyzer (dengan retry 3x: delay 5s, 15s, 30s)
     b. Simpan AnalysisResult ke DB
     c. Publish result ke "analysis.results"
  7. Cleanup /tmp
  8. ACK message
```

**Per-analyzer retry:** Setiap analyzer dicoba maksimal 3 kali sebelum dianggap gagal. Kegagalan satu analyzer tidak menghentikan analyzer lain.

**5 Analyzer:**

| Analyzer | Teknik | Output Metrik |
|---|---|---|
| `CorruptionAnalyzer` | PIL Image.verify() | `corruption_rate` |
| `EmptyAnalyzer` | Count file per folder | `empty_rate`, `empty_count` |
| `ResolutionAnalyzer` | Statistik W×H, ±1σ | `images_in_normal_range` |
| `DistributionAnalyzer` | Gini coefficient | `gini_coefficient` |
| `DuplicateAnalyzer` | pHash + numpy vectorized | `uniqueness_rate` |

**Duplicate analyzer:** Menggunakan perceptual hash (pHash 64-bit) + numpy broadcasting untuk perbandingan O(n²) yang dioptimasi:
```python
# Vectorized: bandingkan gambar i dengan semua gambar setelahnya sekaligus
distances = np.sum(hash_matrix[i] != hash_matrix[i+1:], axis=1)
duplicates = np.where(distances <= HAMMING_THRESHOLD)[0]
# ~30x lebih cepat dari pure Python loop
```

**Owned tables:** `analysis_svc.analysis_results`
**Read-only mirror:** `audit_svc.audits` (untuk update status)

---

### 4. report_service (port 8004)

**Tanggung jawab:** Membaca hasil analisis, menghitung Health Score, dan menghasilkan laporan PDF.

**Health Score Formula:**
```
Score = 0.30×I + 0.25×U + 0.25×D + 0.20×Q

I (Integrity)     = 1 - corruption_rate
U (Uniqueness)    = uniqueness_rate (dari pHash)
D (Distribution)  = 1 - gini_coefficient
Q (Quality)       = images_in_normal_range (dalam ±1σ median resolusi)
```

**Catatan EmptyAnalyzer:** Hasil `empty_rate` ditampilkan di laporan sebagai informasi tambahan, tapi tidak masuk formula Health Score. Alasan: file kosong sudah sebagian tercover oleh Corruption (file tidak bisa dibaca) dan Quality (resolusi outlier).

**Grade:**

| Score | Grade |
|---|---|
| ≥ 0.80 | A |
| 0.60 – 0.79 | B |
| 0.40 – 0.59 | C |
| < 0.40 | D |

**Read-only tables:** `audit_svc.audits`, `analysis_svc.analysis_results`
(Report service tidak memiliki tabel sendiri — hanya membaca dari service lain)

---

## Database Design

### Satu Database, Banyak Schema

ModelGate menggunakan **satu database PostgreSQL** (`modelgate`) dengan **schema terpisah per service**. Ini memberikan isolasi logis tanpa overhead operasional multiple databases.

```
modelgate (database)
├── dataset_svc (schema)   ← owned by dataset_service
│   ├── datasets
│   └── dataset_classes
├── audit_svc (schema)     ← owned by audit_service
│   └── audits
├── analysis_svc (schema)  ← owned by analysis_service
│   └── analysis_results
└── report_svc (schema)    ← owned by report_service (kosong, baca lintas schema)
```

### Bounded Context & Read-Only Mirrors

Setiap service **hanya boleh menulis ke schema miliknya sendiri**. Untuk membaca data service lain, service menggunakan **read-only mirror model** — class SQLAlchemy yang memetakan tabel service lain tapi **tidak pernah di-pass ke `create_all()`**.

```python
# audit_service/models/orm.py
class Audit(AuditBase):           # ← AuditBase di-pass ke create_all() ✓
    __table_args__ = {"schema": "audit_svc"}

class DatasetReadOnly(ReadOnlyBase):  # ← ReadOnlyBase TIDAK di-pass ke create_all() ✗
    __table_args__ = {"schema": "dataset_svc"}
    # Hanya untuk SELECT — tidak bisa CREATE/ALTER tabel ini
```

Pola ini mencegah service lain secara tidak sengaja memodifikasi schema yang bukan miliknya.

---

## Message Queue (RabbitMQ)

Dua queue dengan pesan **persistent** (delivery_mode=2 — bertahan jika RabbitMQ restart):

### Queue: `audit.jobs`

**Publisher:** audit_service (saat audit dibuat atau di-retry)
**Consumer:** analysis_service

```json
{
  "audit_id": "uuid",
  "dataset_id": "uuid",
  "dataset_minio_path": "modelgate-datasets/uuid/",
  "requested_analyzers": ["corruption", "empty", "resolution", "distribution", "duplicate"],
  "created_at": "2026-01-01T00:00:00",
  "force": false
}
```

`force: true` → consumer hapus semua AnalysisResult lama sebelum mulai (retry path).

### Queue: `analysis.results`

**Publisher:** analysis_service (satu pesan per analyzer selesai)
**Consumer:** audit_service (update status audit)

```json
{
  "audit_id": "uuid",
  "analyzer_type": "duplicate",
  "status": "completed",
  "result_payload": { "findings": [...], "summary": {...}, "metrics": {...} },
  "error_message": null,
  "completed_at": "2026-01-01T00:00:00"
}
```

**Prefetch count = 1:** Consumer hanya ambil 1 message sekaligus. Satu audit bisa memakan waktu menit (terutama duplicate analyzer untuk dataset besar) — prefetch 1 mencegah consumer "kehabisan napas" saat ada banyak job antri.

---

## Object Storage (MinIO)

Dataset gambar **tidak disimpan di database** — hanya di MinIO. Database hanya menyimpan path (`minio_path`).

**Bucket:** `modelgate-datasets`

**Struktur objek:**
```
modelgate-datasets/
└── {dataset_id}/
    ├── cats/
    │   ├── img001.jpg
    │   └── img002.jpg
    └── dogs/
        └── img003.jpg
```

**Flow analysis:** analysis_service mendownload seluruh dataset ke `/tmp/analysis_{audit_id}/` sebelum menjalankan analyzer. Setelah selesai, `/tmp` dibersihkan otomatis.

**Soft delete:** Saat dataset dihapus, DB di-update (`status = "deleted"`) lalu MinIO prefix dibersihkan (`delete_prefix("{dataset_id}/")`). Kegagalan MinIO tidak membatalkan DB delete — best-effort cleanup.

---

## API Gateway (Nginx)

Nginx berfungsi sebagai **reverse proxy** yang meneruskan request ke service yang tepat berdasarkan path prefix.

```nginx
location /api/v1/datasets  → dataset_service:8001
location /api/v1/datasets/ → dataset_service:8001  (upload: path ada /upload suffix)
location /api/v1/audits    → audit_service:8002
location /api/v1/analyses  → analysis_service:8003
location /api/v1/reports   → report_service:8004
```

**Catatan trailing slash:** Location tanpa trailing slash (`/api/v1/audits`) mencegah nginx mengirim 301 redirect yang menyebabkan infinite redirect loop dengan FastAPI. Location `/api/v1/datasets/` (dengan slash) aman karena path upload selalu punya suffix (`/upload`).

**Upload limit:** `client_max_body_size 2048M` — sesuai batas maksimum dataset 2GB.

---

## Shared Code

Kode yang dipakai oleh semua service (format response, dll) disimpan di folder `shared/` dan di-mount sebagai Docker volume:

```yaml
volumes:
  - ./shared:/app/shared
environment:
  - PYTHONPATH=/app
```

Service mengimport dengan `from shared.response import success_response`.

**Standar response format:**
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "metadata": {
    "service": "audit_service",
    "version": "1.0.0",
    "timestamp": "2026-01-01T00:00:00+00:00"
  }
}
```

---

## Keputusan Arsitektur

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Komunikasi sinkron | HTTP + Nginx | Simpel untuk operasi CRUD user-facing |
| Komunikasi async | RabbitMQ | Analisis gambar bisa makan waktu menit — tidak bisa blocking HTTP |
| Object storage | MinIO | File gambar tidak masuk DB (besar, binary), MinIO S3-compatible |
| Schema isolation | Satu DB, banyak schema | Isolasi tanpa overhead operasional multi-DB |
| Cross-service read | Read-only mirror model | Tidak ada shared ORM, tidak ada direct cross-schema write |
| Sync SQLAlchemy | psycopg2 | Analisis CPU-bound (numpy, PIL) — async tidak memberikan keuntungan |
| Dedup upload | SHA-256 file hash | Cegah duplikat dataset identik tanpa perbandingan byte-by-byte |
| Dedup audit | Cache per dataset_id | Hasil audit tidak berubah untuk dataset yang sama |
| pHash threshold | Hamming distance ≤ 10 | Toleransi kompresi/resize minor, reject gambar yang benar-benar berbeda |
