#!/usr/bin/env python3
"""Train the unsupervised anomaly model (Isolation Forest) on the real FKRTL samples and export aggregates.

Needs the raw samples, so it runs only on the laptop that holds them. Writes:
- data-uji-konfirmasi/referensi-pola/model-anomali-v1.json: one score per feature-bin combination seen in
  at least 10 participant-months, the threshold and national bin shares (the scorer is tools/anomali.py);
- ai-service/data/reference/pola-2024/anomali-nyata.json: behaviour on real data (counts >= 10 only);
- data-uji-konfirmasi/referensi-pola/EVALUASI-ANOMALI.md: the same numbers for people.

Only July-December of each file is used, because `episode` looks back 6 months and each file starts in
January. --source takes the regular samples (one per year, trained on); --uji-luar takes disease-specific
samples that are only scored, never trained on.
Run with `uv run --group data python scripts/train_anomaly_model.py --source <2023.dta> --source <2024.dta>`.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from vedika_ai.anomali_reference import (
    behaviour,
    build_model,
    hospital_level,
    in_window,
    outside_check,
    validate_over_time,
)
from vedika_ai.claim_reference import assert_privacy_safe_aggregate
from vedika_ai.pola_reference import patient_months, read_visits

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "data-uji-konfirmasi" / "referensi-pola" / "model-anomali-v1.json"
REAL = ROOT / "ai-service" / "data" / "reference" / "pola-2024" / "anomali-nyata.json"
REPORT = ROOT / "data-uji-konfirmasi" / "referensi-pola" / "EVALUASI-ANOMALI.md"

NAMA_KELOMPOK = {
    "ditandai_model": "Ditandai model",
    "dipicu_aturan": "Dipicu aturan (≥ 2 indikator)",
    "keduanya": "Keduanya",
    "hanya_model": "Hanya model (tidak terlihat aturan)",
    "hanya_aturan": "Hanya aturan",
    "dipanggil_aturan_atau_model": "Ditelepon: aturan ATAU model",
}
NAMA_FITUR = {
    "sesi": "Sesi sebulan",
    "maks_minggu": "Sesi terbanyak seminggu",
    "ahad_libur": "Sesi hari Minggu",
    "episode": "Bulan berturut-turut",
    "tanpa_rujukan": "Kunjungan tanpa rujukan FKTP",
    "lintas_wilayah": "Dirujuk dari kab/kota lain",
    "gabungan": "Hanya gabungannya yang jarang",
    "dipicu": "Pangsa terpicu aturan",
    "ahad": "Pangsa dengan sesi hari Minggu",
    "dx_langka": "Diagnosis jarang",
    "cbg_langka": "Kode INA-CBG jarang",
}


def angka(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def ribuan(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def records_of(source: Path, chunk_size: int) -> list[dict]:
    """Participant-months of one sample file, July-December only. Files are never joined."""

    return in_window(patient_months(read_visits(source.resolve(), chunk_size)))


def report(model: dict, facts: dict, real: dict) -> str:
    rows = "\n".join(
        f"| {NAMA_KELOMPOK[g['kelompok']]} | {ribuan(g['bulan_pasien'])} | {ribuan(g['kunjungan'])} | {angka(g['persen'])}% | ≈{ribuan(g['per_bulan_nasional'])} |"
        for g in real["kelompok"]
    )
    reasons = "\n".join(
        f"| {NAMA_FITUR[r['fitur']]} | {ribuan(r['bulan_pasien'])} |"
        for r in real["alasan_pertama_hanya_model"]
    )
    patterns = "\n".join(
        f"| {', '.join(p['pola'])} | {ribuan(p['bulan_pasien'])} |"
        for p in real["pola_teratas_hanya_model"]
    )
    rs = real["rs"]
    drivers = "\n".join(
        f"| {NAMA_FITUR[d['fitur']]} | {d['kelompok_rs']} |" for d in rs["pemicu_utama"]
    )
    peers = real["kelompok_rs"]
    data = "\n".join(
        f"| `{d['berkas']}` | {', '.join(d['tahun'])} | {ribuan(d['bulan_pasien'])} |"
        for d in real["data"]
    )
    v = real.get("validasi_waktu")
    validation = (
        f"""Model dilatih ulang hanya dari {", ".join(v["latih"])}, lalu dipakai pada {", ".join(v["uji"])} yang belum pernah dilihatnya.
Pembanding: model yang dilatih dari {", ".join(v["uji"])} sendiri.

