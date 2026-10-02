"""Membentuk respons Kontrak A dari baris database."""
from . import repo
from .label import ALASAN_SARAN, SARAN

BOBOT = {"kuat": 0, "sedang": 1, "lemah": 2, "info": 3}


def _waktu(w):
    return w.isoformat() if w else None


def _temuan(r) -> dict:
    t = {"cek": r["cek"], "kekuatan": r["kekuatan"], "kalimat": r["kalimat"], "region": r["region"]}
    if r["skor"] is not None:
        t["skor"] = float(r["skor"])
    if r["area"]:
        t["area"] = r["area"]
    if r["pasangan_id"]:
        t["pasangan"] = r["pasangan_id"]
    return t


def ringkasan(temuan: list[dict], kualitas: dict | None, label: str) -> str:
    if label == "ulang" and kualitas:
        return kualitas.get("catatan") or "Berkas belum bisa dinilai."
    if not temuan:
        return "Semua pemeriksaan bersih."
    utama = min(temuan, key=lambda t: BOBOT[t["kekuatan"]])
    return utama["kalimat"]


def _langkah(b: dict, temuan: list[dict]) -> list[dict]:
    if b["status"] == "gagal":
        return [{"nama": "Baca berkas", "status": "henti", "hasil": b["ringkasan"]}]
    kualitas = b["kualitas_scan"] or {}
    ulang = kualitas.get("status") == "scan_ulang"
    langkah = [{"nama": "Cek kualitas scan", "status": "henti" if ulang else "ok", "hasil": kualitas.get("catatan", "")}]
    if ulang:
        return langkah
    isi = b["isi_lembar"] or {}
    langkah.append({"nama": "Baca isi berkas", "status": "ok", "hasil": f"{isi.get('baris_terisi', 0)} baris terisi"})
    cocok = [t for t in temuan if t["cek"] == "kecocokan_klaim"]
    langkah.append({
        "nama": "Cocokkan dengan klaim",
        "status": "temuan" if cocok else "ok",
        "hasil": cocok[0]["kalimat"] if cocok else "Jumlah sesi cocok dengan klaim.",
    })
    return langkah


def _keputusan(r) -> dict | None:
    if not r:
        return None
    return {"tindakan": r["tindakan"], "catatan": r["catatan"], "verifikator": r["verifikator"], "waktu": _waktu(r["waktu"])}


def nomor_laporan(id_: str) -> str:
    return f"LT-VA/{id_[2:].upper()}/X/2026"


def detail(conn, id_: str) -> dict | None:
    b = repo.ambil_berkas(conn, id_)
    if b is None:
        return None
    if b["status"] == "diproses":
        return {"id": b["id"], "status": "diproses", "langkah": [], "diunggah": _waktu(b["waktu_unggah"])}
    temuan = [_temuan(r) for r in repo.ambil_temuan(conn, id_)]
    lb = repo.ambil_label(conn, id_)
    kel = repo.keluarga(conn, id_)
    return {
        "id": b["id"],
        "status": b["status"],
        "langkah": _langkah(b, temuan),
        "label": lb["label"],
        "saran": SARAN[lb["label"]],
        "alasan_saran": ALASAN_SARAN[lb["label"]],
        "ringkasan": b["ringkasan"],
        "klaim": b["klaim"],
        "isi_lembar": b["isi_lembar"],
        "kualitas_scan": b["kualitas_scan"],
        "temuan": temuan,
        "metadata_file": b["metadata_file"],
        "ukuran": b["ukuran"],
        "berkas": {"jpg": None, "pdf": f"/api/v1/berkas/{id_}/file", "sha256": b["sha256"], "nama": b["nama_file"]},
        "keluarga": {"akar": kel[0], "anggota": kel[1]} if kel else None,
        "keputusan": _keputusan(repo.keputusan_terakhir(conn, id_)),
        "konfirmasi": None,
        "galat": b["galat"],
        "versi_aturan": b["versi_aturan"],
        "versi_mesin": b["versi_mesin"],
        "diunggah": _waktu(b["waktu_unggah"]),
    }


def item_antrean(r) -> dict:
    klaim = r["klaim"] or {}
    return {
        "id": r["id"],
        "status": r["status"],
        "label": r["label"],
        "ringkasan": r["ringkasan"],
        "klaim": {k: klaim.get(k) for k in ("sep", "peserta", "faskes", "sesi_ditagih", "nilai_klaim")} if klaim else None,
        "baris_terisi": (r["isi_lembar"] or {}).get("baris_terisi"),
        "diunggah": _waktu(r["waktu_unggah"]),
        "keputusan": r["keputusan"],
    }
