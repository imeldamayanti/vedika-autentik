"""Mengisi database v3 dari data-uji-konfirmasi: 5 RS, 410 peserta, 4.938 klaim sesi, libur,
indikator Agustus 2026 (aturan: tools/aturan.py, model anomali: tools/anomali.py),
4 panggilan riwayat (Selesai), dan panggilan berstatus Antre untuk setiap pasien yang dipilih aturan ATAU
model anomali dan belum punya riwayat.

kunci_kebenaran_2026-08.csv sengaja tidak dibaca: itu milik penguji, bukan sistem.

Pakai:  .venv/bin/python -m scripts.seed_v3 [--reset] [--dry-run]
Syarat: schema_v3.sql sudah diterapkan (scripts.terapkan_v3) dan DATABASE_URL di backend/.env terisi.
"""
import argparse
import csv
import importlib.util
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from app import anomali_v3
from app.config import DATA_UJI as DATA  # noqa: E402

AKAR = Path(__file__).resolve().parents[2]
BULAN = "2026-08"
RETENSI_SESUAI = timedelta(days=30)
PESERTA, PASIEN_AKTIF = 410, 302
WIB = timezone(timedelta(hours=7))
# Empat riwayat latar demo: (waktu_mulai, durasi detik). Sama dengan data demo FE (data-v3.js).
JADWAL_RIWAYAT = {
    "CALL-LATAR-001": (datetime(2026, 10, 5, 9, 42, tzinfo=WIB), 84),
    "CALL-LATAR-002": (datetime(2026, 10, 5, 10, 5, tzinfo=WIB), 71),
    "CALL-LATAR-003": (datetime(2026, 10, 5, 10, 31, tzinfo=WIB), 66),
    "CALL-LATAR-004": (datetime(2026, 10, 5, 11, 18, tzinfo=WIB), 74),
}
PESAN_KONEKSI = "Tidak bisa terhubung ke database: DATABASE_URL salah atau project Supabase di-pause."

TABEL_V3 = (
    "panggilan_log, keputusan_panggilan, panggilan, indikator_bulanan, klaim_sesi, libur_nasional, peserta, rumah_sakit"
)
SQL_PANGGILAN = (
    "insert into panggilan (id, id_peserta, id_rs, bulan_layanan, sesi_ditagih, penerima, nama_penerima,"
    " hubungan, status, percobaan, jawaban, label, alasan, waktu_mulai, waktu_selesai, hapus_pada, sumber,"
    " durasi_detik)"
    " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing"
)


