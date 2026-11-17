# Serah terima: halaman Pengaturan v3 dan rapikan tabel Antrean

Dibuat 17/11/26 oleh sesi Claude sebelumnya. Cabang: `v3-ui-opsi-3`. Tidak ada yang di-commit di sesi ini.

Baca dulu: [rencana-pengaturan-v3.md](rencana-pengaturan-v3.md) (rencana + "Hasil eksekusi" di bagian akhir).

## Yang sudah jadi

1. **Halaman Pengaturan** (`#/pengaturan`, menu bawah sidebar), mode simulasi, data di `localStorage` kunci `vedika.pengaturan.v1`:
   - kartu Nomor penelepon, Pesan pertama, Pesan cadangan, Panggilan, Uji coba, Riwayat perubahan.
   - Templat pesan berplaceholder (`{{nama}}`, `{{menit}}`, `{{nomor}}`, `{{pasien}}`, `{{rs}}`, `{{bulan}}`). Paragraf keamanan dan pilihan 1–6 dikunci dan selalu ditempel di belakang templat.
2. **Tabel Antrean:** sel pasien jadi nama + RS (jarak vertikal), kolom `Sesi` sendiri, kolom RS/Ditagih/Penerima dihapus (penerima ada di halaman panggilan dan kartu bukti), umur tidak tampil. Lebar kolom proporsional 28/11/19/21/21%.

## File yang disentuh (untuk pekerjaan ini)

| File | Isi |
|---|---|
| `data-v3.js` | `PENGATURAN_BAWAAN`, `pengaturan()`, `ubahPengaturan()`, `cekTemplat`, `cekNomor`, `cekAturanPanggilan`, `jumlahSms`, `hitungDipilih`, `pesanPemberitahuan(p, templat?)`, `pesanCadangan(p, templat?)` |
| `app-v3.js` | section "pengaturan" (kartu, draf, simpan, uji coba, riwayat), rute `pengaturan`, menu, handler `input`, sel pasien Antrean |
| `app-v3.css` | blok "Pengaturan" di akhir file, aturan lebar kolom Antrean |
| `tests/pengaturan-v3.test.js` | tes baru, 59 cek |
| `docs/rencana-pengaturan-v3.md` | rencana + hasil eksekusi |

Peringatan: pohon kerja juga berisi perubahan lain yang belum di-commit dari sesi-sesi sebelumnya (`api-v3.js`, `app.js`, `app.css`, `tests/alur-v3.test.js`, folder `videos/`, dll., dan di `app-v3.*` ada bagian pembersihan Antrean lama). Jangan `git add .`. Pilih file per file, atau tanya pemilik perubahannya. File `.pptx` jangan di-commit.

## Cara menjalankan tes

Playwright tidak terpasang di repo. Pasang di luar repo lalu arahkan `NODE_PATH`:

```bash
mkdir -p /tmp/pw && cd /tmp/pw && npm init -y && npm i playwright@1.49.0
cd /Users/imelda/Documents/Lomba/pramana-healthkathon-2026
python3 -m http.server 8899   # terminal lain, bila belum jalan
NODE_PATH=/tmp/pw/node_modules CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" node tests/pengaturan-v3.test.js
```

Hasil terakhir: `pengaturan-v3` 59 lulus, `alur-v3` 49, `alur-v3-api-awal` 6, semua lulus. `tests/alur.test.js` gagal sejak sebelum pekerjaan ini (tes v2 yang mencari layar masuk, sedangkan `index.html` sekarang v3 tanpa login). Bukan akibat perubahan ini.

Catatan saat memeriksa di browser: bila backend lokal di `localhost:8000` hidup, aplikasi masuk mode API (strip "Saluran telepon terputus", antrean dari server). Tes memutus API supaya selalu simulasi.

## Keputusan yang saya ambil (ubah bila tidak cocok)

1. Placeholder wajib pesan pertama: `{{nomor}}`, `{{menit}}`, `{{pasien}}`. Pesan cadangan: `{{pasien}}`. Batas isi 600 dan 400 karakter. Tautan ditolak.
2. Indikator pemicu baru tampil + simpan + hitung efek di data contoh ("N pasien dipilih"). Antrean tidak dihitung ulang dari aturan itu.
3. SMS belum terkirim sungguhan; pilihan saluran hanya mengubah pratinjau dan hitungan 160 karakter per SMS.
4. Uji coba simulasi tiga tahap, diberi catatan "mode contoh". Tidak ada pesan atau telepon sungguhan.
5. Jeda pesan dan jeda antar percobaan ikut Pengaturan di jam layar panggilan; durasi simulasi tetap dipadatkan.
6. Data `localStorage` yang rusak diabaikan per kunci (ada tesnya).
7. Umur pasien dibuang dari tabel Antrean karena format yang diminta hanya "nama | sesi" dan RS. Kalau umur mau kembali, tambahkan di sel pasien.

## Yang belum dikerjakan (urut saran)

1. **Sambung ke backend** (langkah 4 rencana, butuh tim backend): terima field baru di `PUT /pengaturan` (`nomor_penelepon`, `templat_wa`, `templat_cadangan`, saluran, jam, hari, batas, indikator), endpoint uji coba, Lampiran B `docs/api-contract-v3.md` jadi dinamis. Saat API hidup, pesan di layar panggilan masih dari server, bukan dari Pengaturan; halaman sudah memberi catatan "tersimpan di peramban ini".
2. **Efek indikator pemicu ke antrean** (sekarang hanya hitung): hitung ulang antrean di mode simulasi dari `D.hitungDipilih` / `D.SEMUA`. Hati-hati: mengubah KPI, corong RS, dan tes `alur-v3` yang mengunci 12 antre, 16 chip.
3. Sakelar mode presentasi (sekarang `?presentasi=1` di URL) pindah ke Pengaturan.
4. Cek visual ponsel (≤640 px) untuk tabel Antrean dan halaman Pengaturan. Tes hanya memastikan tidak ada geser samping di 390 px; tampilan kartu tabel Antrean di ponsel belum dilihat setelah kolom diubah.
5. Tombol "Buka kartu" turun dua baris di lebar sekitar 735 px; kecilkan kolom lain bila mengganggu.
