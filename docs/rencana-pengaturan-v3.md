# Rencana halaman Pengaturan (Vedika Autentik v3)

Status: langkah 1–3 SELESAI (17/11/26, FE mode simulasi, localStorage). Langkah 4 (sambung API + kontrak) menunggu backend. Lihat "Hasil eksekusi" di bagian akhir.
Sumber: chat tim 17/11/26 (Imelda, Richard).

## Tujuan

Verifikator bisa menyiapkan semuanya dari web, tanpa sentuh kode atau env server:
nomor penelepon, pesan pertama WA/SMS, dan aturan panggilan. Juga jadi bahan demo live di final.

Alur pengguna:
1. Verifikator buka **Pengaturan** (menu bawah sidebar).
2. Cek/ganti nomor penelepon.
3. Atur pesan pertama yang dikirim sebelum telepon (lihat pratinjau di mockup HP).
4. Atur jadwal dan aturan panggilan.
5. Tekan "Kirim uji ke nomor saya" untuk memastikan semuanya jalan.

## Kondisi sekarang (dari kode)

| Hal | Di mana sekarang | Bisa diubah dari web? |
|---|---|---|
| Nomor penelepon | `data-v3.js:23` `NOMOR_PENELEPON` (simulasi), env API `NOMOR_PENELEPON` (hidup) | Tidak |
| Pesan WA pertama | `data-v3.js:104` `pesanPemberitahuan` + Lampiran B kontrak API | Tidak |
| Pesan cadangan | `data-v3.js:110` `pesanCadangan` | Tidak |
| Mode otomatis, jeda | `PUT /pengaturan` | Ya (tombol di Antrean) |
| Jam mulai/selesai, jeda WA, jeda percobaan | `GET/PUT /pengaturan` | Ada di API, belum ada UI |
| Status stasiun (HP) | `pengaturan.stasiun` | Hanya tampil di strip status |

## Isi halaman (usulan)

Rute baru `#/pengaturan`. Tata letak kartu bertumpuk, gaya sama dengan kartu KPI (shadow, tanpa border).

### Kartu 1: Nomor penelepon
- Tampilkan nomor aktif + status stasiun HP (aktif/terputus, perangkat, terakhir terlihat).
- Tombol "Ganti nomor" buka form: nomor baru, alasan.
- Catatan kecil: "Penggantian nomor nantinya butuh persetujuan atasan." Alur persetujuan TIDAK dibuat dulu (arahan Richard).
- Nomor ini otomatis dipakai di placeholder `{{nomor}}` pesan.

### Kartu 2: Pesan pertama (sebelum telepon)
- Editor teks dengan placeholder bertanda chip: `{{nama}}`, `{{menit}}`, `{{nomor}}`, `{{pasien}}`, `{{rs}}`, `{{bulan}}`.
- Bawaan = teks Richard:
  > Halo {{nama}}, kami dari BPJS Kesehatan. Sekitar {{menit}} menit lagi kami akan menelepon dari nomor {{nomor}} untuk konfirmasi singkat layanan fisioterapi {{pasien}} di {{rs}} bulan {{bulan}}. Teleponnya sekitar 2 menit, mohon diangkat.
  >
  > Ini bukan tagihan. Kami tidak akan meminta NIK, kode OTP, nomor rekening, atau pembayaran. Ragu pesan ini asli? Hubungi Care Center 165.
- Paragraf keamanan (baris kedua) dikunci, tidak bisa dihapus: melindungi peserta dari penipuan.
- Pratinjau langsung di mockup HP (pakai ulang komponen `ponsel` yang sudah ada), diisi data pasien contoh.
- Validasi: tanpa tautan (cek yang sudah ada di `data-v3.js:515`), placeholder wajib ada, batas karakter.
- Tombol "Kembalikan ke bawaan".

### Kartu 3: Pesan cadangan (setelah 2x tidak diangkat)
- Editor sama, bawaan = `pesanCadangan` sekarang. Pilihan jawaban 1–6 dikunci karena dibaca otomatis oleh sistem.

### Kartu 4: Panggilan
Usulan isi (dipilih lewat pertanyaan):
- Jam panggilan: mulai/selesai (sudah ada di API).
- Jeda pesan → telepon (menit) (sudah ada: `jeda_wa_menit`).
- Jeda antar percobaan (menit) dan jumlah percobaan maksimal (sekarang tetap 2).
- Hari panggilan: Senin–Jumat / termasuk Sabtu.
- Batas panggilan per hari (melindungi kuota pulsa dan RS).
- Indikator pemicu antrean: minimal berapa indikator (sekarang ≥2), aktif/nonaktif per indikator I1–I4, ikut sertakan pilihan model anomali atau tidak.

### Kartu 5: Uji coba
- "Kirim pesan + telepon uji ke nomor saya": satu tombol, masuk ke nomor tim. Ini senjata utama demo live final (juri lihat HP berdering).
- Hasil uji tampil singkat: terkirim / tersambung / gagal + alasan.

### Kartu 6: Riwayat perubahan
- Daftar siapa mengubah apa dan kapan (nomor, pesan, aturan). Jadi dasar alur persetujuan nanti.

## Ide penyesuaian lain (brainstorm)

Penambahan:
- Pindahkan "mode presentasi" (sekarang `?presentasi=1` di URL) jadi sakelar di Pengaturan, biar aman saat final.
- Pilih saluran pesan pertama: WhatsApp, SMS, atau WA lalu SMS kalau WA gagal.

