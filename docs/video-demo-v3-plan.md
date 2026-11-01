# Video Demo v3 Vedika Autentik — Plan, Flow, VO, Komponen

Durasi target: **1:28** (maks 1:30). 1920x1080, 30 fps, subtitle dibakar.
Penonton = **verifikator BPJS**. VO bicara ke "kamu". Fokus ke *apa yang kamu lakukan dengan fitur*, bukan daftar fitur.
Cerita dipandu satu kasus: **S1 Pak Andi Pratama, RS Melati Sehat, Agustus 2026 — ditagih 11 sesi, versi pasien 3.**

Aturan kata (PRD R3.3): jangan "curang"/"fraud". Pakai "tidak sesuai", "selisih", "bahan klarifikasi".
Semua layar app berlabel "Simulasi"; visual data di Babak 1 dan penutup diberi lencana "Simulasi · data sintetis".

---

## 1. Garis besar

Waktu final mengikuti durasi VO (`videos/v3/timing.json`, total **88,21 dtk**).

| Waktu | Babak | Isi | Sumber visual |
|---|---|---|---|
| 0:00–0:18,5 | Problem | Suara Pak Andi "tiga kali" → RS menagih 11 → 30 dari 300 pasien terpicu, konfirmasi masih manual | Motion graphic dari data uji + komponen website |
| 0:18,5–0:26 | Solusi | Logo sting: "AI menelepon pasien. Kamu yang memutuskan." | Motion graphic HyperFrames |
| 0:26–1:19 | Demo (use case) | Satu hari verifikator: antrean → WA → panggilan → kartu bukti → ringkasan RS → keputusan | Rekaman layar + zoom/kamera + overlay |
| 1:19–1:28 | Penutup | Kalender Pak Andi: tagihan vs versi pasien berdampingan → slogan + logo + tim Veritas | Motion graphic |

Problem + solusi = 26 detik (masuk rentang 15–30).

---

## 2. Flow per adegan + VO

Kecepatan VO ±2,4 kata/detik. Sisanya audio telepon asli, jeda, SFX.

### Babak 1 — Problem (0:00–0:18,5)

Tidak ada video stok/AI. Semua visual dibangun dari data milik kita (`data-uji-konfirmasi/`) dengan token website (lihat bagian 3).

| # | Waktu | Visual | Teks layar | Audio | SFX |
|---|---|---|---|---|---|
| H | 0:00–0:03,6 | Kartu peserta Andi Pratama masuk, panel "Rekaman panggilan · simulasi" dengan waveform yang terisi mengikuti suara. Kalender Agustus 2026 muncul; tiga pita teal menyala saat Pak Andi menyebut "awal bulan", "pertengahan", "dua puluhan" | Subtitle gaya telepon: "**Pak Andi** Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan." | **Suara rekaman S1** (`assets/rekaman/S1/06.mp3`, 0–3,40 dtk, EQ telepon) sebelum VO masuk | musik intro tipis |
| P1 | 0:03,9–0:07,7 | Panel "Versi peserta **3** sesi" pop | — | VO p1: "Itu kata Pak Andi soal terapinya bulan Agustus." | — |
| P2 | 0:08,1–0:11,3 | Kolom kiri keluar. 11 baris klaim RS Melati (SEP-UJI-004697…707, baris 16 & 17 Agt kuning) masuk satu per satu; tiap baris mengisi tanggalnya di kalender (hitam, Minggu/libur cokelat). Counter "Ditagih" naik 1→11, merah setelah lewat 3. "Selisih **8**" pop | — | VO p2: "Tapi yang ditagih ke BPJS: sebelas." | tick per baris (11), thud di Selisih 8 |
| P3 | 0:11,4–0:18,2 | Seluruh layar mengecil jadi satu kotak merah "Pak Andi" di grid 300 pasien aktif (dikelompokkan per RS), 30 terpicu menyala teal (RS Melati 27). Kartu angka 300 / 30. Kartu KPK masuk | "KPK · 2024 — **3.269 dari 4.341** tagihan fisioterapi tak ada di rekam medis. Terungkap setelah pasien dikonfirmasi." | VO p3: "Selisih begini baru ketahuan kalau pasiennya ditanya. Itu masih manual, dan sering telat." | whoosh saat zoom out, whoosh keluar |

### Babak 2 — Solusi (0:14–0:20)

| # | Waktu | Visual | Teks layar | VO | SFX |
|---|---|---|---|---|---|
| S | 0:18,5–0:26 | Layar hitam → ikon telepon berdering → morph jadi logo Vedika Autentik. Tagline mengetik | "AI menelepon pasien. **Kamu yang memutuskan.**" | "Kenalin, Vedika Autentik. AI yang menelepon pasien, supaya kamu dapat jawaban langsung dari sumbernya." | riser pendek → *hit* + beat drop musik |

