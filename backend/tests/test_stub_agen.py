"""Uji D-06: stub agen menjalankan Kontrak B1 dari AKTIF sampai hasil, terhadap API di DB uji (jam dipercepat)."""
import json

import pytest

from app import config
from scripts import stub_agen
from tests.util_v3 import JamMaju, ubah

BASE = "/api/v1"
DATA = config.AKAR / "data-uji-konfirmasi"
SKENARIO = {s["id_skenario"]: s for s in json.loads((DATA / "skenario_uji.json").read_text())}
WAKTU = json.loads((config.AKAR / "assets" / "rekaman" / "waktu.json").read_text())
KUNCI = "kunci-agen-uji"


class Perekam:
    """Pembungkus klien yang mencatat permintaan POST."""

    def __init__(self, klien):
        self.klien, self.catatan = klien, []

    def post(self, url, **kw):
        r = self.klien.post(url, **kw)
        self.catatan.append((url, kw.get("json"), r.status_code))
        return r


def agen_uji(klien, monkeypatch, kunci=KUNCI, **kw):
    jam = JamMaju(monkeypatch)
    keluaran = []
    perekam = Perekam(klien)
    return stub_agen.StubAgen(perekam, kunci, tidur=jam.tidur, cetak=keluaran.append, **kw), jam, keluaran, perekam


def detail(klien, id_):
    return klien.get(f"{BASE}/panggilan/{id_}").json()


def test_s1_dari_mulai_sampai_kartu_bukti(klien_agen, conn_v3, pembaca, tmp_path, monkeypatch):
    pembaca.balasan = [SKENARIO["S1"]["expected_jawaban"]]
    agen, jam, keluaran, perekam = agen_uji(klien_agen, monkeypatch)
    agen.jalankan("S1", maks_putaran=3)
    id_ = "CALL-P-S1-2026-08"
    d = detail(klien_agen, id_)
    assert (d["status"], d["label"], d["percobaan"], d["durasi"]) == ("selesai", "tidak_sesuai", 1, 63)
    assert (d["selisih"], d["saran"], d["alasan"]) == (8, "klarifikasi", SKENARIO["S1"]["expected_alasan"])
    # transkrip baris demi baris memakai detik dari waktu.json (hasil SR)
    assert [t["detik"] for t in d["transkrip"]] == [b["mulai"] for b in WAKTU["S1"]["baris"]]
    assert [t["pembicara"] for t in d["transkrip"]][:3] == ["ai", "penerima", "ai"]
    assert d["transkrip"][5]["teks"] == "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan."
    # rekaman utuh dari SR terkirim
    assert d["rekaman"] and klien_agen.get(d["rekaman"]).content == (config.AKAR / "assets/rekaman/S1.mp3").read_bytes()
    assert [x["status"] for x in d["log"]] == ["wa_terkirim", "menelepon", "tersambung", "merekam", "membaca_jawaban", "selesai"]
    # tautan WA dicetak, tidak dibuka
    assert any("https://wa.me/6281234567890?text=Halo%20Andi%20Pratama" in k for k in keluaran)
    # jeda WA 1 menit dihormati lewat jam API
    assert jam.total_tidur >= 60 + 63
    # RS Melati menjadi Perlu klarifikasi RS
    melati = klien_agen.get(f"{BASE}/ringkasan-rs").json()["rs"][0]
    assert (melati["status"], melati["tidak_sesuai"], melati["terjawab"]) == ("Perlu klarifikasi RS", 3, 5)
    # mode otomatis tetap mati: S1 hanya berjalan karena Telepon sekarang
    assert klien_agen.get(f"{BASE}/pengaturan").json()["mode_otomatis"] is False


def test_tangkapan_sementara_bertambah_seiring_giliran_bicara(klien_agen, pembaca, monkeypatch):
    pembaca.balasan = [SKENARIO["S1"]["expected_jawaban"]]
    agen, _, _, perekam = agen_uji(klien_agen, monkeypatch)
    agen.jalankan("S1", maks_putaran=3)
    kiriman = [j for url, j, st in perekam.catatan if url.endswith("/transkrip")]
    assert len(kiriman) == 9 and all(len(k["baris"]) == 1 for k in kiriman)
    assert kiriman[0]["tangkapan_sementara"] == {}
    assert kiriman[1]["tangkapan_sementara"] == {"penerima": "peserta", "hubungan": None}
    assert kiriman[3]["tangkapan_sementara"].keys() == {"penerima", "hubungan", "hadir"}
    assert kiriman[5]["tangkapan_sementara"]["jumlah_maks"] == 3 and kiriman[5]["tangkapan_sementara"]["keyakinan"] == "tinggi"
    assert kiriman[8]["tangkapan_sementara"] == {
        k: SKENARIO["S1"]["expected_jawaban"][k] for k in
        ("penerima", "hubungan", "hadir", "jumlah_min", "jumlah_maks", "keyakinan", "membantah_tanggal_libur", "tanda_bahaya")
    }
    assert all("label" not in (k["tangkapan_sementara"] or {}) for k in kiriman)  # agen tidak pernah mengirim label


