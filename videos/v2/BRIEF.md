---
workflow: general-video
flow: companion
storyboard: yes
message: "Lengkap belum tentu asli — Vedika Autentik membantu verifikator memeriksa keaslian berkas klaim"
destination: slide 8 deck Healthkathon 2026 (QR dan tautan), gaya promo YouTube
aspect: 1920x1080
fps: 30
language: id
audience: juri Healthkathon 2026 dan verifikator klaim BPJS Kesehatan
length: ~80s
---

## Intent

Video demo "Vedika Autentik" dibuat ulang dari nol (komposisi baru, bukan tambalan `videos/demo`).
Konsep Richard: masalah cuma 5–10 dtk, langsung cara pakai dari sudut pandang verifikator,
gaya video promosi YouTube yang menjelaskan solusi ke pelanggan, sederhana, tanpa tech stack,
tanpa "AI slop" dan tanpa animasi ala PPT (bubble pop, blok highlight, chip, pill callout,
terbang-masuk dari tepi). Narasi menjadi jangkar timing.

Struktur tetap: H1 masalah → H2 pertanyaan → H3 logo/perkenalan → W1–W7 walkthrough
(unggah, cek scan, label, kartu bukti 5 jadi 8, berkas kembar, konfirmasi peserta, keputusan)
→ Z penutup logo + slogan "Lengkap belum tentu asli".

## Assets

- assets/video/h1-hd.mp4, h2-hd.mp4, z-hd.mp4 — klip PixVerse V6 (asal 1280x720, di-upscale lanczos ke 1080p). h2 tidak boleh digenerate ulang.
- assets/video/screen.mp4 — rekaman layar prototipe (transcode H.264 30 fps dari demo-screen.mp4) + screen.marks.json.
- assets/vo/*.wav — narasi final Arunika (ElevenLabs), 11 potongan. Naskah: videos/tools/vo.json (tidak diubah).
- assets/sfx/*.wav — SFX dan musik latar sintetis (bebas hak).
- assets/logo/veritas-mark.svg — logo V (geometri dipakai ulang inline).
- assets/fonts/Poppins-*.ttf — Poppins (OFL).

## Customizations

- Hook sinematik: grading hangat, letterbox, grain, vignette, push-in, potongan wide → close.
- Transisi H2 → H3 "Pindai lalu kunci" (brief 05): garis pindai oranye, dua sayap V bertemu, titik emas jatuh seperti stempel + cincin, wordmark naik dari masker, hold yang hidup. Suara H3 dan sting di t≈1,2 dtk dari awal adegan.
- Walkthrough: jendela prototipe di latar putih-mint, kamera virtual zoom/pan ke elemen yang disebut narasi, potongan di dalam adegan (jump cut) seperti diedit manusia.
- Garis pindai oranye = benang merah (H3, masuk demo, penutup).
- Subtitle Bahasa Indonesia dibakar, per kalimat.

## Notes

- Palet: teal #0F3D3E, hijau #0E7C3A, oranye #F26B21, navy #1B2D4F, mint #EAF3F1/#D3E3DF, abu #5B6B6A, emas titik logo #F3B441.
- Tag "Ilustrasi" di wajah hasil AI. Footer "Prototipe · data fiktif" di bagian demo.
- Jangan klaim angka dampak. Pakai "tanda/temuan/diduga", bukan vonis "curang".
- Storyboard HTML dulu, tunggu persetujuan user. Jangan render mp4 sebelum disetujui.
- Musik: sementara sintetis (bgm.wav). HeyGen belum login, MusicGen lokal belum terpasang.
