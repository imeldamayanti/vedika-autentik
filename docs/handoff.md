# Serah terima: stasiun saluran Android (v3 otomatis)

Status: branch `v3-stasiun-android`, 6 commit, **belum di-push dan belum di-PR**. Semua yang bisa diuji tanpa HP nyata
sudah diuji dan lulus, termasuk panggilan sungguhan lewat Gemini Live dengan HP palsu. Yang belum: uji dengan HP
Android nyata, akun Meta nyata, dan tiket 4.7 (jalan di atas backend Vercel).

Acuan tiket: [rencana-v3-otomatis/PROMPT-FABLE.md](rencana-v3-otomatis/PROMPT-FABLE.md) (spesifikasi yang dikerjakan),
[rencana-v3-otomatis/rencana.html](rencana-v3-otomatis/rencana.html) (rencana dan risiko),
[rencana-v3-otomatis/prototipe-petugas.html](rencana-v3-otomatis/prototipe-petugas.html) (acuan tampilan petugas).
Kontrak API terbaru: [api-contract-v3.md](api-contract-v3.md) (ada bagian **Perubahan** di atas).
Serah terima sebelumnya (pembaca jawaban dan agen suara): [serah-terima-zahra.md](serah-terima-zahra.md).

---

## 1. Apa yang berubah dibanding sebelumnya

Sebelum tiket ini, satu panggilan butuh operator manusia di laptop: mengetik URL dan kunci, memilih perangkat
BlackHole, membuka tautan wa.me lalu menekan kirim di WhatsApp Web, menelepon dari WhatsApp Web, menekan "Saya
menelepon", dan mengirim chat cadangan sendiri.

Sekarang panggilan berjalan sendiri:

```
Petugas ──► website :8899 ──► backend :8000 ──► Supabase
                                  │  ├──► pembaca jawaban (ai-service :8001)
                                  │  └──► Meta WhatsApp Cloud API (pemberitahuan, chat cadangan)
Laptop stasiun: jendela Chrome ── halaman agen /voice/ (ai-service :8001, SALURAN_ADB=1)
                    │  ├──► backend :8000 (detak, ambil, status, transkrip, hasil)
                    │  ├──► Gemini Live (suara masuk dan keluar)
                    │  └──► Phone helper /v1/saluran/* ──adb──► HP Android ──seluler──► HP penguji
```

Keputusan yang sudah dikunci (jangan dibuka lagi tanpa alasan baru): HP Android lewat ADB (bukan Twilio, bukan
panggilan WhatsApp), WhatsApp hanya untuk pesan dan dikirim server, panggilan otomatis dan berurutan dengan "Dahulukan"
menggantikan "Telepon sekarang", petugas hanya memakai website, tanpa perubahan skema database (detak stasiun
menumpang tabel `pengaturan`).

Perubahan kontrak terpenting:

| Sebelum | Sekarang |
|---|---|
| Agen membuka wa.me, lalu lapor `wa_terkirim` | Backend mengirim pesan saat `agen/ambil`, status langsung `wa_terkirim`. Laporan `wa_terkirim` dari agen kini `409 urutan_salah` |
| `wa: {lewati, teks, tautan}` | `wa: {lewati, dikirim_server, status, teks}`, tanpa `tautan` |
| `chat_cadangan: {teks, tautan}` | `chat_cadangan: {teks, dikirim_server, status}`; laporan `chat_cadangan_terkirim` tinggal untuk agen lama (idempoten) |
| Agen menelepon dulu, baru lapor `menelepon` | Lapor `menelepon` dulu (ditahan `409 jeda_belum_lewat` sampai jeda WA lewat), baru menekan nomor |
| Jawaban = fragmen pertama penerima | Jawaban = giliran bicara pertama penerima yang **selesai** dan bukan pengumuman operator |
| `mode_otomatis` bawaan `false` | bawaan `true`, juga setelah reset demo |
| Panggilan macet menggantung | Dilepas otomatis setelah 5 menit, atau dibatalkan petugas lewat `POST …/batal` |

---

## 2. Jalankan dulu, baru baca kode

### Tanpa HP (yang paling sering dipakai)

```bash
./dev.sh                                   # ai-service :8001, backend :8000, website :8899
cd backend && .venv/bin/python -m scripts.stub_agen   # agen palsu: menelepon antrean berurutan
```

