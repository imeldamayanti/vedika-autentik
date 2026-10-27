"""Membangkitkan data uji Vedika Autentik (konfirmasi suara).

Jalankan dari folder data-uji-konfirmasi:  python3 tools/generate.py
Deterministik (seed tetap). Tidak memakai data peserta JKN riil: jumlah sesi per
bulan hanya diambil dari distribusi agregat data panitia (distribusi_sesi_panitia.csv).
"""
import csv, json, random, sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aturan import hitung_indikator, label_jawaban, ringkasan_rs  # noqa: E402

rng = random.Random(2026)
BULAN = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
BULAN_UJI = "2026-08"
LIBUR = [("2026-01-01", "Tahun Baru Masehi"), ("2026-05-01", "Hari Buruh"),
         ("2026-06-01", "Hari Lahir Pancasila"), ("2026-08-17", "Hari Kemerdekaan RI")]
LIBUR_SET = {date.fromisoformat(d) for d, _ in LIBUR}

RS = [
    ("RS01", "RS Melati Sehat", "Swasta setara kelas C", "Kota Sentosa", "pola curang disisipkan"),
    ("RS02", "RSU Bakti Mulia", "Pemerintah kelas B", "Kota Sentosa", "jujur"),
    ("RS03", "RS Cempaka Asri", "Swasta setara kelas C", "Kabupaten Damai", "jujur"),
    ("RS04", "RSU Nusa Sejahtera", "Pemerintah kelas C", "Kabupaten Damai", "jujur"),
    ("RS05", "RS Kenanga Medika", "Swasta setara kelas B", "Kota Sentosa", "jujur"),
]
DX = [("M54.5", "Low back pain", "M-3-16-0", 136900), ("I63.9", "Cerebral infarction, unspecified", "Z-3-12-0", 176900),
      ("M17.9", "Gonarthrosis, unspecified", "M-3-16-0", 136900), ("M75.0", "Adhesive capsulitis of shoulder", "M-3-16-0", 136900),
      ("F80.9", "Developmental disorder of speech and language", "Z-3-12-0", 176900)]
DEPAN = ["Agus", "Bambang", "Rudi", "Dedi", "Eko", "Hari", "Yusuf", "Teguh", "Wahyu", "Fajar", "Sri", "Endang", "Yuni",
         "Ratna", "Lina", "Wati", "Nur", "Ani", "Maya", "Tuti", "Rizky", "Putri", "Bayu", "Dimas", "Intan"]
BELAKANG = ["Saputra", "Hidayat", "Wibowo", "Kurniawan", "Setiawan", "Lestari", "Wulandari", "Handayani", "Susanto",
            "Nugroho", "Rahayu", "Purnamasari", "Siregar", "Harahap", "Gunawan", "Permata", "Utami", "Firmansyah"]

# Distribusi sesi per bulan dari data panitia (agregat)
dist = [(int(r["sesi_per_bulan"]), int(r["jumlah_bulan_pasien"])) for r in csv.DictReader(open(ROOT / "distribusi_sesi_panitia.csv"))]
nilai, bobot = zip(*dist)
ambil_k = lambda: rng.choices(nilai, bobot)[0]


def hari_bulan(ym):
    y, m = map(int, ym.split("-"))
    d = date(y, m, 1)
    while d.month == m:
        yield d
        d += timedelta(days=1)


def hari_kerja(ym):
    return [d for d in hari_bulan(ym) if d.weekday() != 6 and d not in LIBUR_SET]


def pilih_tanggal_jujur(ym, k):
    """Sesi wajar: Senin-Sabtu, maksimal 2 per minggu bila memungkinkan."""
    pool = hari_kerja(ym)
    rng.shuffle(pool)
    out, per_minggu = [], {}
    for d in pool:
        w = d - timedelta(days=d.weekday())
        if per_minggu.get(w, 0) < 2:
            out.append(d)
            per_minggu[w] = per_minggu.get(w, 0) + 1
        if len(out) == k:
            break
    while len(out) < k:  # bulan padat: terpaksa 3 per minggu
        d = rng.choice([x for x in hari_kerja(ym) if x not in out])
        out.append(d)
    return sorted(out)


