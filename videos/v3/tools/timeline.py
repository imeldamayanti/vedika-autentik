#!/usr/bin/env python3
"""Hitung timeline video v3 dari durasi VO (assets/vo/*.align.json) -> videos/v3/timing.json.
Video dibuka potongan suara Pak Andi (call/s1-hook.wav) sebelum VO. Drop musik = awal adegan S.
Jalankan ulang tiap VO diganti, lalu make-audio-v3.py dengan --drop/--build/--hit/--end dari keluaran."""
import json
from pathlib import Path
R = Path(__file__).resolve().parent.parent
D = {k: json.load(open(R / f"assets/vo/{k}.align.json"))["dur"] for k in "p1 p2 p3 s d1 d2 d3a d3b d4 d5 d6 z0 z1".split()}
import subprocess
dur = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(R / f)]))
HOOK, CALL, g = round(dur("assets/call/s1-hook.wav"), 2), round(dur("assets/call/s1-qa.wav"), 2), 0.25
t = {"hook": 0.25}
t["p1"] = t["hook"] + HOOK + 0.2
t["p2"] = t["p1"] + D["p1"] + g + 0.1
t["p3"] = t["p2"] + D["p2"] + g
S = t["p3"] + D["p3"] + 0.3
t["s"] = S + 0.7
D1 = t["s"] + D["s"] + 0.2; t["d1"] = D1 + 0.2
D2 = t["d1"] + D["d1"] + 0.2; t["d2"] = D2 + 0.2
D3 = t["d2"] + D["d2"] - 0.2
t["ring"] = D3
t["d3a"] = D3 + 1.2
t["call"] = t["d3a"] + D["d3a"] + 0.2
t["d3b"] = t["call"] + CALL + 0.15
D4 = t["d3b"] + D["d3b"] + 0.35; t["d4"] = D4 + 0.2
D5 = t["d4"] + D["d4"] + 0.3; t["d5"] = D5 + 0.2
D6 = t["d5"] + D["d5"] + 0.3; t["d6"] = D6 + 0.2
Z = t["d6"] + D["d6"] + 0.45; t["z0"] = Z + 0.1
t["z1"] = t["z0"] + D["z0"] + 0.5
end = t["z1"] + D["z1"] + 0.5
sc = dict(S=S, D1=D1, D2=D2, D3=D3, D4=D4, D5=D5, D6=D6, Z=Z)
r = lambda x: {k: round(v, 2) for k, v in x.items()}
Z_HIT = t["z1"] - 0.7                      # hit musik penutup, sesaat sebelum slogan
out = {"vo": r(t), "scene": r(sc), "dur": r(D), "hook_dur": HOOK, "call_dur": CALL, "z_hit": round(Z_HIT, 2), "total": round(end, 2)}
(R / "timing.json").write_text(json.dumps(out, indent=1))
print(out["scene"], "VO", out["vo"], "TOTAL", out["total"])
print(f"musik: --drop {S:.2f} --build {Z - 1.9:.2f} --hit {Z_HIT:.2f} --end {end:.2f}")
