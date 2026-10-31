"""Kontrak B1: agen suara ↔ API (docs/api-contract-v3.md). Semua endpoint wajib header X-Kunci-Agen.
Prototipe: kunci terlihat di browser agen dan itu diterima (produksi: token per perangkat)."""
import json
import secrets
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from . import agen, config
from .deps import get_buka_conn, get_conn, get_mesin, get_penyimpanan
from .galat import Galat


def periksa_kunci(x_kunci_agen: str | None = Header(None)) -> None:
    kunci = config.kunci_agen()
    if not kunci or not x_kunci_agen or not secrets.compare_digest(x_kunci_agen, kunci):
        raise Galat(401, "kunci_salah", "Header X-Kunci-Agen kosong atau salah.")


router = APIRouter(prefix="/api/v1", dependencies=[Depends(periksa_kunci)])


@router.post("/agen/ambil")
def ambil(conn=Depends(get_conn)):
    tugas = agen.ambil_tugas(conn)
    conn.commit()
    return JSONResponse(tugas) if tugas else Response(status_code=204)


class Laporan(BaseModel):
    laporan: str
    waktu: datetime | None = None
    catatan: str | None = None


@router.post("/panggilan/{id_}/status")
def status(id_: str, body: Laporan, conn=Depends(get_conn)):
    hasil = agen.lapor_status(conn, id_, body.laporan, body.waktu, body.catatan)
    conn.commit()
    return hasil


class BarisTranskrip(BaseModel):
    detik: float
    pembicara: str
    teks: str


class KirimanTranskrip(BaseModel):
    baris: list[BarisTranskrip]
    tangkapan_sementara: dict | None = None


def _baris_valid(baris: list[BarisTranskrip]) -> list[dict]:
    for b in baris:
        if b.pembicara not in ("ai", "penerima") or b.detik < 0:
            raise Galat(422, "transkrip_tidak_valid", "Baris transkrip harus punya detik >= 0 dan pembicara ai atau penerima.")
    return [b.model_dump() for b in baris]


@router.post("/panggilan/{id_}/transkrip", status_code=204)
def transkrip(id_: str, body: KirimanTranskrip, conn=Depends(get_conn)):
    agen.tambah_transkrip(conn, id_, _baris_valid(body.baris), body.tangkapan_sementara)
    conn.commit()
    return Response(status_code=204)


@router.post("/panggilan/{id_}/hasil", status_code=202)
def hasil(
    id_: str,
    latar: BackgroundTasks,
    transkrip: str = Form(...),
    durasi: int = Form(..., ge=0),
    rekaman: UploadFile | None = File(None),
    conn=Depends(get_conn),
    simpan=Depends(get_penyimpanan),
    mesin=Depends(get_mesin),
    buka_conn=Depends(get_buka_conn),
):
    try:
        mentah = json.loads(transkrip)
        if not isinstance(mentah, list):
            raise ValueError
        baris = _baris_valid([BarisTranskrip(**b) for b in mentah])
    except (ValueError, TypeError):
        raise Galat(422, "transkrip_tidak_valid", "transkrip harus berupa JSON array [{detik, pembicara, teks}].")
    berkas = None
    if rekaman is not None and rekaman.filename:
        isi = rekaman.file.read(config.MAKS_REKAMAN + 1)
        if len(isi) > config.MAKS_REKAMAN:
            raise Galat(413, "terlalu_besar", "Ukuran rekaman maksimal 10 MB.")
        berkas = (rekaman.filename, isi)
    agen.simpan_hasil(conn, simpan, id_, baris, durasi, berkas)
    conn.commit()
    latar.add_task(agen.proses_hasil, buka_conn, simpan, mesin, id_)
    return {"status": "membaca_jawaban"}