### Babak 3 — Demo, "satu hari verifikator" (0:26–1:19)

| # | Waktu | Layar app | Aksi + kamera | Overlay | VO | SFX |
|---|---|---|---|---|---|---|
| D1 | 0:20–0:29 | **Antrean** | Zoom ke baris Pak Andi: chip I1 I2 I4, "11 sesi", penerima "Peserta" | Callout di chip: "11 sesi/bulan · 4 sesi/minggu · sesi 17 Agustus" | "Pagi ini antreanmu sudah terisi. Bukan semua pasien, cuma yang polanya janggal. Pak Andi: sebelas sesi, ada yang di tanggal merah." | klik halus |
| D2 | 0:29–0:35 | Antrean → mockup HP | Klik **Mode otomatis AKTIF**. Status "WA terkirim". HP mockup slide-in dari kanan, bubble WA pemberitahuan muncul | "Tanpa tautan · tanpa minta data · cek ke 165" | "Nyalakan mode otomatis. Pak Andi dapat WhatsApp dulu, biar nggak dikira penipuan." | klik, *ding* WA |
| D3 | 0:39–0:53 | **Panggilan berlangsung** | Status "Menelepon" → "Tersambung". Transkrip mengalir; kamera ikut baris terbaru. Field kanan terisi: hadir ✓, jumlah **3**, libur dibantah | Waveform kecil di pojok saat audio asli | VO: "Lalu AI menelepon. Kamu bisa ikuti percakapannya langsung." → **audio rekaman S1 4,5 dtk** (`assets/rekaman/S1/05.mp3` AI tanya jumlah + awal `06.mp3` "Tiga kali.", jawaban lengkap sudah didengar di pembuka) → VO: "Jawabannya langsung tertangkap." | 2x dering telepon di awal; musik *duck* dalam saat audio asli |
| D4 | 0:50–1:03 | **Kartu bukti** S1 | Zoom ke blok "Ditagih 11 · Versi peserta 3 · Selisih 8". Lalu pan ke daftar tanggal (16 & 17 Agt ditandai), kutipan kunci, pemutar rekaman | "Selisih 8" diberi garis bawah animasi | "Sekarang kamu punya kartu bukti. Ditagih sebelas, kata Pak Andi tiga. Rekaman, kutipan, tanggal liburnya, semua siap jadi bahan klarifikasi ke rumah sakit." | counter tick 11→3, *thud* pelan di "Selisih 8" |
| D5 | 1:03–1:11 | **Ringkasan RS** | Fokus baris RS Melati Sehat. Status berubah Normal → **Perlu klarifikasi RS** (3 dari 5) | Badge 2/4 → 3/5 | "Satu jawaban belum cukup. Tapi saat tiga pasien dari RS yang sama bilang hal serupa, RS Melati masuk daftar klarifikasi." | *stamp* saat status berubah |
| D6 | 1:11–1:18 | Kartu bukti, panel keputusan | Klik **Setujui saran: Minta klarifikasi RS**. Jejak keputusan muncul (siapa, kapan, alasan) | — | "Sistem cuma menyarankan. Yang memutuskan tetap kamu, lengkap dengan alasannya." | klik, *pop* konfirmasi |

### Babak 4 — Penutup (1:19–1:28)

| Waktu | Visual | Teks layar | VO | SFX |
|---|---|---|---|---|
| 1:18,7–1:22,9 | Layar app memudar ke kanvas terang. Kalender Agustus Pak Andi kembali, kini dua lapis sekaligus: tanggal yang ditagih (hitam/cokelat) dan tiga pita versi pasien (teal). Kiri: kartu "Ditagih rumah sakit 11 sesi", "Versi pasien 3 sesi", badge "Selisih 8 · bahan klarifikasi ke RS". Legenda: "dibandingkan berdampingan oleh sistem" | Judul kata per kata: "Yang **ditagih** harus sama dengan yang **dijalani**." | z0: "Karena yang ditagih, harus sama dengan yang dijalani." | whoosh masuk, musik build |
| 1:22,3–1:28,2 | Garis pindai → logo Vedika Autentik + slogan + "Tim Veritas · Richard · Zahra · Imelda" | "Vedika Autentik" besar, di bawahnya "Dengar langsung dari pasien." | z1: "Vedika Autentik. Dengar langsung dari pasien." | riser + *hit* akhir di beat |

---

## 3. Rancangan motion Babak 1 + penutup (pengganti Google Flow)

Google Flow tidak dipakai: hasilnya generik dan tidak terhubung ke produk. Babak 1 dan kilas balik penutup diganti motion graphic yang digali dari bahan kita sendiri.

