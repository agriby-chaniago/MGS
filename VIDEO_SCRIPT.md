# Script Video UAS — ModelGate
**Mata Kuliah:** Web Service & Pemrograman Berbasis Platform
**Durasi target:** ±30 menit
**Format:** Penjelasan + Demo langsung

---

## Cara pakai dokumen ini

Setiap bagian punya alokasi waktu, teks narasi (baca apa adanya atau sesuaikan gaya bicara sendiri), dan **[ARAHAN]** — instruksi apa yang harus ditampilkan di layar saat itu. Total kalau dibaca dengan tempo normal (~140 kata/menit) + waktu demo, jatuhnya sekitar 28-31 menit. Latihan baca 1-2 kali dulu sebelum take biar natural, jangan dibaca kaku kayak robot.

Siapkan sebelum mulai rekam:
- Docker stack sudah `docker compose up -d` dan sehat (`docker compose ps`)
- 2 akun siap: satu Free (baru daftar), satu sudah di-upgrade ke Pro/Max
- Dataset kecil (`PetImages-Free-Subset.zip`) dan dataset besar (PetImages penuh) sudah ada di folder yang gampang diakses
- Terminal, browser (React di :3000, opsional Streamlit di :8501), Grafana (:3001), RabbitMQ mgmt (:15672) semua sudah di-bookmark/tab siap pindah-pindah
- API key sudah di-generate & CLI sudah `configure` sebelumnya (biar gak nunggu proses generate di tengah demo, atau bisa juga sengaja didemoin live — pilih sesuai selera)

---

## Bagian 1 — Pembukaan (0:00 – 1:30)

**[ARAHAN: tampilkan wajah/kamera atau slide judul dengan nama, NIM, mata kuliah]**

> Halo, perkenalkan nama saya Agrieby Chaniago, mahasiswa semester 6 Informatika. Video ini adalah pengerjaan UAS untuk dua mata kuliah sekaligus, yaitu Web Service dan Pemrograman Berbasis Platform.
>
> Project yang saya kembangkan bernama **ModelGate** — sebuah platform audit kualitas dataset untuk Computer Vision. Project ini sebenarnya sudah saya bangun sejak beberapa minggu sebelumnya sebagai microservices dasar, dan untuk UAS ini saya upgrade signifikan dengan menambahkan fitur-fitur yang relevan langsung ke materi kedua mata kuliah — mulai dari autentikasi, API Gateway, WebSocket, sampai observability dan horizontal scaling.
>
> Di video ini saya akan menjelaskan latar belakang masalah, arsitektur dan metode yang saya pakai, cara kerja tiap fitur, lalu saya demokan semuanya secara langsung, dan saya tutup dengan kesimpulan serta rencana pengembangan ke depan.

---

## Bagian 2 — Latar Belakang & Rumusan Masalah (1:30 – 4:30)

**[ARAHAN: tampilkan diagram alur ML pipeline dari ABOUT.md, atau cukup slide teks]**

> **Latar belakang.** Dalam pengembangan model Computer Vision, kualitas dataset adalah penentu utama performa model — bukan arsitektur modelnya. Masalah yang sering luput dari pengecekan manual itu ada banyak: file gambar yang rusak tapi tetap terbaca sistem, gambar duplikat yang bikin model overfitting, distribusi kelas yang timpang sehingga model bias, sampai resolusi yang tidak konsisten yang mengganggu proses augmentasi.
>
> Masalahnya, validasi ini biasanya dilakukan manual, atau malah tidak dilakukan sama sekali — dan masalah baru ketahuan setelah berjam-jam waktu training terbuang percuma. Dari situ ModelGate saya bangun sebagai "penjaga gerbang" — dataset di-audit dulu sebelum masuk ke pipeline training, bukan tools untuk training modelnya sendiri.
>
> **Untuk kebutuhan UAS**, saya melihat ini kesempatan bagus untuk mengaplikasikan konsep dari dua mata kuliah sekaligus ke project yang sudah berjalan nyata, bukan sekadar tugas latihan terpisah. Jadi saya rumuskan pengembangan tambahan yang saya bagi ke dua fokus:
>
> Untuk **Web Service**, saya menambahkan sistem autentikasi JWT dengan tiga tingkatan paket berlangganan, akses terprogram lewat API Key dan command-line tool, frontend baru berbasis React yang berkomunikasi real-time lewat WebSocket, serta rate limiting di API Gateway.
>
> Untuk **Pemrograman Berbasis Platform**, saya menambahkan observability dengan Prometheus dan Grafana, kemampuan horizontal scaling pada salah satu service, dan pipeline CI/CD dengan GitHub Actions.
>
> Saya sengaja tidak memasukkan Kubernetes ke dalam scope — bukan karena tidak paham, tapi karena setelah saya timbang, kompleksitas setup-nya tidak sepadan dengan waktu yang saya punya untuk UAS ini, dan saya lebih memilih fitur-fitur yang bisa saya implementasikan dan uji dengan benar-benar matang.

