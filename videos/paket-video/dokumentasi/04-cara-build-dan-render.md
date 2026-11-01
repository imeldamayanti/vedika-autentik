# Cara membangun dan merender

Proyek HyperFrames yang dirender ada di `videos/demo` (di luar folder paket ini). Skrip di `skrip/` adalah salinan dari `videos/tools`. Semua perintah dijalankan dari root repo.

## 1. Generate suara ElevenLabs (jalankan sendiri di Terminal)
Kunci API tidak boleh masuk chat atau file. Isi lewat environment:

```bash
ELEVENLABS_API_KEY=isi_kunci ELEVENLABS_VOICE_ID=isi_voice_id node videos/tools/elevenlabs-vo.mjs
```

Membuat ulang sebagian saja: tambahkan `ONLY=h1,w3` di depan perintah. Hasil: `videos/demo/assets/vo/*.wav` dan `videos/tools/vo-durations.json`.

## 2. Bangun ulang komposisi
```bash
python3 videos/tools/build.py
```
Menghitung timing dari durasi suara, memotong klip rekaman layar, membuat klip hook dan penutup dari video AI di `videos/demo/assets/gen`, menaruh SFX di waktu klik, dan menulis `videos/demo/index.html`.

## 3. Cek dan lihat frame
```bash
cd videos/demo && npm run check
npx hyperframes snapshot --at 5,15,30,60,75 --no-end
```
Storyboard HTML dibuat dari snapshot dengan `python3 videos/tools/make-storyboard.py`.

## 4. Render (setelah storyboard disetujui)
```bash
cd videos/demo && npm run render
```
Hasil di `videos/demo/renders/`. Format 1920×1080, 30 fps.

## Merekam ulang layar (kalau UI prototipe berubah)
```bash
python3 -m http.server 8765 &      # dari root repo
node videos/tools/record-demo.mjs videos/raw/demo-screen.mp4
```

## Membuat ulang SFX dan musik
```bash
python3 videos/tools/make-sfx.py
```

## Mengganti musik latar
Taruh file `bgm.wav` (durasi ≥ video) di `videos/demo/assets/sfx/`, lalu jalankan `build.py` lagi.
