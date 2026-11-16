"""Skor pola Vedika Autentik: satu definisi fitur, bin, skor, dan alasan.

Dipakai oleh pembangun referensi (ai-service), pelatih model, backend, dan uji. Hanya pustaka standar.
Skor pola hanya mengurutkan antrean dan menjelaskan alasannya. Skor tidak memicu panggilan,
tidak memberi label, dan tidak mengubah status RS: itu tetap tugas tools/aturan.py.
"""
import math
from collections import Counter
from datetime import timedelta

FITUR = ("sesi", "maks_minggu", "ahad_libur", "episode")
BIN = {
    "sesi": [str(n) for n in range(1, 13)] + ["13+"],
    "maks_minggu": [str(n) for n in range(1, 6)] + ["6+"],
    "ahad_libur": ["0", "1", "2+"],
    "episode": [str(n) for n in range(1, 7)] + ["7+"],
}
EPISODE_MAKS = 7


def bulan_sebelumnya(ym, n):
    y, m = map(int, ym.split("-"))
    m -= n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def fitur_bulan(tanggal_bulan_ini, bulan_aktif, bulan, libur):
    """Fitur mentah satu pasien (di satu RS bila diketahui) pada satu bulan.
    tanggal_bulan_ini: list[date] sesi di bulan itu; bulan_aktif: set 'YYYY-MM' yang punya sesi; libur: set[date]."""
    minggu = Counter(t - timedelta(days=t.weekday()) for t in tanggal_bulan_ini)
    episode = 1
    while episode < EPISODE_MAKS and bulan_sebelumnya(bulan, episode) in bulan_aktif:
        episode += 1
    return {
        "sesi": len(tanggal_bulan_ini),
        "maks_minggu": max(minggu.values()),
        "ahad_libur": sum(t.weekday() == 6 or t in libur for t in tanggal_bulan_ini),
        "episode": episode,
    }


def bin_nilai(fitur, nilai):
    daftar = BIN[fitur]
    return str(nilai) if str(nilai) in daftar else daftar[-1 if nilai > 0 else 0]


def bin_fitur(fitur):
    return {f: bin_nilai(f, fitur[f]) for f in FITUR}


def indikator(fitur):
    """(I1, I2, I3, I4) dari fitur mentah; sama dengan aturan.hitung_indikator (diuji di uji_pola.py)."""
    return (fitur["sesi"] > 8, fitur["maks_minggu"] >= 3, fitur["episode"] >= 6, fitur["ahad_libur"] > 0)


def kombinasi(i1, i2, i3, i4):
    aktif = [f"I{n}" for n, v in enumerate((i1, i2, i3, i4), 1) if v]
    return "+".join(aktif) or "-"


def skor(model, fitur):
    b = bin_fitur(fitur)
    z = model["intersep"] + sum(model["koefisien"][f].get(b[f], 0.0) for f in model["fitur"])
    return round(1 / (1 + math.exp(-z)), 3)


def persen(x):
    """Persen gaya Indonesia: satu desimal dengan koma, tanpa ',0'; tidak pernah dibulatkan menjadi 100 atau 0."""
    x = min(x, 99.9) if x < 100 else x
    if 0 < x < 0.1:
        return "kurang dari 0,1"
    return f"{x:.1f}".replace(".", ",").removesuffix(",0")


def _teks(f, nilai, di_bawah, punya_libur):
    if f == "sesi":
        return f"{nilai} sesi dalam sebulan; lebih tinggi dari {persen(di_bawah)}% bulan-pasien fisioterapi nasional"
    if f == "maks_minggu":
        return f"{nilai} sesi dalam satu minggu; lebih tinggi dari {persen(di_bawah)}% bulan-pasien fisioterapi nasional"
    if f == "ahad_libur":
        return f"{nilai} sesi di hari Minggu/libur; hanya {persen(punya_libur)}% bulan-pasien nasional punya sesi seperti ini"
    lama = f"{nilai} bulan atau lebih" if nilai >= EPISODE_MAKS else f"{nilai} bulan"
    return f"{lama} berturut-turut ada sesi; lebih panjang dari {persen(di_bawah)}% bulan-pasien fisioterapi nasional"


def alasan(model, referensi, fitur, n=2):
    """n fitur dengan sumbangan positif terbesar terhadap skor, dibanding rata-rata nasional."""
    b = bin_fitur(fitur)
    hasil = []
    for f in model["fitur"]:
        koef = model["koefisien"][f]
        p = referensi["marginal"][f]
        kontribusi = koef.get(b[f], 0.0) - sum(p.get(x, 0.0) * koef.get(x, 0.0) for x in BIN[f])
        if kontribusi <= 0:
            continue
        posisi = BIN[f].index(b[f])
        sampai = sum(p.get(x, 0.0) for x in BIN[f][:posisi + 1])
        di_bawah = sum(p.get(x, 0.0) for x in BIN[f][:posisi])
        hasil.append({
            "fitur": f, "nilai": fitur[f], "kontribusi": round(kontribusi, 3),
            "persentil_nasional": round(100 * sampai, 1),
            "teks": _teks(f, fitur[f], 100 * di_bawah, 100 * (1 - p.get("0", 0.0))),
        })
    return sorted(hasil, key=lambda a: (-a["kontribusi"], FITUR.index(a["fitur"])))[:n]