---

## Bagian 3 — Metode: Arsitektur & Teknologi (4:30 – 11:00)

**[ARAHAN: tampilkan diagram arsitektur — bisa gambar tangan/whiteboard tool, atau tampilkan ARCHITECTURE.md]**

> **Arsitektur dasar.** ModelGate dibangun dengan pola microservices. Ada 5 service backend berbasis Python FastAPI: `dataset_service` untuk upload dan manajemen dataset, `audit_service` untuk orkestrasi audit, `analysis_service` yang menjalankan 5 jenis analyzer gambar, `report_service` untuk laporan dan health score, dan yang baru saya tambahkan untuk UAS ini, `auth_service` untuk autentikasi dan otorisasi.
>
> Semua service ini duduk di belakang **Nginx sebagai API Gateway** — jadi klien manapun, baik web app maupun CLI, selalu masuk lewat satu pintu di port 8080. Komunikasi sinkron pakai HTTP biasa, sementara proses berat seperti analisis gambar berjalan asinkron lewat **RabbitMQ** supaya tidak memblokir request HTTP. Untuk penyimpanan gambar saya pakai **MinIO**, object storage yang kompatibel S3, dan untuk database saya pakai **satu PostgreSQL dengan schema terpisah per service** — jadi tiap service cuma boleh menulis ke schema miliknya sendiri, kalau butuh baca data service lain, dia pakai model "read-only mirror".
>
> Sekarang saya jelaskan satu-satu fitur tambahan untuk UAS.

### 3.1 Autentikasi JWT + Tier Free/Pro/Max

> Saya menambahkan `auth_service` baru yang menangani register, login, dan penerbitan JWT — JSON Web Token — yang di dalamnya membawa klaim plan pengguna: free, pro, atau max. Gateway Nginx saya konfigurasi memakai modul `auth_request`, jadi setiap request yang masuk ke endpoint yang dilindungi, Nginx akan memanggil endpoint internal di `auth_service` dulu untuk validasi token, baru diteruskan ke service tujuan dengan header `X-User-Id` dan `X-User-Plan` yang sudah diverifikasi.
>
> Poin pentingnya di sini: Nginx **hanya** melakukan autentikasi — mengecek "siapa kamu". Soal otorisasi — "apa yang boleh kamu lakukan" — itu jadi tanggung jawab masing-masing service, supaya pola bounded-context yang sudah saya bangun dari awal tetap konsisten.
>
> Tier-nya sendiri saya bedakan tiga: paket **Free** dibatasi ukuran upload 150MB, hanya 3 dari 5 analyzer yang jalan, tanpa akses download PDF, dan kuota 3 audit per hari. Paket **Pro** naik ke 1GB, semua 5 analyzer aktif, PDF bisa diunduh, kuota 20 audit per hari. Paket **Max** sama seperti Pro tapi upload sampai 2GB dan kuota tidak terbatas.

### 3.2 API Key + CLI

> Selain login lewat browser dengan JWT, saya juga menyediakan **API Key** khusus untuk pengguna Pro dan Max — ini ditujukan untuk kebutuhan akses terprogram, bukan manusia yang klik-klik di browser. Analoginya seperti developer yang mau mengintegrasikan ModelGate ke pipeline otomatis mereka sendiri.
>
> Saya juga bikin CLI tool bernama `mgs`, ditulis dengan Python murni. CLI ini bisa upload dataset, membuat audit, memantau progres secara live, sampai mengunduh laporan — semuanya dari terminal, dengan satu command `mgs run`.

### 3.3 React Frontend + WebSocket

