"""Stub mesin AI PRAMANA: menyajikan Kontrak B dari ground truth dataset.

Dipakai selama mesin Zahra belum jadi. Berkas dikenali dari nama file (VA-XXX-NN).
Berkas di luar dataset ditolak 422 tidak_terbaca, sama seperti mesin nyata yang gagal membaca.
"""
import hashlib
import json
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

VERSI_MESIN = "stub-0.1"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "dataset" / "manifest.json"
DATASET = {b["id"]: b for b in json.loads(MANIFEST_PATH.read_text())}

app = FastAPI(title="Stub mesin PRAMANA", version=VERSI_MESIN)


def _id_dari_nama(nama: str) -> str | None:
    m = re.match(r"(VA-[A-Z]+-\d+)", nama or "")
    return m.group(1) if m and m.group(1) in DATASET else None


def _akar(berkas: dict) -> str:
    """Lembar asal. Berkas kembar berbagi akar yang sama."""
    for t in berkas["temuan"]:
        if t["cek"] == "berkas_kembar":
            return t["pasangan"]
    return berkas["id"]


def _hash(teks: str) -> str:
    return hashlib.sha256(teks.encode()).hexdigest()[:16]


def _galat(status: int, kode: str, pesan: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"galat": {"kode": kode, "pesan": pesan}})


@app.get("/v1/kesehatan")
def kesehatan():
    return {"status": "ok", "versi_mesin": VERSI_MESIN, "model": ["stub"]}


@app.post("/v1/analisis")
async def analisis(file: UploadFile = File(...), klaim: str = Form("{}"), template: str = Form("")):
    berkas = DATASET.get(_id_dari_nama(file.filename))
    if berkas is None:
        return _galat(422, "tidak_terbaca", "Stub hanya mengenali berkas dataset (VA-XXX-NN).")
    akar = _akar(berkas)
    # Bukti pasangan hanya boleh lahir dari /v1/bandingkan, bukan analisis satu berkas.
    temuan = [
        {k: v for k, v in t.items() if k != "pasangan"}
        for t in berkas["temuan"]
        if t["cek"] not in {"berkas_kembar", "tempelan"}
    ]
    return {
        "versi_mesin": VERSI_MESIN,
        "ukuran": berkas["ukuran"],
        "halaman_jpg": None,
        "kualitas_scan": berkas["kualitas_scan"],
        "isi_lembar": berkas["isi_lembar"],
        "temuan": temuan,
        "metadata_file": berkas["metadata_file"],
        "sidik_jari": {
            "algoritma": "stub-sha256",
            "halaman": _hash("halaman:" + akar),
            "baris": [_hash(f"baris{i}:{akar}") for i in range(8)],
            "teks": _hash("teks:" + akar),
        },
        "waktu_proses_ms": 5,
    }


@app.post("/v1/bandingkan")
async def bandingkan(file_a: UploadFile = File(...), file_b: UploadFile = File(...)):
    a, b = DATASET.get(_id_dari_nama(file_a.filename)), DATASET.get(_id_dari_nama(file_b.filename))
    if a is None or b is None:
        return _galat(422, "tidak_terbaca", "Stub hanya mengenali berkas dataset (VA-XXX-NN).")
    sama = _akar(a) == _akar(b)
    tempelan = []
    if sama:
        for index in range(1, 9):
            key = f"ttd-{index}"
            if key in a["region_lembar"] and key in b["region_lembar"]:
                tempelan.append(
                    {
                        "bagian": key,
                        "region_a": a["region_lembar"][key],
                        "region_b": b["region_lembar"][key],
                        "kemiripan": 0.99,
                    }
                )
    return {
        "kemiripan": 0.97 if sama else 0.12,
        "sama": sama,
        "kalimat": "Isi berkas 97% sama dengan berkas pembanding, setelah kolom identitas ditutup." if sama
        else "Isi kedua berkas berbeda.",
        "region_a": [a["region_lembar"]["tabel"]] if sama else [],
        "region_b": [b["region_lembar"]["tabel"]] if sama else [],
        "tempelan": tempelan,
    }