### Bahan yang dipakai
| Bahan | Dipakai untuk |
|---|---|
| Website v3 (`app.css`, `app-v3.css`) | Font Plus Jakarta Sans + JetBrains Mono (disalin ke `videos/v3/assets/fonts/`, OFL), token warna oklch (primary teal, brand, kuning cek, merah prioritas), radius panel, bayangan, lencana "Simulasi", kartu angka, chip tanggal kuning untuk Minggu/libur, gaya tabel |
| `assets/rekaman/S1/06.mp3` | Hook pembuka: jawaban Pak Andi soal jumlah sesi (baris 6 transkrip, 39,4 dtk di rekaman penuh) |
| `data-uji-konfirmasi/klaim_sesi.csv` | 11 klaim P-S1 RS01 Agustus 2026: tanggal 3, 4, 6, 10, 11, 13, 16 (Minggu), 17 (libur nasional), 20, 24, 27; id SEP-UJI-004697…707; M54.5; Rp136.900 |
| `data-uji-konfirmasi/expected_indikator_2026-08.csv` | 300 pasien aktif Agustus, 30 terpicu (RS Melati 27 dari 68, Bakti Mulia 1, Cempaka Asri 1, Nusa Sejahtera 0, Kenanga Medika 1). Sebaran kotak di grid bersifat visual, jumlahnya sama dengan data |
| `kunci_kebenaran_2026-08.csv` | **Tidak dibuka.** Karena itu tanggal sebenarnya Pak Andi tidak digambar; versi pasien tampil sebagai tiga pita samar sesuai kata-katanya |

### Dua arah yang dieksplorasi
Still di `videos/v3/renders/eksplorasi/` (dibuat `videos/v3/tools/eksplorasi.html` + `eksplorasi-render.mjs`).

- **A — "Kartu bukti dirakit"** (`A1–A4.png`, `A-sheet.png`): kanvas terang website, kartu peserta, kalender Agustus dengan pita versi pasien vs tanggal tagihan, baris klaim gaya tabel antrean, kartu angka, grid 300 pasien per RS, kartu KPK putih.
- **B — "Ledger gelap"** (`B1–B4.png`, `B-sheet.png`): latar teal gelap logo, waveform emas besar, baris CSV mentah bergaya monospace, kalender bercahaya merah/emas, medan 300 titik.

### Pilihan: A
1. **Satu bahasa visual dengan demo.** Babak 3 adalah rekaman layar website yang terang. Arah A memakai komponen yang sama (kartu, chip tanggal kuning, lencana, font), jadi perpindahan ke demo terasa mulus dan verifikator mengenali komponen yang nanti ia pakai. Arah B membuat lompatan gelap → terang dua kali.
2. **Metafora yang jujur dan spesifik.** Tagihan tampil sebagai tanggal pasti; versi pasien sebagai tiga pita samar ("awal bulan, pertengahan, dua puluhan"). Selisihnya terlihat langsung di kalender tanpa mengarang tanggal yang benar. Metafora ini dipakai ulang di penutup ("berdampingan oleh sistem").
3. **Terbaca tanpa suara di HP.** Baris CSV monospace arah B tidak terbaca di layar kecil; arah A memakai angka besar dan label kapital.
4. Yang dipinjam dari B: waveform yang terisi mengikuti suara sebagai hook.

### Urutan motion (lihat tabel Babak 1 dan Penutup di atas)
Hook kartu peserta + waveform → kalender + 3 pita → "Versi peserta 3" → kolom kiri keluar, kalender bergeser dan mengecil → 11 baris klaim + kalender terisi + counter 1→11 merah → "Selisih 8" → semua mengecil jadi satu kotak "Pak Andi" di grid 300 pasien → 30 menyala → kartu KPK → kartu logo S. Penutup: kalender dua lapis + kartu angka → logo.

Implementasi: `videos/v3/tools/build.py` (bagian "babak 1 + penutup") dan `tools/index.template.html` (CSS "babak 1 + penutup", JS "babak 1" dan "penutup"). `videos/v3/assets/flow/` tidak lagi dipakai komposisi.

---

## 4. Komponen yang dipakai

### Pipeline
- **HyperFrames** sebagai editor utama (sudah ada pipeline di `videos/v2`: `tools/build.py`, `record-demo.mjs`, `elevenlabs-vo.mjs`, `make-sfx.py`). Komposisi baru di `videos/v3/`.
- **Remotion**: tidak dipakai. Semua motion di bawah bisa di HyperFrames; dua framework = dua render + sinkron ulang, risiko besar dengan tenggat 1 Nov 15.00.
- Render akhir: MP4 H.264 1080p, audio AAC 48 kHz, loudness −14 LUFS.

