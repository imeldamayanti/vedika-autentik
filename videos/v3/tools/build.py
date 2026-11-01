#!/usr/bin/env python3
"""Bangun videos/v3/index.html (video demo Vedika Autentik v3, 1:28).

Masukan : timing.json (tools/timeline.py), vo.json + assets/vo/*.align.json (tools/gen_vo.py),
          assets/screen/demo.marks.json (tools/record-demo-v3.mjs), assets/sfx|music|call.
Babak 1 dan penutup = motion graphic dari data uji (klaim S1 Agustus, 300 pasien aktif / 30 terpicu)
dengan token visual website (app.css): Plus Jakarta Sans, kartu putih radius 10, lencana kuning.
Keluaran: videos/v3/index.html (dari tools/index.template.html).

Jalankan dari akar repo:  python3 videos/v3/tools/build.py
"""
import html
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIM = json.loads((ROOT / "timing.json").read_text())
T, S0, DUR = TIM["vo"], TIM["scene"], TIM["dur"]
TOTAL = TIM["total"]
CALL_DUR = TIM["call_dur"]
MARKS = json.loads((ROOT / "assets/screen/demo.marks.json").read_text())
K = MARKS["klik"]                    # [otomatis, baris S1, ringkasan, lihat kartu RS, setujui]
VOT = json.loads((ROOT / "vo.json").read_text())
ALIGN = {k: json.loads((ROOT / f"assets/vo/{k}.align.json").read_text()) for k in VOT}


def probe(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())


# ----------------------------------------------------------------- penanda waktu
S = {"sc": round(S0["S"] - 1.9, 2), "d1": S0["D1"], "d2": S0["D2"], "d3": S0["D3"], "d4": S0["D4"], "d5": S0["D5"], "d6": S0["D6"], "z": S0["Z"]}
HIT = S0["S"]                        # kunci logo = hit musik (drop)
BAR = 60 / 115 * 4                   # make-audio-v3.py membulatkan drop/hit ke batas bar
BGM_OFF = round(round(HIT / BAR) * BAR - HIT, 3)          # musik dimulai sekian detik lebih awal supaya drop tepat di HIT
Z_HIT = round(round(TIM["z_hit"] / BAR) * BAR - BGM_OFF, 2)  # hit musik penutup
Z_SCAN = round(Z_HIT - 0.9, 2)
P0 = 17.06 - (S["d3"] - S["d1"])     # detik rekaman yang tampil di awal D1 (D1-D2-D3A satu potongan menerus)
KL0 = K[0]                           # detik klik "Mode otomatis" = awal panggilan S1
B_SRC = round(KL0 + 6 + 35.14 + 0.55, 2)  # rekaman layar saat audio telepon (baris 5, 35,14 dtk) mulai; +0,55 supaya baris "Tiga kali" muncul bersama suaranya
C_SRC = round(KL0 + 59.0, 2)         # isian "Tanggal libur: Membantah" terisi
D4_SRC, D5B_SRC, D5A_SRC, D6_SRC = 87.6, 28.2, 104.5, 112.44
CALL_END = round(T["call"] + CALL_DUR, 2)
CUT5 = round(S["d5"] + 5.2, 2)       # ringkasan "sebelum" -> "sesudah"
STAMP_T = round(CUT5 + 0.5, 2)
vt = lambda src: round(S["d1"] + (src - P0), 2)   # detik video untuk detik rekaman (potongan D1-D3A)

# ----------------------------------------------------------------- rekaman layar
XF = 0.3
segs = [  # id, mulai, akhir, detik rekaman
    ("sc1", S["d1"], T["call"], P0), ("sc2", T["call"], CALL_END, B_SRC), ("sc3", CALL_END, S["d4"], C_SRC),
    ("sc4", S["d4"], S["d5"], D4_SRC), ("sc5", S["d5"], CUT5, D5B_SRC), ("sc6", CUT5, S["d6"], D5A_SRC),
    ("sc7", S["d6"], round(S["z"] + 1.2, 2), D6_SRC)]
