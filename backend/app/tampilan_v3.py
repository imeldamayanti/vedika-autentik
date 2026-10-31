"""Membentuk respons Kontrak A v3 (docs/api-contract-v3.md) dari baris database."""
from datetime import time

from . import aturan_v3 as at
from . import config, jam, repo_v3

URUT_STATUS = {s: n for n, s in enumerate(at.STATUS_BERJALAN)}


def indikator(r: dict) -> list[str]:
    return [f"I{n}" for n in (1, 2, 3, 4) if r.get(f"i{n}")]


def penerima(r: dict) -> dict:
    return {"nama": r["nama_penerima"], "hubungan": at.hubungan_penerima(r)}


def label_api(r: dict) -> str | None:
    return at.LABEL_API.get(r["label"]) if r["label"] and r["status"] in at.STATUS_SELESAI else None


def baris_antre(r: dict) -> dict:
    return {
        "id": r["id"], "pasien": r["pasien"], "umur": r["umur"], "rs": r["id_rs"], "nama_rs": r["nama_rs"],
        "ditagih": r["sesi_ditagih"], "indikator": indikator(r), "penerima": penerima(r), "status": r["status"],
        "label": label_api(r), "keputusan_tindakan": at.TINDAKAN_API.get(r["keputusan_tindakan"]),
        "prioritas": r["prioritas"], "percobaan": r["percobaan"],
    }


def urutan_antrean(r: dict) -> tuple:
    """Sedang berjalan, lalu prioritas, lalu antre (id biner), lalu selesai (terbaru dulu)."""
    if r["status"] in URUT_STATUS:
        return (0, URUT_STATUS[r["status"]], r["id"])
    if r["status"] == "antre":
        return (1, 0 if r["prioritas"] else 1, r["id"])
    selesai = r["waktu_selesai"] or r["waktu_mulai"]
    return (2, -(selesai.timestamp() if selesai else 0), r["id"])


def dalam_jam(pengaturan: dict, sekarang) -> bool:
    mulai = time.fromisoformat(pengaturan["jam_mulai"])
    selesai = time.fromisoformat(pengaturan["jam_selesai"])
    return mulai <= sekarang.timetz().replace(tzinfo=None) < selesai


def pengaturan_publik(pengaturan: dict) -> dict:
    return {k: pengaturan[k] for k in at.BAWAAN_PENGATURAN}


def ringkasan_rs(conn, bulan: str) -> dict:
    """Ringkasan per RS dihitung oleh aturan.py atas panggilan berlabel; kelima RS selalu ada."""
    selesai = repo_v3.panggilan_selesai(conn, bulan)
    hitung = at.ringkasan_rs([{"id_rs": r["id_rs"], "label": r["label"]} for r in selesai])
    pemicu = {r["id_rs"]: r for r in repo_v3.hitungan_indikator(conn, bulan)}
    daftar = []
    for rs in repo_v3.semua_rs(conn):
        c = hitung.get(rs["id_rs"], {})
        aktif, terpicu = (pemicu[rs["id_rs"]]["aktif"], pemicu[rs["id_rs"]]["terpicu"]) if rs["id_rs"] in pemicu else (0, 0)
        daftar.append({
            "id_rs": rs["id_rs"], "nama": rs["nama_rs"], "aktif": aktif, "terpicu": terpicu,
            "persen": round(100 * terpicu / aktif, 1) if aktif else 0.0,
            "sesuai": c.get("sesuai", 0), "tidak_sesuai": c.get("tidak_sesuai", 0),
            "tidak_yakin": c.get("tidak_yakin", 0), "tidak_terhubung": c.get("tidak_terhubung", 0),
            "menolak": c.get("menolak", 0), "terjawab": c.get("terjawab", 0),
            "rasio": c.get("rasio_tidak_sesuai", 0.0), "status": c.get("status", "Normal"),
            "panggilan": [
                {
                    "id": r["id"], "pasien": r["pasien"], "label": at.LABEL_API[r["label"]], "ditagih": r["sesi_ditagih"],
                    "jumlah_min": (r["jawaban"] or {}).get("jumlah_min"),
                    "jumlah_maks": (r["jawaban"] or {}).get("jumlah_maks"),
                    "selisih": at.selisih(r["sesi_ditagih"], r["jawaban"]),
                }
                for r in selesai if r["id_rs"] == rs["id_rs"]
            ],
        })
    return {"bulan": bulan, "aturan": at.ATURAN_RS, "panggilan_selesai": len(selesai), "rs": daftar}