@pytest.mark.parametrize("sid", ["S2", "S3", "S4", "S6", "S8"])
def test_skenario_lain_berakhir_dengan_label_yang_diharapkan(klien_agen, pembaca, monkeypatch, sid):
    pembaca.balasan = [SKENARIO[sid]["expected_jawaban"]]
    agen, _, _, _ = agen_uji(klien_agen, monkeypatch, kecepatan=10)
    agen.jalankan(sid, maks_putaran=3)
    d = detail(klien_agen, f"CALL-{SKENARIO[sid]['id_peserta']}-2026-08")
    assert d["label"] == {"Tidak sesuai": "tidak_sesuai", "Sesuai": "sesuai", "Tidak yakin": "tidak_yakin", "Menolak": "menolak"}[SKENARIO[sid]["expected_label"]]
    assert d["alasan"] == SKENARIO[sid]["expected_alasan"]
    assert (d["rekaman"] is not None) is SKENARIO[sid]["expected_bukti"]["simpan_rekaman"]


def test_s5_dua_kali_tidak_diangkat_lalu_chat_cadangan(klien_agen, conn_v3, monkeypatch):
    agen, jam, keluaran, _ = agen_uji(klien_agen, monkeypatch, dering=3)
    agen.jalankan("S5", maks_putaran=60)
    d = detail(klien_agen, "CALL-P-S5-2026-08")
    assert (d["status"], d["label"], d["percobaan"]) == ("tidak_terhubung", "tidak_terhubung", 2)
    assert d["pesan_wa"]["cadangan"] is not None and d["rekaman"] is None and d["transkrip"] == []
    assert [(x["status"], x["percobaan"], x["catatan"]) for x in d["log"]] == [
        ("wa_terkirim", 1, None), ("menelepon", 1, None), ("menelepon", 1, "tidak_diangkat"),
        ("menelepon", 2, None), ("menelepon", 2, "tidak_diangkat"), ("tidak_terhubung", 2, "chat_cadangan_terkirim"),
    ]
    assert conn_v3.execute("select chat_cadangan_terkirim as c from panggilan where id = 'CALL-P-S5-2026-08'").fetchone()["c"] is True
    assert sum("Tautan chat cadangan: https://wa.me/6281234567890?text=Kami%20belum%20berhasil" in k for k in keluaran) == 1
    assert sum("kembali antre" in k for k in keluaran) == 1
    assert jam.total_tidur >= 120  # jeda percobaan 2 menit dihormati


def test_panggilan_non_skenario_percakapan_singkat_tanpa_rekaman(klien_agen, pembaca, conn_v3, monkeypatch):
    id_ = conn_v3.execute("select id from panggilan where id not like 'CALL-P-S%%' and status = 'antre' order by id collate \"C\" limit 1").fetchone()["id"]
    agen, _, _, _ = agen_uji(klien_agen, monkeypatch, kecepatan=10)
    klien_agen.post(f"{BASE}/panggilan/{id_}/mulai")
    agen.jalankan(maks_putaran=3)
    d = detail(klien_agen, id_)
    assert (d["status"], d["label"], d["rekaman"]) == ("selesai", "tidak_yakin", None)  # pembaca palsu bawaan: Tidak yakin
    assert len(pembaca.permintaan[0]["transkrip"]) == 4


def test_mode_otomatis_aktif_stub_mengambil_urutan_antrean(klien_agen, pembaca, monkeypatch):
    pembaca.balasan = [SKENARIO["S1"]["expected_jawaban"]]
    klien_agen.put(f"{BASE}/pengaturan", json={"mode_otomatis": True})
    agen, _, keluaran, _ = agen_uji(klien_agen, monkeypatch, kecepatan=10)
    agen.jalankan(maks_putaran=1)
    assert detail(klien_agen, "CALL-P-S1-2026-08")["status"] == "selesai"
    assert any("tugas diambil" in k for k in keluaran)


def test_menunggu_bila_tidak_ada_tugas_dan_mencetak_petunjuk(klien_agen, monkeypatch):
    agen, jam, keluaran, perekam = agen_uji(klien_agen, monkeypatch)
    agen.jalankan(maks_putaran=3)
    assert [st for url, _, st in perekam.catatan] == [204, 204, 204]
    assert sum("menunggu tugas" in k for k in keluaran) == 1 and jam.total_tidur == 9


def test_kunci_salah_dilaporkan_jelas(klien_agen, monkeypatch):
    agen, _, _, _ = agen_uji(klien_agen, monkeypatch, kunci="salah")
    with pytest.raises(stub_agen.GalatAgen, match="401"):
        agen.jalankan(maks_putaran=1)


def test_skenario_tidak_dikenal_dan_bukan_antre(klien_agen, conn_v3, monkeypatch):
    agen, _, _, _ = agen_uji(klien_agen, monkeypatch)
    with pytest.raises(stub_agen.GalatAgen, match="S9"):
        agen.jalankan("S9")
    ubah(conn_v3, "CALL-P-S1-2026-08", status="menelepon")
    with pytest.raises(stub_agen.GalatAgen, match="409"):
        agen.jalankan("S1")


def test_transkrip_uji_sinkron_dengan_waktu_json():
    for sid in ("S1", "S2", "S3", "S4", "S6", "S8"):
        baris = stub_agen.baca_transkrip(sid)
        assert len(baris) == len(WAKTU[sid]["baris"]) and baris[0][0] == "ai" and baris[0][1] == 0.0
        assert [b[0] for b in baris] == ["ai", "penerima"] * (len(baris) // 2) + (["ai"] if len(baris) % 2 else [])


def test_muat_kunci_prioritas_arg_lalu_env(monkeypatch):
    monkeypatch.setenv("AGEN_KEY", "dari-env")
    assert stub_agen.muat_kunci("dari-arg") == "dari-arg"
    assert stub_agen.muat_kunci(None) == "dari-env"