clips, xfs = [], []
for i, (cid, a, b, src) in enumerate(segs):
    ext = XF if i + 1 < len(segs) else 0       # klip berikutnya melebur di atasnya
    clips.append({"id": cid, "s": a, "d": round(b - a + ext, 2), "src": src})
    if i:
        xfs.append({"id": cid, "s": a})
screen_html = "\n".join(
    f'<video id="{c["id"]}" class="clip scr" src="assets/screen/demo-hf.mp4" muted playsinline data-start="{c["s"]}" '
    f'data-duration="{c["d"]}" data-media-start="{c["src"]}" data-track-index="3"></video>' for c in clips)

# ----------------------------------------------------------------- sorot dalam jendela (koordinat rekaman 1920x1080)
RINGS = [  # x, y, w, h, mulai, durasi
    (846, 526, 349, 41, S["d1"] + 2.3, 4.0),                       # chip indikator I1 I2 I4
    (1362, 375, 377, 65, vt(KL0) - 1.2, 1.5),                      # tombol Mode otomatis
    (1384, 211, 504, 298, T["d4"] + 3.0, 2.8),                     # kartu Selisih 8
    (1380, 482, 193, 44, CUT5 + 0.2, 2.8),                         # status RS Melati
    (1395, 761, 468, 65, S["d6"] + (K[4] - 1.2 - D6_SRC), 1.5),    # Setujui saran
]
rings_html = "\n".join(
    f'<div class="ring clip" id="ring-{i}" data-start="{round(s, 2)}" data-duration="{d}" data-track-index="10" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
    for i, (x, y, w, h, s, d) in enumerate(RINGS))

# ----------------------------------------------------------------- label langkah
STEPS = [("d1", "d2", "1", "Antrean"), ("d2", "d3", "2", "Notifikasi WA"), ("d3", "d4", "3", "Panggilan"),
         ("d4", "d5", "4", "Kartu bukti"), ("d5", "d6", "5", "Ringkasan RS"), ("d6", "z", "6", "Keputusan")]
steps_html = "\n".join(
    f'<div class="step clip" id="st-{a}" data-start="{S[a]}" data-duration="{round(S[b] - S[a] - 0.05, 2)}" data-track-index="6"><div class="step-in">'
    f'<span class="step-no">{n}</span><span class="step-rule"></span><span class="step-ti">{ti}</span></div></div>'
    for a, b, n, ti in STEPS)
STAGE_S, STAGE_E = round(S["d1"] - 0.1, 2), round(S["z"] + 0.7, 2)

# ----------------------------------------------------------------- overlay layar
PESAN = ("Halo Andi Pratama. Ini BPJS Kesehatan. Dalam 1 menit kami akan menelepon dari nomor 0800-0000-0165 untuk konfirmasi singkat "
         "layanan fisioterapi Andi Pratama di RS Melati Sehat bulan Agustus. Ini bukan tagihan. Kami tidak akan meminta data pribadi, "
         "kode OTP, atau pembayaran. Untuk memastikan pesan ini, hubungi Care Center 165.")
CALLOUT_S = round(S["d1"] + 2.5, 2)
C2_T0 = round(T["d4"] + 3.45, 2)
WAVE_S = T["call"]
PH_S, PH_E = round(T["d2"] + 2.3, 2), round(S["d3"] - 0.2, 2)


def ov(i, start, end, style, inner, cls="", extra=""):
    return (f'<div class="ov {cls} clip" id="{i}" data-start="{round(start, 2)}" data-duration="{round(end - start, 2)}" data-track-index="11" '
            f'style="{style}" {extra}>{inner}</div>')