| Ukuran | Hasil |
|---|---|
| Ditandai di {", ".join(v["uji"])} oleh model {", ".join(v["latih"])} | {angka(v["persen_ditandai_model_tahun_lalu"])}% |
| Ditandai di {", ".join(v["uji"])} oleh model {", ".join(v["uji"])} | {angka(v["persen_ditandai_model_tahun_ini"])}% |
| Irisan (Jaccard) kedua himpunan yang ditandai | {angka(v["jaccard"])} |
| Hanya model (tidak terpicu aturan), model {", ".join(v["latih"])} | {angka(v["persen_hanya_model_tahun_lalu"])}% |
| Bobot {", ".join(v["uji"])} di gabungan yang tidak ada di tabel {", ".join(v["latih"])} | {angka(v["persen_gabungan_tak_dikenal_tahun_lalu"])}% |
"""
        if v
        else "Hanya satu tahun data, jadi validasi antartahun tidak dijalankan.\n"
    )
    outside = "\n".join(
        f"| {o['sampel']} | {', '.join(o['tahun'])} | {ribuan(o['bulan_pasien'])} | {angka(o['persen_ditandai_model'])}% | {angka(o['persen_dipicu_aturan'])}% | {angka(o['persen_hanya_model'])}% |"
        for o in real["uji_luar"]
    )
    outside_section = (
        f"""## Uji luar (tidak dipakai melatih)

Tabel akhir dipakai pada data sampel kontekstual: peserta yang dipilih karena penyakit tertentu, jadi bukan
gambaran semua pasien fisioterapi. Bobotnya mewakili kelompok penyakit itu, bukan nasional. Tujuannya hanya
melihat apakah model berperilaku wajar pada populasi lain.

| Sampel | Tahun | Bulan-pasien | Ditandai model | Dipicu aturan | Hanya model |
|---|---|---|---|---|---|
{outside}
"""
        if real["uji_luar"]
        else ""
    )
    return f"""# Evaluasi model anomali ({model["versi"]})

Dibuat oleh `ai-service/scripts/train_anomaly_model.py` pada {real["dibuat"]}. Jangan disunting manual.

## Apa yang dilakukan model

Isolation Forest **tanpa label** (unsupervised) dilatih pada {ribuan(model["pelatihan"]["bulan_pasien"])} bulan-pasien fisioterapi
rawat jalan dari data sampel reguler BPJS. Model mencari tagihan bulanan yang polanya jarang dibanding seluruh tagihan
nasional, tanpa diberi tahu mana yang curang. Data sampel memang tidak punya label itu.

Pasien ditelepon bila **aturan (≥ 2 indikator) ATAU model** menandainya. Hasilnya tetap ditentukan jawaban peserta.

Fitur hanya hal yang bisa dikonfirmasi peserta lewat telepon: jumlah sesi sebulan, sesi terbanyak dalam satu minggu,
sesi hari Minggu, bulan berturut-turut, pangsa kunjungan tanpa nomor rujukan FKTP, dan pangsa yang dirujuk dari
kab/kota lain. Kode diagnosis dan INA-CBG tidak dipakai di tingkat pasien karena peserta tidak bisa
mengonfirmasinya; keduanya dipakai di tingkat RS (bagian terakhir).

## Data

| Berkas | Tahun | Bulan-pasien (Juli–Desember) |
|---|---|---|
{data}

Hanya Juli–Desember tiap berkas yang dipakai. Fitur bulan berturut-turut melihat 6 bulan ke belakang, dan tiap berkas
mulai Januari, jadi Januari–Mei tidak punya riwayat lengkap (Januari–Juni tetap dipakai sebagai riwayat). Berkas
tidak digabung per peserta: data sampel tiap tahun diambil terpisah.

## Privasi

- Model disimpan sebagai tabel: satu skor per gabungan bin yang muncul pada minimal {model["minimum_sel"]} bulan-pasien
  ({facts["gabungan_dalam_tabel"]} gabungan). Pohon Isolation Forest, baris, nomor peserta, dan nilai minimum/maksimum tidak disimpan.
- Gabungan yang lebih jarang ({angka(100 * facts["pangsa_gabungan_langka"])}% bobot nasional) tidak disimpan dan dianggap
  tidak biasa oleh penilai. Isolation Forest sebelum ditabelkan juga menandai {angka(100 * facts["gabungan_langka_juga_ditandai_hutan"])}% bobot gabungan itu.
- Batas bin ditetapkan tangan (ambang aturan dan angka bulat), bukan dari data.

