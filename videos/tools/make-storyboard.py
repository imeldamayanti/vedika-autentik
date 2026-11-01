#!/usr/bin/env python3
"""Susun storyboard.html (satu berkas, gambar tertanam) dari snapshot komposisi dan naskah VO.

Dipakai untuk review frame per frame sebelum render mp4. Jalankan setelah snapshot:
  npx hyperframes snapshot --at <waktu> --no-end -o videos/scratch/sb2
"""
import base64, html, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "scratch/sb5"
VO = json.loads((ROOT / "tools/vo.json").read_text())
DUR = json.loads((ROOT / "tools/vo-durations.json").read_text())

# id, judul, mulai, selesai, waktu frame, suara, teks layar, kamera/gerak, sfx, aset
S = [
 ("H1", "Hook 1 · Masalah", 0.0, 5.91, [1.5, 4.5], "h1",
  "Subtitle besar (putih, bayangan lembut). Tag kecil “Ilustrasi”. Tanpa judul atau kartu.",
  "Video AI: Bapak bercerita di meja makan, kamera mendorong pelan. Vignette gelap di tepi.",
  "Musik latar masuk pelan. Tanpa efek lain.",
  "Video AI PixVerse V6 720p dari frame7.jpg. Sudah jadi (5 dtk, 24 fps, tanpa audio)."),
 ("H2", "Hook 2 · Pertanyaannya", 5.91, 11.01, [7.5, 10], "h2",
  "Subtitle besar. Tag “Ilustrasi”.",
  "Video AI: Imelda termenung, Bapak buram di belakang. Potong dari H1 dengan dip gelap singkat.",
  "Whoosh halus di pemotongan.",
  "Video AI PixVerse V6 720p dari frame9.jpg. Sudah jadi (5 dtk, 24 fps, tanpa audio)."),
 ("H3", "Perkenalan · Logo", 11.01, 17.66, [12.5, 15.5], "h3",
  "Logo V + wordmark “Vedika Autentik” + garis oranye yang memanjang. Subtitle di bawah.",
  "Latar teal solid. Logo membesar dari 60% sambil sedikit berputar, wordmark naik, garis memanjang.",
  "Sting logo (denyut bas + kilau) tepat saat logo muncul.",
  "Vektor dari veritas-mark.svg (versi putih)."),
 ("W1", "Langkah 1 · Unggah berkas", 17.66, 24.25, [18.5, 22.5], "w1",
  "Label kecil “01 Unggah berkas” kiri bawah. Subtitle pil teal.",
  "Rekaman layar prototipe di jendela putih-mint. Cincin oranye di tombol “Jalankan demo”, kursor bergerak lalu klik, kamera zoom ke area tombol.",
  "Whoosh di potongan, klik saat tombol ditekan.",
  "Rekaman layar nyata (puppeteer, 1080p)."),
 ("W2", "Langkah 2 · Cek kualitas scan", 24.25, 31.66, [25.5, 29.5], "w2",
  "Label “02 Cek kualitas scan”.",
  "Daftar langkah pemeriksaan jalan satu per satu; kamera zoom ke daftar. Berkas buram berakhir “Scan ulang”.",
  "Whoosh di potongan.",
  "Rekaman layar nyata."),
 ("W3", "Langkah 3 · Label otomatis", 31.66, 39.3, [33, 37], "w3",
  "Label “03 Label otomatis”.",
  "Antrean berlabel. Cincin oranye di baris filter label, klik filter Prioritas lalu kembali Semua. Dorongan kamera halus.",
  "Whoosh, ding lembut saat label terlihat, klik di tiap filter.",
  "Rekaman layar nyata."),
 ("W4", "Langkah 4 · Kartu bukti (5 jadi 8)", 39.3, 47.72, [41, 45.5], "w4",
  "Label “04 Kartu bukti”.",
  "Kartu bukti VA-DST-01. Saklar sorotan dinyalakan, halaman bergulir ke baris kosong yang disorot merah, kamera zoom ke area itu.",
  "Whoosh, klik pada saklar.",
  "Rekaman layar nyata."),
 ("W5", "Langkah 4b · Berkas kembar", 47.72, 54.38, [49, 53], "w5",
  "Label “04 Berkas kembar ketahuan”.",
  "Dua lembar disandingkan. Cincin oranye mengelilingi pasangan, zoom ringan ke tengah.",
  "Whoosh.",
  "Rekaman layar nyata."),
 ("W6", "Langkah 5 · Konfirmasi peserta", 54.38, 63.64, [56, 61.5], "w6",
  "Label “05 Konfirmasi peserta”.",
  "Simulasi WhatsApp PANDAWA. Cincin di ponsel, kursor klik jawaban “2 · Tidak pernah”, balasan muncul, kamera zoom ke ponsel.",
  "Whoosh, klik saat memilih jawaban.",
  "Rekaman layar nyata."),
 ("W7", "Langkah 6 · Keputusan verifikator", 63.64, 70.86, [65, 69], "w7",
  "Label “06 Keputusan di tangan Anda”.",
  "Kartu Saran tindakan. Cincin oranye di kartu, klik “Setujui saran”, status berubah diteruskan ke telaah lanjut.",
  "Whoosh, klik saat Setujui.",
  "Rekaman layar nyata."),
 ("Z", "Penutup · Logo dan slogan", 70.86, 80.45, [72, 75.5, 79], "z1",
  "Mulai tanpa teks (subtitle saja), lalu kartu teal: logo, “Lengkap belum tentu asli”, tag kecil “Tim Veritas · Healthkathon 2026”.",
  "Video AI Bapak dan Imelda tersenyum (hangat), lalu fade ke kartu teal dengan logo dan slogan.",
  "Whoosh, ding lembut saat slogan muncul. Musik latar memudar di akhir.",
  "Video AI PixVerse V6 720p dari frame6.jpg (sudah jadi, diperlambat sedikit lalu menahan frame akhir) + vektor logo."),
]
import re
_T = json.loads(re.search(r"const T = (\{.*?\});\n", (ROOT / "demo/index.html").read_text(), re.S).group(1))
_times = [float(x) for x in (ROOT / "scratch/sb3-times.txt").read_text().split(",")]
_new, _i = [], 0
for row in S:
    t = _T[row[0].lower()]
    n = 3 if row[0] == "Z" else 2
    fr = _times[_i:_i + n]
    _i += n
    _new.append((row[0], row[1], t["s"], t["e"], fr) + row[5:])