Buka `http://localhost:8899`, masuk, buka Autentik. Mode otomatis sudah menyala; S1 jalan sendiri. Stub agen juga
mengirim detak, jadi strip status di website menampilkan "Saluran telepon siap (stub)".

Di luar jam 09.00–17.00 WIB tidak ada panggilan. Untuk demo cepat:

```bash
curl -X PUT localhost:8000/api/v1/pengaturan -H 'Content-Type: application/json' \
  -d '{"jeda_wa_menit": 0, "jeda_percobaan_menit": 0, "jam_mulai": "00:00", "jam_selesai": "23:59"}'
```

### Dengan HP Android

Pasang dulu menurut [rencana-v3-otomatis/STASIUN.md](rencana-v3-otomatis/STASIUN.md), lalu dari akar repo:

```bash
./stasiun.sh
```

Skrip memeriksa adb dan HP, menjaga HP dan Mac tetap menyala, menjalankan tiga layanan, mencetak satu baris per
pemeriksaan (model HP, SIM, mode audio, mode Meta), lalu membuka halaman agen di jendela Chrome tersendiri dan website
di browser biasa. Ctrl-C menghentikan semuanya.

### Panggilan sungguhan tanpa HP (Gemini Live + BlackHole + HP palsu)

```bash
SALURAN_ADB=palsu SALURAN_AUDIO=kabel SALURAN_INPUT="BlackHole 2ch" SALURAN_OUTPUT="BlackHole 16ch" \
  SALURAN_AGEN_KEY="$(grep '^AGEN_KEY=' backend/.env | cut -d= -f2-)" ./dev.sh
# terminal lain, dari ai-service:
node scripts/agent_e2e.mjs S1           # panggilan terjawab; label harus sama dengan expected_label
node scripts/agent_e2e.mjs S5           # dua percobaan tidak diangkat, chat cadangan, tidak_terhubung
node scripts/agent_e2e.mjs pengumuman   # pengumuman operator: tidak pernah tersambung, percobaan 2 dijadwalkan
```

Tiap kali jalan, panggilannya harus `antre` dengan 0 percobaan: tekan "Mulai ulang demo" dulu. Skrip mematikan mode
otomatis selama berjalan supaya hanya panggilannya sendiri yang ditelepon, dan menolak jalan bila HP-nya nyata.

---

## 3. Peta kode

### Backend (`backend/`)

| Berkas | Isi |
|---|---|
| `app/wa.py` | **Baru.** Kirim WhatsApp lewat Meta Cloud API. `kirim(nomor, jenis, teks, parameter)` → `{status: terkirim\|simulasi\|gagal, pesan}`. Satu percobaan, batas 10 detik; token, nomor, dan isi pesan tidak pernah dicatat |
| `app/agen.py` | `kirim_pemberitahuan` (dipanggil dari `ambil_tugas` pada percobaan ke-1), `_gagal_satu_percobaan` (dipakai tidak diangkat + batal + macet), `lepas_macet`, `batalkan` |
| `app/router_agen.py` | `POST /agen/detak` |
| `app/router_v3.py` | `POST /panggilan/{id}/batal`; `GET /antrean` memanggil `lepas_macet` lebih dulu |
| `app/tampilan_v3.py` | `stasiun_publik()`; `coba_lagi_setelah` di baris antrean dan detail |
| `app/repo_v3.py` | `panggilan_macet()` |
| `app/config.py` | `KUNCI_MACET_MENIT = 5`, `STASIUN_AKTIF_DETIK = 30`, pembaca env `META_WA_*`, `SALURAN_*` ada di ai-service |
| `app/aturan_v3.py` | `nomor_internasional()` (dipakai `wa.py` dan `tautan_wa`), `BAWAAN_PENGATURAN["mode_otomatis"] = True` |
| `scripts/stub_agen.py` | Melewati WA yang dikirim server, mengirim detak tiap putaran dan selama panggilan |

### ai-service (`ai-service/`)

