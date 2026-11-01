# Paket video demo Vedika Autentik

Semua yang dibutuhkan untuk mengecek, mengedit, dan membuat ulang video demo (±80 detik).

## Mulai dari sini
1. Buka **`storyboard.html`** di browser: frame per frame, lengkap dengan narasi, teks layar, audio, dan sumber aset.
2. Baca **`dokumentasi/`** secara berurutan:
   - `01-flow-video.md`: konsep (brief Richard), alur adegan, aturan gaya.
   - `02-naskah-vo.md`: naskah narasi per adegan, catatan pembacaan, setelan ElevenLabs.
   - `03-sumber-aset.md`: asal setiap aset, prompt video AI, rujukan fakta.
   - `04-cara-build-dan-render.md`: perintah untuk membangun ulang dan merender.
   - `05-brief-transisi-logo.md`: brief transisi dari video ke logo dan animasi logo (untuk dikerjakan di chat lain), termasuk prompt siap tempel.

## Isi folder
```
paket-video/
├─ 00-BACA-DULU.md
├─ storyboard.html          frame per frame untuk review
├─ dokumentasi/             flow, naskah VO, sumber aset, cara render
├─ aset/
│  ├─ video-ai/             h1, h2, z (PixVerse V6 via OpenArt)
│  ├─ gambar-sumber/        frame6–9 (gambar awal video AI)
│  ├─ rekaman-layar/        rekaman prototipe + penanda waktu klik
│  ├─ sfx-musik/            klik, whoosh, ding, sting, musik latar
│  └─ logo/                 veritas-mark.svg
├─ skrip/                   build, rekam, sintesis SFX, ElevenLabs, naskah vo.json
├─ suara-final/             narasi final Arunika, 11 potongan (wav + mp3)
└─ suara-contoh/            contoh 8 voice wanita Indonesia (ElevenLabs)
```

## Status
- Selesai: struktur dan timing, rekaman layar dengan highlight, video AI (3 klip), SFX dan musik latar, suara Arunika, storyboard HTML.
- Sedang dikerjakan di chat lain: transisi video → logo dan animasi logo (brief di `dokumentasi/05-brief-transisi-logo.md`).
- Belum: render mp4 final.
- Keputusan terbuka: naskah VO disetujui Richard?, avatar tim di penutup (sekarang dibuang sesuai brief), musik latar berlisensi (sekarang sintetis).

Proyek yang dirender: `videos/demo` (jangan dipindah; skrip di `skrip/` hanya salinan dari `videos/tools`).
