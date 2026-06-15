# Product Requirements Document (PRD)
# ModelGate — CV Dataset Quality Audit Platform

**Versi:** 1.0  
**Tanggal:** 15 Juni 2026  
**Author:** Agrieby Chaniago  
**Status:** Released (MVP)

---

## 1. Latar Belakang & Problem Statement

### Masalah

Dalam pengembangan model Computer Vision (CV), kualitas dataset adalah penentu utama performa model. Namun, proses validasi kualitas dataset umumnya dilakukan secara manual — atau tidak dilakukan sama sekali.

**Akibatnya:**
- File gambar rusak lolos ke pipeline training tanpa terdeteksi
- Gambar duplikat menyebabkan model overfit pada subset data tertentu
- Distribusi kelas tidak seimbang (imbalanced) menghasilkan model yang bias
- Inkonsistensi resolusi mengganggu augmentasi dan normalisasi
- Masalah baru terdeteksi saat evaluasi — setelah berjam-jam compute time terbuang

### Root Cause

Tidak ada tools standar yang:
1. Mudah digunakan tanpa koding
2. Menjalankan multiple jenis audit sekaligus
3. Menghasilkan laporan terstruktur yang bisa didokumentasikan

### Solusi

**ModelGate** — platform audit kualitas dataset CV berbasis web. Upload dataset ZIP, sistem menjalankan 5 jenis analisis otomatis, menghasilkan Health Score, dan membuat laporan PDF yang bisa diunduh.

---

## 2. Tujuan Produk

### Tujuan Utama

Menyediakan checkpoint kualitas yang dapat digunakan **sebelum** dataset masuk ke pipeline training machine learning, tanpa memerlukan keahlian coding dari pengguna.

### Success Metrics (MVP)

| Metrik | Target |
|---|---|
| Waktu audit dataset ≤ 500 gambar | < 60 detik |
| Waktu audit dataset ≤ 5.000 gambar | < 10 menit |
| Upload berhasil tanpa error | 100% untuk file ZIP valid |
| Health Score computation | Hasil deterministik untuk input yang sama |
| PDF laporan dapat diunduh | Selalu tersedia setelah audit selesai |
| Retry audit gagal | Berhasil tanpa restart aplikasi |

---

## 3. User Persona

### Persona 1 — Mahasiswa Peneliti

**Profil:** Mahasiswa S1/S2 yang mengerjakan skripsi atau tugas akhir berbasis CV  
**Kebutuhan:** Memastikan dataset yang dikumpulkan dari internet atau labeling tool siap dipakai  
**Pain point:** Tidak tahu cara audit dataset, tidak mau coding tambahan  
**Ekspektasi:** Upload ZIP → tunggu → baca hasil → download laporan  

### Persona 2 — ML Engineer

**Profil:** Engineer yang mengelola pipeline training di tim kecil  
**Kebutuhan:** Audit cepat sebelum dataset masuk ke training job  
**Pain point:** Audit manual memakan waktu, hasil tidak konsisten antar orang  
**Ekspektasi:** API-driven, hasil reproducible, laporan bisa dilampirkan ke ticket  

### Persona 3 — Data Curator

**Profil:** Orang yang bertanggung jawab mengumpulkan dan mengelola dataset tim  
**Kebutuhan:** Deteksi masalah kualitas secara batch, bukan per-file manual  
**Pain point:** Duplikat dan imbalance hanya ketahuan saat model sudah dilatih  
**Ekspektasi:** Laporan detail per-komponen, grade yang jelas, dapat dibandingkan antar versi dataset  

---

## 4. Scope

### In Scope (MVP v1.0)

- Upload dataset dalam format ZIP dengan struktur per-kelas
- 5 analyzer: Corruption, Empty, Resolution, Distribution, Duplicate
- Health Score (0–1) dengan grade A/B/C/D
- Laporan interaktif di UI + PDF yang bisa diunduh
- Dataset history (lihat dataset yang pernah diupload)
- Re-audit paksa (bypass cache) untuk dataset yang sudah pernah diaudit
- Retry audit yang gagal tanpa mulai dari awal
- Soft delete dataset (dengan cleanup file dari object storage)

### Out of Scope (v1.0)

- Autentikasi dan multi-user (semua user akses data yang sama)
- Perbaikan dataset otomatis (remove duplicate, resize, dll)
- Integrasi langsung ke training framework (PyTorch, TensorFlow)
- Dataset non-gambar (teks, audio, video)
- Labeling atau anotasi gambar
- Komparasi dua dataset
- Scheduled / recurring audit
- Notifikasi email/webhook saat audit selesai