strip11 = "".join(f"<div>{n}</div>" for n in range(11, 2, -1))
strip3 = "".join(f"<div>{n}</div>" for n in range(3, 12))
overlays = [
    ov("call-chips", CALLOUT_S, CALLOUT_S + 4.2, "left:500px;top:740px", "<span><b>11</b> sesi/bulan</span><span><b>4</b> sesi/minggu</span><span>sesi <b>17 Agustus</b></span>", "callout"),
    ov("call-leader", CALLOUT_S, CALLOUT_S + 4.2, "left:821px;top:668px;height:72px", "", "leader"),
    ov("wa-phone", PH_S - 0.5, PH_E, "left:1370px;top:150px", f'<div class="phone"><div class="scr"><div class="hd"><i></i><div><b>0800-0000-0165</b><span>Nomor tim · Simulasi</span></div></div>'
       f'<div class="bd"><div class="dayt"><span>Hari ini</span></div><div class="bub">{html.escape(PESAN)}<small>09.20</small></div></div></div></div>', "", 'data-dx="140" data-dy="0"'),
    ov("wa-safe", PH_S + 0.6, PH_E, "left:760px;top:430px", '<div class="safe"><div><i>✓</i>Tanpa tautan</div><div><i>✓</i>Tanpa minta data</div><div><i>✓</i>Cek ke 165</div></div>'),
    ov("wave", WAVE_S, CALL_END, "left:1440px;top:790px", '<div class="waveb">' + "<i></i>" * 26 + '</div><div class="wavel">Rekaman simulasi · telepon</div>'),
    ov("c2", T["d4"] + 2.1, T["d4"] + 6.6, "left:140px;top:690px",
       f'<div class="cnt"><div class="row"><div class="win"><div class="strip" data-layout-allow-overflow data-layout-allow-occlusion>{strip11}</div></div><div class="tx">ditagih RS<br>kata Pak Andi: 3</div></div><div class="sel">Selisih 8<u></u></div></div>', "cnt"),
    ov("bd", S["d5"] + 0.2, S["d6"] - 0.1, "left:140px;top:690px",
       '<div class="rs">RS Melati Sehat</div><div class="st"><div id="bd-before"><div class="big">2 dari 4<small> tidak sesuai</small></div><span class="chipst ok">Normal</span></div>'
       '<div id="bd-after"><div class="big">3 dari 5<small> tidak sesuai</small></div><span class="chipst no">Perlu klarifikasi RS</span></div></div>', "badge"),
    ov("n6", S["d6"] + (K[4] + 0.2 - D6_SRC), S["z"] - 0.25, "left:140px;top:660px", "Tercatat: <b>siapa · kapan · alasan</b>", "note"),
]
overlays_html = "\n".join(overlays)

# ----------------------------------------------------------------- babak 1 + penutup (motion dari data uji)
TGL = [3, 4, 6, 10, 11, 13, 16, 17, 20, 24, 27]      # klaim_sesi.csv: P-S1, RS01, Agustus 2026 (SEP-UJI-004697..707)
TANDA = {16: "Minggu", 17: "Libur nasional"}
HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
PITA = [(3, 7, "awal bulan"), (12, 15, "pertengahan"), (24, 28, "dua puluhan")]   # jawaban Pak Andi, tanpa tanggal pasti
CW, CH, CG, HDH = 104, 92, 10, 34


def kol(d):                                           # 1 Agustus 2026 = Sabtu; kolom 0 = Senin
    return (d + 4) % 7


def baris(d):
    return (d + 4) // 7


def kalender(p):
    sel = "".join(f'<div class="kh">{h}</div>' for h in HARI)
    sel += '<div class="kd x"></div>' * 5
    for d in range(1, 32):
        tg = f'<span class="tg">{TANDA[d]}</span>' if d in TANDA else ""
        sel += f'<div class="kd{" min" if kol(d) == 6 else ""}{" lb" if d in TANDA else ""}" id="{p}-d{d}">{d}{tg}</div>'
    pita = ""
    for i, (a, b, t) in enumerate(PITA):
        x, y = kol(a) * (CW + CG) - 7, HDH + CG + baris(a) * (CH + CG) - 7
        w = (kol(b) - kol(a) + 1) * (CW + CG) - CG + 14
        pita += f'<div class="pita" data-layout-allow-occlusion id="{p}-pita{i}" style="left:{x}px;top:{y}px;width:{w}px;height:{CH + 14}px"><span>{t}</span></div>'
    return f'<div class="kal-t">Agustus 2026</div><div class="kal-g">{sel}{pita}</div>'


def wave_bars(n, h, seed=7):
    out = []
    for i in range(n):
        seed = (seed * 9301 + 49297) % 233280
        r, t = seed / 233280, i / n
        import math
        env = math.sin(t / 0.17 * math.pi) if t < 0.17 else 0.08 if t < 0.27 else 0.35 + 0.65 * abs(math.sin(t * 23)) if t < 0.98 else 0.05
        out.append(f'<i style="height:{max(6, round(h * env * (0.45 + 0.55 * r)))}px"></i>')
    return "".join(out)


