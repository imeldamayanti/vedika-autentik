"""API Vedika Autentik (Kontrak A, docs/api-contract.md)."""
import hashlib
import mimetypes
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from . import config, repo, tampilan
from .deps import get_conn, get_mesin, get_penyimpanan
from .galat import Galat
from .label import SARAN

TINDAKAN = {"scanUlang", "klarifikasi", "telaah", "wajar"}

app = FastAPI(title="Vedika Autentik API", version="0.1")


@app.exception_handler(Galat)
def _galat(_, e: Galat):
    return JSONResponse(status_code=e.status, content={"galat": {"kode": e.kode, "pesan": e.pesan}})


@app.exception_handler(RequestValidationError)
def _validasi(_, e: RequestValidationError):
    pesan = "; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors())
    return JSONResponse(status_code=422, content={"galat": {"kode": "validasi", "pesan": pesan}})


@app.post("/api/v1/berkas", status_code=202)
def unggah(
    file: UploadFile = File(...),
    kode_faskes: str = Form(...),
    sep: str | None = Form(None),
    conn=Depends(get_conn),
    simpan=Depends(get_penyimpanan),
):
    nama = file.filename or "berkas"
    if Path(nama).suffix.lower() not in config.EKSTENSI:
        raise Galat(400, "format_tidak_didukung", "Hanya PDF, JPG, atau PNG yang diterima.")
    if kode_faskes not in config.FASKES:
        raise Galat(422, "faskes_tidak_dikenal", "Kode rumah sakit tidak dikenal.")
    isi = file.file.read(config.MAKS_UKURAN + 1)
    if len(isi) > config.MAKS_UKURAN:
        raise Galat(413, "berkas_terlalu_besar", "Ukuran berkas maksimal 10 MB.")
    id_ = "b_" + uuid.uuid4().hex[:12]
    path = simpan.simpan(id_, nama, isi)
    repo.buat_berkas(
        conn, id_, kode_faskes, config.FASKES[kode_faskes], nama, path,
        hashlib.sha256(isi).hexdigest(), config.VERIFIKATOR, sep=(sep or "").strip() or None,
    )
    conn.commit()
    b = repo.ambil_berkas(conn, id_)
    return {"id": id_, "status": "diproses", "diunggah": b["waktu_unggah"].isoformat()}


@app.get("/api/v1/berkas")
def antrean(
    label: str | None = None,
    kode_faskes: str | None = None,
    q: str | None = None,
    status: str | None = None,
    halaman: int = Query(1, ge=1),
    per_halaman: int = Query(25, ge=1, le=100),
    conn=Depends(get_conn),
):
    total, baris = repo.daftar(
        conn, label=label, kode_faskes=kode_faskes, q=q, status=status, halaman=halaman, per_halaman=per_halaman
    )
    return {"total": total, "halaman": halaman, "per_halaman": per_halaman, "item": [tampilan.item_antrean(r) for r in baris]}


@app.get("/api/v1/berkas/{id_}")
def detail(id_: str, conn=Depends(get_conn)):
    d = tampilan.detail(conn, id_)
    if d is None:
        raise Galat(404, "berkas_tidak_ada", "Berkas tidak ditemukan.")
    return d


@app.get("/api/v1/berkas/{id_}/file")
def berkas_asli(id_: str, conn=Depends(get_conn), simpan=Depends(get_penyimpanan)):
    b = repo.ambil_berkas(conn, id_)
    if b is None:
        raise Galat(404, "berkas_tidak_ada", "Berkas tidak ditemukan.")
    tipe = mimetypes.guess_type(b["nama_file"])[0] or "application/octet-stream"
    return Response(content=simpan.baca(b["path_storage"]), media_type=tipe)


class Keputusan(BaseModel):
    tindakan: str
    catatan: str | None = None


@app.post("/api/v1/berkas/{id_}/keputusan", status_code=201)
def putuskan(id_: str, body: Keputusan, conn=Depends(get_conn)):
    if body.tindakan not in TINDAKAN:
        raise Galat(422, "tindakan_tidak_dikenal", "Tindakan harus salah satu dari: " + ", ".join(sorted(TINDAKAN)))
    b = repo.ambil_berkas(conn, id_)
    if b is None:
        raise Galat(404, "berkas_tidak_ada", "Berkas tidak ditemukan.")
    if b["status"] == "diproses":
        raise Galat(409, "belum_selesai", "Berkas masih diproses.")
    saran = SARAN[repo.ambil_label(conn, id_)["label"]]
    catatan = (body.catatan or "").strip()
    if body.tindakan != saran and not catatan:
        raise Galat(422, "catatan_wajib", "Alasan wajib diisi bila tidak mengikuti saran sistem.")
    r = repo.simpan_keputusan(conn, id_, config.VERIFIKATOR, body.tindakan, catatan or None)
    conn.commit()
    hasil = tampilan._keputusan(r)
    if body.tindakan == "telaah":
        hasil["laporan"] = {"nomor": tampilan.nomor_laporan(id_), "url": f"/api/v1/berkas/{id_}/laporan"}
    return hasil


@app.get("/api/v1/kesehatan")
def kesehatan(conn=Depends(get_conn), mesin=Depends(get_mesin)):
    try:
        conn.execute("select 1").fetchone()
        db = "ok"
    except Exception:
        db = "mati"
    return {"api": "ok", "db": db, "mesin": "ok" if mesin.sehat() else "mati"}
