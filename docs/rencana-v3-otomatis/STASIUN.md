# Stasiun saluran: panduan pasang dan jalan

Stasiun saluran adalah satu laptop (macOS) dan satu HP Android ber-SIM Indonesia. Laptop menjalankan seluruh
sistem dan halaman agen; HP menelepon lewat jaringan seluler biasa dan dikendalikan laptop lewat kabel USB (ADB).
Petugas hanya memakai website. Tidak ada yang perlu diketik atau diklik di laptop stasiun setelah `./stasiun.sh` jalan.

```
Petugas ──► website :8899 ──► backend :8000 ──► Supabase
                                  │  ├──► pembaca jawaban (ai-service :8001)
                                  │  └──► Meta WhatsApp Cloud API (pesan pemberitahuan, chat cadangan)
Laptop stasiun: jendela Chrome ── halaman agen /voice/ (ai-service :8001)
                    │  ├──► backend :8000 (detak, ambil, status, transkrip, hasil)
                    │  ├──► Gemini Live (suara masuk dan keluar)
                    │  └──► Phone helper /v1/saluran/* ──adb──► HP Android ──seluler──► HP penguji
```

Semua panggilan dan pesan prototipe hanya menuju `NOMOR_PENGUJI`. Data sintetis, layar tetap berlabel Simulasi.

## 1. Perangkat

### Mode speaker (bawaan)

| Barang | Catatan |
|---|---|
| Laptop macOS dengan Chrome | Mikrofon dan speaker bawaan dipakai apa adanya |
| HP Android + SIM Indonesia berpulsa | Android 8 ke atas; satu SIM aktif untuk panggilan |
| Kabel USB data | Bukan kabel isi daya saja |
| Dudukan HP | HP berdiri 15–25 cm dari laptop, speaker HP menghadap mikrofon laptop |
| Ruangan sepi | Suara orang lain di ruangan ikut terdengar AI |

HP dipasang speakerphone. Suara AI keluar dari speaker laptop dan masuk ke mikrofon HP; suara penerima keluar dari
speaker HP dan masuk ke mikrofon laptop. Chrome menyalakan peredam gema, peredam bising, dan pengatur volume otomatis.

### Mode kabel (`SALURAN_AUDIO=kabel`)

| Barang | Catatan |
|---|---|
| Antarmuka audio USB (1 masuk, 1 keluar) | Muncul di macOS sebagai perangkat audio, mis. "USB Audio Device" |
| Pemecah TRRS 3,5 mm (mik + headphone terpisah) | Untuk HP berjack 3,5 mm; HP USB-C perlu adaptor USB-C ke 3,5 mm yang mendukung mikrofon |
| 2 kabel audio 3,5 mm | Keluar antarmuka → mik pemecah; headphone pemecah → masuk antarmuka |

Suara lewat kabel, jadi pemrosesan Chrome dimatikan. Isi `SALURAN_INPUT` dan `SALURAN_OUTPUT` dengan potongan nama
perangkat audio itu. Karena USB-C HP dipakai adaptor audio, ADB perlu lewat hub USB-C atau ADB nirkabel; mode speaker
lebih sederhana dan menjadi target pertama.

## 2. Pengaturan HP (sekali saja)

1. **Opsi pengembang.** Setelan → Tentang ponsel → ketuk "Nomor versi" 7 kali.
2. **USB debugging.** Setelan → Sistem → Opsi pengembang → nyalakan "Proses debug USB".
3. **Izinkan laptop.** Colok kabel, buka kunci HP, centang "Selalu izinkan dari komputer ini", lalu Izinkan.
   Cek di laptop: `adb devices` menampilkan satu baris berstatus `device`.
4. **SIM bawaan untuk panggilan.** Setelan → Jaringan → SIM → Panggilan: pilih satu SIM, jangan "Selalu tanya".
   Bila tidak, HP menampilkan pemilih SIM dan panggilan tidak pernah keluar.
5. **Jangan Ganggu.** Nyalakan, supaya notifikasi tidak berbunyi di tengah panggilan. Matikan nada tombol.
6. **Tetap menyala.** `stasiun.sh` menjalankan `adb shell svc power stayon usb`. Disarankan juga tanpa kunci layar
   (atau kunci geser), karena layar terkunci bisa menahan panggilan keluar.
