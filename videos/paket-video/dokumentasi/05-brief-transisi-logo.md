# Brief: transisi video → logo + animasi logo

Untuk dikerjakan di chat lain. Bagian paling bawah berisi **prompt siap tempel**. Video final tidak dibuat di chat ini.

## Konteks
- Posisi: antara **H2** (klip AI Imelda termenung, gelap dan hangat, berakhir di detik 10.8) dan **H3** (kartu logo, 5.9 detik). Setelah H3 langsung masuk walkthrough W1 (jendela putih-mint).
- Narasi H3 (suara Arunika, 5.1 dtk): “Vedika Autentik. Teman verifikator untuk memeriksa keaslian berkas klaim.”
- Emosi yang dibutuhkan: dari pertanyaan yang menggantung (“siapa yang menjamin berkasnya asli?”) menjadi jawaban yang tenang dan meyakinkan. Bukan ledakan, bukan efek heboh.
- Yang sekarang ada di H3 (membosankan): logo muncul membesar sedikit, wordmark naik, garis oranye memanjang, lalu diam. Pembukanya cuma dip gelap 0,1 detik.

## Spesifikasi
- 1920×1080, 30 fps. Durasi H3 ±5.9 dtk (berubah kalau suara berubah), jadi animasi masuk ±2,5 dtk lalu **hold** yang bisa dipanjangkan atau dipendekkan.
- Palet (dari PPT tim): teal gelap `#0F3D3E`, teal terang untuk cahaya `#145558`, teal sangat gelap `#082A2B`, oranye `#F26B21`, emas titik logo `#F3B441`, putih, mint `#EAF3F1`.
- Font wordmark: **Poppins 700**, 150 px, letter-spacing −0,03em, dua baris “Vedika / Autentik”.
- Latar H3 sekarang: radial gradient `#145558` → `#0F3D3E` (62%) → `#082A2B`, pusat di 50% 45%.

## Geometri logo (SVG, viewBox 0 0 48 48)
```svg
<path fill="#fff" d="M5 5h13l6 26-5 11L5 11V5Z"/>            <!-- sayap kiri -->
<path fill="#fff" d="M43 5H30l-6 26 5 11L43 11V5Z"/>          <!-- sayap kanan -->
<circle cx="24" cy="33" r="3.4" fill="#F3B441" stroke="#0F3D3E" stroke-width="1.5"/> <!-- titik emas, ujung "pena" -->
```
Dua sayap membentuk huruf V dengan titik emas di ujung bawah, seperti ujung pena sekaligus tanda “terverifikasi”. Konsep animasi memanfaatkan itu: **dua sayap bertemu, titik emas “menandai” keaslian**.

## Konsep yang direkomendasikan: “Pindai lalu kunci”
Nyambung ke fitur (memindai berkas) dan ke narasi (keaslian). Ada dua opsi lain di bawah kalau mau.

### Beat per detik (t = 0 saat kartu logo mulai; negatif = akhir klip H2)
| Waktu | Apa yang terjadi |
|---|---|
| −0,6 → 0 | Akhir H2: kamera tetap mendorong pelan, warna perlahan memudar ke hangat-gelap, vignette menutup. Whoosh pendek naik. |
| 0 → 0,5 | **Garis pindai**: garis oranye tipis (6 px, glow lembut) menyapu dari kiri ke kanan. Di belakang garis, frame video berubah jadi teal (tint + turun kontras), sehingga video “terpindai” menjadi latar logo. |
| 0,5 → 0,8 | Jeda sunyi sangat singkat. Hanya dengung bas rendah. |
| 0,8 → 1,4 | **Sayap logo**: sayap kiri masuk dari x −160, sayap kanan dari +160 (sedikit miring, ease out cepat). Bertemu di tengah dengan benturan kecil (skala 1 → 1,04 → 1). Kilatan putih 2 frame. |
| 1,3 → 1,7 | **Titik emas jatuh** ke ujung V seperti stempel: skala 0 → 1,3 → 1, lalu satu cincin tipis (stroke emas) memuai dan memudar. **Sting logo jatuh tepat di sini.** |
| 1,5 → 2,2 | Wordmark: “Vedika” lalu “Autentik” naik dari masker (30 px, stagger 0,12 dtk). |
| 2,1 → 2,7 | Garis oranye menarik dari kiri ke kanan (0 → 260 px). |
| 2,7 → akhir | **Hold hidup**: glow radial “bernapas” pelan, logo melayang 4 px naik-turun, satu kali kilau lewat di wordmark sekitar t = 3,5. Tidak ada yang statis total. |
| akhir −0,3 | Whoosh ke W1 (sudah ada di komposisi). |

Easing: masuk cepat dan keluar halus (`power3.out`, `back.out(1.5)` hanya untuk titik emas). Hindari bounce berlebihan.

### Sinkron dengan narasi
Suara H3 sekarang mulai 0,3 detik setelah kartu masuk, jadi “Vedika Autentik” terucap sebelum logo selesai. Sebaiknya **mulai suara H3 di t ≈ 1,2** (saat sayap bertemu), supaya nama disebut tepat ketika logo terkunci. Itu cukup mengubah `LEAD` untuk adegan H3 di `skrip/build.py`; bilang kalau mau gue yang ubah.