> Aplikasi awal saya pakai Streamlit, dan itu masih saya pertahankan berjalan paralel. Tapi untuk UAS ini saya bangun frontend baru pakai **React dan Vite**, dengan styling Tailwind CSS. Frontend baru ini saya desain supaya progres audit itu **real-time** pakai **WebSocket** — bukan polling berkala seperti sebelumnya.
>
> Detail teknis yang saya anggap penting di sini: saya sempat menemukan bug desain sendiri saat testing — kalau klien connect WebSocket-nya telat, misalnya karena dataset kecil selesai diproses lebih cepat dari waktu handshake koneksi, klien itu bisa nunggu selamanya karena tidak ada mekanisme replay pesan. Saya perbaiki dengan pola **snapshot-then-subscribe**: begitu klien connect, server langsung kirim status terkini dulu, baru lanjut streaming update berikutnya.

### 3.4 Rate Limiting

> Di level gateway, saya tambahkan rate limiting berbasis IP di Nginx — endpoint login dibatasi lebih ketat untuk mencegah brute force, endpoint lain dibatasi lebih longgar. Saya juga sempat coba bikin limit yang berbeda per-tier langsung di Nginx, tapi setelah saya pelajari lebih dalam, ternyata ada kendala teknis di urutan eksekusi modul Nginx yang membuat itu tidak reliable — jadi saya pindahkan logic pembatasan per-tier itu ke level aplikasi lewat kuota harian yang sudah saya jelaskan di bagian auth tadi.

### 3.5 Observability — Prometheus & Grafana

> Untuk sisi Pemrograman Berbasis Platform, saya tambahkan **Prometheus** untuk mengumpulkan metrik dari kelima service backend — jumlah request, latency, status code — secara otomatis lewat library instrumentator. Saya juga mengaktifkan plugin Prometheus bawaan **RabbitMQ**, jadi kedalaman antrian dan jumlah consumer juga bisa dipantau tanpa nulis kode tambahan sama sekali. Semua metrik ini divisualisasikan lewat **Grafana**.

### 3.6 Horizontal Scaling

> Salah satu bagian favorit saya: `analysis_service`, yang menjalankan analyzer gambar, itu terhubung ke RabbitMQ sebagai consumer. Ternyata arsitektur yang sudah ada dari awal **sudah mendukung** multiple consumer berjalan paralel dan otomatis dibagi rata oleh RabbitMQ — saya cuma perlu menghilangkan satu batasan port yang bikin container tidak bisa di-scale lebih dari satu, dan langsung bisa didemokan `docker compose up --scale analysis_service=3`.

### 3.7 CI/CD

> Terakhir, saya siapkan GitHub Actions workflow yang otomatis build dan push image Docker setiap service ke GitHub Container Registry setiap kali ada push ke branch utama.

---

## Bagian 4 — Cara Kerja Detail / Alur Sistem (11:00 – 17:00)

**[ARAHAN: bisa tampilkan kode sekilas atau diagram alur, atau lanjut cerita sambil siap-siap pindah ke demo]**

> Sekarang saya jelaskan alur kerja end-to-end supaya lebih jelas sebelum masuk demo.
>
> **Alur upload dan audit:** pengguna login dan dapat JWT. Saat upload dataset, request masuk ke Nginx, tervalidasi lewat `auth_request`, diteruskan ke `dataset_service` dengan informasi plan pengguna di header. `dataset_service` mengecek batas ukuran sesuai plan, menghitung hash SHA-256 untuk deteksi duplikat, lalu menyimpan gambar ke MinIO dan metadata ke database.
>
> Saat audit dibuat, `audit_service` menentukan **di server**, bukan dari input klien, analyzer mana saja yang boleh jalan berdasarkan plan pengguna — supaya pengguna Free tidak bisa 'memaksa' minta 5 analyzer lewat manipulasi request. Job kemudian dipublish ke RabbitMQ.
>
> `analysis_service` men-consume job itu, mendownload dataset dari MinIO, menjalankan analyzer satu per satu — corruption, empty, resolution, distribution, dan duplicate detection pakai perceptual hashing — lalu mempublish tiap hasil analyzer secara individual ke queue hasil.
>
> `audit_service` men-consume hasil itu, dan setiap kali ada hasil baru masuk, langsung di-broadcast lewat WebSocket ke klien yang sedang menonton — baik itu browser React maupun terminal CLI, keduanya memakai channel yang sama persis.
>
> Setelah semua analyzer selesai, `report_service` menghitung **Health Score** dengan formula: 30 persen Integrity, 25 persen Uniqueness, 25 persen Distribution, 20 persen Quality — menghasilkan skor 0 sampai 1 dan grade A sampai F.
>
> **Satu hal menarik yang saya temukan sendiri saat proses testing** — bukan sesuatu yang saya rencanakan dari awal — saya menemukan race condition di kode audit_service yang sudah ada sebelumnya: proses publish job ke antrian itu ternyata terjadi *sebelum* status audit di-commit ke "queued", jadi ada kemungkinan kecil consumer sempat membaca status yang belum ter-update, dan job itu jadi macet permanen. Saya perbaiki urutannya, dan itu jadi bukti kecil bahwa proses testing menyeluruh itu penting, bukan cuma asumsi kode sudah benar dari awal.

