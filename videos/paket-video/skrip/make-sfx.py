#!/usr/bin/env python3
"""Sintesis efek suara dan musik latar sederhana lewat ffmpeg (tanpa sumber luar, bebas hak cipta).

Hasil ke demo/assets/sfx: click, tick, whoosh, ding, sting, bgm (mono 44.1 kHz).
Musik latar berupa pad hangat berprogresi akor lambat; sengaja halus supaya tidak
bersaing dengan narasi. Ganti dengan lagu berlisensi bila tim punya.
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "demo/assets/sfx"
OUT.mkdir(parents=True, exist_ok=True)
SR = 44100


def ff(name, src, af="", dur=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src]
    if af:
        cmd += ["-af", af]
    cmd += ["-ar", str(SR), "-ac", "1", OUT / f"{name}.wav"]
    subprocess.run([str(c) for c in cmd], check=True)


def aeval(expr, d):
    return f"aevalsrc='{expr}':s={SR}:d={d}"


# klik halus: letupan derau singkat + nada pendek
ff("click", aeval("(0.35*(2*random(1)-1)*exp(-110*t))+0.5*sin(2*PI*1800*t)*exp(-120*t)", 0.09), "highpass=f=900,volume=1.4")
# tick kecil untuk teks atau label muncul
ff("tick", aeval("sin(2*PI*2400*t)*exp(-140*t)", 0.06), "volume=0.6")
# whoosh: derau merah muda disaring, naik lalu turun
ff("whoosh", f"anoisesrc=c=pink:d=0.8:r={SR}:a=0.9", "highpass=f=250,lowpass=f=2600,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.45,volume=0.6")
# ding lembut
ff("ding", aeval("0.6*sin(2*PI*988*t)*exp(-5*t)+0.3*sin(2*PI*1480*t)*exp(-6.5*t)+0.12*sin(2*PI*1976*t)*exp(-9*t)", 0.9), "volume=0.7")
# sting logo: denyut bas rendah + kilau tinggi
ff("sting", aeval("0.9*sin(2*PI*(55+25*exp(-6*t))*t)*exp(-2.2*t)+min(1,t*12)*exp(-1.6*t)*(0.25*sin(2*PI*659*t)+0.18*sin(2*PI*988*t)+0.12*sin(2*PI*1319*t))", 2.2), "volume=0.8")

# musik latar: pad akor lambat (Cmaj7 - Am7 - Fmaj7 - G6), 8 detik per akor
CH = [(130.81, 164.81, 196.0, 246.94), (110.0, 130.81, 164.81, 196.0), (87.31, 130.81, 174.61, 220.0), (98.0, 123.47, 146.83, 196.0)]
def chord_expr(ch):
    return "+".join(f"0.1*(sin(2*PI*{f-0.6}*t)+sin(2*PI*{f}*t)+sin(2*PI*{f+0.6}*t))+0.02*sin(2*PI*{f*2}*t)" for f in ch)
k = "mod(floor(t/8),4)"
body = f"if(eq({k},0),{chord_expr(CH[0])},if(eq({k},1),{chord_expr(CH[1])},if(eq({k},2),{chord_expr(CH[2])},{chord_expr(CH[3])})))"
env = "pow(sin(PI*mod(t,8)/8),1.5)"
sparkle = "0.04*sin(2*PI*(if(eq(mod(floor((t-2)/4),4),0),523.25,if(eq(mod(floor((t-2)/4),4),1),659.25,if(eq(mod(floor((t-2)/4),4),2),783.99,659.25))))*t)*exp(-2.2*mod(t-2,4))*gte(t,2)"
ff("bgm", aeval(f"({body})*{env}+{sparkle}", 110), "afade=t=in:d=2,afade=t=out:st=107:d=3,volume=0.45")
print("sfx ->", OUT)
