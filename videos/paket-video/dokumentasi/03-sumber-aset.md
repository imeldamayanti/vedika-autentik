# Sumber aset

Semua aset yang dipakai di video, dari mana asalnya, dan cara membuatnya ulang.

## Ringkasan

| Aset | File di folder ini | Asal | Dibuat dengan | Biaya |
|---|---|---|---|---|
| Gambar meja makan (4 frame bersih, tanpa teks) | `aset/gambar-sumber/frame6.jpg`, `frame7.jpg`, `frame8.jpg`, `frame9.jpg` | Dikirim tim (versi bersih dari gambar di slide cerita) | Tim | – |
| Video AI hook 1 | `aset/video-ai/h1.mp4` | Dari `frame7.jpg` | OpenArt, PixVerse V6 image-to-video, 720p, 5 dtk, tanpa audio | 70 kredit |
| Video AI hook 2 | `aset/video-ai/h2.mp4` | Dari `frame9.jpg` | OpenArt, PixVerse V6, sama | 70 kredit |
| Video AI penutup | `aset/video-ai/z.mp4` | Dari `frame6.jpg` | OpenArt, PixVerse V6, sama | 70 kredit |
| Rekaman layar prototipe | `aset/rekaman-layar/demo-screen.mp4` + `demo-screen.marks.json` | Prototipe di repo (`index.html`, `app.js`) | Skrip `skrip/record-demo.mjs` (puppeteer, Chrome headless, 1920×1080) | – |
| Efek suara | `aset/sfx-musik/click, tick, whoosh, ding, sting.wav` | Disintesis | `skrip/make-sfx.py` (ffmpeg) | – |
| Musik latar | `aset/sfx-musik/bgm.wav` | Disintesis (pad akor lambat) | `skrip/make-sfx.py` | – |
| Logo | `aset/logo/veritas-mark.svg` | Repo (`assets/veritas-mark.svg`) | Tim | – |
| Font Poppins | (diunduh otomatis saat render) | Google Fonts | – | – |
| Suara narasi | `suara-final/*.wav`, `*.mp3` | ElevenLabs, voice Arunika (`o5s6XRBkPSTD4syv6mZg`, model `eleven_multilingual_v2`) | `skrip/elevenlabs-vo.mjs` | kredit kecil (±650 karakter) |
| Contoh suara 8 voice wanita | `suara-contoh/*.mp3` | Preview resmi ElevenLabs Voice Library | – | – |

## Video AI: prompt dan jejak generate

Akun: OpenArt (akun kantor medroyale), project default. Model `pixverseV6`, mode `image2video`, 720p, durasi 5 dtk, `generateAudio: false`. Gambar awal diunggah sebagai referensi.

| Klip | Gambar awal (upload id) | History id | Prompt |
|---|---|---|---|
| h1 | frame7 (`uq0p9aSNCmR9CbG7oj9m`) | `oaZB8JfXBAhqmJy8zukh` | Cinematic, realistic, warm dim Indonesian dining room at night. The middle-aged man in a batik shirt talks earnestly to the woman across the table, small natural head tilt and one hand gesture, subtle blinks and breathing. The woman listens with her chin resting on her hand, barely moving. Very slow, steady camera push-in. Natural motion only, consistent faces, no morphing, no text, no extra people. |
| h2 | frame9 (`EGNO0JML0jjRR1OMNWFY`) | `IlM4a2HbFr06SdIImeRH` | Cinematic, realistic, warm dim dining room at night. The woman in the foreground stares down thoughtfully, slowly breathes in, her fingers resting at her lips, a faint worried blink. The man in the soft-focus background turns his head slightly toward her. Very slow gentle camera push-in. Natural subtle motion only, consistent faces, no morphing, no text, no extra people. |
| z | frame6 (`sdwvjezr0Af4KpKiBl7z`) | `pcG0mXNWQACaNeDf3giH` | Cinematic, realistic, warm golden Indonesian dining room at night. The man and the woman smile at each other with relief and share a soft laugh, he lifts his fork to eat, she tilts her head. Gentle lamp glow, calm relaxed mood. Slow smooth camera drift. Natural subtle motion only, consistent faces, no morphing, no text, no extra people. |

Catatan kualitas: wajah konsisten dengan gambar asal dan gerak natural. Di h2 ekspresi Imelda agak dramatis di tengah klip; diputuskan tidak diulang. Wajah hasil AI diberi tag “Ilustrasi” di video.

## Rekaman layar
- Sumber: prototipe lokal (`python3 -m http.server 8765` dari root repo, lalu buka `index.html`). Data fiktif, berkas dari `dataset/`.
- Alur yang direkam: masuk sebagai verifikator demo, tutup panduan, Autentik → Jalankan demo, antrean berlabel, kartu bukti VA-DST-01 (5 jadi 8), VA-KMB-01 (berkas kembar), konfirmasi peserta (jawab “2 · Tidak pernah”), Setujui saran.
- `demo-screen.marks.json` menyimpan waktu mulai tiap adegan (`w1`…`w7`) dan waktu setiap klik (`klik`), dipakai untuk memotong klip dan menaruh suara klik.
- Highlight (kursor besar, ripple klik, cincin oranye) digambar langsung di halaman saat merekam, jadi selalu pas dengan elemen aslinya.

## Fakta dan rujukan yang dipakai di video
- Cerita Bapak dan Imelda adalah cerita pribadi tim; hanya dipakai sebagai hook singkat.
- Tidak ada angka statistik di video final (kartu temuan KPK 75,3% dibuang karena sudah ada di slide). Kalau suatu saat dipakai lagi: 3.269 dari 4.341 klaim fisioterapi di tiga RS swasta diduga fiktif tanpa rekam medis, Rp501,27 juta, Juli 2017–Juni 2018, diumumkan KPK 24 Juli 2024. Angka “2 sesi terjadi, 10 ditagih” **tidak terverifikasi** dan tidak dipakai.
- Semua nama, nomor kartu, SEP, dan rumah sakit di prototipe fiktif.

## Lisensi dan izin
- SFX dan musik latar disintesis sendiri, bebas hak cipta. Ganti musik dengan lagu berlisensi kalau ada.
- Video AI dibuat di akun OpenArt kantor atas persetujuan; cek izin pemakaian materi untuk lomba bila perlu.
- Preview suara ElevenLabs hanya untuk mendengarkan; suara final dibuat dari voice yang ditambahkan ke akun.