---

## Bagian 5 — Demo (17:00 – 28:00, ±11 menit)

**[ARAHAN: pindah full-screen ke browser/terminal, matikan notifikasi dulu]**

> Sekarang saya akan demokan langsung semua yang saya jelaskan tadi.

### 5.1 Autentikasi & Tier (±3 menit)

**[ARAHAN: buka localhost:3000]**
> Ini frontend React yang baru saya bangun. Saya akan daftar akun baru.

**[ARAHAN: register akun baru, tunjukkan langsung masuk ke wizard]**
> Setelah daftar, saya langsung masuk, dan defaultnya saya dapat paket Free — bisa dilihat di sidebar.

**[ARAHAN: coba upload dataset besar (875MB) → tunjukkan pesan error 413]**
> Saya coba upload dataset penuh yang ukurannya 875 megabyte — dan seperti yang saya jelaskan tadi, otomatis ditolak karena melebihi batas paket Free yang 150MB.

**[ARAHAN: upload dataset kecil (subset) → sukses]**
> Sekarang saya coba dataset yang lebih kecil, dan ini berhasil.

**[ARAHAN: buat audit, tunjukkan cuma 3 analyzer yang muncul]**
> Saat saya buat audit, perhatikan cuma tiga analyzer yang jalan — sesuai batasan paket Free.

**[ARAHAN: buka DevTools > Network > WS, tunjukkan koneksi WebSocket + pesan masuk]**
> Ini saya buka developer tools untuk membuktikan progresnya benar real-time lewat WebSocket, bukan polling — bisa dilihat ada koneksi WS aktif dan pesan masuk satu-satu setiap analyzer selesai.

**[ARAHAN: audit selesai, buka laporan, tunjukkan tombol PDF disabled]**
> Setelah selesai, laporan muncul dengan Health Score dan breakdown komponennya. Tombol download PDF sengaja disembunyikan karena ini masih akun Free.

**[ARAHAN: klik tombol Upgrade ke Pro/Max di sidebar]**
> Sekarang saya upgrade akun ini ke paket Max langsung dari tombol di sidebar — ini fitur self-service yang saya buat khusus supaya bisa didemokan langsung tanpa proses pembayaran sungguhan.

**[ARAHAN: upload dataset besar lagi, sekarang sukses; buat audit, tunjukkan 5 analyzer + PDF aktif]**
> Sekarang dengan akun yang sama tapi sudah upgrade, dataset besar berhasil diupload, lima analyzer semua jalan, dan tombol PDF sudah aktif.

### 5.2 API Key + CLI (±3 menit)

**[ARAHAN: klik "Generate API Key" di sidebar, tunjukkan key + command CLI muncul]**
> Ini fitur yang menurut saya paling relevan dengan konsep Web Service — bukan cuma bisa diakses manusia lewat browser, tapi juga programmatic lewat API Key. Saya generate key-nya di sini, dan aplikasi langsung kasih saya command siap pakai untuk CLI.

**[ARAHAN: split screen atau pindah ke terminal, paste command configure]**
> Saya pindah ke terminal, paste command configure tadi — dan seperti bisa dilihat, key-nya langsung divalidasi saat itu juga.

**[ARAHAN: jalankan `mgs run nama_dataset.zip --pdf`]**
> Sekarang saya jalankan satu command ini — `mgs run` — dan ini akan otomatis upload, bikin audit, menampilkan progres live, sampai unduh PDF, semuanya dari terminal, tanpa pernah buka browser sama sekali.

**[ARAHAN: tunggu sampai selesai, tunjukkan hasil akhir dengan health score]**