7. **Volume.** Volume panggilan HP sekitar 70–80%. Mode speaker: nyalakan speakerphone pada panggilan pertama; sebagian
   HP mengingatnya, sebagian tidak (lihat Pemecahan masalah).
8. **Aplikasi telepon bawaan.** Pakai aplikasi telepon bawaan pabrik, bukan aplikasi pihak ketiga.

## 3. Variabel lingkungan

### `backend/.env`

| Variabel | Isi |
|---|---|
| `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Seperti sebelumnya |
| `MESIN_URL` | `http://localhost:8001` (ai-service di laptop stasiun) |
| `KUNCI_MESIN` | Sama dengan `AI_SERVICE_KEY` di ai-service; kosong bila ai-service tanpa kunci |
| `AGEN_KEY` | Kunci agen. `stasiun.sh` meneruskannya ke halaman agen lewat Phone helper |
| `NOMOR_PENGUJI` | Nomor HP penguji: tujuan semua panggilan dan pesan WA |
| `NOMOR_PENELEPON` | Nomor SIM di HP saluran; disebut di pesan WA |
| `CORS_ORIGINS` | Harus memuat `http://localhost:8001` (asal halaman agen) |
| `META_WA_MODE` | `log` (bawaan, tidak mengirim), `teks`, atau `template` |
| `META_WA_TOKEN` | Token akses Meta. Kosong = mode selalu `log` |
| `META_WA_PHONE_ID` | Phone number ID nomor bisnis (bukan nomor teleponnya). Kosong = mode selalu `log` |
| `META_WA_API_VERSION` | Versi Graph API yang tampil di dasbor aplikasi Meta, mis. `v2x.0`. Wajib di mode `teks` dan `template`; tidak ada nilai bawaan |
| `META_WA_TEMPLATE_PEMBERITAHUAN` | Nama template pesan pemberitahuan (mode `template`) |
| `META_WA_TEMPLATE_CADANGAN` | Nama template chat cadangan (mode `template`) |
| `META_WA_TEMPLATE_BAHASA` | Kode bahasa template, bawaan `id` |

### `ai-service/.env`

| Variabel | Isi |
|---|---|
| `GEMINI_API_KEY`, `GEMINI_LIVE_MODEL`, `GEMINI_TEXT_MODEL` | Seperti sebelumnya |
| `GEMINI_TEXT_MODEL_CADANGAN` | Model teks kedua untuk pembaca jawaban bila model utama sibuk (429/5xx). Bawaan `gemini-3.5-flash`; kosong = mati |
| `AI_SERVICE_KEY` | Opsional; bila diisi, sama dengan `KUNCI_MESIN` |
| `SALURAN_ADB` | `1` = HP nyata lewat adb, `palsu` = HP palsu untuk uji. Kosong = Phone helper tidak ada. `stasiun.sh` mengisinya `1` |
| `SALURAN_ADB_BIN` | Lokasi `adb` bila tidak ada di PATH |
| `SALURAN_ADB_SERIAL` | Nomor seri dari `adb devices`; hanya perlu bila lebih dari satu perangkat terhubung |
| `SALURAN_API_URL` | Alamat backend untuk halaman agen, bawaan `http://localhost:8000` |
| `SALURAN_AGEN_KEY` | Sama dengan `AGEN_KEY`. `stasiun.sh` mengambilnya dari `backend/.env`, jadi tidak perlu diisi |
| `SALURAN_AUDIO` | `speaker` (bawaan) atau `kabel` |
| `SALURAN_INPUT`, `SALURAN_OUTPUT` | Potongan nama perangkat audio di Chrome; kosong = perangkat bawaan macOS |

Rahasia (`GEMINI_API_KEY`, `AGEN_KEY`, `AI_SERVICE_KEY`, `META_WA_TOKEN`, URL database) tidak pernah masuk git, log,
atau browser petugas. Browser stasiun menerima kunci agen hanya dari `GET /v1/saluran/konfigurasi`, yang menolak semua
klien selain `127.0.0.1`.

## 4. Menjalankan

```bash
brew install android-platform-tools   # sekali saja
./stasiun.sh                          # dari akar repo
```

`stasiun.sh`:

