#!/usr/bin/env python3
"""Bangun videos/v2/index.html (video demo Vedika Autentik, versi 2).

Narasi adalah jangkar: durasi tiap potongan suara (assets/vo/*.wav) menentukan panjang adegan,
dan jeda di dalam suara (silencedetect) menentukan kapan subtitle berganti kalimat.
Rekaman layar dipotong lewat data-media-start / data-playback-rate (tanpa render ulang klip),
lalu "kamera" virtual (GSAP x/y/scale pada #win) diarahkan ke elemen yang disebut narasi.

Jalankan dari root repo:  python3 videos/v2/tools/build.py
"""
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent
VO_TEXT = json.loads((REPO / "videos/tools/vo.json").read_text())
MARKS = json.loads((ROOT / "assets/video/screen.marks.json").read_text())


def probe(p):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())


def gaps(p, noise="-38dB", d="0.13"):
    out = subprocess.run(["ffmpeg", "-i", str(p), "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(st, en))


# ------------------------------------------------------------ suara dan kalimat
VO = {}
for k, text in VO_TEXT.items():
    wav = ROOT / f"assets/vo/{k}.wav"
    dur = probe(wav)
    sents = [s.strip() for s in re.findall(r"[^.?!]+[.?!]", text)]
    al = ROOT / f"assets/vo/{k}.align.json"
    if al.exists():  # batas kalimat dari alignment karakter ElevenLabs (tools/gen_vo.py)
        seg = [(x["t"], round(x["s"], 2), round(x["e"], 2)) for x in json.loads(al.read_text())["seg"]]
        VO[k] = {"dur": round(dur, 2), "seg": seg}
        continue
    g = gaps(wav)
    lead = g[0][1] if g and g[0][0] < 0.05 else 0.0
    inner = [x for x in g if x[0] > lead + 0.2 and x[1] < dur - 0.05]
    cut = sorted(sorted(inner, key=lambda x: x[0] - x[1])[: len(sents) - 1])
    seg, s0 = [], lead
    for i, s in enumerate(sents):
        e = cut[i][0] if i < len(cut) else dur
        seg.append((s, round(s0, 2), round(e, 2)))
        if i < len(cut):
            s0 = cut[i][1]
    VO[k] = {"dur": round(dur, 2), "seg": seg}

# ------------------------------------------------------------ timing adegan
# (adegan, potongan suara, jeda sebelum suara, ekor setelah suara, panjang minimum)
PLAN = [("h1", "h1", 0.55, 0.35, 5.6), ("h2", "h2", 0.25, 0.5, 0), ("h2b", "h2b", 0.3, 0.45, 0),
        ("h3", "h3", 0.1, 0.55, 0),
        ("w1", "w1", 0.3, 0.4, 0), ("w2", "w2", 0.25, 0.4, 0), ("w3", "w3", 0.1, 0.35, 0),
        ("w4", "w4", 0.25, 0.4, 0), ("w5", "w5", 0.25, 0.45, 0), ("w6", "w6", 0.25, 0.4, 0),
        ("w7", "w7", 0.25, 0.5, 0), ("z", "z1", 0.5, 2.3, 0)]
T, t = {}, 0.0
for sid, vo, pre, tail, mn in PLAN:
    end = max(t + mn, t + pre + VO[vo]["dur"] + tail)
    T[sid] = {"s": round(t, 2), "e": round(end, 2), "vo": round(t + pre, 2), "id": vo}
    t = end
TOTAL = round(t, 2)


def vs(sid, i, edge=0):
    """Waktu global awal (edge=0) / akhir (edge=1) kalimat ke-i pada adegan sid."""
    v = T[sid]
    return round(v["vo"] + VO[v["id"]]["seg"][i][1 + edge], 2)


# kunci logo H3 jatuh saat kata "Vedika Autentik" terucap (kalimat pertama: "Karena itu, hadirlah Vedika Autentik.")
H3_LOCK = round(vs("h3", 0, 1) - 1.1 - 0.6, 2)

# ------------------------------------------------------------ klip rekaman layar
# Setiap potongan: (id, mulai global, durasi, detik sumber, kecepatan)
S = {k: T[k]["s"] for k in T}
E = {k: T[k]["e"] for k in T}
K = list(MARKS["klik"])
# waktu klik di marks.json meleset dari ripple yang terlihat di rekaman; pakai waktu yang dicek per frame
K[1], K[7] = 6.95, 52.35
clips = []


def clip(cid, start, end, src, rate=1.0):
    clips.append({"id": cid, "s": round(start, 2), "d": round(end - start, 2), "src": round(src, 2), "r": rate})


STAGE_IN = round(E["h3"] - 0.45, 2)              # jendela demo terbuka di bawah kartu logo
W1_CUT = round(S["w1"] + 2.3, 2)                  # dari still ke video
W1_CLICK = round(vs("w1", 1) - 0.15, 2)           # klik "Jalankan demo" tepat sebelum "Satu klik"
clip("w1b", W1_CUT, E["w1"], K[1] - (W1_CLICK - W1_CUT))
W2_CUT = round(S["w2"] + 3.0, 2)
clip("w2a", S["w2"], W2_CUT, 7.9, 1.5)
clip("w2b", W2_CUT, E["w2"], 13.85, 0.7)
# rekaman W3 punya scroll instan di 20,43 dan 22,37 s, dan kartu terbuka di 24,53 s: pakai hanya bagian yang stabil
# (18,1-20,35 tabel; 22,4-24,45 daftar + tabel) supaya tidak ada loncatan layar
W3_CUT = round(S["w3"] + 3.7, 2)
clip("w3a", S["w3"], W3_CUT, 18.1, round(2.25 / (W3_CUT - S["w3"]), 3))
clip("w3b", W3_CUT, E["w3"], 22.4, round(2.05 / (E["w3"] - W3_CUT), 3))
W4_CUT = round(vs("w4", 1) - 0.27, 2)
clip("w4a", S["w4"], W4_CUT, 25.0)
clip("w4b", W4_CUT, E["w4"], 31.0, 0.85)
clip("w5", S["w5"], E["w5"], 41.9)
W6_CLICK = round(vs("w6", 1) - 0.5, 2)
W6_CUT = round(W6_CLICK + 0.17, 2)
clip("w6a", S["w6"], W6_CUT, K[7] - (W6_CLICK - S["w6"]) * 0.8, 0.8)
clip("w6b", W6_CUT, E["w6"], K[7] + 0.14)
clip("w7", S["w7"], E["w7"] + 0.3, 58.6)


# potongan isi rekaman jadi lebur 0,25 dtk (klip sebelumnya diperpanjang di bawah klip berikutnya), bukan potong keras
XF = 0.3
XF_CUTS = []
for prev, nxt in zip(clips, clips[1:]):
    if nxt["id"] == "w1b" or abs(prev["src"] + prev["d"] * prev["r"] - nxt["src"]) < 0.05:
        continue                                  # still → video identik, atau rekaman yang sama bersambung
    prev["d"] = round(prev["d"] + XF, 2)
    XF_CUTS.append({"id": nxt["id"], "s": nxt["s"]})


def g2s(cid, src_t):
    c = next(c for c in clips if c["id"] == cid)
    return round(c["s"] + (src_t - c["src"]) / c["r"], 2)


W7_CLICK = g2s("w7", K[8])
CLICKS = sorted({W1_CLICK, g2s("w3b", K[2]), g2s("w3b", K[3]), W6_CLICK, W7_CLICK})

# ------------------------------------------------------------ penutup
Z_CLIP_IN = round(S["z"] - 0.25, 2)
Z_SCAN = round(vs("z", 1) - 0.75, 2)               # garis pindai mulai, sayap terkunci saat "Vedika Autentik"
Z_SLOGAN = round(vs("z", 2) - 0.1, 2)
Z_CREDIT = round(vs("z", 2, 1) + 0.2, 2)

# ------------------------------------------------------------ subtitle
SUB = []
SKIP = {("z", 1), ("z", 2)}            # kata yang sama sudah tampil sebagai logo/slogan
for sid in T:
    for i, (txt, a, b) in enumerate(VO[T[sid]["id"]]["seg"]):
        if (sid, i) in SKIP:
            continue
        kind = "hook" if sid in ("h1", "h2", "h2b", "z") else ("logo" if sid == "h3" else "demo")
        SUB.append({"t": txt, "s": round(T[sid]["vo"] + a - 0.08, 2), "e": round(T[sid]["vo"] + b + 0.18, 2), "k": kind})
for i in range(len(SUB) - 1):                       # jangan bertumpuk
    if SUB[i]["e"] > SUB[i + 1]["s"] - 0.04:
        SUB[i]["e"] = round(SUB[i + 1]["s"] - 0.04, 2)

# ------------------------------------------------------------ audio
SFX = []  # (nama, mulai, volume)
for c in (S["h2"], E["w1"], E["w2"], E["w3"], E["w4"], E["w5"], E["w6"]):
    SFX.append(("whoosh", c - 0.4, 0.55))
SFX += [("whoosh", S["h3"] - 0.45, 0.8), ("whoosh", STAGE_IN - 0.2, 0.7), ("whoosh", Z_CLIP_IN - 0.3, 0.4),
        ("whoosh", Z_SCAN - 0.2, 0.7)]
SFX += [("sting", H3_LOCK + 0.38, 0.42), ("sting", Z_SCAN + 0.6, 0.38), ("ding", Z_SLOGAN + 0.05, 0.26)]
SFX += [("click", c - 0.02, 0.32) for c in CLICKS]
SFX.sort(key=lambda x: x[1])
SFXDUR = {"whoosh": 0.8, "sting": 2.2, "click": 0.09, "ding": 0.9}

audio = []
for sid in T:
    v = T[sid]
    audio.append(f'<audio id="vo-{v["id"]}" src="assets/vo/{v["id"]}.wav" data-start="{v["vo"]}" '
                 f'data-duration="{VO[v["id"]]["dur"]}" data-track-index="20" data-volume="1" data-audio-group="voiceover"></audio>')
for i, (n, ts, vol) in enumerate(SFX):
    audio.append(f'<audio id="fx-{i:02d}-{n}" src="assets/sfx/{n}.wav" data-start="{ts:.2f}" '
                 f'data-duration="{SFXDUR[n]}" data-track-index="{22 + i % 3}" data-volume="{vol}" data-audio-group="sfx"></audio>')
bgm_lane = {"version": 1, "lanes": [{"target": "volume", "points": [
    {"t": 0, "v": 0}, {"t": 1.4, "v": 1}, {"t": round(TOTAL - 2.4, 2), "v": 1}, {"t": TOTAL, "v": 0}]}]}
audio.append(f'<audio id="bgm" src="assets/sfx/bgm.wav" data-start="0" data-duration="{TOTAL}" '
             f'data-track-index="21" data-volume="0.42" data-audio-group="music" data-automation=\'{json.dumps(bgm_lane)}\'></audio>')

# ------------------------------------------------------------ HTML bagian
GRADE_HOOK = json.dumps({"preset": "muted-editorial", "intensity": 0.5,
                         "adjust": {"contrast": 0.1, "shadows": 0.05, "temperature": 0.1, "saturation": -0.05},
                         "details": {"vignette": 0.3, "vignetteFeather": 0.75, "grain": 0.12, "grainSize": 0.22,
                                     "grainRoughness": 0.6}})
GRADE_Z = json.dumps({"preset": "warm-daylight", "intensity": 0.45,
                      "adjust": {"contrast": 0.06, "temperature": 0.08},
                      "details": {"vignette": 0.22, "vignetteFeather": 0.75, "grain": 0.1, "grainSize": 0.22,
                                  "grainRoughness": 0.6}})

H1A_END = 3.05
H2A_END = round(vs("h2", 1) - 0.35, 2)
hook_shots = [
    ("h1a", "h1-hd", 0.0, H1A_END, 0.0, 0.85),
    ("h1b", "h1-hd", H1A_END, S["h2"] + 0.4, 2.65, 0.92),
    ("h2a", "h2-hd", S["h2"], H2A_END, 0.0, 0.8),
    ("h2b", "h2-hd", H2A_END, S["h2b"] + 0.7, round((H2A_END - S["h2"]) * 0.8, 2), 0.82),
    ("pn", "screen", S["h2b"] + 0.2, S["h3"] + 0.7, 18.2, 1.0),
    ("zv", "z-hd", Z_CLIP_IN, Z_SCAN + 0.7, 0.2, 0.85),
]
shots_html = "\n".join(
    f'<div class="shot" id="sh-{i}"><div class="inner" id="in-{i}" data-layout-allow-overflow><video id="{i}" class="clip" src="assets/video/{f}.mp4" '
    f'muted playsinline data-start="{a}" data-duration="{round(b - a, 2)}" data-media-start="{round(m, 2)}" '
    f'data-playback-rate="{r}" data-track-index="1" '
    f'data-color-grading=\'{GRADE_Z if i == "zv" else GRADE_HOOK}\' '
    f'style="--hf-color-grading-exposure: {-0.2 if i == "pn" else 0}"></video></div></div>'
    for i, f, a, b, m, r in hook_shots)

screen_html = "\n".join(
    f'<video id="{c["id"]}" class="clip scr" src="assets/video/screen.mp4" muted playsinline data-start="{c["s"]}" '
    f'data-duration="{c["d"]}" data-media-start="{c["src"]}" data-playback-rate="{c["r"]}" data-track-index="3"></video>'
    for c in clips)

STEPS = [("w1", "01", "Unggah berkas"), ("w2", "02", "Cek kualitas scan"), ("w3", "03", "Label otomatis"),
         ("w4", "04", "Kartu bukti"), ("w5", "04", "Berkas kembar"), ("w6", "05", "Konfirmasi peserta"),
         ("w7", "06", "Keputusan di tangan Anda")]
steps_html = "\n".join(
    f'<div class="step clip" id="st-{s}" data-start="{max(S[s], STAGE_IN + 0.6)}" data-duration="{round(E[s] - max(S[s], STAGE_IN + 0.6), 2)}" '
    f'data-track-index="6"><div class="step-in"><span class="step-no">{n}</span><span class="step-rule"></span>'
    f'<span class="step-ti">{ti}</span></div></div>'
    for s, n, ti in STEPS)

subs_html = "\n".join(
    f'<div class="sub sub-{c["k"]} clip" id="sub-{i:02d}" data-start="{c["s"]}" data-duration="{round(c["e"] - c["s"], 2)}" '
    f'data-track-index="8"><p>{c["t"]}</p></div>' for i, c in enumerate(SUB))


def mark(pfx):
    return (f'<svg class="mark" id="{pfx}-mark" viewBox="0 0 48 48" overflow="visible">'
            f'<path id="{pfx}-wl" fill="#fff" d="M5 5h13l6 26-5 11L5 11V5Z"/>'
            f'<path id="{pfx}-wr" fill="#fff" d="M43 5H30l-6 26 5 11L43 11V5Z"/>'
            f'<circle id="{pfx}-ring" cx="24" cy="33" r="3.4" fill="none" stroke="#F3B441" stroke-width="0.8"/>'
            f'<circle id="{pfx}-dot" cx="24" cy="33" r="3.4" fill="#F3B441" stroke="#0F3D3E" stroke-width="1.5"/></svg>')


def lockup(pfx):
    return (f'<div class="lock" id="{pfx}-lock"><div class="mark-wrap" id="{pfx}-mw">{mark(pfx)}</div>'
            f'<div class="words">'
            + "".join(f'<div class="wm-line"><div class="wm-in" id="{pfx}-w{i}"><span class="wm">{w}</span>'
                      f'<span class="wm wm-sh">{w}</span></div></div>' for i, w in ((1, "Vedika"), (2, "Autentik")))
            + f'<span class="oline" id="{pfx}-line"></span></div></div>')


# ------------------------------------------------------------ konfigurasi untuk timeline
CFG = {
    "T": T, "TOTAL": TOTAL, "STAGE_IN": STAGE_IN, "W1_CUT": W1_CUT, "W1_CLICK": W1_CLICK, "W2_CUT": W2_CUT,
    "W3_CUT": W3_CUT, "W4_CUT": W4_CUT, "W6_CLICK": W6_CLICK, "W6_CUT": W6_CUT, "W7_CLICK": W7_CLICK,
    "H1A_END": H1A_END, "H2A_END": H2A_END, "H2B_END": round(S["h2b"] + 0.7, 2), "H3_LOCK": H3_LOCK, "Z_CLIP_IN": Z_CLIP_IN, "Z_SCAN": Z_SCAN, "Z_SLOGAN": Z_SLOGAN,
    "Z_CREDIT": Z_CREDIT, "SUB": SUB, "XF": XF_CUTS, "XFD": XF,
    "VS": {sid: [[vs(sid, i), vs(sid, i, 1)] for i in range(len(VO[T[sid]["id"]]["seg"]))] for sid in T},
}

html = (ROOT / "tools/index.template.html").read_text()
for k, v in {
    "__TOTAL__": str(TOTAL), "__CFG__": json.dumps(CFG, ensure_ascii=False), "__SHOTS__": shots_html,
    "__SCREEN__": screen_html, "__STEPS__": steps_html, "__SUBS__": subs_html, "__AUDIO__": "\n".join(audio),
    "__H3LOCK__": lockup("h3"), "__ZLOCK__": lockup("z"),
    "__STILL_S__": str(STAGE_IN), "__STILL_D__": str(round(W1_CUT - STAGE_IN, 2)),
    "__STAGE_S__": str(STAGE_IN), "__STAGE_D__": str(round(E["w7"] + 0.6 - STAGE_IN, 2)),
    "__H3_S__": str(round(S["h3"] - 0.05, 2)), "__H3_D__": str(round(E["h3"] - S["h3"] + 0.1, 2)),
    "__Z_S__": str(Z_SCAN), "__Z_D__": str(round(TOTAL - Z_SCAN, 2)),
    "__LB1_D__": str(round(S["h3"] + 0.7, 2)),
    "__LB2_S__": str(Z_CLIP_IN), "__LB2_D__": str(round(Z_SCAN + 0.7 - Z_CLIP_IN, 2)),
    "__FOOT_S__": str(round(STAGE_IN + 0.6, 2)), "__FOOT_D__": str(round(E["w7"] - STAGE_IN - 0.6, 2)),
}.items():
    html = html.replace(k, v)
(ROOT / "index.html").write_text(html)
# musik latar diberi ruang di pita frekuensi suara narasi (voiceover carve), bukan sekadar dikecilkan
CARVE = Path.home() / ".claude/skills/hyperframes-audio/scripts/carve.mjs"
CORE = os.environ.get("HF_CORE_DIR")  # folder berisi node_modules/@hyperframes/core (npm i -D @hyperframes/core)
if CARVE.exists():
    cmd = ["node", str(CARVE), "--comp", str(ROOT / "index.html"), "--bed", "bgm", "--strength", "0.8"]
    subprocess.run(cmd + (["--core", CORE] if CORE else []), check=True)
(ROOT / "tools/timing.json").write_text(json.dumps({"T": T, "TOTAL": TOTAL, "clips": clips, "subs": SUB,
                                                    "clicks": CLICKS, "sfx": SFX}, indent=1, ensure_ascii=False))
print("total", TOTAL)
for k, v in T.items():
    print(f"{k:3} {v['s']:6.2f} → {v['e']:6.2f}  vo {v['vo']:6.2f}")
for c in clips:
    print(c)
print("klik", CLICKS)
