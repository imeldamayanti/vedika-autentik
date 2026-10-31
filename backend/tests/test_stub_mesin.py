"""Uji stub mesin AI: harus memenuhi Kontrak B (docs/api-contract.md)."""
import json

import pytest
from fastapi.testclient import TestClient

from app import aturan_v3
from app.config import AKAR
from app.mesin import KlienMesin, MesinGalat
from stub_mesin.main import app

klien = TestClient(app)


def kirim(nama, isi=b"%PDF-1.4 stub"):
    return klien.post("/v1/analisis", files={"file": (nama, isi, "application/pdf")}, data={"klaim": "{}"})


def test_kesehatan():
    r = klien.get("/v1/kesehatan")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analisis_berkas_dataset_mengikuti_kontrak_b():
    r = kirim("VA-DST-01.pdf")
    assert r.status_code == 200
    h = r.json()
    for kunci in ["versi_mesin", "ukuran", "kualitas_scan", "isi_lembar", "temuan", "metadata_file", "sidik_jari"]:
        assert kunci in h
    assert h["ukuran"] == [1240, 1754]
    assert {t["cek"] for t in h["temuan"]} == {"kecocokan_klaim", "suntingan"}


def test_analisis_tidak_mengirim_label_atau_saran():
    h = kirim("VA-KMB-01.pdf").json()
    assert "label" not in h and "saran" not in h


def test_berkas_di_luar_dataset_tidak_terbaca():
    r = kirim("foto-juri.jpg")
    assert r.status_code == 422
    assert r.json()["galat"]["kode"] == "tidak_terbaca"


def test_sidik_jari_deterministik():
    assert kirim("VA-ASL-01.pdf").json()["sidik_jari"] == kirim("VA-ASL-01.pdf").json()["sidik_jari"]


def test_sidik_jari_kembar_sama_dan_beda_dengan_berkas_lain():
    kembar_a = kirim("VA-KMB-01.pdf").json()["sidik_jari"]["halaman"]
    kembar_b = kirim("VA-KMB-00.pdf").json()["sidik_jari"]["halaman"]
    lain = kirim("VA-ASL-01.pdf").json()["sidik_jari"]["halaman"]
    assert kembar_a == kembar_b
    assert lain != kembar_a


def bandingkan(a, b):
    return klien.post(
        "/v1/bandingkan",
        files={"file_a": (a, b"x", "application/pdf"), "file_b": (b, b"x", "application/pdf")},
    )


def test_bandingkan_berkas_kembar_sama():
    h = bandingkan("VA-KMB-01.pdf", "VA-KMB-00.pdf").json()
    assert h["sama"] is True
    assert h["kemiripan"] >= 0.9


def test_bandingkan_berkas_beda_tidak_sama():
    h = bandingkan("VA-ASL-01.pdf", "VA-ASL-02.pdf").json()
    assert h["sama"] is False


# ---- v3: POST /v1/baca (Kontrak B2) ----

SKENARIO = {s["id_skenario"]: s for s in json.loads((AKAR / "data-uji-konfirmasi" / "skenario_uji.json").read_text())}
TRANSKRIP = [{"detik": 0, "pembicara": "ai", "teks": "Selamat siang."}, {"detik": 5, "pembicara": "penerima", "teks": "Iya."}]


def baca(id_, transkrip=TRANSKRIP, **kw):
    return klien.post("/v1/baca", json={"id": id_, "transkrip": transkrip, "konteks": {"sesi_ditagih": 11}}, **kw)


@pytest.mark.parametrize("sid", ["S1", "S2", "S3", "S4", "S6", "S8"])
def test_baca_mengembalikan_expected_jawaban_skenario(sid):
    r = baca(f"CALL-{SKENARIO[sid]['id_peserta']}-2026-08")
    assert r.status_code == 200
    j = r.json()
    assert j.pop("versi_pembaca") == "stub-0.1"
    assert j == SKENARIO[sid]["expected_jawaban"]
    label, alasan = aturan_v3.label_jawaban(j, SKENARIO[sid]["expected_indikator"]["sesi_ditagih"])
    assert (label, alasan) == (SKENARIO[sid]["expected_label"], SKENARIO[sid]["expected_alasan"])


def test_baca_tidak_mengirim_label_atau_saran():
    j = baca("CALL-P-S1-2026-08").json()
    assert not {"label", "saran", "skor"} & j.keys()


def test_baca_panggilan_lain_dijawab_tidak_yakin():
    for id_ in ("CALL-P0002-2026-08", "CALL-LATAR-001", "ngawur", None):
        j = baca(id_).json()
        assert aturan_v3.label_jawaban(j, 9)[0] == "Tidak yakin"


def test_baca_transkrip_kosong_ditolak_422():
    r = baca("CALL-P-S1-2026-08", transkrip=[])
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "transkrip_kosong"


def test_baca_mode_gagal_membalas_502(monkeypatch):
    monkeypatch.setenv("GAGAL", "1")
    r = baca("CALL-P-S1-2026-08")
    assert r.status_code == 502 and r.json()["galat"]["kode"] == "llm_gagal"
    monkeypatch.delenv("GAGAL")
    assert baca("CALL-P-S1-2026-08").status_code == 200


def test_baca_bentuk_permintaan_salah_memakai_bentuk_galat_seragam():
    r = klien.post("/v1/baca", json={"id": "x"})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "validasi"


def test_baca_memeriksa_kunci_layanan_bila_diatur(monkeypatch):
    monkeypatch.setenv("KUNCI_MESIN", "rahasia")
    assert baca("CALL-P-S1-2026-08").json()["galat"]["kode"] == "kunci_salah"
    assert baca("CALL-P-S1-2026-08", headers={"X-Kunci-Layanan": "salah"}).status_code == 401
    assert baca("CALL-P-S1-2026-08", headers={"X-Kunci-Layanan": "rahasia"}).status_code == 200


def test_klien_mesin_baca_lewat_stub_dan_galatnya():
    mesin = KlienMesin(klien)
    j = mesin.baca({"id": "CALL-P-S1-2026-08", "transkrip": TRANSKRIP, "konteks": {}})
    assert j["status_panggilan"] == "terjawab" and j["jumlah_maks"] == 3
    with pytest.raises(MesinGalat) as e:
        mesin.baca({"id": "CALL-P-S1-2026-08", "transkrip": [], "konteks": {}})
    assert (e.value.kode, e.value.status) == ("transkrip_kosong", 422)
