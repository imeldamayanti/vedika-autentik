#!/usr/bin/env python3
"""Buat rekaman percakapan skenario v3 lewat ElevenLabs, keluaran ke assets/rekaman.

Transkrip dibaca dari data-v3.js (pembicara A = AI, P = penerima). Satu panggilan TTS per baris
(/with-timestamps, trim awal-akhir seperti videos/v2/tools/gen_vo.py), filter suara telepon, lalu
semua baris disambung dengan jeda alami menjadi satu berkas per skenario.

  python3 tools/suara/buat_rekaman.py --skenario S1      # satu skenario
  python3 tools/suara/buat_rekaman.py                    # semua yang punya transkrip
  python3 tools/suara/buat_rekaman.py --paksa            # buat ulang baris yang sudah ada
  python3 tools/suara/buat_rekaman.py --cek              # tanpa kuota: cocokkan waktu.json, ffprobe, dan data-v3.js

Keluaran:
  assets/rekaman/<S>/<nn>.mp3   potongan per baris (nn = urutan baris, mulai 01)
  assets/rekaman/<S>.mp3        percakapan utuh
  assets/rekaman/waktu.json     detik mulai dan durasi tiap baris, durasi total

Baris yang berkasnya sudah ada tidak dibuat ulang (hemat kuota) kecuali --paksa. Kalau teks baris
berubah sejak dibuat, skrip memberi peringatan; pakai --paksa untuk membuatnya lagi.

Kunci dan ID suara dibaca dari environment atau backend/.env, tidak pernah ditulis ke file atau log:
  ELEVENLABS_API_KEY, ELEVENLABS_VOICE_AI, ELEVENLABS_VOICE_WANITA, ELEVENLABS_VOICE_PRIA
Bila ID suara tidak diisi, dipakai tiga suara yang tercatat di docs/rencana-v3.md bagian SR (ID suara
bukan rahasia). Opsional: MODEL, SPEED, JEDA.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REK = ROOT / "assets/rekaman"
WAKTU = REK / "waktu.json"
ENV = ROOT / "backend/.env"

SUARA_BAWAAN = {
    "ELEVENLABS_VOICE_AI": "o5s6XRBkPSTD4syv6mZg",       # Arunika, wanita
    "ELEVENLABS_VOICE_WANITA": "TrU3igk19A4aIUi2GAA2",   # Velora, penerima wanita
    "ELEVENLABS_VOICE_PRIA": "iP95p4xoKVk53GoZ742B",     # Chris, penerima pria
}
# Dewi (S2) satu-satunya penerima wanita; penerima lain (Andi, Budi, Bayu, Slamet, Hendra) pria.
PENERIMA_WANITA = {"S2"}
# AI lebih datar dan stabil, penerima lebih santai.
PENGATURAN = {
    "A": {"stability": 0.6, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True},
    "P": {"stability": 0.4, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True},
}
FILTER_TELEPON = "highpass=f=300,lowpass=f=3400"
PAD_HEAD, PAD_TAIL = 0.05, 0.14

# Hanya untuk TTS (transkrip di layar tetap apa adanya): singkatan dieja dengan nama huruf Indonesia,
# 165 dibaca per angka seperti nomor Care Center.
LAFAL = [(r"\bBPJS\b", "Be Pe Je Es"), (r"\bOTP\b", "O Te Pe"), (r"\bJKN\b", "Je Ka En"),
         (r"\bRSU\b", "Er Es U"), (r"\bRS\b", "Er Es"), (r"\b165\b", "satu enam lima")]


def muat_env():
    nilai = dict(os.environ)
    if ENV.exists():
        for baris in ENV.read_text().splitlines():
            m = re.match(r"\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*?)\s*$", baris)
            if m and m.group(1) not in nilai:
                nilai[m.group(1)] = m.group(2).strip("'\"")
    for k, v in SUARA_BAWAAN.items():
        nilai.setdefault(k, v)
    return nilai


def baca_transkrip():
    """Transkrip tiap skenario dari data-v3.js lewat node: {id: {nama, durasi, baris: [[pembicara, detik, teks]]}}."""
    js = ("globalThis.window = {}; require('./data-v3.js'); const out = {};"
          "Object.values(window.DATA3.SKENARIO).filter((p) => p.transkrip.length).forEach((p) =>"
          "{ out[p.id] = { nama: p.penerima.nama, durasi: p.durasi, baris: p.transkrip }; });"
          "process.stdout.write(JSON.stringify(out));")
    hasil = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(hasil.stdout)


def ffprobe_durasi(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode())


def untuk_tts(teks):
    for pola, ganti in LAFAL:
        teks = re.sub(pola, ganti, teks)
    return teks


def sha(teks):
    return hashlib.sha256(teks.encode()).hexdigest()[:12]


class Pembuat:
    def __init__(self, env):
        self.kunci = env.get("ELEVENLABS_API_KEY")
        if not self.kunci:
            sys.exit("ELEVENLABS_API_KEY tidak ditemukan di environment atau backend/.env")
        self.suara = {"A": env["ELEVENLABS_VOICE_AI"], "pria": env["ELEVENLABS_VOICE_PRIA"],
                      "wanita": env["ELEVENLABS_VOICE_WANITA"]}
        self.model = env.get("MODEL", "eleven_multilingual_v2")
        self.speed = float(env.get("SPEED", 1.0))
        self.jeda = float(env.get("JEDA", 0.6))
        self.dipanggil = 0

    def tts(self, teks, id_suara, pengaturan, tujuan):
        """Satu panggilan TTS: mp3 ter-trim dan terfilter ke tujuan."""
        badan = {"text": untuk_tts(teks), "model_id": self.model,
                 "voice_settings": dict(pengaturan, speed=self.speed)}
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{id_suara}/with-timestamps?output_format=mp3_44100_128",
            json.dumps(badan).encode(), {"xi-api-key": self.kunci, "content-type": "application/json"})
        try:
            res = json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            rinci = ""
            try:
                d = json.loads(e.read()).get("detail", {})
                rinci = d.get("status", "") if isinstance(d, dict) else str(d)[:120]
            except Exception:
                pass
            sys.exit(f"ElevenLabs menolak permintaan: HTTP {e.code} {rinci}".strip())
        self.dipanggil += 1
        al = res.get("alignment") or res["normalized_alignment"]
        t0 = max(0.0, al["character_start_times_seconds"][0] - PAD_HEAD)
        t1 = al["character_end_times_seconds"][-1] + PAD_TAIL
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            f.write(base64.b64decode(res["audio_base64"]))
            f.flush()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", f.name,
                            "-af", FILTER_TELEPON, "-ar", "44100", "-ac", "1", "-b:a", "96k", str(tujuan)], check=True)

    def sambung(self, berkas, tujuan):
        """Sambung potongan dengan senyap self.jeda di antaranya, simpan sebagai mp3."""
        cmd, label, n = ["ffmpeg", "-v", "error", "-y"], [], 0
        for i, b in enumerate(berkas):
            if i:
                cmd += ["-f", "lavfi", "-t", str(self.jeda), "-i", "anullsrc=r=44100:cl=mono"]
                label.append(n)
                n += 1
            cmd += ["-i", str(b)]
            label.append(n)
            n += 1
        fc = "".join(f"[{i}:a]" for i in label) + f"concat=n={len(label)}:v=0:a=1[a]"
        subprocess.run(cmd + ["-filter_complex", fc, "-map", "[a]", "-ar", "44100", "-ac", "1", "-b:a", "96k",
                              str(tujuan)], check=True)


def buat(pembuat, sid, sken, paksa, lama):
    folder = REK / sid
    folder.mkdir(parents=True, exist_ok=True)
    jk = "wanita" if sid in PENERIMA_WANITA else "pria"
    potongan, sha_baris = [], []
    for i, (pembicara, _detik, teks) in enumerate(sken["baris"], 1):
        berkas = folder / f"{i:02d}.mp3"
        h = sha(teks)
        baris_lama = lama.get(sid, {}).get("baris", [])
        sha_lama = baris_lama[i - 1].get("sha") if i <= len(baris_lama) else None
        if berkas.exists() and not paksa:
            if sha_lama and sha_lama != h:
                print(f"  {sid}/{i:02d}: teks berubah sejak dibuat, pakai --paksa untuk membuat ulang")
            h = sha_lama or h
            print(f"  {sid}/{i:02d}: sudah ada, dilewati")
        else:
            id_suara = pembuat.suara["A"] if pembicara == "A" else pembuat.suara[jk]
            pembuat.tts(teks, id_suara, PENGATURAN[pembicara], berkas)
            print(f"  {sid}/{i:02d}: dibuat ({ffprobe_durasi(berkas):.2f} dtk)")
        potongan.append(berkas)
        sha_baris.append(h)
    utuh = REK / f"{sid}.mp3"
    pembuat.sambung(potongan, utuh)
    mulai, baris = 0.0, []
    for i, b in enumerate(potongan):
        d = ffprobe_durasi(b)
        baris.append({"mulai": round(mulai, 2), "durasi": round(d, 2), "sha": sha_baris[i]})
        mulai += d + pembuat.jeda
    return {"berkas": f"assets/rekaman/{sid}.mp3", "total": round(ffprobe_durasi(utuh), 2), "baris": baris}


def cek(transkrip):
    """Cocokkan waktu.json dengan berkas (ffprobe) dan dengan data-v3.js. Tanpa memakai kuota."""
    if not WAKTU.exists():
        sys.exit("assets/rekaman/waktu.json belum ada")
    waktu = json.loads(WAKTU.read_text())
    salah, toleransi = [], 0.06
    for sid, w in waktu.items():
        utuh = ROOT / w["berkas"]
        if not utuh.exists():
            salah.append(f"{sid}: {w['berkas']} tidak ada")
            continue
        total = ffprobe_durasi(utuh)
        if abs(total - w["total"]) > toleransi:
            salah.append(f"{sid}: total waktu.json {w['total']} beda dengan ffprobe {total:.2f}")
        for i, b in enumerate(w["baris"], 1):
            p = REK / sid / f"{i:02d}.mp3"
            if not p.exists():
                salah.append(f"{sid}/{i:02d}: berkas tidak ada")
            elif abs(ffprobe_durasi(p) - b["durasi"]) > toleransi:
                salah.append(f"{sid}/{i:02d}: durasi waktu.json {b['durasi']} beda dengan ffprobe {ffprobe_durasi(p):.2f}")
        akhir = w["baris"][-1]
        if abs(akhir["mulai"] + akhir["durasi"] - w["total"]) > 0.25:
            salah.append(f"{sid}: baris terakhir berakhir di {akhir['mulai'] + akhir['durasi']:.2f}, total {w['total']}")
        t = transkrip.get(sid)
        if not t:
            salah.append(f"{sid}: tidak ada di data-v3.js")
            continue
        if len(t["baris"]) != len(w["baris"]):
            salah.append(f"{sid}: data-v3.js punya {len(t['baris'])} baris, waktu.json {len(w['baris'])}")
            continue
        if abs(t["durasi"] - w["total"]) > toleransi:
            salah.append(f"{sid}: durasi data-v3.js {t['durasi']} beda dengan waktu.json {w['total']}")
        for i, (b, (_p, detik, _teks)) in enumerate(zip(w["baris"], t["baris"]), 1):
            if abs(detik - b["mulai"]) > toleransi:
                salah.append(f"{sid}/{i:02d}: detik data-v3.js {detik} beda dengan waktu.json {b['mulai']}")
        print(f"{sid}: total {total:.2f} dtk, {len(w['baris'])} baris")
    if salah:
        print("TIDAK COCOK:\n  " + "\n  ".join(salah))
        sys.exit(1)
    print("waktu.json cocok dengan berkas dan data-v3.js")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skenario", action="append", help="id skenario (bisa diulang atau dipisah koma), bawaan semua")
    ap.add_argument("--paksa", action="store_true", help="buat ulang baris yang sudah ada")
    ap.add_argument("--cek", action="store_true", help="hanya periksa, tidak memanggil ElevenLabs")
    a = ap.parse_args()
    transkrip = baca_transkrip()
    if a.cek:
        return cek(transkrip)
    dipilih = [s.strip() for x in (a.skenario or []) for s in x.split(",") if s.strip()] or list(transkrip)
    tak_ada = [s for s in dipilih if s not in transkrip]
    if tak_ada:
        sys.exit("Skenario tanpa transkrip atau tidak dikenal: " + ", ".join(tak_ada))
    pembuat = Pembuat(muat_env())
    lama = json.loads(WAKTU.read_text()) if WAKTU.exists() else {}
    for sid in dipilih:
        print(sid)
        lama[sid] = buat(pembuat, sid, transkrip[sid], a.paksa, lama)
        print(f"  {sid}.mp3: {lama[sid]['total']} dtk")
    WAKTU.write_text(json.dumps(dict(sorted(lama.items())), indent=1))
    print(f"selesai, {pembuat.dipanggil} panggilan TTS")


if __name__ == "__main__":
    main()
