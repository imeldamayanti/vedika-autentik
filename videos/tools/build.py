#!/usr/bin/env python3
"""Bangun videos/demo/index.html dan semua klip pendukung.

Alur video mengikuti brief Richard: hook masalah singkat, langsung walkthrough sebagai
verifikator, tutup dengan logo dan slogan. Timing mengikuti durasi file suara di
demo/assets/vo (tools/vo-durations.json), jadi mengganti suara placeholder dengan suara
ElevenLabs cukup menjalankan ulang skrip ini. Efek suara ditaruh di waktu klik yang tercatat
saat rekam layar. Klip hook memakai video hasil generate (demo/assets/gen/<nama>.mp4) bila ada,
kalau belum ada dipakai foto dengan gerak kamera pelan sebagai cadangan.
"""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"
RAW = ROOT / "raw/demo-screen.mp4"
MARKS = json.loads((ROOT / "raw/demo-screen.marks.json").read_text())
CLIPS = DEMO / "assets/clips"
GEN = DEMO / "assets/gen"
IMG = DEMO / "assets/img"
CLIPS.mkdir(parents=True, exist_ok=True)
GEN.mkdir(parents=True, exist_ok=True)

VO = json.loads((ROOT / "tools/vo.json").read_text())
DUR = json.loads((ROOT / "tools/vo-durations.json").read_text())
LEAD, TAIL = 0.3, 0.5

# (id scene, id suara, panjang minimum)
SCENES = [
    ("h1", "h1", 4.2), ("h2", "h2", 4.0), ("h3", "h3", 5.0),
    ("w1", "w1", 4.9), ("w2", "w2", 5.9), ("w3", "w3", 5.9), ("w4", "w4", 7.0),
    ("w5", "w5", 6.0), ("w6", "w6", 7.5), ("w7", "w7", 6.5),
    ("z", "z1", 8.5),
]
# jendela rekaman layar mentah (detik) tiap adegan walkthrough
M = MARKS
RAW_WIN = {
    "w1": (M["w1"], M["w1"] + 4.4),
    "w2": (M["w2-selesai"] - 6.2, M["w2-selesai"] + 0.8),
    "w3": (M["w3"] + 0.3, M["w4"] - 0.8),
    "w4": (M["w4"] + 2.3, M["w4"] + 11.3),
    "w5": (M["w5"] + 0.4, M["w6"] - 0.6),
    "w6": (M["w6"] + 0.2, M["w7"] - 0.3),
    "w7": (M["w7"] + 0.1, M["selesai"] - 0.2),
}
STILL = {"h1": "frame7.jpg", "h2": "frame9.jpg", "z": "frame6.jpg"}

# ------------------------------------------------------------------ timing
T, t = {}, 0.0
for sid, vo, mn in SCENES:
    ln = max(mn, DUR[vo] + LEAD + TAIL)
    if sid == "z":
        ln = DUR[vo] + LEAD + 3.2
    T[sid] = {"s": round(t, 2), "d": round(ln, 2), "e": round(t + ln, 2), "vs": round(t + LEAD, 2), "vd": DUR[vo]}
    t += ln
TOTAL = round(t, 2)
DEMO_S, DEMO_E = T["w1"]["s"], T["w7"]["e"]


def sh(*a):
    subprocess.run([str(x) for x in a], check=True)