peserta, sesi, kebenaran = [], [], []
no_klaim = [0]


def tambah_sesi(pid, rs, tgl_list, dx):
    for t in tgl_list:
        no_klaim[0] += 1
        sesi.append({"id_klaim": f"SEP-UJI-{no_klaim[0]:06d}", "id_peserta": pid, "id_rs": rs, "tanggal": t,
                     "kode_cbg": dx[2], "kode_icd10": dx[0], "diagnosis": dx[1], "tarif": dx[3]})


def tambah_peserta(pid, nama, umur, jk, keluarga=None, hubungan=None, catatan=""):
    lahir = date(2026 - umur, rng.randint(1, 12), rng.randint(1, 28))
    perlu = umur >= 60 or umur < 13
    peserta.append({"id_peserta": pid, "nama": nama, "tanggal_lahir": lahir.isoformat(), "umur": umur, "jenis_kelamin": jk,
                    "no_hp": f"0800-0000-{len(peserta)+1:04d}", "kontak_keluarga": keluarga or "", "hubungan_keluarga": hubungan or "",
                    "no_hp_keluarga": f"0800-1000-{len(peserta)+1:04d}" if keluarga else "", "hubungi_keluarga": "ya" if perlu and keluarga else "tidak",
                    "catatan": catatan})


# ---------- populasi latar (sintetis, distribusi panitia) ----------
nomor = 0
for rs_id, *_ in RS:
    for _ in range(80):
        nomor += 1
        pid = f"P{nomor:04d}"
        umur = rng.choice([rng.randint(5, 12), rng.randint(25, 59), rng.randint(25, 59), rng.randint(60, 80)])
        jk = rng.choice(["L", "P"])
        nama = f"{rng.choice(DEPAN)} {rng.choice(BELAKANG)}"
        kel = f"{rng.choice(DEPAN)} {rng.choice(BELAKANG)}" if (umur >= 60 or umur < 13) else None
        tambah_peserta(pid, nama, umur, jk, kel, ("anak" if umur >= 60 else "orang tua") if kel else None)
        dx = DX[4] if umur < 13 else rng.choice(DX[:4])
        mulai = rng.randrange(len(BULAN))
        lama = len(BULAN) - mulai if rng.random() < 0.5 else rng.randint(1, len(BULAN) - mulai)
        for ym in BULAN[mulai:mulai + lama]:
            k = ambil_k()
            benar = pilih_tanggal_jujur(ym, k)
            tagih = list(benar)
            if rs_id == "RS01" and rng.random() < 0.35:  # pola curang: sesi ditambah, sebagian di hari Minggu/libur
                target = max(k + 3, rng.randint(9, 12))
                ekstra = [d for d in hari_bulan(ym) if d not in tagih]
                minggu = [d for d in ekstra if d.weekday() == 6 or d in LIBUR_SET]
                if minggu and rng.random() < 0.6:
                    tagih.append(rng.choice(minggu))
                while len(tagih) < target:
                    tagih.append(rng.choice([d for d in ekstra if d not in tagih and d.weekday() != 6]))
                tagih.sort()
            tambah_sesi(pid, rs_id, tagih, dx)
            if ym == BULAN_UJI:
                kebenaran.append({"id_peserta": pid, "id_rs": rs_id, "bulan": ym, "sesi_ditagih": len(tagih),
                                  "sesi_sebenarnya": len(benar), "sumber": "latar"})