| Berkas | Isi |
|---|---|
| `src/vedika_ai/saluran.py` | **Baru.** Phone helper: `kesehatan`, `panggil`, `tutup`, `status`, `konfigurasi`, dan (mode `palsu`) `palsu/tutup-penerima`. Hanya ada bila `SALURAN_ADB` diisi; hanya melayani `127.0.0.1`/`::1` |
| `src/vedika_ai/main.py` | `mount_line_helper(app)` |
| `web/voice-agent.mjs` | `createLineApi`, `stationTick`, `createStationOperator`, `isOperatorAnnouncement`, `isClosingLine`, `isCallGone`, `pickDevice`; `runTask` urutan baru; `VedikaVoiceSession` dengan `acceptAnswer`, `onSpeech`, `lineConstraints`, `playbackRemainingMs` |
| `web/voice-console.html` | Konsol stasiun: tanpa isian, mulai sendiri dengan `?mulai=1` |
| `scripts/agent_e2e.mjs` | e2e stasiun dengan robot penerima |

### Website (akar repo)

| Berkas | Isi |
|---|---|
| `app-v3.js` | `stripStatus()` (tujuh keadaan, yang pertama cocok menang), `chipSehat()`, hitung mundur `coba_lagi_setelah`, `bisaBatal()`, aksi `batal-panggilan`, tombol "Dahulukan", status WA dari `catatan` log |
| `api-v3.js` | `kesehatan()`, `batal()`, `coba_lagi_setelah`, `suara_langsung: null` di mode API |
| `app-v3.css` | `.siap`, `.sehat`, `.btn--bahaya`, `.hitung` |
| `tests/alur-v3.test.js` | **Baru.** Playwright mode simulasi; `tests/alur.test.js` (v2) tidak disentuh |

### Dokumen

`rencana-v3-otomatis/STASIUN.md` (perangkat, pengaturan HP, semua env, `stasiun.sh`, Meta, tabel pemecahan masalah),
`rencana-v3-otomatis/UJI-HP.md` (daftar periksa HP nyata), `api-contract-v3.md`, `backend/README.md`,
`ai-service/README.md`.

---

## 4. Yang belum dikerjakan

### 4.1 Tiket 4.7: jalan di atas backend Vercel (opsional, belum)

Dua hal yang harus diselesaikan dulu:

1. **Rekaman.** `backend/app/penyimpanan.py` menulis ke disk lokal; Vercel tidak menyimpannya. Perlu bucket privat di
   Supabase Storage.
2. **`BackgroundTasks`.** Pembacaan jawaban berjalan setelah respons terkirim. Bila Vercel memutus proses sebelum
   selesai, panggilan tersangkut di `membaca_jawaban` (dan tidak pernah dilepas `lepas_macet`, karena status itu
   sengaja dikecualikan). Bila tidak jalan, baca jawaban langsung di dalam `/hasil`.

### 4.2 Uji dengan HP nyata

Belum pernah. [rencana-v3-otomatis/UJI-HP.md](rencana-v3-otomatis/UJI-HP.md) sudah berisi daftar periksa lengkap:
pemeriksaan ADB hari pertama (A1–A13), stasiun menyala (B1–B6), skenario S1–S8 dengan kalimat yang harus diucapkan
penguji (C), pengumuman operator dan kasus tepi (D1–D10), lalu apa yang harus dicatat termasuk gerbang akurasi ≥90%
(E, F). Jalur adb yang nyata sudah diuji unit dengan runner palsu, tetapi belum pernah menyentuh HP sungguhan.

### 4.3 Meta WhatsApp

Hanya mode `log` yang pernah jalan sungguhan (tercatat "simulasi", tidak mengirim apa pun). Mode `teks` dan `template`
diuji dengan `httpx.MockTransport`. Langkah mendaftar aplikasi, nomor uji, token, dan isi badan template ada di
STASIUN.md bagian 5. Catatan: Meta bisa menolak template yang menyebut "BPJS Kesehatan" karena akunnya bukan milik
lembaga itu; bila ditolak, demo pakai mode `teks`.

Balasan penerima atas chat cadangan (angka 1–6) belum dibaca sistem sama sekali — di luar lingkup tiket ini, tetapi
kolomnya sudah ada di database (`panggilan.jawaban_chat`).

### 4.4 Satu angka ringkasan RS yang belum cocok

Saat seluruh skenario dijalankan berurutan lewat stub, RS01 berakhir `tidak_yakin` 2, sedangkan
`data-uji-konfirmasi/expected_ringkasan_rs.json` menyebut 1. Sebabnya mode otomatis sempat menelepon satu pasien bukan
skenario sebelum sempat dijeda; label `tidak_yakin` tidak memengaruhi status RS (tetap Perlu klarifikasi RS, 5 dari 7).
RS02, RS03, dan RS05 cocok persis, begitu juga keadaan sebelum S1. Bila ingin benar-benar sama, jalankan tiap skenario
dengan mode otomatis mati dan Dahulukan satu per satu, atau jeda segera setelah S8 selesai.

