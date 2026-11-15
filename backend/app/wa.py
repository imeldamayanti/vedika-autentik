"""Pengirim WhatsApp lewat Meta WhatsApp Cloud API: pesan pemberitahuan (Lampiran B) dan chat cadangan.

Mode (META_WA_MODE): log = tanpa jaringan, teks = pesan teks biasa (hanya sampai dalam 24 jam setelah penerima
terakhir mengirim pesan ke nomor bisnis), template = template yang sudah disetujui Meta.
Satu percobaan, batas 10 detik: panggilan tidak pernah menunggu WhatsApp. Token, nomor, dan isi pesan tidak dicatat.
"""
import logging

import httpx

from . import config
from .aturan_v3 import nomor_internasional

log = logging.getLogger("vedika.wa")
BATAS_DETIK = 10


def susun_isi(mode: str, nomor: str, jenis: str, teks: str, parameter: list[str]) -> dict:
    dasar = {"messaging_product": "whatsapp", "to": nomor_internasional(nomor)}
    if mode == "teks":
        return {**dasar, "type": "text", "text": {"body": teks}}
    return {**dasar, "type": "template", "template": {
        "name": config.meta_wa_template(jenis), "language": {"code": config.meta_wa_template_bahasa()},
        "components": [{"type": "body", "parameters": [{"type": "text", "text": str(v)} for v in parameter]}],
    }}


def _gagal(jenis: str, pesan: str) -> dict:
    log.warning("wa %s gagal: %s", jenis, pesan)
    return {"status": "gagal", "pesan": pesan}


def kirim(nomor: str, jenis: str, teks: str, parameter: list[str], transport: httpx.BaseTransport | None = None) -> dict:
    """jenis: pemberitahuan | cadangan. Balasan {"status": terkirim | simulasi | gagal, "pesan"}; pesan tanpa nomor."""
    mode = config.meta_wa_mode()
    if mode == "log":
        log.info("wa %s: simulasi (Meta belum diatur)", jenis)
        return {"status": "simulasi", "pesan": None}
    versi = config.meta_wa_api_version()
    if not versi:
        return _gagal(jenis, "META_WA_API_VERSION belum diisi")
    if mode == "template" and not config.meta_wa_template(jenis):
        return _gagal(jenis, f"META_WA_TEMPLATE_{jenis.upper()} belum diisi")
    try:
        with httpx.Client(timeout=BATAS_DETIK, transport=transport) as klien:
            r = klien.post(
                f"https://graph.facebook.com/{versi}/{config.meta_wa_phone_id()}/messages",
                headers={"Authorization": f"Bearer {config.meta_wa_token()}"},
                json=susun_isi(mode, nomor, jenis, teks, parameter),
            )
    except httpx.TimeoutException:
        return _gagal(jenis, "batas waktu 10 detik")
    except httpx.HTTPError as e:
        return _gagal(jenis, f"tidak terhubung ({type(e).__name__})")
    if not r.is_success:
        return _gagal(jenis, f"HTTP {r.status_code}{_kode_meta(r)}")
    log.info("wa %s: terkirim", jenis)
    return {"status": "terkirim", "pesan": None}


def _kode_meta(r: httpx.Response) -> str:
    """Kode galat Meta (angka) bila ada; isi balasan lainnya dibuang karena bisa memuat nomor."""
    try:
        kode = r.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return ""
    return f", kode Meta {kode}" if isinstance(kode, int) else ""