1. memeriksa `adb` dan bahwa tepat satu HP terhubung dan diizinkan (bila tidak: mencetak sebabnya, keluar);
2. menjaga HP tetap menyala selama dicolok (`svc power stayon usb`) dan Mac tetap terjaga (`caffeinate`);
3. menjalankan ai-service (dengan Phone helper), backend, dan website, lalu menunggu keduanya sehat;
4. mencetak satu baris per pemeriksaan: model HP, keadaan SIM, mode audio, mode Meta;
5. membuka halaman agen di jendela Chrome tersendiri (profil `~/.vedika-stasiun-chrome`, izin mikrofon dan audio
   otomatis) dan website di browser biasa.

Jangan tutup jendela "Stasiun saluran Vedika". Di sana tampil kesiapan HP, tugas yang berjalan, tahap panggilan,
transkrip, dan galat terakhir. Ctrl-C di terminal menghentikan semuanya.

Panggilan hanya berjalan 09.00–17.00 WIB. Untuk uji di luar jam itu:
`curl -X PUT localhost:8000/api/v1/pengaturan -H 'content-type: application/json' -d '{"jam_mulai":"00:00","jam_selesai":"23:59"}'`.

`./dev.sh` tetap ada untuk pengembangan tanpa HP (website + backend + ai-service tanpa Phone helper).

## 5. Meta WhatsApp Cloud API

WhatsApp hanya membawa pesan: pemberitahuan sebelum telepon (Lampiran B) dan chat cadangan. Backend mengirimnya
langsung ke Meta; panggilan tidak pernah menunggu WhatsApp (satu percobaan, batas 10 detik, gagal pun panggilan lanjut).

Tanpa pengaturan apa pun mode-nya `log`: tidak ada yang dikirim, layar menampilkan "Pesan WA (simulasi, Meta belum
diatur)". Ini cukup untuk demo tanpa akun Meta.

Langkah menyalakan pengiriman nyata (nama menu mengikuti dasbor Meta dan bisa berubah):

1. Buat aplikasi bertipe Business di developers.facebook.com, lalu tambahkan produk WhatsApp.
2. Di halaman API Setup, Meta memberi **nomor uji** beserta **Phone number ID**. Isi ID itu ke `META_WA_PHONE_ID`.
3. Daftarkan nomor penerima di halaman yang sama. Nomor uji hanya bisa mengirim ke nomor yang didaftarkan, paling
   banyak 5. Daftarkan `NOMOR_PENGUJI`.
4. Salin token akses ke `META_WA_TOKEN`. Token sementara dari halaman itu berumur pendek (sekitar sehari); untuk
   pemakaian lebih lama buat token System User di Business Settings.
5. Isi `META_WA_API_VERSION` dengan versi yang tampil di contoh `curl` halaman API Setup.
6. Pilih mode:
   - **`teks`**: pesan teks biasa, persis Lampiran B. Hanya sampai bila penerima mengirim pesan ke nomor bisnis
     dalam 24 jam terakhir. Untuk uji: kirim "halo" dari HP penguji ke nomor uji, lalu jalankan panggilan.
   - **`template`**: tidak terikat jendela 24 jam, tetapi template harus dibuat dan disetujui Meta dulu.

### Template

Buat dua template berkategori Utility, bahasa Indonesian (`id`), tanpa header, tanpa tombol, tanpa tautan. Isi badan
template di bawah ini menghasilkan teks yang sama dengan Lampiran B.

**Pemberitahuan** (`META_WA_TEMPLATE_PEMBERITAHUAN`), 6 parameter berurutan:

| Parameter | Isi | Contoh |
|---|---|---|
| `{{1}}` | nama_penerima | Andi Pratama |
| `{{2}}` | jeda_menit | 1 |
| `{{3}}` | nomor_penelepon | 0811-xxxx-xxxx |
| `{{4}}` | nama_pasien | Andi Pratama |
| `{{5}}` | nama_rs | RS Melati Sehat |
| `{{6}}` | bulan | Agustus |

```
Halo {{1}}. Ini BPJS Kesehatan. Dalam {{2}} menit kami akan menelepon dari nomor {{3}} untuk konfirmasi singkat layanan fisioterapi {{4}} di {{5}} bulan {{6}}. Ini bukan tagihan. Kami tidak akan meminta data pribadi, kode OTP, atau pembayaran. Untuk memastikan pesan ini, hubungi Care Center 165.
```

**Chat cadangan** (`META_WA_TEMPLATE_CADANGAN`), 3 parameter berurutan:

| Parameter | Isi | Contoh |
|---|---|---|
| `{{1}}` | nama_pasien | Joko Prasetyo |
| `{{2}}` | nama_rs | RS Cempaka Asri |
| `{{3}}` | bulan | Agustus |