---

## 5. Uji: cara menjalankan dan yang sudah diketahui

| Perintah | Hasil terakhir |
|---|---|
| `cd ai-service && uv run pytest && uv run ruff check .` | 167 lulus, 1 dilewati; ruff bersih |
| `node --test ai-service/web/voice-agent.test.mjs` | 57 lulus |
| `cd ai-service/worker && bun run build && bun test` | 47 lulus |
| `cd backend && .venv/bin/pytest` | 296 lulus (lihat catatan database di bawah) |
| `node tests/alur-v3.test.js` | 19 lulus |
| `TARGET_URL=http://localhost:8899/v2.html node tests/alur.test.js` | **Gagal, tetapi sudah gagal sebelum tiket ini** |
| `node ai-service/scripts/agent_e2e.mjs S1 \| S5 \| pengumuman \| S3` | Keempatnya PASS |

### Database Supabase tidak bisa dipakai dari sini

`DATABASE_URL` di `backend/.env` tersambung di tingkat TCP tetapi ditolak Supabase dengan "tenant/user not found"
(project kemungkinan di-pause atau sudah dihapus). Jalan memutar yang dipakai: Postgres lokal.

```bash
createdb vedika_uji
export DATABASE_URL=postgresql://localhost:5432/vedika_uji
cd backend
.venv/bin/python -m scripts.terapkan_v3     # skema
.venv/bin/python -m scripts.seed_v3         # data uji
.venv/bin/pytest                            # ±5 detik, bukan ±10 menit
```

Variabel lingkungan menimpa `.env`. Seluruh uji v3 lulus di sana. **Perbaiki `DATABASE_URL` dulu** sebelum demo
sungguhan, karena website produksi menunjuk backend Vercel yang memakai Supabase yang sama.

### `tests/alur.test.js` (v2) sudah gagal sebelumnya

Gagal di "langkah 2 menyorot tab Autentik" lalu habis waktu menunggu `#tombolDemo`. Saya menjalankannya di worktree
`main` yang bersih dan hasilnya persis sama, jadi bukan akibat tiket ini. Berkas v2 (`v2.html`, `app.js`, `data.js`,
`api.js`) tidak disentuh sama sekali.

### Playwright

Tidak ada `node_modules` di repo. Di mesin ini modulnya ada di cache npx:

```bash
export NODE_PATH="$HOME/.npm/_npx/e41f203b7505f1fb/node_modules"   # playwright 1.61.1, cocok dengan chromium-1228
```

---

## 6. Keputusan yang saya ambil sendiri (spesifikasi membiarkannya terbuka)

Semuanya bisa diubah; ini sekadar pilihan paling sederhana yang memenuhi spesifikasi.

1. **Gagal menekan nomor** (adb galat) dilaporkan sebagai `tidak_diangkat`, supaya antrean tidak tertahan 5 menit.
2. **`menelepon` ditolak `409` bila panggilan `antre` belum diambil.** Tanpa ini, panggilan yang dibatalkan saat agen
   masih menunggu jeda WA langsung ditelepon lagi oleh agen yang sama.
3. **Detak tetap jalan selama panggilan** (halaman agen dan stub). Tanpa ini website mengira saluran terputus pada
   setiap panggilan lebih dari 30 detik.
4. **Akhir jeda WA dihitung sebagai aktivitas** oleh pemeriksa macet, supaya `jeda_wa_menit` besar tidak dianggap macet.
5. **`isClosingLine` juga cocok "tidak memengaruhi layanan"**, kalimat penutup langkah F skrip, karena itu yang
   benar-benar diucapkan AI di uji S1 dan S3. Giliran yang diakhiri "?" tidak pernah dianggap penutup, dan giliran
   pertama AI dikecualikan (pembuka boleh berisi "Selamat siang").
6. **Penghitung tutup menunggu audio AI selesai diputar** (`playbackRemainingMs`), supaya telepon tidak ditutup saat
   AI masih bicara.
7. **HP diberi 5 detik** meninggalkan keadaan `idle` setelah menekan nomor sebelum itu dihitung panggilan gagal.
8. **"Batalkan panggilan" muncul** bila stasiun tidak aktif atau laporan terakhir lebih dari 60 detik. Karena
   aturannya begitu, tombol itu juga muncul pada panggilan normal yang lebih dari satu menit. Bila mengganggu,
   naikkan `BASI_DETIK` di `app-v3.js` atau batasi hanya pada stasiun tidak aktif.
