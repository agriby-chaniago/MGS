# ModelGate — CV Dataset Quality Audit

Platform audit kualitas dataset Computer Vision berbasis microservices. Upload dataset ZIP, jalankan audit otomatis (corruption, resolution, distribution, duplikat), dan dapatkan laporan dengan Health Score.

---

## Arsitektur

```
Browser → Streamlit (8501)
             ↓
          Nginx (8080)  ← API Gateway
         /    |    \    \
    dataset audit analysis report
     (8001) (8002)  (8003) (8004)
         \     |      /
        PostgreSQL  MinIO  RabbitMQ
```

| Service | Port | Fungsi |
|---|---|---|
| Streamlit | 8501 | UI |
| Nginx | 8080 | API Gateway |
| dataset_service | 8001 | Upload & manajemen dataset |
| audit_service | 8002 | Orkestrasi audit |
| analysis_service | 8003 | Analisis gambar (5 analyzer) |
| report_service | 8004 | Laporan & PDF |
| PostgreSQL | 5432 | Database utama |
| MinIO | 9000/9001 | Object storage (gambar) |
| RabbitMQ | 5672/15672 | Message queue |

---

## Requirements

- Docker & Docker Compose
- 4GB RAM minimum (dataset besar butuh lebih)
- Port 8080, 8501, 9000, 9001, 15672 tidak dipakai proses lain

---

## Cara Menjalankan

### 1. Clone & konfigurasi

```bash
git clone <repo-url>
cd MGS
cp .env.example .env
```

File `.env` berisi kredensial default untuk development. **Jangan commit `.env` ke repository.**

### 2. Jalankan semua service

```bash
docker compose up -d --build
```

Tunggu sampai semua container healthy (±1-2 menit, terutama PostgreSQL dan RabbitMQ).

### 3. Akses aplikasi

| URL | Keterangan |
|---|---|
| http://localhost:8501 | Aplikasi utama (Streamlit UI) |
| http://localhost:8080 | API Gateway (Nginx) |
| http://localhost:8080/docs/ | API Documentation (RapiDoc) |
| http://localhost:9001 | MinIO Console (minioadmin / minioadmin123) |
| http://localhost:15672 | RabbitMQ Management (guest / guest) |

---

## Alur Penggunaan

```
1. Upload Dataset ZIP
   └── Format: ZIP berisi subfolder per kelas
       Contoh: dataset.zip/cats/, dataset.zip/dogs/
       Ukuran maksimum: 2GB

2. Jalankan Audit
   └── 5 analyzer berjalan otomatis:
       - Corruption  : deteksi file gambar rusak
       - Empty       : deteksi folder/kelas kosong
       - Resolution  : analisis distribusi resolusi
       - Distribution: keseimbangan antar kelas (Gini)
       - Duplicate   : deteksi gambar duplikat (pHash)

3. Lihat Laporan
   └── Health Score (0-1) dengan grade A/B/C/D/F
       Komponen: Integrity (30%), Uniqueness (25%),
                 Distribution (25%), Quality (20%)
       Download PDF
```

---

## API Documentation

Dokumentasi interaktif tersedia via **RapiDoc** — buka `http://localhost:8080/docs/` saat stack jalan, atau buka `docs/index.html` langsung di browser (tanpa docker).

### Refresh specs (opsional)

Setelah ada perubahan endpoint, generate ulang spec dari service yang sedang jalan:

```bash
bash docs/generate_specs.sh
```

Lalu commit `docs/openapi/*.json`.

---

## API Endpoints

### Dataset Service
```
POST   /api/v1/datasets/upload      Upload dataset ZIP
GET    /api/v1/datasets             List semua dataset
GET    /api/v1/datasets/{id}        Detail dataset + kelas
DELETE /api/v1/datasets/{id}        Soft delete dataset
```

### Audit Service
```
POST   /api/v1/audits               Buat audit baru
GET    /api/v1/audits/{id}          Status audit
POST   /api/v1/audits/{id}/retry    Retry audit yang gagal
```

### Report Service
```
GET    /api/v1/reports/{audit_id}          Hasil per-analyzer
GET    /api/v1/reports/{audit_id}/summary  Health score & komponen
GET    /api/v1/reports/{audit_id}/pdf      Download PDF
```

---

## Development

### Rebuild satu service

```bash
docker compose up -d --build <service_name>
docker compose restart nginx   # WAJIB setelah rebuild apapun
```

> **Penting:** Setiap rebuild mengubah IP container. Nginx harus di-restart agar tahu IP baru.

### Lihat logs

```bash
docker compose logs -f <service_name>
# Contoh:
docker compose logs -f analysis_service
docker compose logs -f audit_service
```

### Matikan semua service

```bash
docker compose down          # Matikan, data tetap ada
docker compose down -v       # Matikan + hapus semua data (reset total)
```

### Struktur direktori

```
MGS/
├── dataset_service/    FastAPI — upload & dataset management
├── audit_service/      FastAPI — audit orchestration + RabbitMQ publisher
├── analysis_service/   FastAPI — 5 image analyzers + RabbitMQ consumer
├── report_service/     FastAPI — health score + PDF generation
├── streamlit_app/      Streamlit UI
├── shared/             Kode bersama (response format, dll)
├── nginx/              nginx.conf (API gateway config)
├── docs/               API documentation (RapiDoc)
│   ├── index.html          UI docs
│   ├── rapidoc-min.js      RapiDoc bundled (offline)
│   ├── generate_specs.sh   Refresh OpenAPI specs dari running services
│   └── openapi/            OpenAPI 3.0 JSON per service
├── docker-compose.yml
└── .env.example        Template konfigurasi (salin ke .env)
```
