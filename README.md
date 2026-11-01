# Vedika Autentik

*Lengkap belum tentu asli.* Ditenagai PRAMANA.

Prototipe untuk **BPJS Kesehatan Healthkathon 2026**, kategori *Efisiensi Risiko pada Fasilitas Kesehatan*.

**Demo langsung: <https://pramana-flax.vercel.app>**

Vedika Autentik adalah tab baru di aplikasi verifikasi klaim BPJS Kesehatan. Tab ini memeriksa keaslian berkas klaim fisioterapi yang diunggah rumah sakit ke JKN Drive: apakah berkasnya dipakai ulang, disunting, atau dibuat dengan AI, dan apakah isinya cocok dengan jumlah sesi yang ditagih. Setiap berkas mendapat satu dari empat label beserta buktinya. Keputusan tetap di tangan verifikator.

## Mencoba demo

1. Buka tautan demo, lalu tekan **Masuk sebagai verifikator demo**. Panduan singkat langsung terbuka.
2. Di tab **Autentik**, tekan **Jalankan demo**. Lima berkas contoh diperiksa satu per satu dan masuk ke antrean:

   | Berkas | Isi | Label |
   |---|---|---|
   | VA-ASL-01 | Berkas asli, 8 sesi | Lolos |
   | VA-KMB-01 | Lembar Bu Siti dipakai untuk klaim Pak Budi | Prioritas |
   | VA-DST-01 | 5 sesi, angka jumlah kunjungan diubah jadi 8 | Prioritas |
   | VA-AI-01 | Gambar dari generator AI | Perlu dicek |
   | VA-BRM-01 | Scan buram dan terpotong | Scan ulang |

3. Buka salah satu berkas. Kartu bukti menampilkan area yang disorot, temuan beserta kekuatannya, dan langkah yang disarankan. Tekan **Setujui saran**, atau pilih tindakan lain dengan alasan tertulis.
4. Untuk berkas Prioritas, buka **Konfirmasi peserta** dan simulasikan jawaban lewat PANDAWA. Setelah diteruskan ke telaah lanjut, **laporan temuan** bisa diunduh sebagai PDF.

Berkas di folder `dataset/` juga bisa diseret langsung ke kotak unggah; rumah sakitnya mengikuti data klaim contoh. Untuk berkas di luar dataset, pilih rumah sakit pengirim dari daftar dashboard sebelum unggah. Pilihan manual ini hanya konteks demo, bukan verifikasi asal dokumen. Berkas luar ditandai Perlu dicek, karena sistem tidak pernah memberi label Lolos pada berkas yang gagal diproses.

## Aturan label

Label dihitung ulang di peramban dari temuan setiap berkas (`data.js`, fungsi `hitungLabel`), mengikuti PRD bagian 9:

| Label | Kapan | Saran tindakan |
|---|---|---|
| Lolos | Tidak ada temuan dan isi cocok dengan klaim | Tutup sebagai wajar |
| Scan ulang | Berkas tidak terbaca atau terpotong | Minta scan ulang |
| Perlu dicek | Ada sinyal yang masih mungkin kelalaian | Minta klarifikasi rumah sakit |
| Prioritas | Dua sinyal kuat, atau satu kuat ditambah sinyal lain | Teruskan ke telaah lanjut |

Tanda buatan AI tidak pernah menjadi satu-satunya alasan Prioritas. Scan yang jelek tidak pernah dianggap tanda kecurangan.

## Struktur

| Berkas | Isi |
|---|---|
| `index.html` | Kerangka halaman, ditulis tanpa `<!doctype>/<html>/<head>/<body>` supaya bisa dipublikasikan sebagai artifact |
| `app.css` | Token warna dan komponen. Bahasa visual mengikuti JKN Drive v2: Plus Jakarta Sans, teal gelap, tombol 40px bersudut 6px |
| `data.js` | Aturan label, urutan langkah pemeriksaan, empat tindakan, pesan PANDAWA |
| `app.js` | Perute, tujuh layar, demo otomatis, panduan, laporan PDF |
| `dataset/` | 17 berkas uji beserta ground truth. Lihat [dataset/README.md](dataset/README.md) |
| `ai-service/` | Mesin analisis PRAMANA berbasis FastAPI, OpenCV, dan Tesseract |
| `tools/dataset/` | Pembangkit dataset: render lembar di Chromium, lalu efek pindai dan manipulasi di Python |
| `tests/alur.test.js` | Uji alur dari masuk sampai unduh PDF, termasuk layar ponsel |

Demo web publik masih membaca temuan dari ground truth dataset (`dataset/manifest.js`).
Mesin analisis nyata berada di `ai-service/` dan terhubung ke `backend/` melalui
Contract B; ia tidak dijalankan oleh halaman statis demo.

## Menjalankan secara lokal

Tidak ada build step. Cukup layani foldernya:

```bash
python3 -m http.server 8899
```

Lalu buka <http://localhost:8899>.

## Menguji

```bash
npm i playwright && npx playwright install chromium
node tests/alur.test.js
```

Tambahkan `TARGET_URL=https://pramana-flax.vercel.app/` untuk menguji hasil deploy.

## Batasan

- Seluruh data **sintetis**: nama, nomor kartu, SEP, rumah sakit, dan dokter semuanya fiktif. Tidak ada data peserta JKN yang nyata.
- Tampilan aplikasi verifikasi internal BPJS tidak tersedia untuk publik. Bingkai aplikasi di sini mengikuti bahasa desain JKN Drive v2 yang halaman masuknya publik, dan tidak memakai logo resmi BPJS Kesehatan.
- Sistem memberi prioritas pemeriksaan beserta alasannya, bukan penetapan kecurangan. Penetapan tetap wewenang Tim Pencegahan dan Penanganan Kecurangan JKN sesuai Permenkes 16/2019.
