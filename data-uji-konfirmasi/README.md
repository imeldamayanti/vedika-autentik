# Data uji Vedika Autentik: konfirmasi suara

Data ini dipakai untuk menguji tiga bagian sistem: indikator (F1), panggilan AI dan pembaca jawaban (F3–F4), serta kartu bukti dan ringkasan RS (F5). Setiap berkas punya hasil yang diharapkan, jadi lulus atau gagal bisa dicek tanpa menebak.

## Mana yang nyata, mana yang sintetis

| Bagian | Asal |
|---|---|
| Sebaran jumlah sesi rehab per bulan | Nyata, agregat dari Data Sampel Reguler Edisi 2025 (kunjungan 2024, poli IRM, 47.049 bulan-pasien). Lihat `distribusi_sesi_panitia.csv`. Tidak ada baris peserta riil. |
| Nama peserta, RS, nomor HP, tanggal sesi | Sintetis. Nomor HP memakai awalan 0800 yang tidak bisa ditelepon. |
| Pola curang di RS Melati Sehat (RS01) | Sintetis, disisipkan sengaja: 35% bulan-pasien ditambah sesinya menjadi 9–12, sebagian di hari Minggu atau libur. |
| 8 pasien skenario (S1–S8) | Sintetis, ditulis manual untuk pengujian. |
| Riwayat panggilan sebelum demo | Sintetis, ditandai `sintetis-riwayat`. |

## Berkas

| Berkas | Isi | Dipakai oleh |
|---|---|---|
| `rumah_sakit.csv` | 5 RS fiktif | Imelda |
| `peserta.csv` | 408 peserta, termasuk kontak keluarga untuk usia ≥60 atau <13 | Imelda, Zahra |
| `klaim_sesi.csv` | 4.913 klaim sesi rehab, Maret–Agustus 2026 | Zahra (indikator), Imelda (tampilan) |
| `libur_nasional_2026.csv` | Daftar libur yang dipakai indikator I4 (parsial, cukup untuk data uji) | Zahra |
| `expected_indikator_2026-08.csv` | Hasil indikator yang benar untuk 300 pasien aktif Agustus | Uji F1 |
| `riwayat_panggilan_2026-08.json` | 4 panggilan yang dianggap sudah terjadi sebelum demo | Imelda (isi awal database) |
| `skenario_uji.json` | 8 skenario: naskah penguji, perilaku AI wajib, jawaban dan label yang diharapkan | Uji F3–F5 |
| `transkrip_uji/S*.txt` | Contoh transkrip per skenario, untuk menguji pembaca jawaban tanpa menelepon | Zahra |
| `expected_ringkasan_rs.json` | Status tiap RS sebelum skenario dan setelah tiap skenario | Uji F5 |
| `kunci_kebenaran_2026-08.csv` | Jumlah sesi yang sebenarnya terjadi. **Hanya untuk penguji, tidak boleh dibaca sistem.** | Penguji |
| `tools/aturan.py` | Aturan referensi: indikator, label, status RS | Zahra, Imelda |
| `tools/generate.py` | Pembangkit data (deterministik) | — |
| `tools/uji.py` | Pemeriksa keluaran aplikasi | Semua |

## Skenario

| ID | Pasien | RS | Ditagih | Sebenarnya | Indikator | Hasil yang diharapkan |
|---|---|---|---|---|---|---|
| S1 | Andi Pratama, 54 | RS Melati Sehat | 11 | 3 | I1, I2, I4 | Tidak sesuai, bukti disimpan |
| S2 | Siti Rahmawati, 67 (dijawab anak) | RS Melati Sehat | 10 | 2 | I1, I2, I3, I4 | Tidak sesuai + tanda bahaya tanda tangan |
| S3 | Budi Santoso, 45 | RSU Bakti Mulia | 9 | 9 | I1, I3 | Sesuai, kasus ditutup |
| S4 | Karti Lestari, 72 (dijawab anak) | RS Melati Sehat | 9 | 6 | I1, I2, I4 | Tidak yakin, tidak dihitung |
| S5 | Joko Prasetyo, 39 | RS Cempaka Asri | 10 | 10 | I1, I2, I4 | Tidak terhubung, chat WA dikirim |
| S6 | Slamet Riyadi, 58 (bahasa santai) | RS Melati Sehat | 8 | 2 | I2, I4 | Tidak sesuai |
| S7 | Rina Marlina, 41 | RSU Nusa Sejahtera | 4 | 4 | I3 saja | Tidak ditelepon |
| S8 | Hendra Wijaya, 50 (curiga penipuan) | RS Kenanga Medika | 10 | 10 | I1, I3 | Menolak, tidak dihitung |

Ringkasan RS: RS Melati Sehat berstatus Normal sebelum skenario (2 tidak sesuai dari 4 terjawab). Setelah S1 menjadi **Perlu klarifikasi RS** (3 dari 5). RS lain tetap Normal. Persentase pasien terpicu di Agustus: RS Melati 39,7%, RS lain 0–1,8%.

## Cara menguji

```bash
python3 tools/uji.py indikator                       # aturan referensi = expected
python3 tools/uji.py indikator keluaran_app.csv      # keluaran indikator aplikasi
python3 tools/uji.py jawaban keluaran_pembaca.json   # keluaran pembaca jawaban
```

Untuk panggilan sungguhan, ganti `${NOMOR_PENGUJI}` di `skenario_uji.json` lewat konfigurasi `.env` dengan nomor HP anggota tim yang memerankan penerima. Penguji membaca `naskah_penguji` dan menjawab sesuai naskah. Skenario dinyatakan lulus jika label, field kunci, dan bukti yang tersimpan sama dengan yang diharapkan.

## Skema keluaran pembaca jawaban

```json
{
  "status_panggilan": "terjawab | tidak_terhubung | menolak",
  "penerima": "peserta | keluarga | null",
  "hubungan": "anak | orang tua | pasangan | null",
  "hadir": true,
  "jumlah_min": 3,
  "jumlah_maks": 3,
  "keyakinan": "tinggi | rendah | null",
  "tanda_bahaya": ["tanda_tangan_tanpa_layanan", "diminta_membayar", "layanan_berbeda"],
  "membantah_tanggal_libur": true,
  "kutipan_kunci": "kalimat asli penerima yang paling penting",
  "ringkasan": "satu kalimat"
}
```

## Membangkitkan ulang

```bash
python3 tools/generate.py
```

Hasilnya selalu sama karena seed-nya tetap (2026).