### Motion components (HyperFrames)
| Komponen | Dipakai di |
|---|---|
| Kinetic text masuk per kata + angka pop | P1, P2, S, penutup |
| Waveform yang terisi mengikuti suara | H |
| Kalender Agustus: pita versi pasien + tanggal tagihan terisi | H, P2, penutup |
| Baris klaim bertumpuk (gaya tabel antrean) | P2 |
| Counter 1 → 11 (merah setelah 3) dan 11 → 3 | P2, D4 |
| Zoom out ke grid 300 pasien, 30 menyala | P3 |
| Kartu statistik KPK (kecil, sumber di bawah) | P3 |
| Logo sting (ikon telepon → logo) | S, penutup |
| Kamera virtual: zoom/pan halus ke area layar (pose-based, bukan gerak terus) | D1–D6 |
| Sorot klik (lingkaran) + kursor besar | D1, D2, D6 |
| Callout/annotation box ke chip & angka | D1, D4 |
| Mockup HP + bubble WA slide-in | D2 |
| Waveform audio di pojok saat rekaman asli | D3 |
| Badge status berubah + efek stamp | D5 |
| Lower third langkah: "1 · Antrean" … "6 · Keputusan" | D1–D6 |
| Subtitle 2 baris, posisi aman di atas lower third | seluruh video |
| Crossfade 0,3 dtk antar adegan; whip cuma di batas babak | transisi |

### Audio
- **VO**: ElevenLabs (`tools/elevenlabs-vo.mjs`), suara percakapan Indonesia hasil audisi `videos/voice-samples/v3/` (Velora/Anjani). Gaya santai, ramah, bukan pembaca berita: stability 0,35, style 0,45, speed 1,05. Satu file per baris (`p1`, `p2`, … `z1`) supaya gampang disinkron.
- **Audio telepon asli**: dari `assets/rekaman/S1/` lewat `videos/tools/make-audio-v3.py`: `call/s1-hook.wav` (06.mp3, pembuka) dan `call/s1-qa.wav` (05.mp3 + "Tiga kali.", D3). EQ telepon 320–3400 Hz.
- **Backsound**: tech/startup upbeat, minimal house/future-pop ±115 BPM, pluck synth + perkusi ringan, tanpa vokal. Struktur: intro tipis (0:00–0:14) → drop di logo (0:14) → groove stabil di demo, *duck* −18 dB di bawah VO, hampir senyap saat audio telepon (D3) → build di 1:18 → hit akhir di 1:28. Sumber final: **disintesis sendiri** (`videos/tools/make-audio-v3.py`, CC0, bukti + checksum di `videos/v3/assets/LISENSI-AUDIO.md`). Drop dikunci ke awal adegan S lewat offset media musik.
- **SFX (maks ±12 cue, volume di bawah VO)**:

| SFX | Cue |
|---|---|
| Tick counter | P2, D4 |
| Thud/impact pelan | angka 11 (P2), "Selisih 8" (D4) |
| Whoosh | P3→S, S→D1, D6→penutup (3x saja) |
| Riser + hit | logo S, logo penutup |
| Klik mouse halus | D1, D2, D6 |
| Ding notifikasi WA | D2 |
| Dering telepon 2x | awal D3 |
| Stamp | D5 status berubah |
| Pop konfirmasi | D6 |

### Rekaman layar
- `videos/tools/record-demo-v3.mjs` (puppeteer + perekam CDP sendiri, karena screencast bawaan menjatuhkan frame), viewport 1440x810 DPR 2, mode simulasi S1. Satu take realtime 122 dtk, dipotong per adegan memakai `assets/screen/demo.marks.json`.
- Kondisi awal bersih: RS Melati Normal (2/4), S1 Antre.

---

## 5. Keputusan yang masih terbuka

Tidak ada lagi. Sudah diputuskan (31 Okt):
- Slogan penutup: **"Vedika Autentik, dengar langsung dari pasien."** (menggantikan "Lengkap belum tentu asli" dari v2).
- Kartu KPK di P3 pakai **3.269 dari 4.341** (terverifikasi). Angka "2 vs 10" tidak dipakai.
- VO **ElevenLabs penuh**, termasuk babak problem.

## 6. Urutan kerja

1. Kunci slogan + naskah VO. ✓
2. Eksplorasi 2 arah motion Babak 1, pilih A. ✓
3. Rekam layar D1–D6 (`videos/tools/record-demo-v3.mjs`, satu take dari kondisi bersih). ✓
4. VO ElevenLabs per baris (`videos/v3/tools/gen_vo.py`), ukur durasi, `timeline.py`. ✓
5. Backsound + SFX sintesis (`make-audio-v3.py --drop … --build … --hit … --end …` dari keluaran timeline). ✓
6. Rakit komposisi (`python3 videos/v3/tools/build.py`), cek `hyperframes check` + snapshot. ✓
7. Render + normalisasi −14 LUFS: `bash videos/v3/tools/finalize.sh` → `videos/v3/renders/vedika-autentik-demo-v3-final.mp4`. Tonton tanpa suara, unggah, QR.
