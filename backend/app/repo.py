"""Akses database. Semua SQL ada di sini. Tabel tanpa awalan schema, mengikuti search_path."""
from psycopg.types.json import Jsonb

URUT_LABEL = "case l.label when 'prioritas' then 0 when 'cek' then 1 when 'ulang' then 2 when 'lolos' then 3 else 4 end"


def _j(nilai):
    return Jsonb(nilai) if nilai is not None else None


def buat_berkas(conn, id_, kode_faskes, faskes, nama_file, path, sha256, oleh):
    conn.execute(
        "insert into berkas (id, kode_faskes, faskes, nama_file, path_storage, sha256, diunggah_oleh)"
        " values (%s,%s,%s,%s,%s,%s,%s)",
        (id_, kode_faskes, faskes, nama_file, path, sha256, oleh),
    )
    conn.execute("insert into job (berkas_id) values (%s)", (id_,))


def ambil_berkas(conn, id_):
    return conn.execute("select * from berkas where id = %s", (id_,)).fetchone()


def ambil_temuan(conn, id_):
    return conn.execute(
        "select cek, kekuatan, skor, region, area, pasangan_id, kalimat from hasil_cek where berkas_id = %s order by id",
        (id_,),
    ).fetchall()


def ambil_label(conn, id_):
    return conn.execute("select label, alasan from label where berkas_id = %s", (id_,)).fetchone()


def keputusan_terakhir(conn, id_):
    return conn.execute(
        "select tindakan, catatan, verifikator, waktu from keputusan"
        " where berkas_id = %s and not dibatalkan order by waktu desc, id desc limit 1",
        (id_,),
    ).fetchone()


def simpan_keputusan(conn, id_, verifikator, tindakan, catatan):
    return conn.execute(
        "insert into keputusan (berkas_id, verifikator, tindakan, catatan) values (%s,%s,%s,%s)"
        " returning tindakan, catatan, verifikator, waktu",
        (id_, verifikator, tindakan, catatan),
    ).fetchone()


def cari_kembar(conn, sidik_halaman, kecuali):
    """Berkas selesai paling awal dengan sidik jari halaman yang sama."""
    return conn.execute(
        "select id, nama_file, path_storage from berkas"
        " where sidik_jari_halaman = %s and id <> %s and status = 'selesai'"
        " order by waktu_unggah, id limit 1",
        (sidik_halaman, kecuali),
    ).fetchone()


def keluarga(conn, id_):
    """(akar, anggota) untuk peta hubungan berkas, atau None bila tidak ada kembaran."""
    asal = conn.execute(
        "select pasangan_id from hasil_cek where berkas_id = %s and cek = 'berkas_kembar' and pasangan_id is not null limit 1",
        (id_,),
    ).fetchone()
    akar = asal["pasangan_id"] if asal else id_
    anak = conn.execute(
        "select distinct berkas_id from hasil_cek where cek = 'berkas_kembar' and pasangan_id = %s", (akar,)
    ).fetchall()
    anggota = sorted({akar} | {r["berkas_id"] for r in anak})
    return (akar, anggota) if len(anggota) > 1 else None


def simpan_hasil(conn, id_, *, klaim, hasil, temuan, label, alasan, ringkasan, versi_aturan):
    sidik = hasil.get("sidik_jari") or {}
    conn.execute(
        "update berkas set status = 'selesai', sep = %s, klaim = %s, isi_lembar = %s, kualitas_scan = %s,"
        " metadata_file = %s, ukuran = %s, sidik_jari = %s, sidik_jari_halaman = %s, sidik_jari_teks = %s,"
        " versi_mesin = %s, versi_aturan = %s, ringkasan = %s, waktu_selesai = now() where id = %s",
        (
            (hasil.get("isi_lembar") or {}).get("no_sep"),
            _j(klaim), _j(hasil.get("isi_lembar")), _j(hasil.get("kualitas_scan")), _j(hasil.get("metadata_file")),
            hasil.get("ukuran"), _j(sidik), sidik.get("halaman"), sidik.get("teks"),
            hasil.get("versi_mesin"), versi_aturan, ringkasan, id_,
        ),
    )
    _simpan_temuan(conn, id_, temuan, hasil.get("versi_mesin"), versi_aturan)
    _simpan_label(conn, id_, label, alasan)


def simpan_gagal(conn, id_, *, galat, kalimat, alasan, versi_aturan):
    conn.execute(
        "update berkas set status = 'gagal', galat = %s, versi_aturan = %s, ringkasan = %s, waktu_selesai = now() where id = %s",
        (galat, versi_aturan, kalimat, id_),
    )
    _simpan_temuan(
        conn, id_, [{"cek": "kualitas_scan", "kekuatan": "info", "kalimat": kalimat}], None, versi_aturan
    )
    _simpan_label(conn, id_, "cek", alasan)


def _simpan_temuan(conn, id_, temuan, versi_mesin, versi_aturan):
    for t in temuan:
        conn.execute(
            "insert into hasil_cek (berkas_id, cek, kekuatan, skor, region, area, pasangan_id, kalimat, versi_mesin, versi_aturan)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                id_, t["cek"], t["kekuatan"], t.get("skor"), t.get("region"), _j(t.get("area")),
                t.get("pasangan"), t["kalimat"], versi_mesin, versi_aturan,
            ),
        )


def _simpan_label(conn, id_, label, alasan):
    conn.execute(
        "insert into label (berkas_id, label, alasan) values (%s,%s,%s)"
        " on conflict (berkas_id) do update set label = excluded.label, alasan = excluded.alasan, waktu = now()",
        (id_, label, alasan),
    )


def daftar(conn, *, label=None, kode_faskes=None, q=None, status=None, halaman=1, per_halaman=25):
    syarat, param = [], []
    if label:
        syarat.append("l.label = %s"); param.append(label)
    if kode_faskes:
        syarat.append("b.kode_faskes = %s"); param.append(kode_faskes)
    if status:
        syarat.append("b.status = %s"); param.append(status)
    if q:
        syarat.append("(b.klaim->>'peserta' ilike %s or b.sep ilike %s or b.id ilike %s)")
        param += [f"%{q}%"] * 3
    where = ("where " + " and ".join(syarat)) if syarat else ""
    dari = "from berkas b left join label l on l.berkas_id = b.id"
    total = conn.execute(f"select count(*) as n {dari} {where}", param).fetchone()["n"]
    baris = conn.execute(
        f"select b.id, b.status, l.label, b.ringkasan, b.klaim, b.isi_lembar, b.waktu_unggah,"
        f" (select tindakan from keputusan where berkas_id = b.id and not dibatalkan order by waktu desc, id desc limit 1) as keputusan"
        f" {dari} {where} order by {URUT_LABEL}, b.waktu_unggah desc, b.id limit %s offset %s",
        param + [per_halaman, (halaman - 1) * per_halaman],
    ).fetchall()
    return total, baris
