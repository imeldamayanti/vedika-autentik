#!/usr/bin/env python3
"""Sintesis SFX dan backsound video demo v3 dari nol (tanpa sampel atau materi pihak ketiga).

Keluaran:
  videos/v3/assets/sfx/*.wav        efek suara sesuai tabel cue di docs/video-demo-v3-plan.md
  videos/v3/assets/music/bgm.wav    musik tech/startup ±115 BPM tanpa vokal (stereo 44,1 kHz)
  videos/v3/assets/call/s1-qa.wav   potongan audio telepon S1 (tanya jumlah + "tiga kali") dengan EQ telepon
  videos/v3/assets/LISENSI-AUDIO.md bukti lisensi + checksum

Struktur musik mengikuti plan: intro tipis -> drop di logo -> groove demo -> build -> hit akhir.
Waktu tiap bagian diberikan lewat argumen (detik) lalu dibulatkan ke batas bar, supaya bisa dibuat ulang
begitu durasi VO final diketahui:

  python make-audio-v3.py --drop 14.6 --build 78 --hit 84 --end 88

Butuh numpy dan scipy.
"""
import argparse
import datetime
import hashlib
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "videos/v3/assets"
SR = 44100
BPM = 115
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(31102026)  # deterministik: hasil sama tiap dijalankan


# ---------------------------------------------------------------- util DSP
def t_(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    b, a = butter(order, f / (SR / 2), "low")
    return lfilter(b, a, x)


def hp(x, f, order=2):
    b, a = butter(order, f / (SR / 2), "high")
    return lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return lfilter(b, a, x)


def noise(d):
    return rng.uniform(-1, 1, int(d * SR))


def save(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) or 1) * 0.89  # -1 dBFS
    wavfile.write(path, SR, (x * 32767).astype(np.int16))


def put(buf, x, at, gain=1.0):
    i = int(at * SR)
    n = min(len(x), buf.shape[0] - i)
    if n <= 0:
        return
    buf[i:i + n, 0] += x[:n] * gain
    buf[i:i + n, 1] += x[:n] * gain


def put_st(buf, xl, xr, at, gain=1.0):
    i = int(at * SR)
    n = min(len(xl), buf.shape[0] - i)
    if n <= 0:
        return
    buf[i:i + n, 0] += xl[:n] * gain
    buf[i:i + n, 1] += xr[:n] * gain


# ------------------------------------------------------------------ SFX
def sfx_click():
    t = t_(0.09)
    return 0.35 * noise(0.09) * np.exp(-110 * t) + 0.5 * np.sin(2 * np.pi * 1800 * t) * np.exp(-120 * t)


def sfx_tick():
    t = t_(0.06)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-140 * t)


def sfx_thud():
    t = t_(0.6)
    ph = 2 * np.pi * np.cumsum(45 + 90 * np.exp(-14 * t)) / SR
    return np.sin(ph) * np.exp(-6 * t) + 0.25 * lp(noise(0.6), 900) * np.exp(-40 * t)


def sfx_whoosh():
    d = 0.9
    t = t_(d)
    x = noise(d)
    out = np.zeros_like(x)
    seg = 12
    n = len(x) // seg
    for k in range(seg):  # pita frekuensi menyapu naik lalu turun
        c = 500 + 2600 * np.sin(np.pi * (k + .5) / seg)
        sl = slice(k * n, (k + 1) * n)
        out[sl] = bp(x[sl], c * 0.6, c * 1.5)
    return out * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6


def sfx_riser(d=1.3):
    t = t_(d)
    x = hp(noise(d), 1200) * (t / d) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2.2 * t / d)) / SR) * (t / d) ** 2.5 * 0.35
    return x + tone


def sfx_hit(d=1.6):
    t = t_(d)
    sub = np.sin(2 * np.pi * np.cumsum(40 + 110 * np.exp(-9 * t)) / SR) * np.exp(-2.6 * t)
    crash = hp(noise(d), 3000) * np.exp(-3.2 * t) * 0.5
    stab = sum(np.sin(2 * np.pi * f * t) for f in (220, 261.63, 329.63, 440)) * np.exp(-3.5 * t) * 0.12
    return sub + crash + stab