S = _new
TOTAL = S[-1][3]


def b64(t):
    cand = sorted(SNAP.glob(f"frame-*-at-{t:g}s.png"))
    p = cand[0]
    jpg = ROOT / "scratch" / "sbtmp.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vf", "scale=960:-1", "-q:v", "4", str(jpg)], check=True)
    return base64.b64encode(jpg.read_bytes()).decode()


def tc(x):
    return f"{int(x // 60)}:{x % 60:04.1f}"


bar = "".join(
    f'<a href="#{s[0]}" class="seg {"hook" if s[0] in ("H1","H2","H3") else "demo" if s[0].startswith("W") else "end"}" style="flex:{s[3]-s[2]:.2f}" title="{html.escape(s[1])}"><b>{s[0]}</b></a>' for s in S)

cards = []
for sid, title, a, b, fr, vo, onscreen, motion, sfx, asset in S:
    imgs = "".join(f'<figure><img src="data:image/jpeg;base64,{b64(t)}" alt=""><figcaption>{tc(t)}</figcaption></figure>' for t in fr)
    cards.append(f'''
<section class="card" id="{sid}">
  <header><span class="id">{sid}</span><h2>{html.escape(title)}</h2><span class="time">{tc(a)} – {tc(b)} · {b-a:.1f} dtk</span></header>
  <div class="frames n{len(fr)}">{imgs}</div>
  <dl>
    <dt>Narasi (VO)</dt><dd class="vo">“{html.escape(VO[vo])}”<small>suara ElevenLabs (Arunika) {DUR[vo]:.1f} dtk</small></dd>
    <dt>Teks di layar</dt><dd>{html.escape(onscreen)}</dd>
    <dt>Visual dan gerak</dt><dd>{html.escape(motion)}</dd>
    <dt>Audio</dt><dd>{html.escape(sfx)}</dd>
    <dt>Sumber aset</dt><dd>{html.escape(asset)}</dd>
  </dl>
</section>''')