def antrean(conn, bulan: str, id_rs: str | None = None, status: str | None = None) -> dict:
    semua = repo_v3.semua_baris(conn, bulan)
    pengaturan = repo_v3.ambil_pengaturan(conn)
    sekarang = jam.sekarang()
    pemicu = repo_v3.hitungan_indikator(conn, bulan)
    ringkasan = ringkasan_rs(conn, bulan)
    angka = {
        "pasien_aktif": sum(r["aktif"] for r in pemicu), "terpicu": sum(r["terpicu"] for r in pemicu),
        "sudah_ditelepon": sum(r["status"] in at.STATUS_SELESAI for r in semua),
        "tidak_sesuai": sum(r["label"] == "Tidak sesuai" for r in semua),
        "rs_perlu_klarifikasi": sum(r["status"] == "Perlu klarifikasi RS" for r in ringkasan["rs"]),
        "antre": sum(r["status"] == "antre" for r in semua),
        "menunggu_keputusan": sum(r["label"] == "Tidak sesuai" and r["keputusan_tindakan"] is None for r in semua),
    }
    terpilih = [r for r in semua if (not id_rs or r["id_rs"] == id_rs) and (not status or r["status"] == status)]
    return {
        "bulan": bulan, "angka": angka,
        "pengaturan": {
            **pengaturan_publik(pengaturan), "dalam_jam": dalam_jam(pengaturan, sekarang),
            "waktu_server": jam.iso(sekarang),
        },
        "daftar_rs": [{"id_rs": r["id_rs"], "nama": r["nama_rs"]} for r in repo_v3.semua_rs(conn)],
        "baris": [baris_antre(r) for r in sorted(terpilih, key=urutan_antrean)],
    }


def tanda_tanggal(tanggal: list[dict]) -> dict:
    """Satu tanda per tanggal; bila Minggu sekaligus libur nasional, Minggu."""
    tanda = {}
    for t in tanggal:
        if t["tanggal"].weekday() == 6:
            tanda[t["tanggal"].isoformat()] = "Minggu"
        elif t["libur"]:
            tanda[t["tanggal"].isoformat()] = "Libur nasional"
    return tanda


def objek_keputusan(k: dict | None) -> dict | None:
    if k is None:
        return None
    return {
        "id": k["id"], "panggilan_id": k["panggilan_id"], "verifikator": k["verifikator"],
        "tindakan": at.TINDAKAN_API[k["tindakan"]], "ikut_saran": k["ikut_saran"], "alasan": k["alasan"],
        "waktu": jam.iso(k["waktu"]),
    }


def rekaman_tersedia(r: dict, sekarang) -> bool:
    """R5.5: hanya Sesuai dan Tidak sesuai yang menyimpan rekaman, dan hanya sampai hapus_pada."""
    return bool(
        r["rekaman_path"] and r["label"] in ("Sesuai", "Tidak sesuai")
        and (r["hapus_pada"] is None or r["hapus_pada"] > sekarang)
    )


def konteks_rs(conn, r: dict) -> dict:
    ringkas = at.ringkasan_rs([
        {"id_rs": x["id_rs"], "label": x["label"]} for x in repo_v3.panggilan_selesai(conn, r["bulan_layanan"], r["id_rs"])
    ]).get(r["id_rs"], {})
    return {
        "rs": r["id_rs"], "tidak_sesuai": ringkas.get("tidak_sesuai", 0), "terjawab": ringkas.get("terjawab", 0),
        "status": ringkas.get("status", "Normal"),
    }