def sfx_ding():
    t = t_(0.9)
    n1 = np.sin(2 * np.pi * 880 * t) * np.exp(-6 * t)
    n2 = np.zeros_like(t)
    m = t >= 0.14
    tt = t[m] - 0.14
    n2[m] = (np.sin(2 * np.pi * 1318.5 * tt) + 0.3 * np.sin(2 * np.pi * 2637 * tt)) * np.exp(-6 * tt)
    return 0.7 * n1 + 0.8 * n2


def sfx_ring2x():
    """Dering telepon dua kali: nada ganda 440+480 Hz dimodulasi 20 Hz, disaring ala speaker telepon."""
    out = np.zeros(int(2.6 * SR))
    t = t_(0.9)
    x = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 20 * t)))
    x = x * np.minimum(1, t / 0.02) * np.minimum(1, (0.9 - t) / 0.03)
    for start in (0.0, 1.3):
        i = int(start * SR)
        out[i:i + len(x)] += x
    return bp(out, 300, 3400)


def sfx_stamp():
    t = t_(0.5)
    slap = hp(noise(0.5), 1500) * np.exp(-60 * t) * 0.8
    body = np.sin(2 * np.pi * np.cumsum(70 + 160 * np.exp(-25 * t)) / SR) * np.exp(-12 * t)
    return slap + body


def sfx_pop():
    t = t_(0.14)
    return np.sin(2 * np.pi * np.cumsum(380 + 700 * (t / 0.14)) / SR) * np.exp(-26 * t)


SFX = {"click": sfx_click, "tick": sfx_tick, "thud": sfx_thud, "whoosh": sfx_whoosh, "riser": sfx_riser,
       "hit": sfx_hit, "ding": sfx_ding, "ring2x": sfx_ring2x, "stamp": sfx_stamp, "pop": sfx_pop}


# ---------------------------------------------------------------- musik
ROOTS = [55.0, 43.65, 65.41, 49.0]  # Am F C G (bass)
CHORDS = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]


def kick():
    t = t_(0.45)
    return np.sin(2 * np.pi * np.cumsum(48 + 130 * np.exp(-28 * t)) / SR) * np.exp(-7 * t) + 0.3 * noise(0.45) * np.exp(-200 * t)


def clap():
    d = 0.3
    t = t_(d)
    env = np.exp(-22 * t)
    for k in (0.012, 0.024):  # tiga lapisan tepuk
        env = env + np.where(t > k, np.exp(-22 * np.clip(t - k, 0, None)), 0) * 0.6
    return bp(noise(d), 900, 5000) * env * 0.8


def hat(open_=False):
    d = 0.25 if open_ else 0.06
    return hp(noise(d), 7000) * np.exp(-(14 if open_ else 70) * t_(d))


def pluck(f, d=0.35):
    t = t_(d)
    x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t) + 0.12 * np.sin(8 * np.pi * f * t)) * np.exp(-11 * t)
    return x * np.minimum(1, t / 0.003)


def bass_note(f, d):
    t = t_(d)
    x = lp(2 * ((t * f) % 1) - 1, 420) * 0.9 + np.sin(2 * np.pi * f * t) * 0.8
    return x * np.minimum(1, t / 0.005) * np.minimum(1, (d - t) / 0.03)


def pad_chord(freqs, d):
    t = t_(d)
    L = np.zeros_like(t)
    R = np.zeros_like(t)
    for f in freqs:
        for det, w, side in ((-0.004, 1, 0), (0.0, 0.8, 1), (0.004, 1, 2)):
            saw = (2 * ((t * f * (1 + det)) % 1) - 1) * w
            if side == 0:
                L += saw
            elif side == 2:
                R += saw
            else:
                L += saw * 0.6
                R += saw * 0.6
    env = np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.4)
    return lp(L, 1400) / 9 * env, lp(R, 1400) / 9 * env