## Perilaku di data nyata (Tingkat A)

Ambang dipilih supaya model menandai sekitar {angka(100 * model["target_pangsa"])}% bulan-pasien nasional, setara aturan.
"Per bulan" = perkiraan nasional dengan bobot sampel, rata-rata atas {real["bulan"]} bulan.

| Kelompok | Bulan-pasien | Kunjungan | Bobot nasional | Per bulan |
|---|---|---|---|---|
{rows}

- Persen ditandai per bulan: {angka(real["persen_bulanan"]["min"])}% sampai {angka(real["persen_bulanan"]["maks"])}%.
- {peers["dengan_minimal_bulan_pasien"]} kelompok RS sejenis punya minimal {peers["minimal_bulan_pasien"]} bulan-pasien;
  {peers["tanpa_ditandai"]} di antaranya tanpa satu pun yang ditandai. 10% kelompok teratas memuat
  {angka(peers["pangsa_di_10_persen_teratas"])}% bobot yang ditandai.
- Kestabilan: irisan (Jaccard) himpunan yang ditandai antara seed pertama dan empat seed lain:
  {", ".join(angka(x) for x in facts["jaccard_antar_seed"])}.

Alasan pertama pada kasus "hanya model":

| Alasan | Bulan-pasien |
|---|---|
{reasons}

Pola "hanya model" yang paling sering:

| Pola | Bulan-pasien |
|---|---|
{patterns}

## Validasi antartahun

{validation}
{outside_section}
## Tingkat RS

Isolation Forest kedua atas {rs["kelompok_rs"]} kelompok RS sejenis (minimal {peers["minimal_bulan_pasien"]} bulan-pasien),
dengan fitur pangsa terpicu, rata-rata sesi, pangsa dengan sesi Minggu, pangsa tanpa rujukan FKTP, pangsa dari kab/kota lain,
pangsa diagnosis jarang, dan pangsa kode INA-CBG jarang (kode di bawah 1% kunjungan nasional). Ditandai
{rs["ditandai"]} kelompok (5% teratas). Identitas kelompok tidak disimpan.

| Fitur paling menyimpang | Kelompok RS |
|---|---|
{drivers}

## Batasan

- Tidak ada label kecurangan di data sampel, jadi angka di atas adalah perilaku, bukan ketepatan.
  Ketepatan baru bisa diukur dari hasil panggilan (berapa yang ditandai model berakhir Tidak sesuai).
- Nomor rujukan FKTP kosong bisa berarti kunjungan kontrol dengan surat kontrol RS, bukan pelanggaran.
  Arti sinyal ini perlu dipastikan bersama verifikator BPJS.
- Data sampel tidak memuat identitas RS. "Kelompok RS sejenis" = kab/kota + kepemilikan + jenis + tipe.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        action="append",
        required=True,
        help="Regular FKRTL .dta, one per year",
    )
    parser.add_argument(
        "--uji-luar",
        type=Path,
        action="append",
        default=[],
        help="Disease-specific FKRTL .dta, scored only",
    )
    parser.add_argument("--chunk-size", type=int, default=200_000)
    args = parser.parse_args()

    per_file = [(source, records_of(source, args.chunk_size)) for source in args.source]
    records = [r for _, rows in per_file for r in rows]
    model, facts = build_model(records)
    model["dilatih"] = date.today().isoformat()

    years = sorted({r["bulan"][:4] for r in records})
    validation = None
    if len(years) >= 2:
        validation = validate_over_time(
            [r for r in records if r["bulan"][:4] == years[0]],
            [r for r in records if r["bulan"][:4] == years[-1]],
        )
    outside = [
        outside_check(source.stem, records_of(source, args.chunk_size), model)
        for source in args.uji_luar
    ]
    real = behaviour(records, model) | {
        "data": [
            {
                "berkas": source.name,
                "tahun": sorted({r["bulan"][:4] for r in rows}),
                "bulan_pasien": len(rows),
            }
            for source, rows in per_file
        ],
        "validasi_waktu": validation,
        "uji_luar": [o for o in outside if o],
        "rs": hospital_level(records),
        "pelatihan": facts,
        "dibuat": model["dilatih"],
    }
    assert_privacy_safe_aggregate(model)
    assert_privacy_safe_aggregate(real)
    MODEL.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REAL.write_text(json.dumps(real, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(report(model, facts, real), encoding="utf-8")
    print(json.dumps({"model": str(MODEL), "ambang": model["ambang"], "sel": len(model["sel"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
