"""Akses database v3 (konfirmasi suara). Semua SQL v3 ada di sini. Tabel tanpa awalan schema."""
from psycopg.types.json import Jsonb

from .aturan_v3 import BAWAAN_PENGATURAN, STATUS_BERJALAN, STATUS_SELESAI

KOLOM_BARIS = (
    "p.id, p.id_peserta, p.id_rs, p.bulan_layanan, p.sesi_ditagih, p.penerima, p.nama_penerima, p.hubungan,"
    " p.status, p.percobaan, p.prioritas, p.label, p.coba_lagi_setelah, p.diambil_pada, p.waktu_mulai,"
    " p.waktu_selesai, p.jawaban, s.nama as pasien, s.umur, s.jenis_kelamin, r.nama_rs,"
    " i.i1_lebih_8_sebulan as i1, i.i2_3x_seminggu as i2, i.i3_episode_6_bulan as i3, i.i4_hari_libur as i4,"
    " (select k.tindakan from keputusan_panggilan k where k.panggilan_id = p.id order by k.waktu desc, k.id desc limit 1)"
    " as keputusan_tindakan"
)
DARI_BARIS = (
    " from panggilan p join peserta s on s.id_peserta = p.id_peserta join rumah_sakit r on r.id_rs = p.id_rs"
    " left join indikator_bulanan i on i.id_peserta = p.id_peserta and i.id_rs = p.id_rs and i.bulan = p.bulan_layanan"
)


def _j(nilai):
    return Jsonb(nilai) if nilai is not None else None


# ---- pengaturan ----

def ambil_pengaturan(conn) -> dict:
    """Pengaturan terkini; kunci yang belum ada di database memakai nilai bawaan."""
    baris = conn.execute("select kunci, nilai from pengaturan").fetchall()
    return {**BAWAAN_PENGATURAN, **{b["kunci"]: b["nilai"] for b in baris}}


def simpan_pengaturan(conn, perubahan: dict) -> None:
    for kunci, nilai in perubahan.items():
        conn.execute(
            "insert into pengaturan (kunci, nilai) values (%s, %s)"
            " on conflict (kunci) do update set nilai = excluded.nilai",
            (kunci, Jsonb(nilai)),
        )


# ---- panggilan ----

def semua_baris(conn, bulan: str) -> list[dict]:
    """Seluruh panggilan satu bulan layanan, sudah digabung dengan peserta, RS, indikator, dan keputusan terkini."""
    return conn.execute(f"select {KOLOM_BARIS}{DARI_BARIS} where p.bulan_layanan = %s", (bulan,)).fetchall()


def satu_baris(conn, id_: str) -> dict | None:
    return conn.execute(
        f"select {KOLOM_BARIS}, p.transkrip, p.tangkapan_sementara, p.alasan, p.rekaman_path, p.hapus_pada,"
        f" p.sumber, p.durasi_detik, p.waktu_wa, p.galat_pembaca, p.chat_cadangan_terkirim, p.no_tujuan,"
        f" p.jeda_wa_menit{DARI_BARIS} where p.id = %s",
        (id_,),
    ).fetchone()


def log_panggilan(conn, id_: str) -> list[dict]:
    return conn.execute(
        "select status, waktu, percobaan, catatan from panggilan_log where panggilan_id = %s order by waktu, id", (id_,)
    ).fetchall()


def tanggal_sesi(conn, id_peserta: str, id_rs: str, bulan: str) -> list[dict]:
    """Tanggal sesi yang ditagih dan penanda libur nasional (hari Minggu dihitung di pemanggil)."""
    return conn.execute(
        "select k.tanggal, (l.tanggal is not null) as libur from klaim_sesi k"
        " left join libur_nasional l on l.tanggal = k.tanggal"
        " where k.id_peserta = %s and k.id_rs = %s and to_char(k.tanggal, 'YYYY-MM') = %s order by k.tanggal",
        (id_peserta, id_rs, bulan),
    ).fetchall()


def tanggal_libur(conn, id_peserta: str, id_rs: str, bulan: str) -> list:
    r = conn.execute(
        "select tanggal_libur from indikator_bulanan where id_peserta = %s and id_rs = %s and bulan = %s",
        (id_peserta, id_rs, bulan),
    ).fetchone()
    return list(r["tanggal_libur"]) if r else []


# ---- ringkasan RS ----

def semua_rs(conn) -> list[dict]:
    return conn.execute("select id_rs, nama_rs from rumah_sakit order by id_rs").fetchall()


def hitungan_indikator(conn, bulan: str) -> list[dict]:
    """Pasien aktif dan terpicu per RS pada satu bulan layanan."""
    return conn.execute(
        "select id_rs, count(*) as aktif, count(*) filter (where dipicu) as terpicu"
        " from indikator_bulanan where bulan = %s group by id_rs",
        (bulan,),
    ).fetchall()