# ---------- pasien skenario (disisipkan manual) ----------
d = lambda s: date.fromisoformat(s)
SK = [  # id, nama, umur, jk, rs, keluarga, hubungan, dx, sesi Agustus ditagih, sesi Agustus sebenarnya, bulan aktif sebelumnya (jumlah sesi)
    ("S1", "Andi Pratama", 54, "L", "RS01", None, None, DX[0],
     ["2026-08-03", "2026-08-04", "2026-08-06", "2026-08-10", "2026-08-11", "2026-08-13", "2026-08-16", "2026-08-17", "2026-08-20", "2026-08-24", "2026-08-27"],
     ["2026-08-04", "2026-08-11", "2026-08-20"], {"2026-06": 3, "2026-07": 4}),
    ("S2", "Siti Rahmawati", 67, "P", "RS01", "Dewi Rahmawati", "anak", DX[2],
     ["2026-08-01", "2026-08-03", "2026-08-05", "2026-08-07", "2026-08-12", "2026-08-14", "2026-08-19", "2026-08-23", "2026-08-26", "2026-08-28"],
     ["2026-08-05", "2026-08-19"], {"2026-03": 6, "2026-04": 7, "2026-05": 6, "2026-06": 8, "2026-07": 8}),
    ("S3", "Budi Santoso", 45, "L", "RS02", None, None, DX[1],
     ["2026-08-01", "2026-08-03", "2026-08-06", "2026-08-10", "2026-08-13", "2026-08-18", "2026-08-21", "2026-08-25", "2026-08-28"],
     None, {"2026-03": 8, "2026-04": 8, "2026-05": 8, "2026-06": 8, "2026-07": 8}),
    ("S4", "Karti Lestari", 72, "P", "RS01", "Bayu Lestari", "anak", DX[2],
     ["2026-08-04", "2026-08-06", "2026-08-11", "2026-08-13", "2026-08-16", "2026-08-18", "2026-08-20", "2026-08-25", "2026-08-27"],
     ["2026-08-04", "2026-08-06", "2026-08-11", "2026-08-18", "2026-08-25", "2026-08-27"], {"2026-07": 5}),
    ("S5", "Joko Prasetyo", 39, "L", "RS03", None, None, DX[3],
     ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-10", "2026-08-12", "2026-08-17", "2026-08-19", "2026-08-24", "2026-08-26", "2026-08-31"],
     None, {"2026-07": 6}),
    ("S6", "Slamet Riyadi", 58, "L", "RS01", None, None, DX[0],
     ["2026-08-03", "2026-08-05", "2026-08-07", "2026-08-09", "2026-08-12", "2026-08-19", "2026-08-24", "2026-08-26"],
     ["2026-08-05", "2026-08-19"], {}),
    ("S7", "Rina Marlina", 41, "P", "RS04", None, None, DX[3],
     ["2026-08-04", "2026-08-11", "2026-08-18", "2026-08-25"],
     None, {"2026-03": 4, "2026-04": 4, "2026-05": 4, "2026-06": 4, "2026-07": 4}),
    ("S8", "Hendra Wijaya", 50, "L", "RS05", None, None, DX[1],
     ["2026-08-01", "2026-08-03", "2026-08-05", "2026-08-10", "2026-08-12", "2026-08-18", "2026-08-20", "2026-08-24", "2026-08-26", "2026-08-31"],
     None, {"2026-03": 8, "2026-04": 8, "2026-05": 8, "2026-06": 8, "2026-07": 8}),
]
for sid, nama, umur, jk, rs, kel, hub, dx, tagih, benar, sebelum in SK:
    pid = f"P-{sid}"
    tambah_peserta(pid, nama, umur, jk, kel, hub, catatan=f"pasien skenario {sid}")
    for ym, k in sebelum.items():
        tambah_sesi(pid, rs, pilih_tanggal_jujur(ym, k), dx)
    tagih = [d(x) for x in tagih]
    tambah_sesi(pid, rs, tagih, dx)
    kebenaran.append({"id_peserta": pid, "id_rs": rs, "bulan": BULAN_UJI, "sesi_ditagih": len(tagih),
                      "sesi_sebenarnya": len(benar) if benar else len(tagih), "sumber": f"skenario {sid}"})

# ---------- indikator referensi ----------
ind = hitung_indikator(sesi, LIBUR_SET, BULAN_UJI)
kb = {(k["id_peserta"], k["id_rs"]): k for k in kebenaran}