def make_music(drop, build, hit, end, path):
    nbars = int(round(end / BAR))
    drop_b = int(round(drop / BAR))
    build_b = int(round(build / BAR))
    hit_b = min(nbars - 1, int(round(hit / BAR)))
    total = hit_b * BAR + 4.0  # ekor setelah hit
    mix = np.zeros((int(total * SR), 2))
    kick_times = []
    K, C, H, HO = kick(), clap(), hat(), hat(True)

    for bar in range(hit_b):
        b0 = bar * BAR
        chord, root = CHORDS[bar % 4], ROOTS[bar % 4]
        intro = bar < drop_b
        groove = drop_b <= bar < build_b
        L, R = pad_chord(chord, BAR + 0.3)
        put_st(mix, L, R, b0, 0.35 if intro else 0.5 if groove else 0.7)
        tones = chord + [chord[0] * 2]
        if intro:
            for k, off in enumerate((0, 1.5, 2.5)):  # pluck jarang, nada atas
                put(mix, pluck(chord[(k + bar) % 3] * 2), b0 + off * BEAT, 0.28)
            if bar >= drop_b - 2:  # hat halus menjelang drop
                for s in range(8):
                    put(mix, H, b0 + s * BEAT / 2, 0.10 + 0.01 * (bar - (drop_b - 2)))
            if bar == drop_b - 1:  # roll tepuk setengah bar terakhir
                for s in range(8):
                    put(mix, C, b0 + 2 * BEAT + s * BEAT / 4, 0.12 + 0.05 * s)
            continue
        for bt in range(4):  # kick empat-ke-lantai
            put(mix, K, b0 + bt * BEAT, 0.95)
            kick_times.append(b0 + bt * BEAT)
        for bt in (1, 3):
            put(mix, C, b0 + bt * BEAT, 0.55)
        for s in range(8):
            put(mix, H if s % 2 else HO * 0.5, b0 + s * BEAT / 2, 0.16 if s % 2 else 0.12)
        if groove:
            for s in range(8):
                put(mix, bass_note(root, BEAT * 0.45), b0 + s * BEAT / 2, 0.55)
            pat = [0, 2, 1, 3, 2, 1, 3, 2, 0, 2, 1, 3, 2, 3, 1, 2]
            for s, p in enumerate(pat):
                put(mix, pluck(tones[p] * 2), b0 + s * BEAT / 4, 0.24 if s % 2 else 0.34)
        else:  # build: roll tepuk makin rapat, arp 16-an, bass panjang
            steps = 16 if bar == hit_b - 1 else 8
            for s in range(steps):
                put(mix, C, b0 + s * BAR / steps, 0.25 + 0.5 * (s / steps))
            for s in range(16):
                put(mix, pluck(tones[s % 4] * 2), b0 + s * BEAT / 4, 0.3)
            put(mix, bass_note(root, BEAT * 0.9), b0, 0.5)

    hb = hit_b * BAR  # hit akhir
    put(mix, K, hb, 1.0)
    put(mix, sfx_hit(2.4) / 1.0, hb, 0.9)
    for f in CHORDS[0]:
        put(mix, pluck(f, 1.6), hb, 0.2)
    L, R = pad_chord(CHORDS[0], 2.4)
    put_st(mix, L, R, hb, 0.7)

    # sidechain ringan: seluruh campuran menunduk sesaat setelah tiap kick
    tt = np.arange(len(mix)) / SR
    kt = np.array(kick_times)
    if len(kt):
        idx = np.searchsorted(kt, tt, side="right") - 1
        since = np.where(idx >= 0, tt - kt[np.clip(idx, 0, None)], 9.0)
        mix *= (1 - 0.38 * np.exp(-since / 0.11))[:, None]
    mix *= np.minimum(1, tt / 1.2)[:, None]
    mix *= np.minimum(1, (tt[-1] - tt) / 1.8)[:, None]
    mix = np.tanh(mix * 1.1)
    mix = mix / np.max(np.abs(mix)) * 0.89
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, SR, (mix * 32767).astype(np.int16))
    return dict(bpm=BPM, bar=round(BAR, 3), drop_s=round(drop_b * BAR, 2), build_s=round(build_b * BAR, 2), hit_s=round(hb, 2), durasi_s=round(total, 2))


