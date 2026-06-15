# ModelGate — CV Dataset Quality Audit Platform

## What — Apa itu ModelGate?

ModelGate adalah platform audit kualitas dataset Computer Vision (CV) yang menganalisis dataset gambar secara otomatis dan menghasilkan **Health Score** sebagai indikator kelayakan dataset untuk digunakan dalam pelatihan model machine learning.

ModelGate bukan tool untuk melatih model — ModelGate adalah **penjaga gerbang** sebelum dataset masuk ke pipeline training.

---

## Who — Untuk Siapa?

| Pengguna | Kebutuhan |
|---|---|
| **Peneliti & Mahasiswa** | Memastikan dataset yang dikumpulkan layak sebelum eksperimen dimulai |
| **ML Engineer** | Audit dataset sebelum masuk pipeline training produksi |
| **Data Curator** | Mendeteksi masalah kualitas (duplikat, file rusak, distribusi tidak merata) secara otomatis |

---

## Why — Mengapa ModelGate Dibutuhkan?

Dataset berkualitas buruk adalah penyebab utama model CV yang gagal — bukan arsitektur modelnya.

**Masalah umum dataset yang sering tidak terdeteksi secara manual:**

- File gambar rusak yang tetap terbaca sebagai valid oleh sistem file
- Gambar duplikat yang menyebabkan model overfit pada data tertentu
- Ketidakseimbangan kelas yang signifikan (Gini coefficient tinggi)
- Resolusi tidak konsisten yang memengaruhi hasil augmentasi
- Folder kelas yang kosong atau hampir kosong

Tanpa audit, masalah ini baru ditemukan saat akurasi model stagnan atau saat evaluasi gagal — setelah berjam-jam waktu training terbuang.

---

## When — Kapan Menggunakannya?

ModelGate digunakan **sebelum** proses training dimulai, sebagai checkpoint wajib dalam ML pipeline:

```
Pengumpulan Data → [MODELGATE AUDIT] → Preprocessing → Training → Evaluasi
```

Gunakan ModelGate setiap kali:
- Dataset baru selesai dikumpulkan atau di-scraping
- Menggabungkan beberapa sumber dataset menjadi satu
- Menerima dataset dari pihak ketiga yang belum diverifikasi
- Menambahkan data baru ke dataset yang sudah ada

---

## Where — Di Mana ModelGate Berada dalam Ekosistem?

ModelGate berada di lapisan **Data Quality** — sebelum preprocessing dan training, setelah pengumpulan data mentah.

```
[Sumber Data]         raw images, scraping, labeling tools
      ↓
[MODELGATE]           audit otomatis, health score, laporan PDF
      ↓
[Preprocessing]       augmentasi, normalisasi, split train/val/test
      ↓
[Training]            PyTorch, TensorFlow, Keras, dll
      ↓
[Evaluasi & Deploy]   inference, monitoring
```

ModelGate berjalan sebagai layanan independen — tidak terikat pada framework ML apapun.

---

## How — Bagaimana Cara Kerjanya?

### 1. Upload Dataset

Dataset diunggah dalam format ZIP dengan struktur per kelas:

```
dataset.zip/
├── cats/
│   ├── img001.jpg
│   └── img002.jpg
└── dogs/
    ├── img003.jpg
    └── img004.jpg
```

### 2. Analisis Otomatis (5 Analyzer)

| Analyzer | Apa yang Dideteksi |
|---|---|
| **Corruption** | File gambar yang rusak atau tidak dapat dibaca |
| **Empty** | Kelas dengan sedikit atau tanpa gambar |
| **Resolution** | Konsistensi ukuran gambar antar kelas |
| **Distribution** | Keseimbangan jumlah gambar per kelas (Gini coefficient) |
| **Duplicate** | Gambar hampir identik menggunakan perceptual hash (pHash) |

### 3. Health Score

Skor akhir dihitung dari empat komponen berbobot:

```
Health Score = 0.30 × I  +  0.25 × U  +  0.25 × D  +  0.20 × Q

I = Integrity    (1 - corruption_rate)
U = Uniqueness   (1 - duplicate_rate)
D = Distribution (1 - gini_coefficient)
Q = Quality      (% gambar dalam ±1 sigma resolusi median)
```

| Score | Grade | Interpretasi |
|---|---|---|
| ≥ 0.80 | A | Dataset siap digunakan |
| 0.65 – 0.79 | B | Layak dengan catatan minor |
| 0.50 – 0.64 | C | Perlu perbaikan sebelum training |
| 0.35 – 0.49 | D | Kualitas rendah, risiko tinggi |
| < 0.35 | F | Tidak layak, perlu pengumpulan ulang |

### 4. Laporan

Hasil audit tersedia dalam dua format:
- **Dashboard interaktif** di UI dengan breakdown per komponen
- **PDF Report** yang dapat diunduh untuk dokumentasi atau presentasi

---

## Value — Nilai yang Diberikan

**Hemat waktu training.**
Dataset bermasalah yang lolos ke pipeline training membuang jam hingga berhari-hari compute time. ModelGate mendeteksi masalah dalam menit.

**Hasil model yang lebih baik.**
Dataset bersih menghasilkan model yang lebih general dan tidak overfit. Health Score memberikan baseline terukur untuk perbandingan antar versi dataset.

**Proses yang dapat direproduksi.**
Setiap audit menghasilkan laporan dengan ID unik. Tim dapat melacak riwayat kualitas dataset dari waktu ke waktu.

**Tidak perlu koding.**
Seluruh proses dilakukan melalui UI — upload, tunggu, baca laporan. Tidak perlu menulis skrip analisis sendiri.

---

## Health Score Threshold

ModelGate merekomendasikan ambang batas minimum **0.80** untuk dataset yang siap masuk pipeline training produksi. Dataset di bawah ambang ini dapat tetap digunakan dengan risiko yang dipahami, namun disarankan untuk melakukan perbaikan terlebih dahulu.