# ---------- riwayat panggilan latar (sudah terjadi sebelum demo) ----------
riwayat = []
dipicu_latar = [v for (pid, rs), v in sorted(ind.items()) if v["dipicu"] and not pid.startswith("P-S")]
tidak_sesuai_rs01 = 0
for v in dipicu_latar:
    t = kb[(v["id_peserta"], v["id_rs"])]
    curang = t["sesi_ditagih"] - t["sesi_sebenarnya"] > 2
    if curang:
        if v["id_rs"] != "RS01" or tidak_sesuai_rs01 >= 2:
            continue  # sisanya masih antre, belum ditelepon
        tidak_sesuai_rs01 += 1
        j = {"status_panggilan": "terjawab", "penerima": "peserta", "hubungan": None, "hadir": True,
             "jumlah_min": t["sesi_sebenarnya"], "jumlah_maks": t["sesi_sebenarnya"], "keyakinan": "tinggi", "tanda_bahaya": [],
             "kutipan_kunci": f"Seingat saya cuma {t['sesi_sebenarnya']} kali.", "ringkasan": "Jumlah sesi versi peserta jauh di bawah tagihan."}
    else:
        n = t["sesi_sebenarnya"]
        j = {"status_panggilan": "terjawab", "penerima": "peserta", "hubungan": None, "hadir": True,
             "jumlah_min": max(1, n - 1), "jumlah_maks": n + 1, "keyakinan": "tinggi", "tanda_bahaya": [],
             "kutipan_kunci": f"Kurang lebih {n} kali.", "ringkasan": "Jumlah sesi sesuai tagihan."}
    lab, alasan = label_jawaban(j, v["sesi_ditagih"])
    riwayat.append({"id_panggilan": f"CALL-LATAR-{len(riwayat)+1:03d}", "id_peserta": v["id_peserta"], "id_rs": v["id_rs"],
                    "bulan_layanan": BULAN_UJI, "sesi_ditagih": v["sesi_ditagih"], "jawaban": j, "label": lab, "alasan": alasan,
                    "sumber": "sintetis-riwayat (bukan panggilan nyata)"})

# ---------- skenario uji ----------
transkrip = json.load(open(ROOT / "tools" / "skenario_sumber.json"))
skenario = []
hasil_sesudah = [{"id_rs": r["id_rs"], "label": r["label"]} for r in riwayat]
langkah_rs = []
for sid, nama, umur, jk, rs, kel, hub, dx, tagih, benar, sebelum in SK:
    v = ind[(f"P-{sid}", rs)]
    src = transkrip[sid]
    entry = {"id_skenario": sid, "judul": src["judul"], "id_peserta": f"P-{sid}", "nama_peserta": nama, "umur": umur,
             "id_rs": rs, "nama_rs": dict((r[0], r[1]) for r in RS)[rs], "bulan_layanan": BULAN_UJI,
             "penerima_telepon": {"nama": kel or nama, "hubungan": hub or "peserta", "nomor_tujuan": "${NOMOR_PENGUJI}"},
             "kebenaran_untuk_penguji": {"sesi_sebenarnya": kb[(f'P-{sid}', rs)]["sesi_sebenarnya"], "sesi_ditagih": v["sesi_ditagih"]},
             "expected_indikator": {k: v[k] for k in ["sesi_ditagih", "maks_sesi_seminggu", "I1_lebih_8_sebulan", "I2_3x_seminggu",
                                                      "I3_episode_6_bulan", "I4_hari_libur", "tanggal_libur", "jumlah_indikator", "dipicu"]},
             "naskah_penguji": src["naskah_penguji"], "perilaku_ai_wajib": src["perilaku_ai_wajib"]}
    if v["dipicu"]:
        j = src["expected_jawaban"]
        lab, alasan = label_jawaban(j, v["sesi_ditagih"])
        assert lab == src["expected_label"], (sid, lab)
        entry.update({"expected_jawaban": j, "expected_label": lab, "expected_alasan": alasan,
                      "expected_bukti": src["expected_bukti"], "transkrip_contoh": f"transkrip_uji/{sid}.txt"})
        (ROOT / "transkrip_uji" / f"{sid}.txt").write_text(src["transkrip_contoh"].strip() + "\n")
        hasil_sesudah.append({"id_rs": rs, "label": lab})
        langkah_rs.append({"setelah": sid, "ringkasan": ringkasan_rs(hasil_sesudah)})
    else:
        assert src["expected_label"] is None, sid
        entry.update({"expected_jawaban": None, "expected_label": None,
                      "expected_alasan": "Tidak dipicu: indikator aktif kurang dari 2. Tidak ada panggilan."})
    skenario.append(entry)