> Ini menunjukkan skenario yang relevan untuk misalnya seorang ML Engineer yang mau otomatisasi pengecekan kualitas dataset di dalam pipeline mereka sendiri, tanpa perlu interaksi manual.

### 5.3 Rate Limiting & Keamanan (±2 menit)

**[ARAHAN: terminal, jalankan loop curl ke /api/v1/auth/login berkali-kali cepat]**
> Saya tunjukkan rate limiting-nya. Saya kirim beberapa request login beruntun dengan cepat...

**[ARAHAN: tunjukkan output — awal 401, lalu 429]**
> ...dan setelah melewati batas, responsnya jadi 429 Too Many Requests — ini mencegah serangan brute force ke endpoint login.

**[ARAHAN: curl langsung ke port service di belakang, misal localhost:8001, tunjukkan connection refused]**
> Saya juga coba akses salah satu service backend langsung, melewati gateway — dan ini gagal connect, karena port-nya memang sengaja saya tutup dari luar. Semua trafik wajib lewat gateway yang sudah terautentikasi.

### 5.4 Horizontal Scaling (±2 menit)

**[ARAHAN: terminal, jalankan docker compose up -d --scale analysis_service=3]**
> Sekarang saya scale service analysis jadi 3 replika.

**[ARAHAN: rabbitmqctl list_consumers, tunjukkan 3 baris]**
> Dan bisa dilihat di sini, RabbitMQ sekarang punya tiga consumer terpisah untuk antrian yang sama — otomatis dibagi rata, tanpa saya perlu menulis kode load balancing sendiri.

### 5.5 Observability (±1 menit)

**[ARAHAN: buka localhost:9090/targets]**
> Ini dashboard Prometheus, menunjukkan semua service dalam status UP dan sedang di-scrape metriknya.

**[ARAHAN: buka localhost:3001 Grafana, tunjukkan panel/dashboard]**
> Dan ini Grafana, yang sudah otomatis terhubung ke Prometheus, menampilkan metrik-metrik itu secara visual.

---

## Bagian 6 — Kesimpulan & Penutup (28:00 – 30:00)

**[ARAHAN: kembali ke kamera/slide]**

> Sebagai kesimpulan, di project ModelGate ini saya sudah mengimplementasikan konsep-konsep inti dari kedua mata kuliah:
>
> Untuk **Web Service**: REST API dengan API Gateway, autentikasi JWT dan API Key sebagai dua skema berbeda, komunikasi real-time lewat WebSocket, serta rate limiting.
>
> Untuk **Pemrograman Berbasis Platform**: containerization dengan Docker, message queue asinkron dengan RabbitMQ, observability dengan Prometheus dan Grafana, horizontal scaling, dan automasi CI/CD.
>
> Yang saya pelajari paling berharga dari proses ini bukan cuma soal implementasi fitur baru, tapi juga proses debugging dan testing yang menyeluruh — beberapa bug yang saya temukan, seperti race condition di pembuatan audit dan masalah WebSocket yang saya jelaskan tadi, itu justru ketemu karena saya benar-benar menjalankan dan menguji sistemnya secara langsung, bukan cuma asumsi kodenya benar.
>
> Untuk pengembangan selanjutnya, saya melihat beberapa arah yang bisa dikembangkan lagi — misalnya orkestrasi dengan Kubernetes yang sengaja saya keluarkan dari scope UAS ini, reconnect otomatis untuk WebSocket yang terputus, dan dashboard Grafana yang lebih lengkap dengan alerting.
>
> Sekian presentasi dari saya, terima kasih sudah menonton.

**[ARAHAN: fade out / tampilkan link repository GitHub di layar]**

---

## Catatan tambahan

- **Kalau waktu kepepet:** bagian yang paling aman dipotong adalah 5.3 (rate limiting) dan 5.4 (scaling) — sudah cukup terwakili oleh penjelasan di Bagian 3.
- **Kalau mau lebih detail buat dosen:** siapkan juga `ARCHITECTURE.md` dan diagram dari repo untuk ditunjukkan sekilas saat Bagian 3, biar keliatan dokumentasinya rapi.
- **Total kata narasi:** ±2100 kata penjelasan + ±11 menit demo (tidak dihitung kata karena aktivitas, bukan bacaan) ≈ pas di 30 menit dengan tempo bicara wajar.