def panggilan_selesai(conn, bulan: str, id_rs: str | None = None) -> list[dict]:
    """Panggilan berlabel (selesai atau tidak terhubung), terbaru dulu."""
    param: list = [list(STATUS_SELESAI), bulan]
    saring = ""
    if id_rs:
        saring = " and p.id_rs = %s"
        param.append(id_rs)
    return conn.execute(
        "select p.id, p.id_rs, p.label, p.sesi_ditagih, p.jawaban, s.nama as pasien, p.waktu_selesai, p.waktu_mulai"
        " from panggilan p join peserta s on s.id_peserta = p.id_peserta"
        f" where p.status = any(%s) and p.label is not null and p.bulan_layanan = %s{saring}"
        " order by coalesce(p.waktu_selesai, p.waktu_mulai) desc nulls last, p.id",
        param,
    ).fetchall()


# ---- keputusan ----

def keputusan_terkini(conn, panggilan_id: str) -> dict | None:
    return conn.execute(
        "select id, panggilan_id, verifikator, tindakan, ikut_saran, alasan, waktu from keputusan_panggilan"
        " where panggilan_id = %s order by waktu desc, id desc limit 1",
        (panggilan_id,),
    ).fetchone()


def daftar_keputusan(conn) -> list[dict]:
    """Seluruh keputusan, terbaru dulu, dengan penanda terkini (keputusan terbaru tiap panggilan)."""
    return conn.execute(
        "select k.id, k.panggilan_id, k.verifikator, k.tindakan, k.ikut_saran, k.alasan, k.waktu,"
        " (k.id = (select k2.id from keputusan_panggilan k2 where k2.panggilan_id = k.panggilan_id"
        "          order by k2.waktu desc, k2.id desc limit 1)) as terkini,"
        " s.nama as pasien, s.umur, p.id_rs, r.nama_rs, p.label"
        " from keputusan_panggilan k join panggilan p on p.id = k.panggilan_id"
        " join peserta s on s.id_peserta = p.id_peserta join rumah_sakit r on r.id_rs = p.id_rs"
        " order by k.waktu desc, k.id desc"
    ).fetchall()


# ---- tulis (D-03) ----

def tandai_prioritas(conn, id_: str) -> None:
    conn.execute("update panggilan set prioritas = true where id = %s", (id_,))


def simpan_keputusan(conn, id_: str, verifikator: str, tindakan: str, ikut_saran: bool, alasan: str | None, waktu) -> dict:
    return conn.execute(
        "insert into keputusan_panggilan (panggilan_id, verifikator, tindakan, ikut_saran, alasan, waktu)"
        " values (%s,%s,%s,%s,%s,%s) returning id, panggilan_id, verifikator, tindakan, ikut_saran, alasan, waktu",
        (id_, verifikator, tindakan, ikut_saran, alasan, waktu),
    ).fetchone()


def jalur_rekaman(conn) -> list[str]:
    return [r["rekaman_path"] for r in conn.execute("select rekaman_path from panggilan where rekaman_path is not null")]


# ---- agen suara (D-04) ----

KOLOM_JSON = ("jawaban", "transkrip", "tangkapan_sementara")


def perbarui(conn, id_: str, kolom: dict) -> None:
    """Ubah kolom panggilan; nilai dict/list untuk kolom jsonb dibungkus otomatis."""
    sets = ", ".join(f"{k} = %s" for k in kolom)
    nilai = [Jsonb(v) if k in KOLOM_JSON and v is not None else v for k, v in kolom.items()]
    conn.execute(f"update panggilan set {sets} where id = %s", (*nilai, id_))


def tambah_log(conn, id_: str, status: str, waktu, percobaan: int | None, catatan: str | None = None) -> None:
    conn.execute(
        "insert into panggilan_log (panggilan_id, status, waktu, percobaan, catatan) values (%s,%s,%s,%s,%s)",
        (id_, status, waktu, percobaan, catatan),
    )


def tambah_transkrip(conn, id_: str, baris: list[dict]) -> None:
    conn.execute(
        "update panggilan set transkrip = coalesce(transkrip, '[]'::jsonb) || %s where id = %s", (Jsonb(baris), id_)
    )


def ada_panggilan_aktif(conn, batas_kunci) -> bool:
    """Satu panggilan aktif sekaligus: ada yang sedang berjalan, atau sudah diambil agen dan kuncinya belum lepas."""
    return conn.execute(
        "select 1 from panggilan where status = any(%s) or (status = 'antre' and diambil_pada > %s) limit 1",
        (list(STATUS_BERJALAN), batas_kunci),
    ).fetchone() is not None


def kunci_tugas(conn, sekarang, batas_kunci, boleh_otomatis: bool) -> str | None:
    """Ambil dan kunci satu panggilan antre: prioritas dulu, lalu urutan id biner. Kunci yang lewat batas boleh diambil lagi."""
    r = conn.execute(
        "update panggilan set diambil_pada = %s where id = ("
        " select id from panggilan where status = 'antre'"
        " and (diambil_pada is null or diambil_pada <= %s)"
        " and (coba_lagi_setelah is null or coba_lagi_setelah <= %s)"
        " and (prioritas or %s)"
        ' order by prioritas desc, id collate "C" limit 1 for update skip locked) returning id',
        (sekarang, batas_kunci, sekarang, boleh_otomatis),
    ).fetchone()
    return r["id"] if r else None
