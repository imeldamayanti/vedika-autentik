"""Fixture uji API.

Uji berjalan di Postgres Supabase asli, tetapi di dalam schema sementara `uji` yang dibuat
dan di-rollback per tes. Tabel produksi (schema public) tidak tersentuh.
Tanpa DATABASE_URL di backend/.env, uji yang butuh DB dilewati.
"""
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.deps import get_conn, get_mesin, get_penyimpanan
from app.main import app
from app.mesin import KlienMesin
from app.penyimpanan import Penyimpanan
from stub_mesin.main import app as app_stub

AKAR = Path(__file__).resolve().parents[2]
SKEMA = (AKAR / "backend" / "db" / "schema.sql").read_text().replace("public.", "uji.")

load_dotenv(AKAR / "backend" / ".env")


@pytest.fixture
def conn():
    url = os.environ.get("DATABASE_URL", "")
    if not url or "GANTI_" in url:
        pytest.skip("DATABASE_URL belum diisi di backend/.env")
    c = psycopg.connect(url, connect_timeout=10, prepare_threshold=None, row_factory=dict_row)
    c.execute("create schema uji")
    c.execute("set local search_path to uji")
    c.execute(SKEMA)
    c.commit = lambda: None  # semua perubahan dibuang di akhir tes
    yield c
    c.rollback()
    c.close()


@pytest.fixture
def mesin():
    return KlienMesin(TestClient(app_stub))


@pytest.fixture
def klien(conn, mesin, tmp_path):
    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[get_mesin] = lambda: mesin
    app.dependency_overrides[get_penyimpanan] = lambda: Penyimpanan(tmp_path)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def unggah(klien):
    def _unggah(nama, isi=b"%PDF-1.4 uji", kode_faskes="0901R014", tipe="application/pdf"):
        return klien.post(
            "/api/v1/berkas",
            files={"file": (nama, isi, tipe)},
            data={"kode_faskes": kode_faskes},
        )

    return _unggah
