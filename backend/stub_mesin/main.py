"""Stub mesin AI PRAMANA: menyajikan Kontrak B dari ground truth dataset.

Dipakai selama mesin Zahra belum jadi. Berkas dikenali dari nama file (VA-XXX-NN).
Berkas di luar dataset ditolak 422 tidak_terbaca, sama seperti mesin nyata yang gagal membaca.

v3: POST /v1/baca (Kontrak B2, docs/api-contract-v3.md) mengembalikan expected_jawaban dari
data-uji-konfirmasi/skenario_uji.json menurut id panggilan skenario (S1 sampai S8). Panggilan lain dijawab
Tidak yakin. GAGAL=1 membuat /v1/baca selalu membalas 502 llm_gagal (uji jalur gagal aman).
"""
import hashlib
import json
import os
import re
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

VERSI_MESIN = "stub-0.1"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "dataset" / "manifest.json"
DATASET = {b["id"]: b for b in json.loads(MANIFEST_PATH.read_text())}
SKENARIO_PATH = MANIFEST_PATH.parents[1] / "data-uji-konfirmasi" / "skenario_uji.json"
# id_peserta skenario (P-S1 ...) -> expected_jawaban; kunci_kebenaran_2026-08.csv sengaja tidak dibaca.
JAWABAN_SKENARIO = (
    {s["id_peserta"]: s["expected_jawaban"] for s in json.loads(SKENARIO_PATH.read_text()) if s["expected_label"]}
    if SKENARIO_PATH.exists() else {}
)
JAWABAN_TIDAK_YAKIN = {
    "status_panggilan": "terjawab", "penerima": "peserta", "hubungan": None, "hadir": True, "jumlah_min": None,
    "jumlah_maks": None, "keyakinan": "rendah", "tanda_bahaya": [], "membantah_tanggal_libur": None,
    "kutipan_kunci": "", "ringkasan": "Stub tidak mengenali panggilan ini, jawaban dianggap belum yakin.",
}

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


@app.exception_handler(RequestValidationError)
def _validasi(_, e: RequestValidationError):
    pesan = "; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors())
    return _galat(422, "validasi", pesan)


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


class PermintaanBaca(BaseModel):
    id: str | None = None
    transkrip: list[dict]
    konteks: dict = {}


def _id_peserta(id_panggilan: str | None) -> str | None:
    """CALL-<id_peserta>-<bulan> -> id_peserta."""
    m = re.fullmatch(r"CALL-(.+)-\d{4}-\d{2}", id_panggilan or "")
    return m.group(1) if m else None


@app.post("/v1/baca")
def baca(body: PermintaanBaca, x_kunci_layanan: str | None = Header(None)):
    """Kontrak B2. Kunci diperiksa hanya bila KUNCI_MESIN diisi di lingkungan stub (nyata: selalu)."""
    kunci = os.environ.get("KUNCI_MESIN")
    if kunci and not secrets.compare_digest(x_kunci_layanan or "", kunci):
        return _galat(401, "kunci_salah", "Header X-Kunci-Layanan kosong atau salah.")
    if os.environ.get("GAGAL") == "1":
        return _galat(502, "llm_gagal", "Stub dalam mode GAGAL=1.")
    if not body.transkrip:
        return _galat(422, "transkrip_kosong", "Transkrip kosong, tidak ada yang bisa dibaca.")
    jawaban = JAWABAN_SKENARIO.get(_id_peserta(body.id), JAWABAN_TIDAK_YAKIN)
    return {**jawaban, "versi_pembaca": VERSI_MESIN}