# ---------- tulis berkas ----------
def tulis_csv(nama, baris, kolom):
    with open(ROOT / nama, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom)
        w.writeheader()
        for b in baris:
            w.writerow({k: (b[k].isoformat() if hasattr(b[k], "isoformat") else b[k]) for k in kolom})

tulis_csv("rumah_sakit.csv", [dict(zip(["id_rs", "nama_rs", "tipe", "wilayah", "catatan_uji"], r)) for r in RS],
          ["id_rs", "nama_rs", "tipe", "wilayah", "catatan_uji"])
tulis_csv("peserta.csv", peserta, list(peserta[0].keys()))
sesi.sort(key=lambda s: (s["id_peserta"], s["tanggal"]))
tulis_csv("klaim_sesi.csv", sesi, list(sesi[0].keys()))
tulis_csv("libur_nasional_2026.csv", [{"tanggal": a, "nama": b} for a, b in LIBUR], ["tanggal", "nama"])
tulis_csv("kunci_kebenaran_2026-08.csv", kebenaran, list(kebenaran[0].keys()))
ind_rows = []
for v in sorted(ind.values(), key=lambda x: (x["id_rs"], x["id_peserta"])):
    r = dict(v); r["tanggal_libur"] = ";".join(v["tanggal_libur"]); ind_rows.append(r)
tulis_csv("expected_indikator_2026-08.csv", ind_rows, list(ind_rows[0].keys()))
json.dump(riwayat, open(ROOT / "riwayat_panggilan_2026-08.json", "w"), ensure_ascii=False, indent=2)
pemicu = {}
for v in ind.values():
    p_ = pemicu.setdefault(v["id_rs"], {"id_rs": v["id_rs"], "pasien_aktif": 0, "pasien_dipicu": 0})
    p_["pasien_aktif"] += 1; p_["pasien_dipicu"] += int(v["dipicu"])
for p_ in pemicu.values():
    p_["persen_dipicu"] = round(100 * p_["pasien_dipicu"] / p_["pasien_aktif"], 1)
json.dump({"aturan": "Perlu klarifikasi RS jika tidak sesuai >= 3 DAN rasio tidak sesuai/terjawab >= 10%",
           "pemicu_per_rs_2026-08": dict(sorted(pemicu.items())),
           "sebelum_skenario": ringkasan_rs([{"id_rs": r["id_rs"], "label": r["label"]} for r in riwayat]),
           "langkah": langkah_rs}, open(ROOT / "expected_ringkasan_rs.json", "w"), ensure_ascii=False, indent=2)
json.dump(skenario, open(ROOT / "skenario_uji.json", "w"), ensure_ascii=False, indent=2)

# ---------- laporan singkat ----------
n_dipicu = sum(v["dipicu"] for v in ind.values())
print({k: (v["pasien_dipicu"], v["pasien_aktif"], v["persen_dipicu"]) for k, v in sorted(pemicu.items())})
print(f"peserta={len(peserta)} sesi={len(sesi)} pasien_aktif_agustus={len(ind)} dipicu={n_dipicu} riwayat_panggilan={len(riwayat)}")
for rs, r in ringkasan_rs([{"id_rs": x["id_rs"], "label": x["label"]} for x in riwayat]).items():
    print("sebelum", rs, r["status"], r["tidak_sesuai"], "/", r["terjawab"])
for l in langkah_rs:
    print("setelah", l["setelah"], {k: (v["status"], v["tidak_sesuai"], v["terjawab"]) for k, v in l["ringkasan"].items()})