page = f'''<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Storyboard Vedika Autentik</title>
<style>
:root{{--teal:#0f3d3e;--green:#0e7c3a;--orange:#f26b21;--navy:#1b2d4f;--mint:#eaf3f1;--line:#d3e3df;--slate:#5b6b6a}}
*{{box-sizing:border-box}}
body{{margin:0;background:#f6faf8;color:var(--navy);font:15px/1.55 Poppins,Inter,system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 20px 80px}}
h1{{margin:0;font-size:30px;color:var(--teal);letter-spacing:-.02em}}
.sub{{margin:6px 0 20px;color:var(--slate)}}
.stats{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:18px}}
.stats span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:13px}}
.stats b{{color:var(--green)}}
.bar{{display:flex;gap:3px;margin:0 0 6px;position:sticky;top:0;background:#f6faf8;padding:10px 0;z-index:5}}
.seg{{display:block;text-align:center;border-radius:8px;padding:8px 0;color:#fff;text-decoration:none;font-size:12px;min-width:34px}}
.seg.hook{{background:var(--teal)}}.seg.demo{{background:var(--green)}}.seg.end{{background:var(--orange)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:16px;margin:22px 0;padding:18px 20px;scroll-margin-top:70px}}
.card header{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px}}
.id{{background:var(--orange);color:#fff;border-radius:8px;padding:2px 10px;font-weight:600;font-size:13px}}
.card h2{{margin:0;font-size:19px;color:var(--teal)}}
.time{{margin-left:auto;color:var(--slate);font-size:13px}}
.frames{{display:grid;gap:12px;margin-bottom:14px}}
.frames.n2{{grid-template-columns:1fr 1fr}}.frames.n3{{grid-template-columns:1fr 1fr 1fr}}
figure{{margin:0}}figure img{{width:100%;border-radius:10px;border:1px solid var(--line);display:block}}
figcaption{{font-size:12px;color:var(--slate);margin-top:3px}}
dl{{display:grid;grid-template-columns:150px 1fr;gap:8px 16px;margin:0}}
dt{{font-weight:600;color:var(--green);font-size:13px}}
dd{{margin:0}}
dd.vo{{font-weight:500;color:var(--teal)}}dd small{{display:block;color:var(--slate);font-weight:400;font-size:12px}}
.rich{{background:#fff;border:1px solid var(--line);border-left:6px solid var(--green);border-radius:14px;padding:14px 20px;margin:0 0 14px}}.rich h2{{margin:0 0 6px;font-size:17px;color:var(--teal)}}.rich ol{{margin:0;padding-left:20px}}.rich li{{margin:4px 0}}
.todo{{background:#fff6ee;border:1px solid #f4c9a6;border-radius:16px;padding:16px 20px;margin-top:30px}}
.todo h2{{margin:0 0 8px;font-size:18px;color:var(--orange)}}
@media(max-width:720px){{dl{{grid-template-columns:1fr}}.frames.n2,.frames.n3{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>Storyboard video demo · Vedika Autentik</h1>
<p class="sub">Revisi mengikuti brief Richard. Frame diambil langsung dari komposisi saat ini (timing mengikuti suara uji ElevenLabs). Belum ada mp4 final: hook dan penutup sudah memakai video AI (PixVerse V6).</p>
<div class="stats"><span>Durasi <b>{TOTAL:.0f} dtk</b> (±1:20)</span><span>Format <b>1920×1080 · 30 fps</b></span><span>Bahasa <b>Indonesia</b>, subtitle tertanam</span><span>Palet <b>teal · hijau · oranye · navy · mint</b> (mengikuti PPT)</span><span>Font <b>Poppins</b></span></div>
<div class="rich"><h2>Brief Richard → penerapan</h2><ol>
<li><b>Problem cepat, 5–10 detik.</b> Hook cuma H1 + H2 (±10 dtk), satu masalah: petugas tanda tangan sendiri, siapa yang menjamin keasliannya. Cerita meja makan yang panjang, bubble chat, dan kartu temuan KPK dibuang karena sudah ada di slide.</li>
<li><b>Langsung walkthrough sebagai verifikator.</b> W1–W7 berurutan: unggah, cek scan, label, kartu bukti, berkas kembar, konfirmasi peserta, keputusan. Narasi memakai “Anda”.</li>
<li><b>Gaya video promo.</b> Bahasa sederhana, fokus manfaat. Tidak ada tech stack. Pengenalan produk lewat sting logo (H3).</li>
<li><b>Tanpa AI slop dan tanpa animasi ala PPT.</b> Tidak ada bubble pop, blok highlight, chip, atau pill callout. Highlight datang dari rekaman layar nyata: kursor, ripple klik, cincin oranye di elemen yang dibahas, zoom kamera halus. Suara ElevenLabs berbahasa Indonesia.</li>
<li><b>Gabungan motion, video AI, SFX, backsound, highlight rekaman layar.</b> Hook dan penutup memakai video AI (menunggu upload frame), SFX (klik, whoosh, ding, sting), musik latar, dan highlight klik di UI.</li>
<li><b>Penutup logo dan slogan.</b> Z: adegan hangat singkat, lalu logo dan “Lengkap belum tentu asli”.</li>
</ol></div>
<nav class="bar">{bar}</nav>
{''.join(cards)}
<div class="todo"><h2>Perlu keputusan atau aset sebelum render</h2><ol>
<li><b>Video AI sudah jadi</b> (3 klip PixVerse V6 720p, ±210 kredit). Cek wajah dan gerak. Imelda di H2 agak dramatis; bisa diminta ulang dengan prompt lebih tenang.</li>
<li>Pilih <b>voice ElevenLabs</b> (8 contoh wanita Indonesia sudah dikirim). Suara sekarang cuma uji (Lily, aksen Inggris). Setelah dipilih, narasi digenerate ulang dan timing menyesuaikan.</li>
<li>Naskah VO: cek kata-kata tiap adegan (bagian “Narasi”) bersama Richard.</li>
<li>Musik latar: sekarang pad sintetis sederhana. Ganti dengan lagu berlisensi kalau ada.</li>
<li>Penutup: avatar tim dibuang sesuai brief, hanya teks kecil “Tim Veritas”. Setuju atau mau avatar kembali?</li>
</ol></div>
</div></body></html>'''
out = ROOT / "storyboard.html"
out.write_text(page)
print("ok", out, round(out.stat().st_size / 1e6, 1), "MB")