AP = '<div class="avatar">AP</div>'
klaim_rows = "".join(
    f'<div class="klaim{" lb" if d in TANDA else ""}" id="kl{i}"><span class="mono">SEP-UJI-00{4697 + i}</span><b>{HARI[kol(d)]}, {d} Agt</b>'
    f'<span>M54.5 · Low back pain</span><span class="rp">Rp136.900</span></div>' for i, d in enumerate(TGL))
RS_GRID = [("RS Melati Sehat", 68, 27), ("RSU Bakti Mulia", 65, 1), ("RS Cempaka Asri", 59, 1), ("RSU Nusa Sejahtera", 53, 0), ("RS Kenanga Medika", 55, 1)]
grid = ""
for k, (nm, tot, nyala) in enumerate(RS_GRID):    # expected_indikator_2026-08.csv: 300 aktif, 30 terpicu
    cells = ""
    for i in range(tot):
        on = (i * 7) % 68 < 27 and i > 0 if k == 0 else nyala > 0 and i == 17     # sebaran visual; jumlah = data
        cells += f'<i class="{"andi" if k == 0 and i == 0 else "on" if on else ""}"></i>'
    grid += f'<div class="rsg"><div class="cells">{cells}</div><div class="rsn">{nm}<br><b class="{"" if nyala else "nol"}">{nyala} terpicu</b></div></div>'

# waktu babak 1 (detik video)
HK = T["hook"]
B1 = {"hook": HK, "kal": round(HK + 0.55, 2), "pita": [round(HK + x, 2) for x in (1.05, 1.75, 2.6)], "ver": round(T["p1"] + 0.5, 2),
      "p2": round(T["p2"] - 0.25, 2), "kl0": round(T["p2"] + 0.15, 2), "kl_dt": 0.185, "zoom": round(T["p3"] - 0.1, 2),
      "kpk": round(T["p3"] + 2.1, 2), "end": round(S["sc"] + 0.7, 2)}
B1["sel"] = round(B1["kl0"] + 10 * B1["kl_dt"] + 0.45, 2)
babak1 = f"""<div class="clip" id="b1" data-start="0" data-duration="{B1['end']}" data-track-index="7">
  <div class="b1-dots" data-layout-allow-overflow></div>
  <div class="lencana" id="b1-len">Simulasi · data sintetis</div>
  <div id="b1-s2">
    <div id="b1-kiri">
      <div class="panel pas" id="b1-pas">{AP}<div><div class="nm">Andi Pratama</div><div class="sb">Peserta JKN · 54 th · RS Melati Sehat</div></div></div>
      <div class="panel rek" id="b1-rek"><div class="kapital">Rekaman panggilan · simulasi</div><div class="wv" id="b1-wv">{wave_bars(88, 130)}</div></div>
      <div class="panel ver" id="b1-ver"><div class="kapital">Versi peserta</div><div class="vr"><span class="angka hijau" id="b1-ver3">3</span><span class="sesi">sesi</span></div></div>
    </div>
    <div id="b1-klaim"><div class="kapital">Klaim fisioterapi · RS Melati Sehat → BPJS</div><div class="rows">{klaim_rows}</div></div>
    <div id="b1-kal">{kalender("k1")}</div>
    <div class="panel cntp" id="b1-cnt">
      <div><div class="kapital">Ditagih</div><div class="win"><div class="strip" data-layout-allow-overflow data-layout-allow-occlusion>{"".join(f"<div>{n}</div>" for n in range(0, 12))}</div></div></div>
      <div><div class="kapital">Versi peserta</div><div class="angka hijau">3</div></div>
      <div class="sel" id="b1-sel"><div class="kapital">Selisih</div><div class="angka">8</div></div>
    </div>
  </div>
  <div id="b1-s3">
    <div class="kpi"><div class="panel"><span class="angka">300</span><span>pasien fisioterapi<br>aktif Agustus</span></div>
      <div class="panel teal"><span class="angka">30</span><span>terpicu<br>indikator</span></div></div>
    <div class="grid" id="b1-grid">{grid}</div>
    <div class="andi-tag" id="b1-andi">Pak Andi</div>
  </div>
  <div class="panel" id="kpk"><div class="src">KPK · 2024</div><div class="n">3.269 <small>dari 4.341</small></div>
    <div class="t">tagihan fisioterapi <b>tak ada di rekam medis</b>.</div><div class="t2">Terungkap setelah pasien dikonfirmasi.</div>
    <div class="cr">Sumber: KPK dan Itjen Kemenkes, Juli 2024</div></div>
</div>"""