### Opsi lain
- **B. Iris dari titik emas:** frame video menyusut ke satu lingkaran emas di tengah, lalu lingkaran itu melebar jadi latar teal dan titik menjadi bagian logo. Lebih dramatis, cocok kalau mau momen “aha”.
- **C. Sayap V sebagai tirai:** dua bentuk sayap besar (skala layar) menutup frame dari kiri dan kanan, bertemu di tengah membentuk V raksasa, lalu mengecil jadi logo. Lebih tegas dan grafis.

## Format keluaran yang berguna
1. **Komponen HTML + GSAP (paling cocok dengan proyek ini)**: satu berkas HTML dengan timeline GSAP `paused`, seekable, tanpa `Math.random` atau `Date.now`, memakai ID `h3` dan durasi yang bisa diatur. Bisa langsung ditaruh menggantikan kartu H3 di `skrip/index.template.html`.
2. Alternatif: klip mp4 1920×1080 30 fps **dengan 1,5 detik awal berupa transisi dari frame terakhir H2** (kirim bersama `aset/video-ai/h2.mp4` sebagai referensi frame akhir), atau webm/ProRes 4444 transparan untuk animasi logonya saja.

## Yang jangan dilakukan
- Efek ala slide PPT (terbang masuk dari tepi layar, putar 3D, glow neon berlebihan).
- Menambah teks lain selain “Vedika Autentik”. Slogan baru muncul di penutup.
- Mengubah bentuk logo atau warnanya.

## Aset referensi di paket ini
`aset/logo/veritas-mark.svg`, `aset/video-ai/h2.mp4` (klip sebelum transisi), `aset/sfx-musik/sting.wav` dan `whoosh.wav` (suara yang sudah ada), `suara-final/h3.wav` (narasi H3), `storyboard.html` bagian H2 dan H3.

---

## Prompt siap tempel (chat lain)

> Buatkan transisi dan animasi logo untuk video promo 1920×1080, 30 fps, sebagai **satu berkas HTML dengan timeline GSAP seekable (`gsap.timeline({ paused: true })`)**, tanpa `Math.random` atau `Date.now`.
>
> **Konteks:** transisi dari klip video (Imelda termenung di meja makan, nuansa hangat-gelap) ke kartu logo “Vedika Autentik” berdurasi ±6 detik. Setelah itu video lanjut ke rekaman layar. Narasi: “Vedika Autentik. Teman verifikator untuk memeriksa keaslian berkas klaim.” Mood: pertanyaan yang menggantung berubah jadi jawaban yang tenang dan meyakinkan, bukan heboh. Gaya promo bersih, bukan animasi ala PPT.
>
> **Logo (SVG viewBox 0 0 48 48):** sayap kiri `M5 5h13l6 26-5 11L5 11V5Z`, sayap kanan `M43 5H30l-6 26 5 11L43 11V5Z` (putih), titik emas `circle cx=24 cy=33 r=3.4 fill=#F3B441 stroke=#0F3D3E stroke-width=1.5`. Wordmark “Vedika / Autentik” Poppins 700, 150 px, letter-spacing −0,03em, putih. Garis aksen oranye `#F26B21`. Latar teal radial `#145558` → `#0F3D3E` → `#082A2B`. Jangan ubah bentuk atau warna logo.
>
> **Konsep “Pindai lalu kunci”, beat (t=0 saat kartu logo mulai):**
> - −0,6 → 0: akhir klip, vignette menutup, warna memudar hangat-gelap.
> - 0 → 0,5: garis pindai oranye 6 px dengan glow menyapu kiri → kanan; di belakangnya frame video menjadi tint teal dan jadi latar logo.
> - 0,5 → 0,8: jeda sunyi singkat.
> - 0,8 → 1,4: dua sayap logo masuk dari x −160 dan +160, bertemu di tengah dengan benturan kecil (skala 1 → 1,04 → 1) dan kilatan putih 2 frame.
> - 1,3 → 1,7: titik emas jatuh seperti stempel (skala 0 → 1,3 → 1) disertai satu cincin emas tipis memuai dan memudar. Beri penanda waktu di sini untuk sting audio.
> - 1,5 → 2,2: wordmark “Vedika” lalu “Autentik” naik dari masker 30 px, stagger 0,12 dtk.
> - 2,1 → 2,7: garis oranye memanjang 0 → 260 px.
> - 2,7 → akhir: hold yang hidup (glow radial bernapas, logo melayang 4 px, satu kilau lewat sekitar t=3,5). Durasi hold harus bisa diatur.
>
> Easing masuk cepat, keluar halus (`power3.out`; `back.out(1.5)` hanya untuk titik emas). Hindari efek terbang masuk dari tepi, putar 3D, dan neon. Jangan tambah teks lain.
>
> **Keluaran:** satu HTML mandiri (root `data-composition-id`, timeline didaftarkan di `window.__timelines`), parameter durasi total dan waktu mulai, plus daftar waktu penanda untuk SFX (whoosh, sting). Beri juga dua varian pendek: (B) iris dari titik emas, (C) sayap V besar sebagai tirai.