---

## 5. User Stories

### Upload Dataset

**US-01** — Sebagai pengguna, saya ingin mengupload dataset dalam format ZIP agar sistem bisa menganalisisnya tanpa saya perlu menyiapkan lingkungan khusus.

**Acceptance Criteria:**
- [ ] Upload ZIP melalui UI drag-and-drop
- [ ] Batas ukuran: 2GB
- [ ] Struktur valid: minimal 2 subfolder (kelas) berisi file gambar
- [ ] Upload yang sama (hash identik) tidak diupload ulang — return cached
- [ ] Tampilkan progress bar saat upload berlangsung
- [ ] Tampilkan error jelas jika format tidak valid

**US-02** — Sebagai pengguna, saya ingin melihat daftar dataset yang pernah saya upload agar bisa langsung memilih tanpa upload ulang.

**Acceptance Criteria:**
- [ ] Sidebar menampilkan list dataset dengan nama dan jumlah gambar
- [ ] Klik dataset langsung masuk ke step audit dengan dataset terpilih
- [ ] Dataset yang dihapus tidak muncul di list

---

### Audit

**US-03** — Sebagai pengguna, saya ingin menjalankan audit kualitas dataset dengan satu klik agar tidak perlu mengkonfigurasi apa pun.

**Acceptance Criteria:**
- [ ] Tombol "Buat Audit" tersedia setelah dataset siap
- [ ] Audit berjalan otomatis untuk semua 5 analyzer
- [ ] Tampilkan progress real-time per analyzer (nama, status, waktu selesai)
- [ ] Notifikasi jika audit sudah pernah ada (cached) dengan opsi force re-run

**US-04** — Sebagai pengguna, saya ingin bisa menjalankan ulang audit yang gagal tanpa harus upload dataset lagi.

**Acceptance Criteria:**
- [ ] Tampilkan tombol "Coba Lagi" jika audit berstatus `failed`
- [ ] Retry langsung melanjutkan dari state yang ada, tanpa upload ulang
- [ ] Progress polling restart otomatis setelah retry

---

### Laporan

**US-05** — Sebagai pengguna, saya ingin melihat Health Score dataset saya beserta penjelasan komponen-komponennya.

**Acceptance Criteria:**
- [ ] Tampilkan score numerik (0–1, 4 desimal) dan grade (A/B/C/D)
- [ ] Breakdown 4 komponen: Integrity, Uniqueness, Distribution, Quality
- [ ] Penjelasan temuan per analyzer (contoh: "12 gambar duplikat ditemukan")
- [ ] Laporan tersedia segera setelah audit selesai (auto-load)

**US-06** — Sebagai pengguna, saya ingin mengunduh laporan dalam format PDF agar bisa saya lampirkan ke dokumentasi atau presentasi.

**Acceptance Criteria:**
- [ ] Tombol download PDF tersedia di halaman laporan
- [ ] PDF berisi Health Score, grade, breakdown komponen, dan detail temuan
- [ ] Download berlangsung dalam 1 klik tanpa loading page

---

### Manajemen Dataset

**US-07** — Sebagai pengguna, saya ingin menghapus dataset yang sudah tidak diperlukan agar tidak memenuhi storage.

**Acceptance Criteria:**
- [ ] Tombol delete tersedia di UI
- [ ] Soft delete: dataset tidak muncul di list, file di object storage dihapus
- [ ] Konfirmasi sebelum delete

---

## 6. Functional Requirements

### FR-01: Upload & Validasi

| ID | Requirement |
|---|---|
| FR-01.1 | Sistem menerima file ZIP maksimal 2GB |
| FR-01.2 | Struktur ZIP harus berisi minimal 2 subfolder level-1 (kelas) |
| FR-01.3 | File di root ZIP (bukan dalam subfolder kelas) diabaikan |
| FR-01.4 | File SHA-256 hash dicek sebelum upload — duplikat return `cached: true` tanpa re-upload |
| FR-01.5 | Gambar diunggah ke object storage dengan path `{dataset_id}/{class}/{filename}` |
| FR-01.6 | Metadata (jumlah gambar, kelas, ukuran file) disimpan ke database |

### FR-02: Analisis