words = "Yang <em>ditagih</em> harus sama dengan yang <em>dijalani</em>.".split(" ")
ZB_E = round(Z_SCAN + 0.7, 2)
ztext = f"""<div class="clip" id="zb" data-start="{round(S['z'] - 0.3, 2)}" data-duration="{round(ZB_E - S['z'] + 0.3, 2)}" data-track-index="7">
  <div class="b1-dots" data-layout-allow-overflow></div>
  <div class="lencana" style="left:80px;top:56px">Simulasi · data sintetis</div>
  <div id="zt">{" ".join(f'<span class="w"><i>{w}</i></span>' for w in words)}</div>
  <div id="z-kiri">
    <div class="panel zk" id="zk1"><div class="kapital">Ditagih rumah sakit</div><div class="vr"><span class="angka">11</span><span class="sesi">sesi</span></div></div>
    <div class="panel zk" id="zk2"><div class="kapital">Versi pasien</div><div class="vr"><span class="angka hijau">3</span><span class="sesi">sesi</span></div></div>
    <div class="zsel" id="zk3"><b>Selisih 8</b> · bahan klarifikasi ke RS</div>
  </div>
  <div id="z-kal">{kalender("k2")}<div class="leg"><span><i class="lg-t"></i>ditagih RS</span><span><i class="lg-p"></i>kata pasien</span><span class="by">dibandingkan berdampingan oleh sistem</span></div></div>
</div>"""

def mark(p):
    return (f'<svg class="mark" id="{p}-mark" viewBox="0 0 48 48" overflow="visible"><path id="{p}-wl" fill="#fff" d="M5 5h13l6 26-5 11L5 11V5Z"/>'
            f'<path id="{p}-wr" fill="#fff" d="M43 5H30l-6 26 5 11L43 11V5Z"/><circle id="{p}-ring" cx="24" cy="33" r="3.4" fill="none" stroke="#F3B441" stroke-width="0.8"/>'
            f'<circle id="{p}-dot" cx="24" cy="33" r="3.4" fill="#F3B441" stroke="#0F3D3E" stroke-width="1.5"/></svg>')


def lockup(p):
    return (f'<div class="lock" id="{p}-lock"><div class="mark-wrap" id="{p}-mw">{mark(p)}</div><div class="words">'
            + "".join(f'<div class="wm-line"><div class="wm-in" id="{p}-w{i}"><span class="wm">{w}</span><span class="wm wm-sh">{w}</span></div></div>'
                      for i, w in ((1, "Vedika"), (2, "Autentik"))) + f'<span class="oline" id="{p}-line"></span></div></div>')


# ----------------------------------------------------------------- subtitle
SUB = []
for k in ("p1", "p2", "p3", "s", "d1", "d2", "d3a", "d3b", "d4", "d5", "d6"):
    kind = "logo" if k == "s" else "demo"
    for seg in ALIGN[k]["seg"]:
        SUB.append({"t": html.escape(seg["t"]), "s": round(T[k] + seg["s"] - 0.08, 2), "e": round(T[k] + seg["e"] + 0.18, 2), "k": kind})