# ------------------------------------------------------------------ klip
for sid, (a, b) in RAW_WIN.items():
    f = T[sid]["d"] / (b - a)
    sh("ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", RAW,
       "-vf", f"setpts={f:.4f}*(PTS-STARTPTS),fps=30", "-an", "-c:v", "libx264", "-crf", "17",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart", CLIPS / f"{sid}.mp4")


def photo_clip(name, ln):
    out, gen = CLIPS / f"{name}.mp4", GEN / f"{name}.mp4"
    if gen.exists():
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", gen]).decode())
        f = min(1.2, max(1.0, ln / dur))
        sh("ffmpeg", "-v", "error", "-y", "-i", gen,
           "-vf", f"setpts={f:.4f}*PTS,scale=1920:1080:flags=lanczos:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,tpad=stop_mode=clone:stop_duration={ln:.2f}",
           "-t", f"{ln:.2f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out)
    else:
        n = int(ln * 30) + 1
        sh("ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", IMG / STILL[name],
           "-vf", f"scale=3840:-1,zoompan=z='min(zoom+0.0006,1.07)':d={n}:s=1920x1080:fps=30",
           "-t", f"{ln:.2f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out)


for sid in ("h1", "h2", "z"):
    photo_clip(sid, T[sid]["d"])

# ------------------------------------------------------------------ efek suara
sfx = []  # (file, waktu, volume)
cuts = [T[k]["s"] for k in ("h2", "h3", "w1", "w2", "w3", "w4", "w5", "w6", "w7", "z")]
for c in cuts:
    sfx.append(("whoosh", max(0, c - 0.35), 2.2))
sfx.append(("sting", T["h3"]["s"] + 0.25, 1.0))
for ck in MARKS["klik"]:
    for sid, (a, b) in RAW_WIN.items():
        if a <= ck <= b:
            sfx.append(("click", T[sid]["s"] + (ck - a) * T[sid]["d"] / (b - a), 1.6))
sfx.append(("ding", T["w3"]["s"] + 1.6, 1.4))
sfx.append(("ding", T["z"]["s"] + 3.4, 1.4))
sfx.sort(key=lambda x: x[1])
SFXDUR = {"whoosh": 0.8, "sting": 2.2, "click": 0.09, "ding": 0.9}

audio = [f'<audio id="vo-{vo}" src="assets/vo/{vo}.wav" data-start="{T[sid]["vs"]}" data-duration="{T[sid]["vd"]}" data-track-index="10"></audio>' for sid, vo, _ in SCENES]
audio += [f'<audio id="fx{i}" src="assets/sfx/{n}.wav" data-start="{ts:.2f}" data-duration="{SFXDUR[n]}" data-volume="{v}" data-track-index="{11 + (i % 3)}"></audio>' for i, (n, ts, v) in enumerate(sfx)]
audio.append(f'<audio id="bgm" src="assets/sfx/bgm.wav" data-start="0" data-duration="{TOTAL}" data-volume="0.55" data-track-index="9"></audio>')

# ------------------------------------------------------------------ HTML
def attrs(sid, track):
    return f'data-start="{T[sid]["s"]}" data-duration="{T[sid]["d"]}" data-track-index="{track}"'


videos_hook = "\n      ".join(f'<video id="v{s}" src="assets/clips/{s}.mp4" muted playsinline {attrs(s, 0)}></video>' for s in ("h1", "h2"))
video_z = f'<video id="vz" src="assets/clips/z.mp4" muted playsinline {attrs("z", 0)}></video>'
videos_demo = "\n          ".join(f'<video id="v{s}" src="assets/clips/{s}.mp4" muted playsinline {attrs(s, 1)}></video>' for s in RAW_WIN)
STEPS = {"w1": ("01", "Unggah berkas"), "w2": ("02", "Cek kualitas scan"), "w3": ("03", "Label otomatis"),
         "w4": ("04", "Kartu bukti"), "w5": ("04", "Berkas kembar ketahuan"), "w6": ("05", "Konfirmasi peserta"), "w7": ("06", "Keputusan di tangan Anda")}
strips = "\n      ".join(f'<div class="strip clip" id="st-{s}" {attrs(s, 2)}><span class="no">{n}</span><span class="ti">{ti}</span></div>' for s, (n, ti) in STEPS.items())

MARK = '<svg viewBox="0 0 48 48" __ID__><path fill="__A__" d="M5 5h13l6 26-5 11L5 11V5Z"/><path fill="__B__" d="M43 5H30l-6 26 5 11L43 11V5Z"/><circle cx="24" cy="33" r="3.4" fill="#F3B441" stroke="__S__" stroke-width="1.5"/></svg>'
def mark(i="", a="#fff", b="#fff", s="#0F3D3E"):
    return MARK.replace("__ID__", i).replace("__A__", a).replace("__B__", b).replace("__S__", s)

caps = [{"s": T[s]["vs"], "d": T[s]["vd"], "t": VO[vo], "k": "hook" if s in ("h1", "h2", "h3", "z") else "demo"} for s, vo, _ in SCENES]
html = (ROOT / "tools/index.template.html").read_text()
sub = {
    "__T__": json.dumps(T), "__CAPS__": json.dumps(caps, ensure_ascii=False), "__TOTAL__": str(TOTAL),
    "__AUDIO__": "\n      ".join(audio), "__VIDEOS_HOOK__": videos_hook, "__VIDEO_Z__": video_z,
    "__VIDEOS_DEMO__": videos_demo, "__STRIPS__": strips,
    "__MARK_LOGO__": mark('id="h3mark"'), "__MARK_Z__": mark('id="zmark"'), "__MARK_FOOT__": mark("", "#15324A", "#087A70", "#fff"),
    "__A_H1__": attrs("h1", 1), "__A_H2__": attrs("h2", 1), "__A_H3__": attrs("h3", 0), "__A_Z__": attrs("z", 1),
    "__A_SB__": f'data-start="{DEMO_S}" data-duration="{round(DEMO_E - DEMO_S, 2)}" data-track-index="3"',
}
for k, v in sub.items():
    html = html.replace(k, v)
(DEMO / "index.html").write_text(html)
print("total", TOTAL, "detik;", len(sfx), "efek suara")
for k, v in T.items():
    print(k, v["s"], "→", v["e"])
