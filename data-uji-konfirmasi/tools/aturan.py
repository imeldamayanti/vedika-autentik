"""Aturan referensi Vedika Autentik (konfirmasi suara).

Satu sumber kebenaran untuk tiga hal yang diuji:
1. indikator per pasien per bulan (F1),
2. label hasil panggilan (F4),
3. status ringkasan rumah sakit (F5).

Aplikasi boleh menulis ulang aturan ini dalam bahasa lain, tetapi hasilnya
harus sama dengan fungsi di berkas ini untuk data uji yang sama.
"""
from collections import defaultdict
from datetime import timedelta

BATAS_SESI_BULAN = 8          # I1: lebih dari 8 sesi dalam sebulan
BATAS_SESI_MINGGU = 3         # I2: 3 sesi atau lebih dalam satu minggu Senin-Minggu
PANJANG_EPISODE = 6           # I3: ada sesi di 6 bulan berturut-turut sampai bulan ini
MIN_INDIKATOR_PICU = 2        # panggilan dipicu jika indikator aktif >= 2
TOLERANSI_SESI = 2            # selisih <= 2 sesi dianggap salah ingat yang wajar
RS_MIN_TIDAK_SESUAI = 3       # RS perlu klarifikasi jika tidak sesuai >= 3 ...
RS_MIN_RASIO = 0.10           # ... dan rasio tidak sesuai / terjawab >= 10%


def bulan_sebelumnya(ym, n):
    y, m = map(int, ym.split("-"))
    m -= n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def hitung_indikator(sesi, libur, bulan):
    """sesi: list dict {id_peserta, id_rs, tanggal (date)}; libur: set[date]; bulan: 'YYYY-MM'.
    Mengembalikan dict (id_peserta, id_rs) -> hasil indikator untuk bulan tersebut."""
    per_pasien_bulan = defaultdict(list)
    for s in sesi:
        per_pasien_bulan[(s["id_peserta"], s["id_rs"], s["tanggal"].strftime("%Y-%m"))].append(s["tanggal"])
    hasil = {}
    for (pid, rs, ym), tgl in per_pasien_bulan.items():
        if ym != bulan:
            continue
        minggu = defaultdict(int)
        for t in tgl:
            minggu[t - timedelta(days=t.weekday())] += 1
        i1 = len(tgl) > BATAS_SESI_BULAN
        i2 = max(minggu.values()) >= BATAS_SESI_MINGGU
        i3 = all((pid, rs, bulan_sebelumnya(bulan, n)) in per_pasien_bulan for n in range(PANJANG_EPISODE))
        tgl_libur = sorted(t for t in tgl if t.weekday() == 6 or t in libur)
        i4 = len(tgl_libur) > 0
        jumlah = int(i1) + int(i2) + int(i3) + int(i4)
        hasil[(pid, rs)] = {
            "id_peserta": pid, "id_rs": rs, "bulan": bulan, "sesi_ditagih": len(tgl),
            "maks_sesi_seminggu": max(minggu.values()),
            "I1_lebih_8_sebulan": i1, "I2_3x_seminggu": i2, "I3_episode_6_bulan": i3, "I4_hari_libur": i4,
            "tanggal_libur": [t.isoformat() for t in tgl_libur],
            "jumlah_indikator": jumlah, "dipicu": jumlah >= MIN_INDIKATOR_PICU,
        }
    return hasil


def label_jawaban(jawaban, sesi_ditagih):
    """jawaban: keluaran pembaca jawaban (skema di README). Mengembalikan (label, alasan)."""
    status = jawaban.get("status_panggilan")
    if status == "tidak_terhubung":
        return "Tidak terhubung", "Panggilan tidak diangkat setelah 2 kali percobaan."
    if status == "menolak":
        return "Menolak", "Penerima tidak bersedia menjawab. Tidak dihitung sebagai sinyal negatif."
    if jawaban.get("hadir") is False:
        return "Tidak sesuai", "Penerima menyatakan tidak pernah menjalani layanan di RS ini pada bulan tersebut."
    if jawaban.get("tanda_bahaya"):
        return "Tidak sesuai", "Ada pernyataan berisiko: " + ", ".join(jawaban["tanda_bahaya"]) + "."
    jmax = jawaban.get("jumlah_maks")
    if jmax is None or jawaban.get("keyakinan") == "rendah":
        return "Tidak yakin", "Penerima tidak ingat jumlah sesi dengan yakin. Tidak dihitung."
    selisih = sesi_ditagih - jmax
    if selisih > TOLERANSI_SESI:
        return "Tidak sesuai", f"Ditagih {sesi_ditagih} sesi, versi penerima paling banyak {jmax} sesi (selisih {selisih})."
    return "Sesuai", f"Ditagih {sesi_ditagih} sesi, versi penerima {jawaban.get('jumlah_min')}-{jmax} sesi. Masih dalam toleransi."


def ringkasan_rs(hasil_panggilan):
    """hasil_panggilan: list dict {id_rs, label}. Mengembalikan dict id_rs -> ringkasan."""
    r = defaultdict(lambda: defaultdict(int))
    for h in hasil_panggilan:
        r[h["id_rs"]][h["label"]] += 1
    out = {}
    for rs, c in sorted(r.items()):
        terjawab = c["Sesuai"] + c["Tidak sesuai"]
        rasio = c["Tidak sesuai"] / terjawab if terjawab else 0.0
        perlu = c["Tidak sesuai"] >= RS_MIN_TIDAK_SESUAI and rasio >= RS_MIN_RASIO
        out[rs] = {
            "id_rs": rs, "sesuai": c["Sesuai"], "tidak_sesuai": c["Tidak sesuai"], "tidak_yakin": c["Tidak yakin"],
            "tidak_terhubung": c["Tidak terhubung"], "menolak": c["Menolak"], "terjawab": terjawab,
            "rasio_tidak_sesuai": round(rasio, 3),
            "status": "Perlu klarifikasi RS" if perlu else "Normal",
        }
    return out
