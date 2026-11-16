# Hasil uji dengan HP nyata (16 November 2026)

Uji pertama stasiun saluran dengan HP Android sungguhan, mengikuti [UJI-HP.md](UJI-HP.md). Semua sebelumnya baru diuji
dengan HP palsu. Data tetap sintetis; semua panggilan hanya ke satu nomor penguji (HP Zahra).

| | |
|---|---|
| HP saluran | Xiaomi Redmi Note 13 Pro 5G (2312DRA50G), Android 13 (HyperOS), dua SIM |
| SIM panggilan | SIM 1 (Tri), diatur sebagai SIM bawaan untuk panggilan |
| Laptop | MacBook Pro, mikrofon dan speaker bawaan |
| Mode audio | speaker |
| Mode Meta | log (WA belum dikirim sungguhan) |
| Database | Postgres lokal (`vedika_uji`), karena Supabase proyek masih tidak bisa diakses |

## Ringkasan

Alur penuh sudah berjalan di HP nyata tanpa disentuh: antrean → WA (simulasi) → jeda 1 menit → HP menekan nomor →
speakerphone menyala → penerima mengangkat → AI membuka dan bertanya → telepon ditutup → jawaban dibaca → label.

Yang belum lulus: **mutu suara penerima di mode speaker**. Ucapan penguji sampai ke Gemini dalam potongan yang
ditranskrip sebagai kata asing ("hier", "madre", "die haben"), sehingga label S1 berakhir Tidak yakin, bukan Tidak sesuai.
Gerbang R3.6 (transkrip ≥ 90%) belum terpenuhi. Lihat bagian "Yang masih terbuka".

## Bagian A: pemeriksaan ADB

| # | Hasil | Catatan |
|---|---|---|
| A1 | L | Setelah dialog "Izinkan debugging USB" disetujui |
| A2 | L | `gsm.sim.state` = `LOADED,LOADED`, bukan `READY` (lihat temuan 2) |
| A3 | L | Dua baris `mCallState=0` |
| A4 | G → L | Gagal: muncul pemilih aplikasi Phone/Zoom, lalu pemilih SIM. Lulus setelah temuan 1 diperbaiki dan SIM bawaan diatur |
| A5 | L | `mCallState=2` sejak menekan nomor |
| A6 | L | Putus dalam 1 detik |
| A7 | G → L | `KEYCODE_ENDCALL` tanpa panggilan mematikan dan mengunci layar. Lulus setelah temuan 3 diperbaiki |
| A8–A9 | L | Speakerphone harus dinyalakan; suara dua arah terdengar |
| A10 | G → L | Speakerphone **tidak** diingat antar panggilan. Lulus setelah temuan 4 diperbaiki |
| A11–A12 | belum | |
| A13 | belum | Akun Meta belum dibuat |

## Bagian B: stasiun menyala

| # | Hasil | Catatan |
|---|---|---|
| B1 | L | Empat baris pemeriksaan lalu "Stasiun siap." |
| B2 | L | Halaman agen: "siap, menunggu tugas", HP dan SIM terbaca, detak masuk ke backend |
| B3 | L | Website: chip "Saluran telepon siap (2312DRA50G)" |
| B4–B6 | belum | Perlu mencabut kabel secara fisik |

## Bagian C: panggilan AI S1

| Percobaan | Yang terjadi | Hasil |
|---|---|---|
| 1 (19:06 WIB) | Penguji mengangkat lalu diam menunggu. Agen menunggu penerima bicara lebih dulu, tidak ada yang terdengar, telepon ditutup oleh batas 40 detik | Tidak diangkat (salah). Memicu temuan 5 |
| 2 (19:14) | Setelah temuan 5: AI membuka 3 detik setelah diangkat. Ucapan penguji tertangkap sebagai "Hello? Hello?", "hier", "llevar", "madre", lalu "Kayaknya enggak ingat" | Tidak yakin. Alur lengkap, suara buram |
| 3 (19:34) | Bahasa dikunci id-ID. Ucapan penguji tertangkap "die haben", lalu hening 10 detik | Tidak yakin |
| 4 (19:37) | Peredam bising Chrome dimatikan. Penguji tidak mengangkat; stasiun menutup setelah 40 detik dan menjadwalkan percobaan 2 | Tidak diangkat (benar) |
| 5 (19:41) | Sama dengan percobaan 4; penguji tidak mengangkat | Tidak diangkat (benar). Uji suara dengan peredam bising mati belum terjadi |

Di setiap panggilan yang diangkat, AI mematuhi naskah: mengaku asisten otomatis, menyebut panggilan direkam, bukan
tagihan, tidak meminta NIK/OTP/rekening/uang, dan tidak memakai kata "curang" atau "fraud". Label Tidak yakin juga
benar menurut `aturan.py`, karena jumlah sesi tidak tertangkap; rekaman dan transkripnya tidak disimpan, sesuai aturan.

## Temuan dan perbaikan

