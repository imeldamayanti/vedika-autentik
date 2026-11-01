"""Pemeriksa hasil aplikasi terhadap expected data uji.

  python3 tools/uji.py indikator                    # cek aturan referensi = expected
  python3 tools/uji.py indikator hasil_app.csv      # cek keluaran indikator aplikasi (kolom sama dengan expected)
  python3 tools/uji.py jawaban hasil_pembaca.json   # cek keluaran pembaca jawaban: [{"id_skenario": "S1", "jawaban": {...}}]
"""
import csv, json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aturan import hitung_indikator, label_jawaban  # noqa: E402

KOLOM_IND = ["sesi_ditagih", "I1_lebih_8_sebulan", "I2_3x_seminggu", "I3_episode_6_bulan", "I4_hari_libur", "jumlah_indikator", "dipicu"]
KOLOM_JWB = ["status_panggilan", "penerima", "hadir", "jumlah_maks", "keyakinan", "tanda_bahaya"]


def norm(v):
    return {"True": True, "False": False, "true": True, "false": False}.get(v, v) if isinstance(v, str) else v


def uji_indikator(path_app=None):
    exp = {(r["id_peserta"], r["id_rs"]): r for r in csv.DictReader(open(ROOT / "expected_indikator_2026-08.csv"))}
    if path_app:
        got = {(r["id_peserta"], r["id_rs"]): r for r in csv.DictReader(open(path_app))}
    else:
        sesi = [{"id_peserta": r["id_peserta"], "id_rs": r["id_rs"], "tanggal": date.fromisoformat(r["tanggal"])}
                for r in csv.DictReader(open(ROOT / "klaim_sesi.csv"))]
        libur = {date.fromisoformat(r["tanggal"]) for r in csv.DictReader(open(ROOT / "libur_nasional_2026.csv"))}
        got = {k: {c: str(v[c]) for c in KOLOM_IND} for k, v in hitung_indikator(sesi, libur, "2026-08").items()}
    salah = [(k, c, exp[k][c], got.get(k, {}).get(c)) for k in exp for c in KOLOM_IND if str(norm(exp[k][c])) != str(norm(got.get(k, {}).get(c)))]
    lebih = set(got) - set(exp)
    print(f"Indikator: {len(exp) - len({s[0] for s in salah})}/{len(exp)} pasien cocok; baris tak dikenal: {len(lebih)}")
    for s in salah[:20]:
        print("  SALAH", s)
    return not salah and not lebih


def uji_jawaban(path_app):
    sk = {s["id_skenario"]: s for s in json.load(open(ROOT / "skenario_uji.json")) if s["expected_label"]}
    got = {x["id_skenario"]: x["jawaban"] for x in json.load(open(path_app))}
    ok = True
    for sid, s in sk.items():
        if sid not in got:
            print(f"  {sid}: TIDAK ADA keluaran"); ok = False; continue
        beda = [c for c in KOLOM_JWB if norm(s["expected_jawaban"].get(c)) != norm(got[sid].get(c))]
        lab, _ = label_jawaban(got[sid], s["expected_indikator"]["sesi_ditagih"])
        lulus = lab == s["expected_label"] and not beda
        ok &= lulus
        print(f"  {sid}: {'LULUS' if lulus else 'GAGAL'} label={lab} (expected {s['expected_label']}) beda_field={beda}")
    return ok


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "indikator"
    hasil = uji_indikator(sys.argv[2] if len(sys.argv) > 2 else None) if mode == "indikator" else uji_jawaban(sys.argv[2])
    print("HASIL:", "LULUS" if hasil else "GAGAL")
    sys.exit(0 if hasil else 1)
