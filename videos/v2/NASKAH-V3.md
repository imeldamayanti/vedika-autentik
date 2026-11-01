# Naskah VO v3 (sudut pandang verifikator, maks 1:30)

Perubahan dari v2: hook tetap cerita Imel, lalu satu adegan baru (H2B) soal beban verifikator,
jembatan "Karena itu, hadirlah Vedika Autentik", dan semua penjelasan fitur memakai "Anda" = verifikator.
Daftar langkah pemeriksaan di produk ada 7 (data.js `langkah()`), bukan 8.

| id  | naskah |
|-----|--------|
| h1  | Bapak bilang, waktu rehabilitasi dulu, petugasnya yang tanda tangan sendiri. |
| h2  | Berkasnya tampak lengkap. Tapi siapa yang memastikan berkasnya asli? |
| h2b | Setiap hari, verifikator BPJS memeriksa berkas yang terus menumpuk. Mustahil teliti satu per satu. Akhirnya, yang janggal bisa lolos. |
| h3  | Karena itu, hadirlah Vedika Autentik. Teman kerja untuk Anda, para verifikator, memeriksa keaslian berkas klaim. |
| w1  | Anda tak perlu lagi memeriksa semuanya manual. Cukup unggah berkas di tab Autentik. Satu klik, tujuh langkah pemeriksaan berjalan sekaligus. |
| w2  | Pertama, kualitas scan. Kalau buram, cukup minta scan ulang, tanpa menuduh siapa pun. |
| w3  | Hasilnya berlabel jelas: lolos, perlu dicek, atau prioritas. Yang paling mendesak selalu di atas. |
| w4  | Buka satu berkas, buktinya langsung terlihat. Angka lima sesi yang diubah jadi delapan, ditandai tepat di tempatnya. |
| w5  | Berkas yang dipakai ulang untuk pasien lain? Disandingkan, kembarannya langsung ketahuan. |
| w6  | Untuk berkas prioritas, tanyai peserta langsung lewat WhatsApp resmi BPJS. Satu balasan, dan Anda tahu yang sebenarnya. |
| w7  | Sistem hanya menyarankan. Keputusan akhir tetap di tangan Anda, lengkap dengan alasan tertulis. |
| z1  | Memeriksa lebih tenang, memutuskan lebih adil. Vedika Autentik. Lengkap belum tentu asli. |

## Setelan ElevenLabs (anti-berita)

- Arunika = "National TV Voice Over", makanya terdengar seperti pembaca berita. Ganti voice.
- Kandidat suara percakapan (semua `language: id`): Velora (conversational), Anjani, Luna, Honeypie.
- Model `eleven_multilingual_v2`: stability 0.35, style 0.45, speed 1.05. Stability rendah = intonasi lebih hidup.
- Alternatif `eleven_v3` dengan tag seperti `[thoughtful]` dan `[warmly]` untuk emosi per kalimat.
- Sampel audisi: `videos/voice-samples/v3/`.
