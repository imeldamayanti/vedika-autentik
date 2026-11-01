# Bukti lisensi audio video demo v3

Dibuat 2026-11-01 oleh `videos/tools/make-audio-v3.py` (seed acak tetap 31102026, hasil bisa direproduksi).

## SFX dan backsound
- Seluruhnya **disintesis dari rumus** (sinus, derau, filter) di skrip. Tidak memakai sampel, loop, atau materi pihak ketiga.
- Hak cipta dipegang tim Veritas. Dilepas sebagai **CC0** (domain publik), bebas dipakai dan disebarkan tanpa atribusi.
- Tanpa vokal. Parameter musik: 115 BPM, bar 2.087 dtk, drop 18.78 dtk, build 77.22 dtk, hit 83.48 dtk, durasi 87.48 dtk.
- Cara buat ulang: `python videos/tools/make-audio-v3.py --drop 18.54 --build 77.08 --hit 83.39 --end 88.21`

## Audio telepon S1 (`call/s1-hook.wav`, `call/s1-qa.wav`)
- Dari `assets/rekaman/S1/` (satu berkas per baris transkrip), diberi EQ telepon (320-3400 Hz).
- `s1-hook.wav`: baris 06 (jawaban "Tiga kali. Awal bulan, ..."), 0-3,40 dtk. `s1-qa.wav`: baris 05 (tanya jumlah) + 0-0,62 dtk baris 06 ("Tiga kali.").
- Sumber: rekaman **simulasi dari suara buatan ElevenLabs**, bukan suara orang sungguhan (sudah diberi keterangan itu di aplikasi).

## VO
- ElevenLabs (suara Velora v3). Lisensi mengikuti paket akun ElevenLabs yang dipakai tim saat generate. Isi paket dan tanggal generate dicatat setelah VO dibuat.

## Checksum (sha256, 16 karakter pertama)
| File | sha256 |
|---|---|
| `call/s1-hook.wav` | 781b490d5cdee1fa |
| `call/s1-qa.wav` | 7dd8e717cf60b484 |
| `music/bgm.wav` | 8f0f6e6f9b65e5b2 |
| `sfx/click.wav` | aa591ab0ec431107 |
| `sfx/ding.wav` | 0c2d312c4b0f05a4 |
| `sfx/hit.wav` | dbd7132902d7135b |
| `sfx/pop.wav` | 8c2b48568ccacc84 |
| `sfx/ring2x.wav` | 25ef38266120d48e |
| `sfx/riser.wav` | 720d2def7fc6ae3e |
| `sfx/stamp.wav` | edf0d995499edf45 |
| `sfx/thud.wav` | 9a9139c278a6e525 |
| `sfx/tick.wav` | 4cde4559faa35350 |
| `sfx/whoosh.wav` | b7dfe22617113e33 |