Penyesuaian:
- Ganti teks pesan bawaan di `data-v3.js` dan Lampiran B ke versi Richard (lebih jelas: durasi telepon, sebut NIK dan rekening).
- Tombol Panggilan otomatis/Jeda tetap di Antrean (dipakai harian), Pengaturan hanya untuk hal yang jarang diubah.

Pengurangan:
- Jangan buat alur persetujuan, peran pengguna, atau login dulu.
- Jangan buat editor skrip suara agen; terlalu berisiko untuk demo.

## Dampak teknis

| Bagian | Perubahan |
|---|---|
| `app-v3.js` | Rute `pengaturan`, menu sidebar, render kartu, aksi simpan |
| `app-v3.css` | Gaya form, chip placeholder, editor |
| `data-v3.js` | Template pakai placeholder, fungsi isi placeholder, nilai bawaan baru |
| `api-v3.js` | `PUT /pengaturan` dengan field baru, endpoint uji (bila ada) |
| Backend + `docs/api-contract-v3.md` | Field baru di `pengaturan`: `nomor_penelepon`, `templat_wa`, `templat_cadangan`, dll. Lampiran B jadi dinamis |
| `tests/alur-v3.test.js` | Uji rute, validasi template, placeholder terisi |

## Urutan kerja (setelah pertanyaan dijawab)

1. Ubah template pesan jadi berplaceholder + teks bawaan Richard (data-v3.js, tes).
2. Rute + menu + kartu Nomor & Pesan pertama (mode simulasi dulu).
3. Kartu Panggilan + Uji coba + Riwayat.
4. Sambungkan ke API (perlu tim backend) + perbarui kontrak.
5. Cek di browser, jalankan tes.

Perkiraan: langkah 1–3 sekitar 3–4 jam (FE saja, simulasi). Langkah 4 tergantung backend, sekitar setengah hari.

## Keputusan (dijawab 17/11/26)

1. **Penyimpanan:** FE dulu (localStorage, mode simulasi), bentuk datanya disiapkan sama dengan `PUT /pengaturan` supaya nanti tinggal disambung ke API.
2. **Edit pesan:** bebas, tapi paragraf keamanan dikunci dan placeholder wajib ada.
3. **Saluran:** pilihan WhatsApp / SMS / WA lalu SMS. Selama backend belum bisa kirim SMS, pilihan SMS hanya mengubah pratinjau dan teks (diberi batas 160 karakter per SMS).
4. **Panggilan versi pertama:** semua kartu masuk: jam & jeda, telepon uji, indikator pemicu, batas & riwayat.

Catatan risiko: "Indikator pemicu" mengubah siapa yang masuk antrean. Di mode simulasi antrean berasal dari data contoh, jadi perlu dihitung ulang dari `D.UJI`. Kalau terlalu berat, tahap pertama cukup tampil + simpan, efek ke antrean menyusul.

Perkiraan baru: langkah 1–3 sekitar 5–6 jam (FE, simulasi), karena indikator pemicu dan SMS ikut masuk.

## Hasil eksekusi (17/11/26)

Selesai (FE simulasi, `#/pengaturan`, menu bawah sidebar):
- Kartu Nomor penelepon (ganti nomor + alasan), Pesan pertama (editor, chip placeholder, pratinjau HP, saluran WA/SMS/WA lalu SMS, hitungan 160 karakter per SMS), Pesan cadangan, Panggilan (jam, hari, jeda, percobaan, batas harian, indikator pemicu), Uji coba, Riwayat perubahan.
- Templat berplaceholder di `data-v3.js` dengan teks Richard. Paragraf keamanan dan pilihan 1–6 dikunci dan selalu ikut terkirim.
- Data di `localStorage` (`vedika.pengaturan.v1`), bentuknya sama dengan `PUT /pengaturan`. "Mulai ulang demo" tidak menghapusnya.
- Tes: `tests/pengaturan-v3.test.js` (59 cek), `alur-v3` 49, `alur-v3-api-awal` 6, semuanya lulus.

Keputusan yang saya ambil (ubah bila tidak cocok):
1. Placeholder wajib di pesan pertama: `{{nomor}}`, `{{menit}}`, `{{pasien}}`. Pesan cadangan: `{{pasien}}`. Batas isi: 600 dan 400 karakter. Tautan ditolak.
2. Indikator pemicu: tahap pertama hanya tampil + simpan + hitung efek di data contoh ("N pasien dipilih"). Antrean di layar Antrean belum dihitung ulang (sesuai catatan risiko).
3. SMS belum terkirim sungguhan: pilihan hanya mengubah pratinjau dan hitungan karakter.
4. Uji coba berjalan simulasi (3 tahap berurutan) dan diberi catatan "mode contoh". Tidak ada pesan atau telepon sungguhan.
5. Jeda pesan dan jeda antar percobaan ikut Pengaturan di jam pada layar panggilan; durasi simulasi tetap dipadatkan.

Belum dikerjakan:
- Langkah 4: backend menerima field baru (`nomor_penelepon`, `templat_wa`, `templat_cadangan`, dll.), endpoint uji coba, dan Lampiran B kontrak API dinamis. Saat API hidup, pesan di layar panggilan tetap dari server, bukan dari Pengaturan.
- Ide brainstorm: sakelar mode presentasi di Pengaturan.