SUB.append({"t": "<b>Pak Andi</b>Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan.", "s": round(HK, 2), "e": round(HK + TIM["hook_dur"] + 0.1, 2), "k": "call"})
SUB.append({"t": "<b>AI</b>Kira-kira berapa kali Bapak datang terapi di bulan Agustus?", "s": round(T["call"], 2), "e": round(T["call"] + 3.5, 2), "k": "call"})
SUB.append({"t": "<b>Pak Andi</b>Tiga kali.", "s": round(T["call"] + 3.6, 2), "e": round(CALL_END + 0.15, 2), "k": "call"})
SUB.sort(key=lambda x: x["s"])
for i in range(len(SUB) - 1):
    if SUB[i]["e"] > SUB[i + 1]["s"] - 0.04:
        SUB[i]["e"] = round(SUB[i + 1]["s"] - 0.04, 2)
subs_html = "\n".join(f'<div class="sub sub-{c["k"]} clip" id="sub-{i:02d}" data-start="{c["s"]}" data-duration="{round(c["e"] - c["s"], 2)}" data-track-index="8"><p>{c["t"]}</p></div>'
                      for i, c in enumerate(SUB))

# ----------------------------------------------------------------- audio
SFX = [  # nama, mulai, volume
    ("click", vt(KL0), 0.34), ("click", vt(K[1]), 0.3), ("click", round(S["d6"] + (K[4] - D6_SRC), 2), 0.34),
    ("ding", round(PH_S - 0.35, 2), 0.5), ("ring2x", T["ring"], 0.5),
    ("thud", B1["sel"], 0.6), ("thud", round(C2_T0 + 1.0, 2), 0.4), ("whoosh", round(B1["zoom"] - 0.1, 2), 0.35),
    ("riser", round(HIT - 1.3, 2), 0.5), ("hit", HIT, 0.55), ("riser", round(Z_HIT - 1.3, 2), 0.5),
    ("whoosh", round(S["sc"] + 0.1, 2), 0.5), ("whoosh", round(S["d1"] - 0.35, 2), 0.5), ("whoosh", round(S["z"] - 0.4, 2), 0.5),
    ("stamp", STAMP_T, 0.6), ("pop", round(S["d6"] + (K[4] + 0.05 - D6_SRC), 2), 0.5),
]
SFX += [("tick", round(B1["kl0"] + k * B1["kl_dt"], 2), 0.4) for k in range(11)]
SFX += [("tick", round(C2_T0 + k * 0.1125, 2), 0.4) for k in range(1, 9)]
SFX.sort(key=lambda x: x[1])
sdur = {n: round(probe(ROOT / f"assets/sfx/{n}.wav"), 2) for n in {x[0] for x in SFX}}
audio = []
for k in VOT:
    audio.append(f'<audio id="vo-{k}" src="assets/vo/{k}.wav" data-start="{T[k]}" data-duration="{ALIGN[k]["dur"]}" data-track-index="20" data-volume="1" data-audio-group="voiceover"></audio>')
audio.append(f'<audio id="hook" src="assets/call/s1-hook.wav" data-start="{HK}" data-duration="{TIM["hook_dur"]}" data-track-index="20" data-volume="1" data-audio-group="voiceover"></audio>')
audio.append(f'<audio id="call" src="assets/call/s1-qa.wav" data-start="{T["call"]}" data-duration="{round(probe(ROOT / "assets/call/s1-qa.wav"), 2)}" data-track-index="20" data-volume="1" data-audio-group="voiceover"></audio>')
for i, (n, ts, vol) in enumerate(SFX):
    audio.append(f'<audio id="fx-{i:02d}-{n}" src="assets/sfx/{n}.wav" data-start="{ts}" data-duration="{sdur[n]}" data-track-index="{22 + i % 3}" data-volume="{vol}" data-audio-group="sfx"></audio>')

# musik: normal 0,85, menunduk ~-14 dB di bawah VO, hampir senyap saat audio telepon. Hit penutup dibiarkan lepas.
FREE, DUCK, CALLV = 0.85, 0.17, 0.05
WIN = []
for k in VOT:
    end = T[k] + ALIGN[k]["dur"] + 0.4
    WIN.append((T[k] - 0.25, min(end, Z_HIT - 0.05) if k == "z0" else end, DUCK))
WIN.append((T["call"] - 0.1, CALL_END + 0.1, CALLV))
WIN.append((HK - 0.1, HK + TIM["hook_dur"] + 0.1, CALLV))