| # | Temuan di HP ini | Perbaikan |
|---|---|---|
| 1 | Zoom ikut mendaftar sebagai aplikasi telepon, sehingga intent CALL memunculkan pemilih aplikasi dan panggilan tidak pernah keluar | `saluran.py`: intent diarahkan ke `com.android.server.telecom` |
| 2 | SIM terbaca `LOADED`, bukan `READY`; Phone helper menganggap SIM tidak siap sehingga stasiun tidak pernah menelepon | `sim_ready` menerima `READY` dan `LOADED`; `stasiun.sh` disamakan |
| 3 | `KEYCODE_ENDCALL` tanpa panggilan mengunci layar, dan dari layar terkunci telepon berikutnya tidak pernah ditekan (layar menelepon tampil, nomor tidak keluar) | Tombol tutup hanya dikirim bila ada panggilan. Kesehatan melaporkan "Layar HP terkunci" dan stasiun tidak mengambil tugas |
| 4 | Panggilan selalu mulai di earpiece; speakerphone tidak diingat, dan Android tidak punya perintah adb untuknya | Phone helper mengetuk tombol "Speaker" layar panggilan lewat `uiautomator`, lalu memastikan rute telecom pindah ke speaker (paling banyak 2 ketukan). Hanya di mode speaker |
| 5 | Penerima nomor tak dikenal sering mengangkat lalu diam. Agen menunggu ucapan pertama penerima, jadi panggilan dianggap tidak diangkat | `/v1/saluran/status` menambah `tersambung` dari `mForegroundCallState=1` (jaringan menyatakan diangkat). Bila tersambung dan penerima diam 3 detik, AI membuka lebih dulu. Pengumuman operator terjadi sebelum diangkat, jadi filternya tidak terpengaruh |
| 6 | Gemini menebak bahasa ucapan penerima yang buram | `languageCode: "id-ID"` di token sesi (`voice.py`), di halaman agen, dan di Cloudflare Worker |
| 7 | Peredam bising Chrome diduga memotong suara telepon dari speaker HP | Mode speaker: `noiseSuppression` dimatikan, peredam gema tetap menyala. **Belum terbukti**; panggilan sesudahnya tidak diangkat |

Uji otomatis setelah perbaikan: ai-service pytest lulus semua (1 dilewati seperti sebelumnya), `node --test
ai-service/web/voice-agent.test.mjs` 61 lulus, `cd ai-service/worker && bun test` 47 lulus, ruff bersih.

## Yang masih terbuka

1. **Mutu suara mode speaker.** Ulangi S1 dengan peredam bising mati. Bila transkrip masih buram, pindah ke mode kabel
   (`SALURAN_AUDIO=kabel`, splitter TRRS + antarmuka audio USB, lihat [STASIUN.md](STASIUN.md) bagian 1). Mode kabel
   memang disiapkan untuk keadaan ini.
2. **Meta WhatsApp** (dikerjakan Zahra, lihat di bawah).
3. **B4–B6, A11–A12, S2–S8, bagian D** belum dijalankan.
4. **Cloudflare Worker** belum di-deploy ulang dengan `languageCode`.
5. Rekaman halaman agen tidak menyimpan transkrip untuk label Tidak yakin, jadi diagnosis mutu suara bergantung pada
   transkrip di jendela agen. Untuk uji suara, salin transkrip itu sebelum panggilan berikutnya.

## Meta WhatsApp: langkah untuk Zahra

Akun Meta dibuat Zahra. Nomor uji Meta gratis, tanpa kartu pembayaran, dan bisa mengirim ke paling banyak 5 nomor
penerima yang didaftarkan. Langkah lengkap ada di [STASIUN.md](STASIUN.md) bagian 5; urutannya:

1. developers.facebook.com → My Apps → Create App → tipe **Business** (buat Meta Business portfolio bila diminta).
2. Add product → **WhatsApp** → **API Setup**. Catat **Phone number ID** dan token sementara (berlaku sekitar 1 hari).
3. Di kolom "To", daftarkan nomor penguji. Penerima memasukkan kode verifikasi yang masuk ke WhatsApp-nya.
4. Kirim `hello_world` dari halaman itu. Pesan harus masuk (UJI-HP A13).
5. Tambahkan anggota tim sebagai Admin di Business Settings → Users, supaya akun tidak bergantung pada satu orang.
6. Kirim `META_WA_TOKEN`, `META_WA_PHONE_ID`, dan `META_WA_API_VERSION` ke pemegang laptop stasiun lewat jalur pribadi
   (bukan grup, bukan git). Di `backend/.env` isi juga `META_WA_MODE=teks`.
7. Sebelum uji, penguji mengirim "halo" ke nomor uji Meta supaya jendela 24 jam terbuka (mode `teks`).

Untuk pemakaian lebih dari sehari, buat token System User di Business Settings. Template (`META_WA_MODE=template`)
tidak terikat jendela 24 jam, tetapi harus disetujui Meta dan bisa ditolak bila menyebut "BPJS Kesehatan".
