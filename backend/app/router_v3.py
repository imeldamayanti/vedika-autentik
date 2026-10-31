"""Kontrak A v3: FE ↔ API (docs/api-contract-v3.md). Tanpa login di prototipe (produksi: login Supabase)."""
from fastapi import APIRouter, Depends, Query

from . import config, repo_v3, tampilan_v3
from .deps import get_conn
from .galat import Galat

router = APIRouter(prefix="/api/v1")
POLA_BULAN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.get("/antrean")
def antrean(
    bulan: str = Query(config.BULAN_BAWAAN, pattern=POLA_BULAN),
    id_rs: str | None = None,
    status: str | None = None,
    conn=Depends(get_conn),
):
    return tampilan_v3.antrean(conn, bulan, id_rs, status)


@router.get("/panggilan/{id_}")
def detail_panggilan(id_: str, conn=Depends(get_conn)):
    d = tampilan_v3.detail(conn, id_)
    if d is None:
        raise Galat(404, "panggilan_tidak_ada", "Panggilan tidak ditemukan.")
    return d


@router.get("/ringkasan-rs")
def ringkasan_rs(bulan: str = Query(config.BULAN_BAWAAN, pattern=POLA_BULAN), conn=Depends(get_conn)):
    return tampilan_v3.ringkasan_rs(conn, bulan)


@router.get("/keputusan")
def riwayat_keputusan(conn=Depends(get_conn)):
    return tampilan_v3.daftar_keputusan(conn)


@router.get("/pengaturan")
def pengaturan(conn=Depends(get_conn)):
    return tampilan_v3.pengaturan_publik(repo_v3.ambil_pengaturan(conn))
