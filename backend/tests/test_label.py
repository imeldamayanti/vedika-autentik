"""Uji aturan label (PRD bagian 9) terhadap ground truth dataset."""
import json
from pathlib import Path

import pytest

from app.label import hitung_label, SARAN, NAMA_LABEL

MANIFEST = json.loads((Path(__file__).resolve().parents[2] / "dataset" / "manifest.json").read_text())


@pytest.mark.parametrize("berkas", MANIFEST, ids=[b["id"] for b in MANIFEST])
def test_label_hitungan_sama_dengan_ground_truth(berkas):
    assert NAMA_LABEL[hitung_label(berkas)] == berkas["label_diharapkan"]


def temuan(cek, kekuatan):
    return {"cek": cek, "kekuatan": kekuatan}


def berkas(*ts, scan="baik"):
    return {"kualitas_scan": {"status": scan}, "temuan": list(ts)}


def test_scan_jelek_selalu_ulang_walau_ada_temuan_kuat():
    b = berkas(temuan("berkas_kembar", "kuat"), temuan("tempelan", "kuat"), scan="scan_ulang")
    assert hitung_label(b) == "ulang"


def test_tanpa_temuan_lolos():
    assert hitung_label(berkas()) == "lolos"


def test_hanya_info_tetap_lolos():
    assert hitung_label(berkas(temuan("kualitas_scan", "info"))) == "lolos"


def test_satu_sinyal_kuat_saja_perlu_dicek():
    assert hitung_label(berkas(temuan("copy_paste", "kuat"))) == "cek"


def test_dua_sinyal_kuat_prioritas():
    assert hitung_label(berkas(temuan("berkas_kembar", "kuat"), temuan("tempelan", "kuat"))) == "prioritas"


def test_satu_kuat_plus_sinyal_lain_prioritas():
    assert hitung_label(berkas(temuan("kecocokan_klaim", "kuat"), temuan("suntingan", "sedang"))) == "prioritas"


def test_tanda_ai_tidak_pernah_jadi_satu_satunya_alasan_prioritas():
    assert hitung_label(berkas(temuan("tanda_ai", "kuat"), temuan("tanda_ai", "kuat"))) == "cek"


def test_satu_sinyal_sedang_perlu_dicek():
    assert hitung_label(berkas(temuan("suntingan", "sedang"))) == "cek"


def test_saran_per_label():
    assert SARAN == {"lolos": "wajar", "ulang": "scanUlang", "cek": "klarifikasi", "prioritas": "telaah"}
