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

**S1 lulus di percobaan ke-9**: label Tidak sesuai, ditagih 11 vs versi peserta 3 (selisih 8), rekaman tersimpan, RS
Melati Sehat menjadi Perlu klarifikasi RS (3 dari 5). Keenam field kunci S1 benar. Delapan percobaan sebelumnya
membuka sepuluh perbaikan di bawah; yang terbesar menyangkut mutu suara mode speaker. Satu panggilan lulus belum cukup
untuk gerbang R3.6 (tiga panggilan berturut-turut, transkrip ≥ 90%).

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
| 4 (19:37) | Peredam bising Chrome dimatikan. HP penguji tidak berdering sama sekali; 40 detik tanpa tersambung, stasiun menutup dan menjadwalkan percobaan 2 | Tidak diangkat (benar untuk stasiun; sebabnya jaringan) |
| 5 (19:41) | Telepon tidak pernah sampai ke HP penguji: jaringan memutus dengan "Recovery on timer expiry" | Tidak diangkat (benar). Gangguan jaringan Tri, bukan kode |
| 6 (19:44) | Berdering 8 detik setelah ditekan, diangkat. AI bertanya identitas; ucapan penguji tidak tertranskrip, lalu AI berlanjut "Baik, Bapak Andi…" seolah dibenarkan, giliran itu tanpa pertanyaan, dan aturan hening 10 detik menutup telepon sebelum penguji menjawab | Tidak yakin. Memicu temuan 8 |
| 7 (19:48) | Naskah wajib bertanya dan tidak boleh menganggap sudah dijawab; hening pertama memicu pertanyaan ulang. Lengkap sampai pamit, tetapi pembuka diulang dan transkrip awal masih buram ("¿Aló?", "या बनार") | **Tidak sesuai, 11 vs 3.** Memicu temuan 9 |
| 8 (19:52) | Pendeteksi suara Gemini dibuat peka. Saat HP penguji masih berdering, gumaman di ruangan dianggap jawaban, AI mulai bicara, panggilan putus 5 detik kemudian | Tidak terhubung (salah). Memicu temuan 10 |
| 9 (19:55) | Mikrofon ditahan sampai jaringan menyatakan diangkat. Semua jawaban tertranskrip benar: "Iya, benar", "tiga kali", "Enggak pernah, hari Minggu kan tutup". Pertanyaan identitas diulang sekali (sesuai aturan), pembuka sekali | **Tidak sesuai, 11 vs 3, selisih 8.** 59 detik, rekaman tersimpan. Lulus |

Akurasi field kunci percobaan 9 (UJI-HP bagian E): penerima, hadir, jumlah sesi, keyakinan, tanggal libur, tanda
bahaya, **6 dari 6 benar**.

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
| 7 | Peredam bising Chrome diduga memotong suara telepon dari speaker HP | Mode speaker: `noiseSuppression` dimatikan, peredam gema tetap menyala |
| 8 | AI menganggap penerima sudah membenarkan padahal jawabannya tidak terdengar, lalu telepon ditutup sebelum penerima menjawab | Naskah: setiap giliran diakhiri satu pertanyaan, dilarang menganggap sudah dijawab. Hening pertama setelah giliran AI memicu pertanyaan ulang (`SILENCE_NUDGE`); telepon ditutup hanya bila hening lagi |
| 9 | Pembuka diulang; jawaban pendek penerima terlewat atau ditranskrip dalam huruf lain | Naskah: pembuka sekali, ulang hanya pertanyaannya, paling banyak sekali per pertanyaan; "iya/benar/saya sendiri" cukup untuk identitas. Gemini: `startOfSpeechSensitivity` HIGH, `endOfSpeechSensitivity` LOW, `inputAudioTranscription.languageCodes` id-ID |
| 10 | Dengan pendeteksi peka, bunyi saat masih berdering dianggap jawaban | Halaman agen menahan audio mikrofon (`holdInput`) sampai Phone helper melaporkan `tersambung: true`. HP palsu melaporkan `tersambung: null` dan langsung didengar seperti sebelumnya |

Uji otomatis setelah perbaikan: ai-service pytest lulus semua (1 dilewati seperti sebelumnya), `node --test
ai-service/web/voice-agent.test.mjs` 66 lulus, `cd ai-service/worker && bun test` 47 lulus, ruff bersih, backend 296
lulus, `node tests/alur-v3.test.js` 19 lulus.

## Yang masih terbuka

1. **Gerbang R3.6.** Ulangi S1 dua kali lagi berturut-turut, lalu S2–S8. Bila transkrip turun di bawah 90%, pindah ke
   mode kabel (`SALURAN_AUDIO=kabel`, lihat [STASIUN.md](STASIUN.md) bagian 1).
2. **Jaringan lambat.** Pada percobaan 3, HP penerima baru berdering sekitar 30 detik setelah nomor ditekan, padahal batas
   "tidak diangkat" 40 detik dihitung sejak menekan. Status `mForegroundCallState=4` (berdering di penerima) sudah terbaca,
   jadi batas itu bisa dihitung sejak berdering. Belum diubah.
3. **Meta WhatsApp** (dikerjakan Zahra, lihat di bawah).
4. **B4–B6, A11–A12, bagian D** belum dijalankan.
5. **Cloudflare Worker** belum di-deploy ulang dengan pengaturan suara baru.
6. Rekaman halaman agen tidak menyimpan transkrip untuk label Tidak yakin, jadi diagnosis mutu suara bergantung pada
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