def detail(conn, id_: str) -> dict | None:
    r = repo_v3.satu_baris(conn, id_)
    if r is None:
        return None
    sekarang = jam.sekarang()
    pengaturan = repo_v3.ambil_pengaturan(conn)
    log = repo_v3.log_panggilan(conn, id_)
    sesi = repo_v3.tanggal_sesi(conn, r["id_peserta"], r["id_rs"], r["bulan_layanan"])
    selesai = r["status"] in at.STATUS_SELESAI
    label = label_api(r)
    jawaban = at.lengkapi_jawaban(r["jawaban"] or (at.JAWABAN_TIDAK_TERHUBUNG if r["status"] == "tidak_terhubung" else None)) if selesai else None
    pertama_menelepon = next((x["waktu"] for x in log if x["status"] == "menelepon"), None)
    simpan_transkrip = not selesai or (r["label"] in ("Sesuai", "Tidak sesuai") and r["sumber"] == "panggilan"
                                       and (r["hapus_pada"] is None or r["hapus_pada"] > sekarang))
    nama_cadangan = at.pesan_cadangan(nama_pasien=r["pasien"], nama_rs=r["nama_rs"], bulan=r["bulan_layanan"])
    return {
        "id": r["id"], "sumber": r["sumber"], "pasien": r["pasien"], "umur": r["umur"], "rs": r["id_rs"],
        "nama_rs": r["nama_rs"], "bulan": r["bulan_layanan"], "ditagih": r["sesi_ditagih"],
        "tanggal": [t["tanggal"].isoformat() for t in sesi], "tanda_tanggal": tanda_tanggal(sesi),
        "indikator": indikator(r),
        "tanggal_libur": [t.isoformat() for t in repo_v3.tanggal_libur(conn, r["id_peserta"], r["id_rs"], r["bulan_layanan"])],
        "penerima": penerima(r), "status": r["status"], "percobaan": r["percobaan"],
        "waktu": jam.iso(r["waktu_mulai"] or pertama_menelepon),
        "log": [
            {"status": x["status"], "waktu": jam.iso(x["waktu"]), "percobaan": x["percobaan"], "catatan": x["catatan"]}
            for x in log
        ],
        "durasi": r["durasi_detik"],
        "transkrip": (r["transkrip"] or []) if simpan_transkrip else [],
        "tangkapan_sementara": None if selesai else r["tangkapan_sementara"],
        "jawaban": jawaban, "label": label, "alasan": r["alasan"] if selesai else None,
        "selisih": at.selisih(r["sesi_ditagih"], jawaban) if selesai else None,
        "toleransi": at.aturan().TOLERANSI_SESI, "saran": at.saran(label),
        "rekaman": f"/api/v1/panggilan/{r['id']}/rekaman" if selesai and rekaman_tersedia(r, sekarang) else None,
        "hapus_pada": jam.iso(r["hapus_pada"]),
        "konteks_rs": konteks_rs(conn, r),
        "pesan_wa": {
            "dari": config.nomor_penelepon(),
            "pemberitahuan": at.pesan_pemberitahuan(
                nama_penerima=r["nama_penerima"], nama_pasien=r["pasien"], nama_rs=r["nama_rs"],
                bulan=r["bulan_layanan"], jeda_menit=pengaturan["jeda_wa_menit"], nomor_penelepon=config.nomor_penelepon(),
            ),
            "cadangan": nama_cadangan if label == "tidak_terhubung" else None,
        },
        "keputusan": objek_keputusan(repo_v3.keputusan_terkini(conn, id_)),
        "galat_pembaca": r["galat_pembaca"],
    }


def daftar_keputusan(conn) -> list[dict]:
    return [
        {
            **objek_keputusan(k), "terkini": k["terkini"], "pasien": k["pasien"], "umur": k["umur"], "rs": k["id_rs"],
            "nama_rs": k["nama_rs"], "label": at.LABEL_API.get(k["label"]),
        }
        for k in repo_v3.daftar_keputusan(conn)
    ]