# ---------------------------------------------------------------- main
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", type=float, default=14.6)
    ap.add_argument("--build", type=float, default=78.0)
    ap.add_argument("--hit", type=float, default=84.0)
    ap.add_argument("--end", type=float, default=88.0)
    a = ap.parse_args()

    sfx_dir = V3 / "sfx"
    for name, fn in SFX.items():
        save(sfx_dir / f"{name}.wav", fn())
    info = make_music(a.drop, a.build, a.hit, a.end, V3 / "music/bgm.wav")

    # audio telepon asli S1 (assets/rekaman/S1/, satu berkas per baris transkrip), EQ telepon 320-3400 Hz.
    #   s1-hook.wav : baris 6 jawaban Pak Andi "Tiga kali. Awal bulan, ..." (0-3,40 dtk), pembuka video sebelum VO
    #   s1-qa.wav   : baris 5 tanya jumlah + awal baris 6 "Tiga kali." (0-0,62 dtk), adegan D3
    EQ = "highpass=f=320,lowpass=f=3400,acompressor=threshold=-22dB:ratio=3"
    rek = ROOT / "assets/rekaman/S1"
    hook, call = V3 / "call/s1-hook.wav", V3 / "call/s1-qa.wav"
    call.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(rek / "06.mp3"),
                    "-af", f"atrim=0:3.40,{EQ},afade=t=in:d=0.03,afade=t=out:st=3.25:d=0.15,volume=1.1", "-ar", "44100", "-ac", "1", str(hook)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(rek / "05.mp3"), "-i", str(rek / "06.mp3"), "-filter_complex",
                    f"[0]atrim=0:3.45,apad=pad_dur=0.25[a];[1]atrim=0:0.62,afade=t=out:st=0.5:d=0.12[b];[a][b]concat=n=2:v=0:a=1,{EQ},afade=t=in:d=0.03,volume=1.1",
                    "-ar", "44100", "-ac", "1", str(call)], check=True)

    files = sorted(list(sfx_dir.glob("*.wav")) + [V3 / "music/bgm.wav", hook, call])
    rows = "\n".join(f"| `{p.relative_to(V3)}` | {sha(p)} |" for p in files)
    (V3 / "LISENSI-AUDIO.md").write_text(f"""# Bukti lisensi audio video demo v3

Dibuat {datetime.date.today().isoformat()} oleh `videos/tools/make-audio-v3.py` (seed acak tetap 31102026, hasil bisa direproduksi).

## SFX dan backsound
- Seluruhnya **disintesis dari rumus** (sinus, derau, filter) di skrip. Tidak memakai sampel, loop, atau materi pihak ketiga.
- Hak cipta dipegang tim Veritas. Dilepas sebagai **CC0** (domain publik), bebas dipakai dan disebarkan tanpa atribusi.
- Tanpa vokal. Parameter musik: {info['bpm']} BPM, bar {info['bar']} dtk, drop {info['drop_s']} dtk, build {info['build_s']} dtk, hit {info['hit_s']} dtk, durasi {info['durasi_s']} dtk.
- Cara buat ulang: `python videos/tools/make-audio-v3.py --drop {a.drop} --build {a.build} --hit {a.hit} --end {a.end}`

## Audio telepon S1 (`call/s1-hook.wav`, `call/s1-qa.wav`)
- Dari `assets/rekaman/S1/` (satu berkas per baris transkrip), diberi EQ telepon (320-3400 Hz).
- `s1-hook.wav`: baris 06 (jawaban "Tiga kali. Awal bulan, ..."), 0-3,40 dtk. `s1-qa.wav`: baris 05 (tanya jumlah) + 0-0,62 dtk baris 06 ("Tiga kali.").
- Sumber: rekaman **simulasi dari suara buatan ElevenLabs**, bukan suara orang sungguhan (sudah diberi keterangan itu di aplikasi).

## VO
- ElevenLabs (suara Velora v3). Lisensi mengikuti paket akun ElevenLabs yang dipakai tim saat generate. Isi paket dan tanggal generate dicatat setelah VO dibuat.

## Checksum (sha256, 16 karakter pertama)
| File | sha256 |
|---|---|
{rows}
""")
    print("selesai", info)


if __name__ == "__main__":
    main()