```
Kami belum berhasil menelepon. Kira-kira berapa kali {{1}} menjalani fisioterapi di {{2}} bulan {{3}}? Balas dengan angka: 1) 1–2 kali  2) 3–4 kali  3) 5–8 kali  4) lebih dari 8 kali  5) tidak ingat  6) tidak pernah terapi di sana.
```

Catatan: prototipe memakai nama "BPJS Kesehatan" hanya di teks pesan uji ke nomor tim. Meta bisa menolak template
yang menyebut lembaga yang bukan pemilik akun; bila ditolak, pakai mode `teks` untuk demo.

Balasan penerima atas chat cadangan belum dibaca sistem (di luar lingkup tiket ini).

## 6. Pemecahan masalah

| Gejala | Sebab | Tindakan |
|---|---|---|
| `stasiun.sh`: "HP belum mengizinkan laptop ini" / website: "belum siap: Izinkan debugging USB di HP" | HP belum mengizinkan debugging dari laptop ini | Buka kunci HP, setujui dialog "Izinkan debugging USB", centang "Selalu izinkan". Bila dialog tidak muncul: cabut-colok kabel, atau `adb kill-server && adb devices` |
| "HP tidak terhubung ke laptop" | Kabel isi daya saja, mode USB salah, atau kabel longgar | Ganti kabel data; di notifikasi USB HP pilih "Transfer file"; cek `adb devices` |
| "SIM tidak siap" | SIM belum terbaca, PIN SIM aktif, atau mode pesawat | Matikan mode pesawat, buka PIN SIM, cek `adb shell getprop gsm.sim.state` berisi `READY` |
| Panggilan tidak keluar, HP menampilkan pemilih SIM | HP dua SIM tanpa SIM bawaan untuk panggilan | Setelan → SIM → Panggilan: pilih satu SIM (bukan "Selalu tanya") |
| Panggilan tidak keluar, layar HP terkunci | Kunci layar menahan intent panggilan | Hilangkan kunci layar, atau pakai kunci geser |
| Tidak ada suara ke penerima / AI tidak mendengar | Speakerphone HP mati, volume kecil, atau perangkat audio salah | Nyalakan speakerphone; cek baris "Audio" di halaman agen; mode kabel: periksa `SALURAN_INPUT`/`SALURAN_OUTPUT` |
| Gema: AI menjawab dirinya sendiri atau memotong ucapannya | Speaker laptop terlalu keras atau HP terlalu dekat | Kecilkan volume laptop, jauhkan HP 20–30 cm, pastikan mode `speaker` (peredam gema aktif); bila tetap, pakai mode kabel |
| AI bicara ke rekaman operator, atau penerima asli dianggap pengumuman | Kalimat operator belum ada di daftar, atau transkrip meleset | Tambah frasa di `ANNOUNCEMENTS` (`ai-service/web/voice-agent.mjs`) dan ujinya; catat kalimat persisnya dari transkrip halaman agen |
| Halaman agen: "Chrome memblokir audio; jalankan lewat stasiun.sh" | Chrome dibuka tanpa `--autoplay-policy=no-user-gesture-required` | Tutup jendela itu, jalankan `./stasiun.sh`; jangan buka `/voice/` dari Chrome biasa |
| Halaman agen: "Halaman ini hanya berjalan di laptop stasiun" | ai-service jalan tanpa `SALURAN_ADB` (mis. lewat `dev.sh`) | Jalankan `./stasiun.sh` |
| Website: "Saluran telepon terputus sejak HH.MM" | Halaman agen tertutup, laptop tidur, atau backend tidak terjangkau dari laptop stasiun | Buka lagi lewat `./stasiun.sh`. Panggilan yang tertahan: tekan "Batalkan panggilan", atau tunggu 5 menit sampai dilepas otomatis |
| Layar: "Pesan WA gagal terkirim" | Token kedaluwarsa, nomor belum didaftarkan di Meta, di luar jendela 24 jam (mode `teks`), atau template belum disetujui | Lihat `catatan` log panggilan (mis. `wa:gagal (HTTP 401, kode Meta 190)`), perbaiki, ulangi. Panggilan tetap berjalan |
| Panggilan terputus sendiri setelah AI berpamitan terlalu cepat/lambat | Batas waktu tutup tidak cocok dengan HP ini | Atur `CLOSING_HANGUP_MS` dan `SILENCE_HANGUP_MS` di `voice-agent.mjs` |
| Website: "belum siap: Layar HP terkunci; buka kunci layar HP" | Layar terkunci menahan panggilan keluar: layar menelepon tampil, tetapi nomor tidak pernah ditekan | Buka kunci HP sekali; `svc power stayon usb` menjaga layar tetap menyala. Stasiun tidak mengambil tugas selama layar terkunci |
| HP menampilkan "Complete action using" (mis. Phone / Zoom) | Aplikasi lain ikut menangani panggilan | Sudah ditangani: Phone helper mengarahkan panggilan langsung ke `com.android.server.telecom`. Bila masih muncul, cek versi `saluran.py` |
| HP menampilkan "Choose SIM card" | SIM bawaan untuk panggilan belum diatur | Setelan → Kartu SIM & jaringan seluler → Panggilan → pilih satu SIM |
| SIM terbaca `LOADED` | Sebagian HP (Xiaomi, Android 13) melaporkan `LOADED` setelah `READY` | Normal; dianggap siap |
| Speakerphone mati di setiap panggilan baru | HP tidak mengingat speaker antar panggilan | Sudah ditangani di mode speaker: Phone helper mengetuk tombol "Speaker" dan memeriksa rute audio. Log ai-service: `saluran speaker aktif=True` |
| Penerima mengangkat tetapi diam, lalu dianggap tidak diangkat | Agen menunggu ucapan pertama penerima | Sudah ditangani: bila jaringan menyatakan diangkat (`tersambung`) dan penerima diam 3 detik, AI membuka lebih dulu |
| Transkrip penerima berisi kata asing ("hier", "madre") | Suara dari speaker HP sampai ke mikrofon laptop dalam keadaan buram | Volume panggilan HP maksimum, HP 15–20 cm dengan speaker menghadap mikrofon laptop, ruangan sepi. Bila tetap, pakai mode kabel. Hasil uji: [HASIL-UJI-HP.md](HASIL-UJI-HP.md) |
| Penerima mengangkat, tetapi suara AI tidak terdengar | (1) Keluaran audio Mac pindah ke headset Bluetooth; (2) Gemini tidak menjawab aba-aba pembuka atau mengirim audio kosong | Sudah ditangani: mode speaker selalu memakai mikrofon dan speaker bawaan MacBook, dan aba-aba pembuka dikirim ulang bila 6 detik tanpa suara. Cek baris "Audio" di halaman agen dan catatan `· AI mulai bersuara` di transkripnya. Volume Mac sekitar 70% |
| Kalimat pembuka AI terpotong, lalu AI langsung berkata "Baik, Ibu…" | Penerima berkata "halo" saat mengangkat; agen dulu mengirim dorongan "tanggapi jawaban" saat suara AI masih diputar | Sudah ditangani: hening baru dihitung setelah suara AI selesai diputar, dan mikrofon dibisukan selama AI bicara (mode speaker) |
| Durasi di layar panggilan website diam di 0:00 | Penghitung memakai detik baris transkrip terakhir | Sudah ditangani: durasi dihitung sejak log `tersambung`. Muat ulang tab website (Cmd+Shift+R) setelah pembaruan |
| Hasil "Tidak yakin" dengan `llm_gagal` padahal jawaban jelas | Model teks Gemini sibuk (429/503) | Backend mengulang pembaca dengan jeda 3, 10, 20, 40 detik, dan ai-service pindah ke `GEMINI_TEXT_MODEL_CADANGAN`. Bila tetap gagal: cek kuota kunci di Google AI Studio |
| Halaman agen: "token endpoint 503" | Google lambat membuat token sesi (lebih dari 15 detik) | Sudah ditangani: token diminta ulang sampai 3 kali selama HP berdering |
| Panggilan otomatis memutar suara demo (rekaman contoh), HP tidak menelepon | Website memakai data contoh karena API sempat tidak terjangkau (backend dimulai ulang) atau peramban memakai `app-v3.js` lama dari cache | Sudah ditangani: website mencoba API tiap 3 detik dan kembali ke data langsung sendiri, dan `tools/web.py` menyajikan website tanpa cache. Tanda data langsung: strip status "Saluran telepon …" tampil di Antrean. Sekali setelah pembaruan: Cmd+Shift+R |
