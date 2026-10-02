"""Dependensi FastAPI: koneksi DB, klien mesin, penyimpanan. Diganti di uji lewat dependency_overrides."""
import httpx
import psycopg
from psycopg.rows import dict_row

from . import config
from .mesin import KlienMesin
from .penyimpanan import Penyimpanan


def get_conn():
    conn = psycopg.connect(config.database_url(), row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
    try:
        yield conn
    finally:
        conn.close()


def get_mesin() -> KlienMesin:
    return KlienMesin(httpx.Client(base_url=config.mesin_url(), timeout=60), config.kunci_mesin())


def get_penyimpanan() -> Penyimpanan:
    return Penyimpanan(config.upload_dir())