def level(t):
    lv = FREE
    for a, b, v in WIN:
        if a <= t <= b:
            lv = min(lv, v)
        elif a - 0.25 < t < a:
            lv = min(lv, FREE + (v - FREE) * (t - (a - 0.25)) / 0.25)
        elif b < t < b + 0.35:
            lv = min(lv, v + (FREE - v) * (t - b) / 0.35)
    return lv


pts, prev = [], None
for i in range(int(TOTAL * 10) + 1):
    t = round(i / 10, 1)
    v = round(level(t), 3)
    if v != prev or i == int(TOTAL * 10):
        pts.append({"t": t, "v": v})
        prev = v
bgm_dur = round(min(probe(ROOT / "assets/music/bgm.wav") - BGM_OFF, TOTAL), 2)
audio.append(f'<audio id="bgm" src="assets/music/bgm.wav" data-start="0" data-duration="{bgm_dur}" data-media-start="{BGM_OFF}" data-track-index="21" data-volume="1" data-audio-group="music" '
             f"data-automation='{json.dumps({'version': 1, 'lanes': [{'target': 'volume', 'points': pts}]})}'></audio>")

# ----------------------------------------------------------------- kamera
CAM = [
    (STAGE_S, 960, 540, 1.0), (S["d1"] + 0.7, 1128, 560, 1.25), (S["d3"] - 0.3, 1128, 560, 1.25), (S["d3"] + 0.7, 1150, 620, 1.2), (S["d4"] - 0.2, 1150, 620, 1.2),
    (S["d4"] + 0.6, 1125, 380, 1.25), (S["d4"] + 6.0, 1125, 380, 1.25), (S["d4"] + 7.4, 1110, 640, 1.3), (S["d5"] - 0.3, 1110, 640, 1.3),
    (S["d5"] + 0.6, 1110, 500, 1.3), (CUT5 - 0.2, 1110, 500, 1.3), (CUT5 + 0.5, 1110, 540, 1.3), (S["d6"] - 0.3, 1110, 540, 1.3),
    (S["d6"] + 0.6, 1128, 560, 1.25), (S["d6"] + 2.2, 1128, 560, 1.25), (S["d6"] + 3.2, 1500, 640, 1.5), (S["z"] - 0.5, 1500, 640, 1.5),
    (S["z"] + 0.5, 960, 540, 0.7)]
CAM = [[round(t, 2), x, y, s] for t, x, y, s in CAM]

CFG = {"T": T, "S": S, "B1": B1, "TGL": TGL, "XF": xfs, "XFD": XF, "CAM": CAM, "HIT": HIT,
       "TAG_S": round(HIT + 1.0, 2), "STAGE_S": STAGE_S, "STAGE_D": round(STAGE_E - STAGE_S, 2), "CALLOUT_S": CALLOUT_S, "WAVE_S": WAVE_S, "C2_T0": C2_T0,
       "STAMP_T": STAMP_T, "ZB_E": ZB_E, "Z_SCAN": Z_SCAN, "Z_HIT": Z_HIT, "TOTAL": TOTAL}

page = (ROOT / "tools/index.template.html").read_text()
for k, v in {
    "__TOTAL__": str(TOTAL), "__CFG__": json.dumps(CFG, ensure_ascii=False), "__SCREEN__": screen_html, "__RINGS__": rings_html,
    "__STAGE_S__": str(STAGE_S), "__STAGE_D__": str(round(STAGE_E - STAGE_S, 2)), "__STEPS__": steps_html, "__OVERLAYS__": overlays_html,
    "__BABAK1__": babak1, "__ZTEXT__": ztext,
    "__SC_S__": str(S["sc"]), "__SC_D__": str(round(S["d1"] + 0.6 - S["sc"], 2)), "__SLOCK__": lockup("s"), "__ZLOCK__": lockup("z"),
    "__Z_S__": str(Z_SCAN), "__Z_D__": str(round(TOTAL - Z_SCAN, 2)), "__SUBS__": subs_html, "__AUDIO__": "\n".join(audio),
}.items():
    page = page.replace(k, v)
(ROOT / "index.html").write_text(page)
print("total", TOTAL, "| klip", len(clips), "| sub", len(SUB), "| sfx", len(SFX), "| musik titik", len(pts))
