"""Mengisi database v3 dari data-uji-konfirmasi: 5 RS, 408 peserta, 4.913 klaim sesi, libur,
indikator Agustus 2026 (dihitung dengan tools/aturan.py), 4 panggilan riwayat (Selesai), dan
panggilan berstatus Antre untuk setiap pasien terpicu yang belum punya riwayat.

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

AKAR = Path(__file__).resolve().parents[2]
DATA = AKAR / "data-uji-konfirmasi"
BULAN = "2026-08"
RETENSI_SESUAI = timedelta(days=30)
WAKTU_RIWAYAT = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
PESAN_KONEKSI = "Tidak bisa terhubung ke database: DATABASE_URL salah atau project Supabase di-pause."

TABEL_V3 = (
    "panggilan_log, keputusan_panggilan, panggilan, indikator_bulanan, klaim_sesi, libur_nasional, peserta, rumah_sakit"
)
SQL_PANGGILAN = (
    "insert into panggilan (id, id_peserta, id_rs, bulan_layanan, sesi_ditagih, penerima, nama_penerima,"
    " hubungan, status, percobaan, jawaban, label, alasan, waktu_mulai, waktu_selesai, hapus_pada, sumber)"
    " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing"
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


def baris_klaim(r):
    return (
        r["id_klaim"], r["id_peserta"], r["id_rs"], r["tanggal"], r["kode_cbg"], r["kode_icd10"], r["diagnosis"],
        int(r["tarif"]),
    )


def baris_indikator(h):
    return (
        h["id_peserta"], h["id_rs"], h["bulan"], h["sesi_ditagih"], h["maks_sesi_seminggu"],
        h["I1_lebih_8_sebulan"], h["I2_3x_seminggu"], h["I3_episode_6_bulan"], h["I4_hari_libur"],
        [date.fromisoformat(t) for t in h["tanggal_libur"]], h["jumlah_indikator"], h["dipicu"],
    )


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


def baris_panggilan(p, peserta, waktu):
    """Riwayat: penerima mengikuti jawaban yang tercatat di berkas riwayat."""
    j = p["jawaban"]
    pes = peserta[p["id_peserta"]]
    keluarga = j["penerima"] == "keluarga"
    nama = pes["kontak_keluarga"] if keluarga else pes["nama"]
    return (
        p["id_panggilan"], p["id_peserta"], p["id_rs"], p["bulan_layanan"], p["sesi_ditagih"],
        j["penerima"], nama, j.get("hubungan"), "selesai", 1, Jsonb(j), p["label"], p["alasan"],
        waktu, waktu, hapus_pada(p["label"], waktu), "sintetis-riwayat",
    )


def baris_antre(h, pes):
    """Panggilan Antre untuk satu hasil indikator terpicu; penerima sesuai R1.3."""
    penerima, nama, hubungan = tentukan_penerima(pes)
    return (
        id_panggilan(h["id_peserta"], h["bulan"]), h["id_peserta"], h["id_rs"], h["bulan"], h["sesi_ditagih"],
        penerima, nama, hubungan, "antre", 0, None, None, None, None, None, None, "panggilan",
    )


def susun_antre(indikator, peserta, riwayat):
    """Satu baris Antre per pasien terpicu yang belum punya panggilan riwayat (pasien, RS, bulan)."""
    sudah = {(p["id_peserta"], p["id_rs"], p["bulan_layanan"]) for p in riwayat}
    return [
        baris_antre(h, peserta[h["id_peserta"]])
        for _, h in sorted(indikator.items())
        if h["dipicu"] and (h["id_peserta"], h["id_rs"], h["bulan"]) not in sudah
    ]


def muat_data():
    """Baca data uji dan hitung indikator. Tanpa database."""
    aturan = muat_aturan()
    peserta = baca_csv("peserta.csv")
    klaim = baca_csv("klaim_sesi.csv")
    libur = baca_csv("libur_nasional_2026.csv")
    riwayat = json.loads((DATA / "riwayat_panggilan_2026-08.json").read_text(encoding="utf-8"))
    sesi = [
        {"id_peserta": k["id_peserta"], "id_rs": k["id_rs"], "tanggal": date.fromisoformat(k["tanggal"])}
        for k in klaim
    ]
    indikator = aturan.hitung_indikator(sesi, {date.fromisoformat(r["tanggal"]) for r in libur}, BULAN)
    peta_peserta = {r["id_peserta"]: r for r in peserta}
    return {
        "rs": baca_csv("rumah_sakit.csv"), "peserta": peserta, "klaim": klaim, "libur": libur,
        "riwayat": riwayat, "indikator": indikator, "peta_peserta": peta_peserta,
        "antre": susun_antre(indikator, peta_peserta, riwayat),
    }


def isi_database(url, d, reset=False):
    """Tulis data ke database dalam satu transaksi. reset = kosongkan tabel v3 dulu (tabel v2 tidak disentuh)."""
    with psycopg.connect(url, autocommit=False, connect_timeout=10) as conn:
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
        cur.executemany(
            "insert into klaim_sesi values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing",
            [baris_klaim(r) for r in d["klaim"]],
        )
        cur.executemany(
            "insert into libur_nasional (tanggal, nama) values (%s,%s) on conflict do nothing",
            [(r["tanggal"], r["nama"]) for r in d["libur"]],
        )
        cur.executemany(
            "insert into indikator_bulanan values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing",
            [baris_indikator(h) for h in d["indikator"].values()],
        )
        cur.executemany(SQL_PANGGILAN, [baris_panggilan(p, d["peta_peserta"], WAKTU_RIWAYAT) for p in d["riwayat"]])
        cur.executemany(SQL_PANGGILAN, d["antre"])
        conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="kosongkan tabel v3 sebelum mengisi")
    ap.add_argument("--dry-run", action="store_true", help="hitung dan cek saja, tanpa menulis ke database")
    arg = ap.parse_args()

    d = muat_data()
    dipicu = sum(h["dipicu"] for h in d["indikator"].values())
    print(f"RS {len(d['rs'])} | peserta {len(d['peserta'])} | klaim {len(d['klaim'])} | libur {len(d['libur'])} | "
          f"indikator {len(d['indikator'])} (dipicu {dipicu}) | riwayat {len(d['riwayat'])} | "
          f"antre baru {len(d['antre'])}")
    if len(d["peserta"]) != 408 or len(d["indikator"]) != 300:
        print("Jumlah tidak sesuai PRD (408 peserta, 300 pasien aktif Agustus)")
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
