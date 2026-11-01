#!/usr/bin/env python3
"""Buat videos/v2/storyboard.html dari snapshot komposisi (snapshots/sb) dan tools/timing.json.

Snapshot diambil dulu:
  cd videos/v2 && npx hyperframes snapshot --at <daftar waktu di SCENES> --no-end --describe false -o snapshots/sb
Lalu:  python3 videos/v2/tools/make_storyboard.py
"""
import base64
import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent
TM = json.loads((ROOT / "tools/timing.json").read_text())
VO = json.loads((REPO / "videos/tools/vo.json").read_text())
SNAP = ROOT / "snapshots/sb"
OUT = ROOT / "storyboard-frames"
OUT.mkdir(exist_ok=True)

snaps = {}
for p in SNAP.glob("frame-*-at-*s.png"):
    t = float(re.search(r"-at-([\d.]+)s\.png$", p.name).group(1))
    snaps[t] = p


def frame(t):
    src = snaps[min(snaps, key=lambda k: abs(k - t))]
    dst = OUT / f"f{t:05.1f}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale=1280:-1", "-q:v", "3", str(dst)], check=True)
    return "data:image/jpeg;base64," + base64.b64encode(dst.read_bytes()).decode()


def mmss(x):
    return f"{int(x // 60)}:{x % 60:04.1f}"


T = TM["T"]
FONT = {w: "data:font/ttf;base64," + base64.b64encode((ROOT / f"assets/fonts/Poppins-{w}.ttf").read_bytes()).decode()
        for w in ("Regular", "Medium", "SemiBold", "Bold")}