def muat_aturan():
    spec = importlib.util.spec_from_file_location("aturan", DATA / "tools" / "aturan.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def baca_csv(nama):
    with open(DATA / nama, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def kosong(v):
    return v if v not in ("", None) else None


def baris_peserta(r):
    return (
        r["id_peserta"], r["nama"], kosong(r["tanggal_lahir"]), int(r["umur"]), r["jenis_kelamin"], r["no_hp"],
        kosong(r["kontak_keluarga"]), kosong(r["hubungan_keluarga"]), kosong(r["no_hp_keluarga"]),
        r["hubungi_keluarga"] == "ya", kosong(r["catatan"]),
    )


SQL_KLAIM = (
    "insert into klaim_sesi (id_klaim, id_peserta, id_rs, tanggal, kode_cbg, kode_icd10, diagnosis, tarif,"
    " rujukan_fktp, perujuk_luar_wilayah) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing"
)
SQL_INDIKATOR = (
    "insert into indikator_bulanan (id_peserta, id_rs, bulan, sesi_ditagih, maks_sesi_seminggu, i1_lebih_8_sebulan,"
    " i2_3x_seminggu, i3_episode_6_bulan, i4_hari_libur, tanggal_libur, jumlah_indikator, dipicu,"
    " skor_anomali, anomali_ditandai, anomali_langka, alasan_anomali)"
    " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    # baris lama (database yang di-seed sebelum model ada) hanya menerima hasil model; kolom aturan tidak disentuh
    " on conflict (id_peserta, id_rs, bulan) do update set"
    " skor_anomali = excluded.skor_anomali, anomali_ditandai = excluded.anomali_ditandai,"
    " anomali_langka = excluded.anomali_langka, alasan_anomali = excluded.alasan_anomali"
)


def baris_klaim(r):
    return (
        r["id_klaim"], r["id_peserta"], r["id_rs"], r["tanggal"], r["kode_cbg"], r["kode_icd10"], r["diagnosis"],
        int(r["tarif"]), r["rujukan_fktp"] == "ya", r["perujuk_luar_wilayah"] == "ya",
    )


def baris_indikator(h, anomali):
    """anomali: keluaran anomali_v3.score untuk bulan-pasien ini."""
    return (
        h["id_peserta"], h["id_rs"], h["bulan"], h["sesi_ditagih"], h["maks_sesi_seminggu"],
        h["I1_lebih_8_sebulan"], h["I2_3x_seminggu"], h["I3_episode_6_bulan"], h["I4_hari_libur"],
        [date.fromisoformat(t) for t in h["tanggal_libur"]], h["jumlah_indikator"], h["dipicu"],
        anomali["skor"], anomali["ditandai"], anomali["langka"], Jsonb(anomali["alasan"]),
    )


def fitur_pola(sesi, libur, bulan):
    """(id_peserta, id_rs) -> fitur kunjungan tools/pola.py untuk setiap pasien aktif di bulan itu (semua, bukan hanya terpicu)."""
    return anomali_v3.pola().features_per_patient(
        [((s["id_peserta"], s["id_rs"]), s["tanggal"]) for s in sesi], bulan, libur
    )


def nilai_anomali(klaim, peserta, fitur, bulan):
    """(id_peserta, id_rs) -> keluaran anomali_v3.score untuk setiap pasien aktif di bulan itu."""
    kunjungan = {}
    for k in klaim:
        if k["tanggal"].startswith(bulan):
            kunjungan.setdefault((k["id_peserta"], k["id_rs"]), []).append(
                {"referred": k["rujukan_fktp"] == "ya", "other_district": k["perujuk_luar_wilayah"] == "ya"}
            )
    return {
        kunci: anomali_v3.score(f, kunjungan[kunci], int(peserta[kunci[0]]["umur"]))
        for kunci, f in fitur.items()
    }


def hapus_pada(label, waktu):
    """R5.5: Sesuai dihapus 30 hari setelah selesai; Tidak sesuai disimpan sampai klarifikasi selesai; lainnya tanpa rekaman."""
    return waktu + RETENSI_SESUAI if label == "Sesuai" else None


def tentukan_penerima(pes):
    """R1.3: keluarga jika hubungi_keluarga = ya dan ada kontak keluarga, selain itu peserta.
    Mengembalikan (penerima, nama_penerima, hubungan)."""
    if pes["hubungi_keluarga"] == "ya" and kosong(pes["kontak_keluarga"]):
        return "keluarga", pes["kontak_keluarga"], kosong(pes["hubungan_keluarga"])
    return "peserta", pes["nama"], None


def id_panggilan(id_peserta, bulan):
    return f"CALL-{id_peserta}-{bulan}"


def baris_panggilan(p, peserta, jadwal=JADWAL_RIWAYAT):
    """Riwayat: penerima mengikuti R1.3 (bukan kolom penerima di berkas riwayat); jawaban disesuaikan.
    Hasil demo (demo_2026-08.json) membawa waktu, status, dan percobaannya sendiri."""
    pes = peserta[p["id_peserta"]]
    penerima, nama, hubungan = tentukan_penerima(pes)
    j = {**p["jawaban"], "penerima": penerima, "hubungan": hubungan}
    if p["id_panggilan"] in jadwal:
        mulai, durasi = jadwal[p["id_panggilan"]]
    else:
        mulai, durasi = datetime.fromisoformat(p["waktu_mulai"]), p["durasi_detik"]
    selesai = mulai + timedelta(seconds=durasi or 0)
    return (
        p["id_panggilan"], p["id_peserta"], p["id_rs"], p["bulan_layanan"], p["sesi_ditagih"],
        penerima, nama, hubungan, p.get("status", "selesai"), p.get("percobaan", 1), Jsonb(j), p["label"], p["alasan"],
        mulai, selesai, hapus_pada(p["label"], selesai), "sintetis-riwayat", durasi,
    )


def baris_antre(h, pes):
    """Panggilan Antre untuk satu hasil indikator terpicu; penerima sesuai R1.3."""
    penerima, nama, hubungan = tentukan_penerima(pes)
    return (
        id_panggilan(h["id_peserta"], h["bulan"]), h["id_peserta"], h["id_rs"], h["bulan"], h["sesi_ditagih"],
        penerima, nama, hubungan, "antre", 0, None, None, None, None, None, None, "panggilan", None,
    )


def susun_antre(indikator, peserta, riwayat, anomali):
    """Satu baris Antre per pasien yang dipilih aturan ATAU model anomali dan belum punya panggilan riwayat."""
    sudah = {(p["id_peserta"], p["id_rs"], p["bulan_layanan"]) for p in riwayat}
    return [
        baris_antre(h, peserta[h["id_peserta"]])
        for kunci, h in sorted(indikator.items())
        if (h["dipicu"] or anomali[kunci]["ditandai"]) and (h["id_peserta"], h["id_rs"], h["bulan"]) not in sudah
    ]


def susun_demo(demo, indikator, peserta, riwayat, anomali):
    """Keadaan demo: semua pasien terpilih lain sudah punya hasil, hanya pasien demo yang antre, sesuai urutan."""
    selesai = riwayat + demo["selesai"]
    sudah = {(p["id_peserta"], p["id_rs"]) for p in selesai}
    sisa = [k for k, h in indikator.items() if (h["dipicu"] or anomali[k]["ditandai"]) and k[:2] not in sudah]
    ke = {pid: i for i, pid in enumerate(demo["urutan"])}
    if sorted(k[0] for k in sisa) != sorted(ke):
        raise ValueError(f"Antre demo harus tepat {demo['urutan']}, ternyata {sorted(k[0] for k in sisa)}")
    sisa.sort(key=lambda k: ke[k[0]])
    return selesai, [baris_antre(indikator[k], peserta[k[0]]) for k in sisa]


def muat_data(demo=False):
    """Baca data uji dan hitung indikator. Tanpa database. demo: tambah pasien dan hasil dari demo_2026-08.json."""
    aturan = muat_aturan()
    peserta = baca_csv("peserta.csv")
    klaim = baca_csv("klaim_sesi.csv")
    libur = baca_csv("libur_nasional_2026.csv")
    riwayat = json.loads((DATA / "riwayat_panggilan_2026-08.json").read_text(encoding="utf-8"))
    data_demo = json.loads((DATA / "demo_2026-08.json").read_text(encoding="utf-8")) if demo else None
    if data_demo:
        peserta = peserta + [{k: str(v) for k, v in r.items()} for r in data_demo["peserta"]]
        klaim = klaim + [{k: str(v) for k, v in r.items()} for r in data_demo["klaim"]]
    sesi = [
        {"id_peserta": k["id_peserta"], "id_rs": k["id_rs"], "tanggal": date.fromisoformat(k["tanggal"])}
        for k in klaim
    ]
    tanggal_libur = {date.fromisoformat(r["tanggal"]) for r in libur}
    indikator = aturan.hitung_indikator(sesi, tanggal_libur, BULAN)
    peta_peserta = {r["id_peserta"]: r for r in peserta}
    fitur = fitur_pola(sesi, tanggal_libur, BULAN)
    anomali = nilai_anomali(klaim, peta_peserta, fitur, BULAN)
    antre = susun_antre(indikator, peta_peserta, riwayat, anomali)
    if data_demo:
        riwayat, antre = susun_demo(data_demo, indikator, peta_peserta, riwayat, anomali)
    return {
        "rs": baca_csv("rumah_sakit.csv"), "peserta": peserta, "klaim": klaim, "libur": libur,
        "riwayat": riwayat, "indikator": indikator, "peta_peserta": peta_peserta,
        "fitur_pola": fitur, "anomali": anomali, "antre": antre, "demo": data_demo,
    }


def isi_ke(conn, d, reset=False):
    """Tulis data lewat koneksi yang diberikan (tanpa commit). reset = kosongkan tabel v3 dulu (tabel v2 tidak disentuh)."""
    if reset:
        conn.execute(f"truncate {TABEL_V3} restart identity cascade")
    cur = conn.cursor()
    cur.executemany(
        "insert into rumah_sakit (id_rs, nama_rs, tipe, wilayah) values (%s,%s,%s,%s) on conflict do nothing",
        [(r["id_rs"], r["nama_rs"], r["tipe"], r["wilayah"]) for r in d["rs"]],
    )
    cur.executemany(
        "insert into peserta values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing",
        [baris_peserta(r) for r in d["peserta"]],
    )
    cur.executemany(SQL_KLAIM, [baris_klaim(r) for r in d["klaim"]])
    cur.executemany(
        "insert into libur_nasional (tanggal, nama) values (%s,%s) on conflict do nothing",
        [(r["tanggal"], r["nama"]) for r in d["libur"]],
    )
    cur.executemany(SQL_INDIKATOR, [baris_indikator(h, d["anomali"][kunci]) for kunci, h in d["indikator"].items()])
    cur.executemany(SQL_PANGGILAN, [baris_panggilan(p, d["peta_peserta"]) for p in d["riwayat"]])
    cur.executemany(SQL_PANGGILAN, d["antre"])


def tambah_master_demo(conn, d):
    """Pasien demo, klaim, dan indikatornya. Baris yang sudah ada tidak ditimpa, jadi nomor HP asli yang diisi
    langsung di database tetap."""
    ids = set(d["demo"]["urutan"])
    cur = conn.cursor()
    cur.executemany(
        "insert into peserta values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing",
        [baris_peserta(r) for r in d["peserta"] if r["id_peserta"] in ids],
    )
    cur.executemany(SQL_KLAIM, [baris_klaim(r) for r in d["klaim"] if r["id_peserta"] in ids])
    cur.executemany(SQL_INDIKATOR, [baris_indikator(h, d["anomali"][k]) for k, h in d["indikator"].items() if k[0] in ids])


def reset_panggilan(conn, d):
    """Keadaan awal demo: hapus panggilan, log, dan keputusan, isi ulang riwayat Selesai + panggilan Antre, matikan
    Jeda. Tanpa commit. Data biasa: mode otomatis menyala. Data demo: pasien demo ditambahkan bila belum ada, dan mode
    otomatis mati supaya panggilan pertama dimulai saat verifikator menyalakannya. Data master lain tidak disentuh."""
    if d.get("demo"):
        tambah_master_demo(conn, d)
    conn.execute("delete from panggilan_log")
    conn.execute("delete from keputusan_panggilan")
    conn.execute("delete from panggilan")
    cur = conn.cursor()
    cur.executemany(SQL_PANGGILAN, [baris_panggilan(p, d["peta_peserta"]) for p in d["riwayat"]])
    cur.executemany(SQL_PANGGILAN, d["antre"])
    for kunci, nilai in (("mode_otomatis", "false" if d.get("demo") else "true"), ("jeda", "false")):
        conn.execute(
            "insert into pengaturan (kunci, nilai) values (%s, %s::jsonb)"
            " on conflict (kunci) do update set nilai = excluded.nilai",
            (kunci, nilai),
        )


def isi_database(url, d, reset=False):
    """Tulis data ke database dalam satu transaksi."""
    with psycopg.connect(url, prepare_threshold=None, connect_timeout=10) as conn:
        isi_ke(conn, d, reset)
        conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="kosongkan tabel v3 sebelum mengisi")
    ap.add_argument("--dry-run", action="store_true", help="hitung dan cek saja, tanpa menulis ke database")
    arg = ap.parse_args()

    d = muat_data()
    dipicu = sum(h["dipicu"] for h in d["indikator"].values())
    hanya_model = sum(a["ditandai"] and not d["indikator"][k]["dipicu"] for k, a in d["anomali"].items())
    print(f"RS {len(d['rs'])} | peserta {len(d['peserta'])} | klaim {len(d['klaim'])} | libur {len(d['libur'])} | "
          f"indikator {len(d['indikator'])} (dipicu {dipicu}, hanya model {hanya_model}) | riwayat {len(d['riwayat'])} | "
          f"antre baru {len(d['antre'])}")
    if len(d["peserta"]) != PESERTA or len(d["indikator"]) != PASIEN_AKTIF:
        print(f"Jumlah tidak sesuai data uji ({PESERTA} peserta, {PASIEN_AKTIF} pasien aktif Agustus)")
        return 1
    if arg.dry_run:
        return 0

    from app.config import database_url

    url = database_url()
    if not url:
        print("DATABASE_URL kosong. Isi backend/.env dulu.")
        return 1
    try:
        isi_database(url, d, reset=arg.reset)
    except psycopg.OperationalError:
        print(PESAN_KONEKSI)
        return 1
    except psycopg.errors.UndefinedTable:
        print("Tabel v3 belum ada. Jalankan scripts.terapkan_v3 dulu.")
        return 1
    print("Seed v3 selesai.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
