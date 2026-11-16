"""Uji pengirim WhatsApp (app/wa.py): mode, isi permintaan ke Meta, normalisasi nomor, dan kegagalan. Tanpa DB."""
import json

import httpx
import pytest

from app import aturan_v3 as at
from app import wa

TEKS = "Halo Andi."
PEMBERITAHUAN = ["Andi Pratama", "1", "0811-0000-0000", "Andi Pratama", "RS Melati Sehat", "Agustus"]
CADANGAN = ["Joko Prasetyo", "RS Cempaka Asri", "Agustus"]


def meta(monkeypatch, mode="teks", **kw):
    nilai = {"META_WA_MODE": mode, "META_WA_TOKEN": "token-rahasia", "META_WA_PHONE_ID": "1234567890",
             "META_WA_API_VERSION": "v99.0", "META_WA_TEMPLATE_PEMBERITAHUAN": "vedika_pemberitahuan",
             "META_WA_TEMPLATE_CADANGAN": "vedika_cadangan", **kw}
    for k, v in nilai.items():
        monkeypatch.setenv(k, v) if v is not None else monkeypatch.delenv(k, raising=False)


def perekam(status=200, isi=None, galat=None):
    permintaan = []

    def tangani(request: httpx.Request) -> httpx.Response:
        permintaan.append(request)
        if galat:
            raise galat
        return httpx.Response(status, json=isi if isi is not None else {"messages": [{"id": "wamid.x"}]})

    return httpx.MockTransport(tangani), permintaan


def tidak_boleh_dipanggil():
    return httpx.MockTransport(lambda request: pytest.fail("tidak boleh ada panggilan jaringan"))


# ---- mode ----

@pytest.mark.parametrize("env", [
    {}, {"META_WA_MODE": "log"}, {"META_WA_MODE": "ngawur"},
    {"META_WA_MODE": "teks", "META_WA_TOKEN": None}, {"META_WA_MODE": "template", "META_WA_PHONE_ID": None},
    {"META_WA_MODE": "teks", "META_WA_TOKEN": ""},
])
def test_mode_log_tanpa_jaringan(monkeypatch, env):
    meta(monkeypatch, mode="log", **env)
    assert wa.kirim("0812-3456-7890", "pemberitahuan", TEKS, PEMBERITAHUAN, tidak_boleh_dipanggil()) == {"status": "simulasi", "pesan": None}


def test_tanpa_env_apa_pun_adalah_simulasi():
    assert wa.kirim("0812-3456-7890", "cadangan", TEKS, CADANGAN, tidak_boleh_dipanggil())["status"] == "simulasi"


# ---- isi permintaan ----

def test_mode_teks_mengirim_pesan_teks(monkeypatch):
    meta(monkeypatch, "teks")
    transport, permintaan = perekam()
    assert wa.kirim("0812-3456-7890", "pemberitahuan", TEKS, PEMBERITAHUAN, transport) == {"status": "terkirim", "pesan": None}
    (r,) = permintaan  # satu percobaan saja
    assert str(r.url) == "https://graph.facebook.com/v99.0/1234567890/messages" and r.method == "POST"
    assert r.headers["authorization"] == "Bearer token-rahasia"
    assert json.loads(r.content) == {"messaging_product": "whatsapp", "to": "6281234567890", "type": "text", "text": {"body": TEKS}}


@pytest.mark.parametrize("jenis,parameter,nama", [
    ("pemberitahuan", PEMBERITAHUAN, "vedika_pemberitahuan"), ("cadangan", CADANGAN, "vedika_cadangan"),
])
def test_mode_template_mengirim_parameter_berurutan(monkeypatch, jenis, parameter, nama):
    meta(monkeypatch, "template")
    transport, permintaan = perekam()
    assert wa.kirim("+62 812-3456-7890", jenis, TEKS, parameter, transport)["status"] == "terkirim"
    assert json.loads(permintaan[0].content) == {
        "messaging_product": "whatsapp", "to": "6281234567890", "type": "template",
        "template": {"name": nama, "language": {"code": "id"},
                     "components": [{"type": "body", "parameters": [{"type": "text", "text": v} for v in parameter]}]},
    }


def test_mode_teks_untuk_chat_cadangan_dan_bahasa_template(monkeypatch):
    meta(monkeypatch, "teks")
    transport, permintaan = perekam()
    wa.kirim("081234567890", "cadangan", "Kami belum berhasil menelepon.", CADANGAN, transport)
    assert json.loads(permintaan[0].content)["text"] == {"body": "Kami belum berhasil menelepon."}
    meta(monkeypatch, "template", META_WA_TEMPLATE_BAHASA="id_ID")
    wa.kirim("081234567890", "cadangan", TEKS, CADANGAN, transport)
    assert json.loads(permintaan[1].content)["template"]["language"] == {"code": "id_ID"}