# (kode, judul, adegan di timing, [(waktu snapshot, keterangan)], visual, teks layar, gerak, audio, sumber)
SCENES = [
    ("H1", "Hook 1 · Masalah", "h1",
     [(1.5, "Wide: Bapak bercerita, push-in pelan"), (4.2, "Potong ke close Bapak (punch-in 1,34×)")],
     "Video AI meja makan malam. Grading hangat-redup (muted editorial + suhu hangat), vignette, grain halus, letterbox 2.39:1.",
     "Subtitle putih besar tanpa kotak di atas bar bawah. Tag kecil “ILUSTRASI” di kanan atas.",
     "Fade dari hitam 0,9 dtk, bar letterbox mengecil ke posisi. Shot A push-in 1,04→1,13 (0–3,05 dtk), lalu potong ke shot B lebih dekat ke wajah Bapak dari bagian klip yang berbeda (ritme potongan, bukan satu klip polos).",
     "Narasi h1 mulai 0,55 dtk. Musik latar masuk 1,4 dtk lalu di-carve di bawah narasi.",
     "assets/video/h1-hd.mp4 (PixVerse V6 dari frame7, upscale 1080p)"),
    ("H2", "Hook 2 · Pertanyaan", "h2",
     [(7.0, "Lebur 0,45 dtk ke Imelda termenung"), (9.8, "“Tapi…”: potong ke close wajah"), (11.25, "Garis pindai oranye menyapu, frame jadi teal")],
     "Video AI Imelda termenung, Bapak buram di belakang. Grading sama dengan H1.",
     "Subtitle per kalimat: “Berkasnya tampak lengkap.” lalu “Tapi siapa yang menjamin berkasnya asli?”. Tag “ILUSTRASI”.",
     "H1→H2 lebur dengan sedikit blur (bukan potong keras). Jeda sebelum “Tapi…” dipakai untuk potong ke close-up wajah, push-in makin pelan. 0,6 dtk terakhir: eksposur turun, bar letterbox menutup sedikit, lalu garis pindai oranye (6 px, glow) menyapu kiri→kanan; di belakang garis, frame berubah teal.",
     "Narasi h2 mulai 5,85 dtk. Whoosh halus di lebur H1→H2 dan whoosh naik menjelang pindai.",
     "assets/video/h2-hd.mp4 (dari frame9, tidak digenerate ulang)"),
    ("H3", "Perkenalan · Pindai lalu kunci", "h3",
     [(12.32, "Dua sayap V bertemu (t≈1,25), kilatan 2 frame"), (13.0, "Titik emas jatuh + cincin, wordmark naik"), (15.6, "Hold hidup: glow bernapas, logo melayang, satu kilau")],
     "Kartu teal radial (#145558→#0F3D3E→#082A2B), grid titik halus yang memudar ke tepi, glow bernapas. Logo V putih + titik emas, wordmark “Vedika / Autentik” Poppins 700 150 px, garis oranye 260 px.",
     "Hanya logo dan wordmark. Subtitle kalimat kedua: “Teman verifikator untuk memeriksa keaslian berkas klaim.” (kalimat “Vedika Autentik.” tidak dibuat subtitle karena sudah tampil sebagai logo).",
     "0–0,55 garis pindai; 0,8–1,25 sayap kiri dan kanan masuk dari samping (geser 14 unit + putar 7°, power3.out) lalu benturan kecil 1→1,04→1 dan kilatan putih 2 frame; 1,3–1,7 titik emas jatuh seperti stempel (back.out 1,5) + cincin emas memuai; 1,5–2,1 wordmark naik dari masker (stagger 0,12); 2,1–2,7 garis oranye memanjang; sisanya hold hidup (melayang 4 px, glow bernapas, satu kilau melintas di huruf sekitar t≈4,2). Keluar: garis pindai horizontal turun membuka jendela demo.",
     "Narasi h3 mulai tepat 1,2 dtk setelah kartu (saat sayap terkunci). Sting logo di 1,18 dtk, volume di bawah narasi.",
     "Geometri assets/logo/veritas-mark.svg (dibangun ulang inline sebagai SVG)"),
    ("W1", "Langkah 1 · Unggah berkas", "w1",
     [(18.3, "Jendela prototipe di latar mint"), (19.8, "Zoom ke tab Autentik dan zona unggah"), (21.5, "Potong ke tombol “Jalankan demo”, klik")],
     "Rekaman layar asli di jendela putih bersudut 22 px, bayangan lembut, latar mint #EAF3F1 dengan grid titik yang bergeser pelan.",
     "Label langkah “01 | Unggah berkas” (angka oranye, judul teal, tanpa kotak). Subtitle teal per kalimat. Footer “Prototipe · data fiktif”.",
     "Jendela muncul dari garis pindai lalu kamera mendorong ke sidebar Autentik + zona “Tarik berkas klaim ke sini” (still frame + gerak kamera). Potong ke close tombol, klik jatuh tepat sebelum “Satu klik”, lalu kamera mundur ke daftar pemeriksaan yang mulai berjalan.",
     "Narasi w1. Klik halus saat tombol ditekan. Whoosh saat jendela terbuka.",
     "assets/video/screen.mp4 (demo-screen 5,3–9,8 dtk) + still w1-still.png"),
    ("W2", "Langkah 2 · Cek kualitas scan", "w2",
     [(25.5, "Daftar langkah pemeriksaan berjalan"), (29.3, "Ringkasan: VA-BRM-01 berlabel Scan ulang")],
     "Rekaman layar: checklist “Terima berkas / Cek kualitas scan / Baca isi berkas…”, lalu berkas Dewi Lestari (scan buram) dan ringkasan hasil.",
     "“02 | Cek kualitas scan”. Subtitle: “Pertama, kualitas scan.” / “Scan yang buruk akan diminta scan ulang, tanpa penuduhan.”",
     "Potong whip (blur gerak 0,36 dtk) dari W1. Shot A zoom 1,9× ke checklist (rekaman dipercepat 1,5×). Shot B jump cut ke pemeriksaan VA-BRM-01 lalu kamera turun ke baris “Scan ulang” saat kalimat kedua.",
     "Narasi w2. Whoosh di potongan.",
     "screen.mp4 7,9–12,4 dtk dan 13,85–16,2 dtk"),
    ("W3", "Langkah 3 · Label otomatis", "w3",
     [(32.8, "Baris filter label dengan cincin sorot"), (37.2, "Antrean: Prioritas paling atas")],
     "Rekaman layar: filter Semua/Prioritas/Perlu dicek/Scan ulang/Lolos dan antrean berlabel.",
     "“03 | Label otomatis”. Subtitle per kalimat.",
     "Shot A: kamera di filter + kolom label saat “lolos, perlu dicek, atau prioritas”. Shot B: jump cut ke antrean, kamera naik pelan ke baris Prioritas teratas saat “Yang paling mendesak selalu di atas”; klik Semua dan klik nama Ratna Kusuma (jembatan ke W4).",
     "Narasi w3. Klik di filter dan saat membuka berkas.",
     "screen.mp4 18,1–22,0 dtk dan 22,3–24,85 dtk"),
    ("W4", "Langkah 4 · Kartu bukti (5 jadi 8)", "w4",
     [(40.5, "Kartu bukti Ratna Kusuma: kalimat temuan"), (46.5, "Zoom 2× ke baris 6–8 kosong + angka 8")],
     "Rekaman layar: kartu bukti VA-DST-01, sorotan merah di baris kosong dan kotak jumlah kunjungan.",
     "“04 | Kartu bukti”. Subtitle: “Buka satu berkas, buktinya langsung terlihat.” / “Angka lima sesi yang diubah jadi delapan, ditandai tepat di tempatnya.”",
     "Shot A: kamera di kepala kartu “Hanya 5 baris terisi, angka … diubah dari 5 menjadi 8”. Shot B: jump cut ke lembar yang sudah digulir, lalu dorong ke baris 6–8 yang disorot merah dan angka “8” tepat saat “ditandai tepat di tempatnya”.",
     "Narasi w4. Whoosh di potongan.",
     "screen.mp4 25,0–28,3 dtk dan 31,0–35,4 dtk"),
    ("W5", "Langkah 4b · Berkas kembar", "w5",
     [(48.3, "Kalimat temuan: lembar Bu Siti dipakai untuk Pak Budi"), (50.4, "Tarik mundur: dua lembar bersanding"), (52.6, "Dorong ke kolom tanda tangan kembar")],
     "Rekaman layar: VA-KMB-01, dua lembar disandingkan dengan cincin oranye dan sorotan merah.",
     "“04 | Berkas kembar”. Subtitle per kalimat.",
     "Satu shot dengan tiga gerak kamera mengikuti kata: close kalimat temuan → tarik mundur ke 1,08× saat “Disandingkan” → dorong ke kolom tanda tangan yang identik saat “kembarannya langsung ketahuan”.",
     "Narasi w5. Whoosh di potongan.",
     "screen.mp4 41,9–48,1 dtk"),
    ("W6", "Langkah 5 · Konfirmasi peserta", "w6",
     [(55.5, "Pesan WhatsApp resmi PANDAWA"), (58.6, "Jawaban “2 · Tidak pernah” diklik"), (61.6, "Panel: Jawaban peserta 2 · Tidak pernah")],
     "Rekaman layar: simulasi WhatsApp di ponsel + aturan pesan (lewat PANDAWA, tanpa tautan, tidak menyebut dugaan).",
     "“05 | Konfirmasi peserta”. Subtitle per kalimat.",
     "Shot A (0,8×): kamera dari ponsel bergeser ke aturan pesan saat “WhatsApp resmi BPJS”, lalu turun ke tombol jawaban; klik jatuh sebelum “Satu balasan”. Shot B: balasan masuk, kamera bergeser ke panel “Jawaban peserta” saat “Anda tahu yang sebenarnya”.",
     "Narasi w6. Klik saat memilih jawaban.",
     "screen.mp4 48,0–52,5 dtk dan 52,5–56,5 dtk"),
    ("W7", "Langkah 6 · Keputusan di tangan Anda", "w7",
     [(64.5, "Kartu Langkah yang disarankan"), (68.8, "Diteruskan + catatan alasan tertulis")],
     "Rekaman layar: kartu saran tindakan, tombol Setujui saran, status berubah “Diteruskan ke telaah lanjut” dengan catatan.",
     "“06 | Keputusan di tangan Anda”. Subtitle per kalimat.",
     "Kamera di kartu saran saat “Sistem hanya menyarankan”, klik Setujui di tengah kalimat kedua, lalu dorong ke kotak catatan saat “lengkap dengan alasan tertulis”.",
     "Narasi w7. Klik pada Setujui.",
     "screen.mp4 58,6–66,0 dtk"),
    ("Z", "Penutup · Logo dan slogan", "z",
     [(71.5, "Adegan hangat: Bapak dan Imelda tersenyum"), (73.7, "Garis pindai kembali (callback H3)"), (75.0, "Logo terkunci saat “Vedika Autentik”"), (79.0, "Slogan + Tim ADA healthkathon")],
     "Video AI hangat (grading warm, vignette ringan) → kartu teal yang sama dengan H3.",
     "Subtitle hanya untuk kalimat pertama. “Lengkap belum tentu asli” tampil sebagai slogan 76 px; teks kecil “Tim ADA healthkathon”.",
     "Demo lebur 0,6 dtk ke adegan hangat (letterbox masuk, kamera mundur pelan 1,1→1,02). Garis pindai menyapu lagi, logo dikunci dengan gerak yang sama seperti H3 tepat saat “Vedika Autentik”, slogan naik dari masker saat diucapkan, kredit muncul, hold, fade ke hitam 0,6 dtk.",
     "Narasi z1. Whoosh pelan ke adegan hangat, whoosh + sting di logo, ding lembut di slogan. Musik turun di 2,4 dtk terakhir.",
     "assets/video/z-hd.mp4 (dari frame6) + logo inline"),
]

