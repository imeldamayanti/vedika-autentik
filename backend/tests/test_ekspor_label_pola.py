"""Uji ekspor label panggilan untuk melatih ulang skor pola: hanya fitur dibin dan label, tanpa identitas."""
import json

from scripts import ekspor_label_pola
from tests.util_v3 import ubah


def test_ekspor_awal_empat_riwayat_tanpa_identitas(conn_v3):
    baris = ekspor_label_pola.susun_label(conn_v3)
    assert len(baris) == 4 and sum(b["label"] for b in baris) == 2
    assert all(b.keys() == {"sesi", "maks_minggu", "ahad_libur", "episode", "label"} for b in baris)
    teks = json.dumps(baris)
    assert not any(kata in teks for kata in ("CALL-", "P00", "RS0", "0800", "Bayu", "2026"))


def test_ekspor_hanya_sesuai_dan_tidak_sesuai_yang_selesai(conn_v3):
    ubah(conn_v3, "CALL-P-S1-2026-08", status="selesai", label="Tidak sesuai")
    ubah(conn_v3, "CALL-P-S4-2026-08", status="selesai", label="Tidak yakin")
    ubah(conn_v3, "CALL-P-S5-2026-08", status="tidak_terhubung", label="Tidak terhubung")
    ubah(conn_v3, "CALL-P-S8-2026-08", status="selesai", label="Menolak")
    baris = ekspor_label_pola.susun_label(conn_v3)
    assert len(baris) == 5
    assert {"sesi": "11", "maks_minggu": "4", "ahad_libur": "2+", "episode": "3", "label": 1} in baris
