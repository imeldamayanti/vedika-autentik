#!/usr/bin/env python3
"""Buat narasi v3 lewat ElevenLabs /with-timestamps dari videos/v3/vo.json, keluaran ke videos/v3/assets/vo.

Kunci dan voice dibaca dari environment (tidak pernah ditulis ke file):
  ELEVENLABS_API_KEY=... ELEVENLABS_VOICE_ID=... python3 videos/v3/tools/gen_vo.py
Opsional: STABILITY, STYLE, SPEED, MODEL, ONLY=h1,w2.

Selain {id}.wav, tiap potongan dapat {id}.align.json: batas kalimat (detik, sudah dikurangi trim awal)
dari alignment karakter ElevenLabs. build.py memakainya, jadi pemisahan subtitle tidak bergantung pada jeda
senyap (suara dengan stability rendah hampir tidak punya jeda antarkalimat).

Jeda yang dipaksa: tulis " ||0.4|| " di vo.json. Teks dipecah di situ, tiap bagian dibuat terpisah
(intonasi tiap bagian utuh), lalu disambung dengan senyap 0,4 dtk. Dipakai untuk "Lengkap, belum tentu asli."
"""
import base64
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VO = json.loads((ROOT / "vo.json").read_text())
OUT = ROOT / "assets/vo"
OUT.mkdir(parents=True, exist_ok=True)
# kunci dibaca dari environment, atau dari videos/.env.local (di-gitignore)
_env = ROOT.parent / ".env.local"
if _env.exists():
    for _l in _env.read_text().splitlines():
        if "=" in _l and not _l.startswith("#"):
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
key, voice = os.environ["ELEVENLABS_API_KEY"], os.environ["ELEVENLABS_VOICE_ID"]
model = os.environ.get("MODEL", "eleven_multilingual_v2")
only = os.environ["ONLY"].split(",") if os.environ.get("ONLY") else None
settings = {"stability": float(os.environ.get("STABILITY", 0.35)), "similarity_boost": 0.75,
            "style": float(os.environ.get("STYLE", 0.45)), "use_speaker_boost": True,
            "speed": float(os.environ.get("SPEED", 1.05))}
PAD_HEAD, PAD_TAIL = 0.05, 0.14


def tts(text, dest):
    """Satu panggilan TTS. Tulis wav ter-trim ke dest, kembalikan (start, end) tiap karakter relatif ke wav itu."""
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
        json.dumps({"text": text, "model_id": model, "voice_settings": settings}).encode(),
        {"xi-api-key": key, "content-type": "application/json"})
    res = json.loads(urllib.request.urlopen(req).read())
    al = res["alignment"]
    st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    t0, t1 = max(0.0, st[0] - PAD_HEAD), en[-1] + PAD_TAIL
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        f.write(base64.b64decode(res["audio_base64"]))
        f.flush()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", f.name,
                        "-ar", "44100", "-ac", "1", str(dest)], check=True)
    return [x - t0 for x in st], [x - t0 for x in en]


def dur_of(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode())


for cid, raw in VO.items():
    if only and cid not in only:
        continue
    parts = re.split(r"\s*\|\|([\d.]+)\|\|\s*", raw)   # [teks, jeda, teks, jeda, teks, ...]
    texts, gaps = parts[0::2], [float(g) for g in parts[1::2]]
    wav = OUT / f"{cid}.wav"
    text, st, en = "", [], []
    if len(texts) == 1:
        st, en = tts(texts[0], wav)
        text = texts[0]
    else:
        tmp, offset, wavs = Path(tempfile.mkdtemp()), 0.0, []
        for i, tx in enumerate(texts):
            w = tmp / f"p{i}.wav"
            s_, e_ = tts(tx, w)
            if i:  # spasi antarbagian: menempati jeda paksa
                text += " "
                st.append(offset)
                en.append(offset + gaps[i - 1])
                offset += gaps[i - 1]
            text += tx
            st += [x + offset for x in s_]
            en += [x + offset for x in e_]
            offset += dur_of(w)
            wavs.append(w)
        lst = tmp / "list.txt"
        seq = []
        for i, w in enumerate(wavs):
            if i:
                sil = tmp / f"sil{i}.wav"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                                "-t", str(gaps[i - 1]), str(sil)], check=True)
                seq.append(sil)
            seq.append(w)
        lst.write_text("".join(f"file '{p}'\n" for p in seq))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        str(wav)], check=True)
    # batas kalimat: awal = karakter non-spasi pertama kalimat, akhir = karakter terakhir kalimat
    seg, pos = [], 0
    for m in re.finditer(r"[^.?!]+[.?!]", text):
        a = pos + len(m.group(0)) - len(m.group(0).lstrip())
        b = m.end() - 1
        seg.append({"t": m.group(0).strip(), "s": round(st[a], 3), "e": round(en[b], 3)})
        pos = m.end()
    dur = dur_of(wav)
    (OUT / f"{cid}.align.json").write_text(json.dumps({"dur": round(dur, 3), "seg": seg}, ensure_ascii=False, indent=1))
    print(cid, round(dur, 2), [(x["s"], x["e"]) for x in seg])