STEP_SCENES = {"w1", "w2", "w3", "w4", "w5", "w6", "w7"}
cards = []
for code, title, sid, frs, visual, onscreen, motion, audio, source in SCENES:
    t = T[sid]
    narr = VO[t["id"]]
    figs = "".join(
        f'<figure><img src="{frame(ft)}" alt="{html.escape(cap)}" loading="lazy"><figcaption><b>{mmss(ft)}</b> {html.escape(cap)}</figcaption></figure>'
        for ft, cap in frs)
    kind = "demo" if sid in STEP_SCENES else "film"
    cards.append(f'''
    <section class="scene {kind}" id="{code.lower()}">
      <header><span class="code">{code}</span><h2>{html.escape(title)}</h2>
        <span class="time">{mmss(t["s"])}–{mmss(t["e"])} · {t["e"] - t["s"]:.1f} dtk</span></header>
      <div class="frames n{len(frs)}">{figs}</div>
      <blockquote>“{html.escape(narr)}”<span>narasi {t["id"]} mulai {mmss(t["vo"])}</span></blockquote>
      <dl>
        <dt>Visual</dt><dd>{html.escape(visual)}</dd>
        <dt>Teks layar</dt><dd>{html.escape(onscreen)}</dd>
        <dt>Gerak</dt><dd>{html.escape(motion)}</dd>
        <dt>Audio</dt><dd>{html.escape(audio)}</dd>
        <dt>Sumber</dt><dd><code>{html.escape(source)}</code></dd>
      </dl>
    </section>''')