@pytest.mark.parametrize("nomor,hasil", [
    ("0812-3456-7890", "6281234567890"), ("+62 812 3456 7890", "6281234567890"), ("6281234567890", "6281234567890"),
    ("0800-0000-0000", "6280000000000"),
])
def test_nomor_internasional(nomor, hasil):
    assert at.nomor_internasional(nomor) == hasil
    assert at.tautan_wa(nomor, "a b") == f"https://wa.me/{hasil}?text=a%20b"


# ---- gagal ----

@pytest.mark.parametrize("status", [400, 401, 404, 429, 500, 503])
def test_balasan_bukan_2xx_gagal_tanpa_ulang(monkeypatch, status):
    meta(monkeypatch, "teks")
    transport, permintaan = perekam(status, {"error": {"message": "Recipient 6281234567890 not allowed", "code": 131030}})
    h = wa.kirim("0812-3456-7890", "pemberitahuan", TEKS, PEMBERITAHUAN, transport)
    assert h == {"status": "gagal", "pesan": f"HTTP {status}, kode Meta 131030"} and len(permintaan) == 1


@pytest.mark.parametrize("galat,pesan", [
    (httpx.ReadTimeout("lama"), "batas waktu 10 detik"), (httpx.ConnectTimeout("lama"), "batas waktu 10 detik"),
    (httpx.ConnectError("mati"), "tidak terhubung (ConnectError)"),
])
def test_timeout_dan_tak_terhubung_gagal(monkeypatch, galat, pesan):
    meta(monkeypatch, "template")
    transport, permintaan = perekam(galat=galat)
    assert wa.kirim("0812-3456-7890", "cadangan", TEKS, CADANGAN, transport) == {"status": "gagal", "pesan": pesan}
    assert len(permintaan) == 1


def test_versi_api_dan_nama_template_wajib(monkeypatch):
    meta(monkeypatch, "teks", META_WA_API_VERSION=None)
    assert wa.kirim("0812", "pemberitahuan", TEKS, PEMBERITAHUAN, tidak_boleh_dipanggil()) == {"status": "gagal", "pesan": "META_WA_API_VERSION belum diisi"}
    meta(monkeypatch, "template", META_WA_TEMPLATE_CADANGAN=None)
    assert wa.kirim("0812", "cadangan", TEKS, CADANGAN, tidak_boleh_dipanggil()) == {"status": "gagal", "pesan": "META_WA_TEMPLATE_CADANGAN belum diisi"}


def test_pesan_dan_log_tidak_memuat_nomor_token_atau_teks(monkeypatch, caplog):
    meta(monkeypatch, "teks")
    caplog.set_level("DEBUG")
    for transport in (perekam()[0], perekam(400, {"error": {"message": "to 6281234567890 invalid", "code": 100}})[0],
                      perekam(500, {"bukan": "galat meta"})[0]):
        h = wa.kirim("0812-3456-7890", "pemberitahuan", "Halo Andi Pratama rahasia.", PEMBERITAHUAN, transport)
        assert "81234567890" not in (h["pesan"] or "")
    catatan = caplog.text
    assert catatan and all(x not in catatan for x in ("81234567890", "token-rahasia", "Andi Pratama"))


# ---- Lampiran B ----

def test_teks_lampiran_b_tanpa_tautan():
    pemberitahuan = at.pesan_pemberitahuan(nama_penerima="Andi Pratama", nama_pasien="Andi Pratama", nama_rs="RS Melati Sehat",
                                           bulan="2026-08", jeda_menit=1, nomor_penelepon="0811-0000-0000")
    cadangan = at.pesan_cadangan(nama_pasien="Joko Prasetyo", nama_rs="RS Cempaka Asri", bulan="2026-08")
    assert pemberitahuan == (
        "Halo Andi Pratama. Ini BPJS Kesehatan. Dalam 1 menit kami akan menelepon dari nomor 0811-0000-0000 untuk "
        "konfirmasi singkat layanan fisioterapi Andi Pratama di RS Melati Sehat bulan Agustus. Ini bukan tagihan. "
        "Kami tidak akan meminta data pribadi, kode OTP, atau pembayaran. Untuk memastikan pesan ini, hubungi Care Center 165."
    )
    assert cadangan.startswith("Kami belum berhasil menelepon. Kira-kira berapa kali Joko Prasetyo menjalani fisioterapi di RS Cempaka Asri bulan Agustus?")
    for teks in (pemberitahuan, cadangan):
        assert not any(x in teks.lower() for x in ("http", "www.", "wa.me", ".com", ".id/"))
