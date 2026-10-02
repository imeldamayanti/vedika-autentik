"""Uji stub mesin AI: harus memenuhi Kontrak B (docs/api-contract.md)."""
from fastapi.testclient import TestClient

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
    assert not {"berkas_kembar", "tempelan"} & {finding["cek"] for finding in h["temuan"]}


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
    assert len(h["tempelan"]) == 8


def test_bandingkan_berkas_beda_tidak_sama():
    h = bandingkan("VA-ASL-01.pdf", "VA-ASL-02.pdf").json()
    assert h["sama"] is False