strip = "".join(
    f'<span style="flex:{T[k]["e"] - T[k]["s"]:.2f}" class="seg {"d" if k.startswith("w") else ""}">{k.upper()}</span>'
    for k in T)
total = TM["TOTAL"]

page = f'''<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Storyboard Vedika v2</title>
<style>
@font-face{{font-family:Poppins;font-weight:400;src:url({FONT['Regular']})}}
@font-face{{font-family:Poppins;font-weight:500;src:url({FONT['Medium']})}}
@font-face{{font-family:Poppins;font-weight:600;src:url({FONT['SemiBold']})}}
@font-face{{font-family:Poppins;font-weight:700;src:url({FONT['Bold']})}}
:root{{--teal:#0F3D3E;--green:#0E7C3A;--orange:#F26B21;--navy:#1B2D4F;--mint:#EAF3F1;--mint2:#D3E3DF;--grey:#5B6B6A;--bg:#F6FAF9;--card:#fff;--ink:#14302F}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:400 15px/1.6 Poppins,system-ui,sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:40px 16px 80px}}
.top{{background:var(--teal);color:#fff;border-radius:20px;padding:34px 36px;display:grid;gap:14px}}
.top h1{{margin:0;font:700 34px/1.15 Poppins,system-ui,sans-serif}}.top h1 em{{font-style:normal;color:#F3B441}}
.top p{{margin:0;color:#cfe3de;max-width:820px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px 22px;color:#e6f1ee;font-size:14px}}.meta b{{color:#fff}}
.bar{{display:flex;height:34px;border-radius:10px;overflow:hidden;margin-top:6px}}
.seg{{display:flex;align-items:center;justify-content:center;font:600 11px Poppins;color:#fff;background:#1d5658;border-right:1px solid #0F3D3E}}
.seg.d{{background:#e7f1ee;color:var(--teal)}}
h3.sec{{font:600 13px Poppins;letter-spacing:.12em;text-transform:uppercase;color:var(--grey);margin:42px 0 14px}}
.notes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}}
.note{{background:var(--card);border:1px solid var(--mint2);border-radius:14px;padding:18px 20px}}
.note h4{{margin:0 0 6px;font:600 15px Poppins;color:var(--teal)}}.note p,.note ul{{margin:0;color:#3d5352;font-size:14px}}.note ul{{padding-left:18px}}
.scene{{background:var(--card);border:1px solid var(--mint2);border-radius:18px;padding:24px 26px;margin-top:22px}}
.scene header{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:16px}}
.code{{font:700 15px Poppins;color:#fff;background:var(--teal);border-radius:8px;padding:2px 10px}}
.scene.demo .code{{background:var(--orange)}}
.scene h2{{margin:0;font:600 22px Poppins;color:var(--teal)}}.time{{margin-left:auto;color:var(--grey);font-size:14px;font-variant-numeric:tabular-nums}}
.frames{{display:grid;gap:12px}}.frames.n2{{grid-template-columns:1fr 1fr}}.frames.n3{{grid-template-columns:repeat(3,1fr)}}.frames.n4{{grid-template-columns:repeat(2,1fr)}}
figure{{margin:0}}figure img{{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;display:block;background:#0b1a1a;border:1px solid var(--mint2)}}
figcaption{{font-size:13px;color:var(--grey);margin-top:6px}}figcaption b{{color:var(--orange);font-weight:600;margin-right:4px}}
blockquote{{margin:18px 0 6px;padding:14px 18px;background:var(--mint);border-radius:12px;font:500 17px/1.5 Poppins;color:var(--teal)}}
blockquote span{{display:block;font:400 12px Poppins;color:var(--grey);margin-top:4px}}
dl{{display:grid;grid-template-columns:120px 1fr;gap:8px 18px;margin:14px 0 0}}dt{{font:600 13px Poppins;color:var(--grey);text-transform:uppercase;letter-spacing:.06em;padding-top:2px}}dd{{margin:0;font-size:14.5px}}
code{{font:500 13px ui-monospace,Menlo,monospace;background:var(--mint);padding:1px 6px;border-radius:6px;color:var(--teal)}}
.sw{{display:flex;gap:10px;flex-wrap:wrap}}.sw span{{display:flex;align-items:center;gap:8px;font-size:13px}}.sw i{{width:22px;height:22px;border-radius:6px;display:block;border:1px solid #0001}}
@media (max-width:760px){{.frames.n2,.frames.n3,.frames.n4{{grid-template-columns:1fr}}dl{{grid-template-columns:1fr}}.time{{margin-left:0}}.top{{padding:24px 20px}}.top h1{{font-size:26px}}}}
</style></head><body><div class="wrap">
<div class="top">
  <h1>Vedika Autentik · video demo <em>v2</em></h1>
  <p>Storyboard frame per frame dari komposisi HyperFrames baru (<code style="background:#ffffff1a;color:#fff">videos/v2</code>). Semua gambar di bawah adalah snapshot asli komposisi, bukan sketsa. Belum dirender ke mp4.</p>
  <div class="meta"><span><b>1920×1080</b> · 30 fps</span><span><b>{total:.1f} dtk</b> (timing dari durasi suara Arunika)</span><span><b>11 adegan</b> · H1–H3, W1–W7, Z</span><span>Subtitle Indonesia dibakar, per kalimat</span></div>
  <div class="bar">{strip}</div>
</div>

<h3 class="sec">Arah yang diubah dari versi lama</h3>
<div class="notes">
  <div class="note"><h4>Hook sinematik, bukan subtitle di atas klip</h4><p>Grading hangat-redup, letterbox 2.39:1, grain, vignette. Tiap hook dua shot dari klip yang sama (wide lalu close), dorongan kamera pelan, lebur dengan blur antara H1 dan H2.</p></div>
  <div class="note"><h4>Benang merah: garis pindai oranye</h4><p>Garis yang “memindai” muncul di tiga titik: H2→logo, logo→demo, adegan hangat→logo penutup. Satu motif, tidak ada efek lain yang bersaing.</p></div>
  <div class="note"><h4>Demo diedit, bukan slideshow</h4><p>Rekaman layar asli di jendela putih atas latar mint. Kamera virtual zoom/pan ke elemen yang sedang diucapkan, jump cut di dalam adegan, whip blur singkat antar-adegan, klik jatuh tepat di kata “Satu klik” / sebelum “Satu balasan”.</p></div>
  <div class="note"><h4>Tanpa ornamen PPT</h4><p>Tidak ada bubble, chip, pill callout, atau terbang-masuk. Label langkah hanya angka oranye + judul teal yang dibuka dengan masker. Highlight datang dari rekaman (cincin oranye, sorotan merah).</p></div>
</div>

<h3 class="sec">Adegan</h3>
{''.join(cards)}

<h3 class="sec">Audio</h3>
<div class="notes">
  <div class="note"><h4>Narasi dominan</h4><p>11 potongan suara Arunika (ElevenLabs) pada volume penuh, naskah tidak diubah. Subtitle mengikuti jeda di dalam suara, jadi berganti tepat per kalimat.</p></div>
  <div class="note"><h4>Musik jauh di bawah</h4><p>Pad latar sintetis (bebas hak) di 0,42 lalu di-<i>carve</i>: 6 pita frekuensi suara (250 Hz–2,5 kHz) dipotong 7–15 dB hanya saat narasi berbunyi, sisanya tetap terdengar sebagai musik. Masuk 1,4 dtk, keluar 2,4 dtk terakhir.</p></div>
  <div class="note"><h4>SFX halus</h4><ul><li>whoosh 0,4–0,8 di tiap potongan adegan dan garis pindai</li><li>klik 0,32 di 5 klik yang terlihat</li><li>sting logo 0,4 di H3 dan Z, ding 0,26 di slogan</li></ul></div>
</div>

<h3 class="sec">Token desain</h3>
<div class="notes">
  <div class="note"><h4>Palet (dari PPT)</h4><div class="sw"><span><i style="background:#0F3D3E"></i>teal</span><span><i style="background:#0E7C3A"></i>hijau</span><span><i style="background:#F26B21"></i>oranye</span><span><i style="background:#1B2D4F"></i>navy</span><span><i style="background:#EAF3F1"></i>mint</span><span><i style="background:#D3E3DF"></i>mint 2</span><span><i style="background:#5B6B6A"></i>abu</span><span><i style="background:#F3B441"></i>emas logo</span></div></div>
  <div class="note"><h4>Tipografi</h4><p>Poppins 700 wordmark 150 px · 600 label langkah 34 px dan slogan 76 px · 500 subtitle 38–46 px.</p></div>
  <div class="note"><h4>Kepatuhan</h4><ul><li>Tag “Ilustrasi” di semua klip AI</li><li>Footer “Prototipe · data fiktif” sepanjang demo</li><li>Tanpa angka dampak, tanpa kata vonis</li></ul></div>
</div>

<h3 class="sec">Perlu keputusan</h3>
<div class="notes">
  <div class="note"><h4>1. Subtitle di kartu logo</h4><p>“Vedika Autentik.” (H3) dan “Vedika Autentik. Lengkap belum tentu asli.” (Z) tidak dibuat subtitle karena kata yang sama sudah tampil besar di layar. Mau tetap ditampilkan?</p></div>
  <div class="note"><h4>2. Musik latar</h4><p>Masih pad sintetis lama. Opsi: tetap, atau login HeyGen (<code>npx hyperframes auth login</code>) untuk musik berlisensi/generate, atau kirim file lagu berlisensi sendiri.</p></div>
  <div class="note"><h4>3. Label W5</h4><p>W4 dan W5 sama-sama bernomor “04” (Kartu bukti / Berkas kembar) mengikuti versi lama. Bisa juga “04b”.</p></div>
</div>
</div></body></html>'''
(ROOT / "storyboard.html").write_text(page)
print("storyboard.html", len(page) // 1024, "KB,", len(list(OUT.glob("*.jpg"))), "frame")