9. **Mode simulasi website** tetap memakai mode otomatis mati; hanya teksnya yang diubah.
10. **Fixture uji backend** menghapus env `META_WA_*` dan mengunci `NOMOR_PENELEPON`. Satu uji sebelumnya gagal karena
    membaca nomor sungguhan dari `.env`.
11. **Dokumen di `docs/rencana-v3-otomatis/`**: hanya `STASIUN.md` dan `UJI-HP.md` yang saya commit. `PROMPT-FABLE.md`,
    `rencana.html`, dan `prototipe-petugas.html` masih untracked, begitu juga `docs/slides/` — commit sendiri bila mau.

---

## 7. Lima hal yang paling mungkin perlu disetel di HP nyata

1. **Gema di mode speaker.** Apakah peredam gema Chrome cukup supaya AI tidak mendengar suaranya sendiri. Perlu
   menyetel jarak dan volume, atau pindah ke mode kabel.
2. **Kalimat pengumuman operator.** Kata-kata operator Indonesia yang sebenarnya, dan apakah Gemini menutup "giliran
   bicara" cukup cepat pada rekaman yang mengalir terus. Daftarnya: `ANNOUNCEMENTS` di `voice-agent.mjs`.
3. **`KEYCODE_ENDCALL` saat tidak ada panggilan.** Di sebagian HP ini mematikan atau mengunci layar, padahal stasiun
   mengirimnya sesudah setiap panggilan (`finally`).
4. **Waktu keadaan panggilan.** `mCallState` menjadi 2 sejak berdering, jadi panggilan tak terjawab bergantung pada
   penghitung 40 detik; tenggang 5 detik setelah menekan nomor juga bisa terlalu pendek atau terlalu panjang.
5. **Menelepon tanpa dialog.** Pemilih SIM di HP dua SIM, layar terkunci menahan intent panggilan, dan speakerphone
   yang tidak bertahan antar panggilan.

---

## 8. Jebakan yang sudah diketahui

- **Rahasia.** Kunci agen sampai ke browser stasiun **hanya** lewat `GET /v1/saluran/konfigurasi`, dan itulah sebabnya
  seluruh router Phone helper menolak klien selain localhost. Jangan pasang router itu di Cloudflare Worker, jangan
  menaruh kunci di HTML.
- **`membaca_jawaban` tidak pernah dilepas** oleh `lepas_macet`. Kalau pembaca jawaban menggantung, panggilan tersangkut
  dan petugas tidak bisa membatalkannya. Sengaja (pembacaan selalu selesai sendiri lewat jaring pengaman di
  `proses_hasil`), tetapi perlu diingat saat mengerjakan 4.7.
- **`PUT /pengaturan` mengabaikan kunci `stasiun`.** Validatornya hanya menerima kunci di `BAWAAN_PENGATURAN`; kalau
  menambah kunci baru di sana, pastikan `stasiun` tetap tidak bisa ditimpa.
- **Label hanya dihitung backend** dengan `data-uji-konfirmasi/tools/aturan.py`. Agen, Phone helper, dan pembaca tidak
  pernah mengirim label.
- **Jangan commit** `.env`, token, `backend/uploads/`, rekaman, dan keluaran e2e. Jangan baca
  `data-uji-konfirmasi/kunci_kebenaran_*.csv` dari kode produk.
- **`dev.sh` tetap apa adanya** untuk pengembangan tanpa HP; `stasiun.sh` yang memakai HP.

---

## 9. Langkah berikutnya yang saya sarankan

1. Perbaiki `DATABASE_URL` Supabase, jalankan `cd backend && .venv/bin/pytest` terhadap database sungguhan sekali.
2. Push branch `v3-stasiun-android` dan buka PR.
3. Pinjam satu HP Android, kerjakan [UJI-HP.md](rencana-v3-otomatis/UJI-HP.md) bagian A (pemeriksaan ADB, sekitar 20
   menit). Bagian A yang lulus hampir memastikan sisanya jalan.
4. Daftarkan aplikasi Meta dan uji mode `teks` ke satu nomor tim.
5. Baru setelah itu, tiket 4.7 (Supabase Storage + pembacaan di Vercel).