| ID | Requirement |
|---|---|
| FR-02.1 | Setiap audit menjalankan 5 analyzer: Corruption, Empty, Resolution, Distribution, Duplicate |
| FR-02.2 | Analyzer berjalan asinkron via message queue — tidak blocking HTTP request |
| FR-02.3 | Kegagalan satu analyzer tidak menghentikan analyzer lain |
| FR-02.4 | Setiap analyzer dicoba ulang maksimal 3 kali (delay: 5s, 15s, 30s) sebelum dinyatakan gagal |
| FR-02.5 | Audit kedua untuk dataset yang sama (hash sama) return hasil cached tanpa re-analisis |
| FR-02.6 | Force re-audit (bypass cache) tersedia via toggle di UI |

#### Spesifikasi Per Analyzer

**Corruption Analyzer**
- Cek setiap file dengan `PIL.Image.verify()`
- Output: `corruption_rate` = jumlah file rusak / total file

**Empty Analyzer**
- Hitung jumlah gambar per kelas
- Deteksi kelas dengan 0 gambar
- Output: `empty_count`, `empty_rate`

**Resolution Analyzer**
- Hitung width dan height setiap gambar
- Tentukan median resolusi
- Gambar "normal" = dalam ±1 standar deviasi dari median
- Output: `images_in_normal_range` (rasio 0–1)

**Distribution Analyzer**
- Hitung jumlah gambar per kelas
- Hitung Gini coefficient dari distribusi tersebut
- Output: `gini_coefficient` (0 = sempurna merata, 1 = semua di satu kelas)

**Duplicate Analyzer**
- Hitung perceptual hash (pHash 64-bit) setiap gambar
- Bandingkan semua pasang gambar dengan numpy vectorized (O(n²) dioptimasi)
- Dua gambar = duplikat jika Hamming distance ≤ 10
- Output: `uniqueness_rate` = gambar unik / total gambar

### FR-03: Health Score

| ID | Requirement |
|---|---|
| FR-03.1 | Health Score dihitung dari 4 komponen: `0.30×I + 0.25×U + 0.25×D + 0.20×Q` |
| FR-03.2 | I (Integrity) = `1 - corruption_rate` |
| FR-03.3 | U (Uniqueness) = `uniqueness_rate` |
| FR-03.4 | D (Distribution) = `1 - gini_coefficient` |
| FR-03.5 | Q (Quality) = `images_in_normal_range` |
| FR-03.6 | Grade: A ≥ 0.80, B ≥ 0.60, C ≥ 0.40, D < 0.40 |
| FR-03.7 | Empty rate ditampilkan sebagai informasi, tidak masuk formula |

### FR-04: State Machine Audit

Status audit mengikuti transisi yang valid:

```
pending → queued → processing → completed
                             ↘ failed → queued (retry)
```

Transisi di luar pola ini ditolak sistem.

### FR-05: Laporan

| ID | Requirement |
|---|---|
| FR-05.1 | Laporan tersedia di UI segera setelah audit selesai (auto-load) |
| FR-05.2 | Laporan menampilkan Health Score, grade, breakdown per komponen, dan temuan per analyzer |
| FR-05.3 | PDF dapat diunduh dalam 1 klik |
| FR-05.4 | Laporan diberi ID unik (audit_id) untuk referensi |

### FR-06: Manajemen Dataset

| ID | Requirement |
|---|---|
| FR-06.1 | Dataset dapat dihapus (soft delete) — status berubah jadi `deleted`, tidak muncul di list |
| FR-06.2 | File gambar di object storage dihapus saat dataset dihapus (best-effort) |
| FR-06.3 | Dataset history ditampilkan di sidebar, urut dari terbaru |
| FR-06.4 | Dataset yang dihapus tidak bisa di-audit ulang |

---

## 7. Non-Functional Requirements

### Performance

| Requirement | Target |
|---|---|
| Upload dataset 100MB | < 30 detik (bergantung koneksi) |
| Audit 500 gambar (5 analyzer) | < 60 detik |
| Audit 5.000 gambar | < 10 menit |
| Load laporan setelah audit selesai | < 2 detik |
| Download PDF | < 5 detik |

### Reliability

| Requirement | Ketentuan |
|---|---|
| Idempotency upload | Upload file yang sama dua kali → hasil sama, tidak duplikat di DB |
| Idempotency audit | Restart consumer saat audit jalan tidak create duplicate results |
| Message durability | RabbitMQ message persistent (delivery_mode=2) — bertahan jika broker restart |
| Retry on analyzer failure | Setiap analyzer coba 3x dengan exponential delay sebelum mark failed |

### Scalability (scope MVP)

Sistem dirancang untuk single-node deployment. Multi-node (horizontal scale) bukan requirement MVP — arsitektur microservices memungkinkan scale per service di iterasi berikutnya.

### Security

| Requirement | Ketentuan |
|---|---|
| Secret management | Semua credential via environment variable, tidak hardcode |
| File gambar | Tidak pernah masuk ke RabbitMQ message body — hanya path ke object storage |
| Git | `.env` (credential asli) tidak boleh masuk repository |

### Usability

| Requirement | Ketentuan |
|---|---|
| No-code | Seluruh alur (upload → audit → laporan) bisa dilakukan dari UI tanpa API call manual |
| Step navigation | User tidak bisa melewati step yang belum selesai |
| Error recovery | Audit gagal bisa di-retry dari UI tanpa upload ulang |
| History | Dataset yang sudah diupload bisa dipilih kembali dari sidebar |

---

## 8. Technical Constraints

- **Runtime:** Docker Compose (semua service dalam satu host)
- **Language:** Python 3.11+ (semua service)
- **Database:** PostgreSQL — satu database, schema terpisah per service
- **Message queue:** RabbitMQ
- **Object storage:** MinIO (S3-compatible)
- **UI framework:** Streamlit
- **ORM:** SQLAlchemy (sync) + psycopg2
- **Image hashing:** imagehash (pHash), numpy untuk vectorized comparison
- **PDF generation:** reportlab

---

## 9. Asumsi & Dependensi

### Asumsi

- Dataset disediakan dalam format ZIP dengan struktur flat: `zip/class_name/images`
- Setiap subfolder level-1 dianggap sebagai satu kelas
- Gambar yang valid adalah file yang bisa dibuka oleh PIL
- "Duplikat" didefinisikan sebagai Hamming distance pHash ≤ 10 (bukan byte-identical)
- Satu audit mencakup semua 5 analyzer — tidak ada audit parsial

### Dependensi Eksternal

| Dependensi | Versi | Keterangan |
|---|---|---|
| Docker & Docker Compose | ≥ 24.0 | Runtime environment |
| PostgreSQL | 15 | Database |
| RabbitMQ | 3.12 | Message broker |
| MinIO | Latest | Object storage |

---

## 10. Risks & Mitigations

| Risk | Dampak | Mitigasi |
|---|---|---|
| Dataset sangat besar (> 1GB) → timeout upload | Upload gagal di tengah | Streaming upload; batas 2GB dengan validasi di Nginx |
| Duplicate analyzer O(n²) → lambat untuk dataset besar | Audit > 10 menit untuk 10k+ gambar | Numpy vectorized, bukan pure Python loop (~30x speedup) |
| RabbitMQ restart saat audit jalan | Message hilang, audit stuck di `processing` | delivery_mode=2 (persistent), consumer idempotency check |
| MinIO cleanup gagal saat delete | File orphan di storage | Best-effort cleanup; DB delete tidak rollback jika MinIO gagal |
| Consumer crash saat processing | Audit stuck di `processing` | Manual retry via `POST /api/v1/audits/{id}/retry` |
| pHash false positive | Gambar berbeda dianggap duplikat | Threshold Hamming ≤ 10 (bukan 0) — toleransi minor compression artifact |

---

## 11. Alur Pengguna (Happy Path)

```
1. Buka http://localhost:8501

2. [Step 1 — Upload]
   - Upload dataset.zip
   - Lihat progress bar
   - Lihat konfirmasi: nama, jumlah kelas, jumlah gambar
   - Klik "Lanjut ke Audit"

3. [Step 2 — Audit]
   - (Opsional) centang "Force re-audit" jika ingin audit ulang
   - Klik "Buat Audit"
   - Lihat tabel progress per analyzer (live update)
   - Tunggu status "Selesai"

4. [Step 3 — Laporan]
   - Lihat Health Score dan grade
   - Baca breakdown per komponen
   - Expand detail per analyzer
   - Klik "Download PDF"

5. (Opsional) Pilih dataset lain dari sidebar → kembali ke step 2
```

---

## 12. Riwayat Versi

| Versi | Tanggal | Perubahan |
|---|---|---|
| 0.1 | – | Phase 1–4: Core microservices, upload, audit, analysis, report |
| 0.5 | – | Phase 5 awal: 10 UI/UX bug fixes, step wizard, polling live |
| 1.0 | 2026-06-15 | Phase 5 final: sidebar history, MinIO cleanup, retry audit, dataset CRUD |
