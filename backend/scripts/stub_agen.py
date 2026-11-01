#!/usr/bin/env python3
"""Stub agen suara: berpura-pura jadi agen Zahra lewat Kontrak B1 (docs/api-contract-v3.md).

Tidak menelepon dan tidak membuka WhatsApp: tautan wa.me hanya dicetak. Skenario dikenali dari id panggilan
(CALL-P-S1-2026-08 dst.). Percakapan diputar dari transkrip_uji + assets/rekaman/waktu.json (hasil SR) supaya
layar Panggilan bergerak seirama suara; rekaman utuh assets/rekaman/<S>.mp3 dikirim sebagai hasil.

  .venv/bin/python -m scripts.stub_agen                    # terus mengambil antrean (mode otomatis harus AKTIF)
  .venv/bin/python -m scripts.stub_agen --skenario S1      # sekali jalan: Telepon sekarang S1 lalu selesai
  .venv/bin/python -m scripts.stub_agen --kecepatan 4      # putar 4x lebih cepat

Perilaku:
  S1 S2 S3 S4 S6 S8   WA, jeda, menelepon, tersambung, merekam, transkrip baris demi baris (+ tangkapan_sementara),
                      hasil dengan rekaman .mp3.
  S5                  menelepon dua kali, tidak diangkat; tautan chat cadangan dicetak lalu dilaporkan terkirim.
  panggilan lain      percakapan singkat tanpa rekaman (pembaca stub menjawab Tidak yakin).

Kunci agen dibaca dari --kunci, environment AGEN_KEY, atau backend/.env. Tidak pernah dicetak.
"""
import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx

AKAR = Path(__file__).resolve().parents[2]
DATA = AKAR / "data-uji-konfirmasi"
REKAMAN = AKAR / "assets" / "rekaman"
PREFIX = "/api/v1"
PEMBICARA = {"AI": "ai", "Penerima": "penerima"}

# Indeks baris transkrip tempat tiap isian panel "Yang ditangkap AI" terisi (sama dengan data-v3.js).
ISIAN = {
    "penerima": ("penerima", "hubungan"), "hadir": ("hadir",), "jumlah": ("jumlah_min", "jumlah_maks"),
    "keyakinan": ("keyakinan",), "libur": ("membantah_tanggal_libur",), "bahaya": ("tanda_bahaya",),
}
TANGKAP = {
    "S1": {"penerima": 1, "hadir": 3, "jumlah": 5, "keyakinan": 5, "libur": 7, "bahaya": 8},
    "S2": {"penerima": 1, "hadir": 3, "jumlah": 5, "keyakinan": 5, "libur": 7, "bahaya": 5},
    "S3": {"penerima": 1, "hadir": 3, "jumlah": 5, "keyakinan": 5, "libur": 6, "bahaya": 6},
    "S4": {"penerima": 1, "hadir": 3, "jumlah": 5, "keyakinan": 5, "libur": 7, "bahaya": 8},
    "S6": {"penerima": 1, "hadir": 3, "jumlah": 3, "keyakinan": 3, "libur": 5, "bahaya": 6},
    "S8": {"penerima": 1, "hadir": 3, "jumlah": 3, "keyakinan": 3, "libur": 3, "bahaya": 4},
}
TIDAK_DIANGKAT = {"S5"}
PERCAKAPAN_UMUM = [
    ("ai", 0.0, "Selamat siang, saya asisten otomatis dari BPJS Kesehatan. Panggilan ini direkam untuk konfirmasi layanan."),
    ("penerima", 6.0, "Iya, saya sendiri."),
    ("ai", 9.0, "Kira-kira berapa kali terapi di bulan ini?"),
    ("penerima", 13.0, "Waduh, saya kurang ingat."),
]


class GalatAgen(Exception):
    pass


def muat_kunci(arg: str | None) -> str | None:
    if arg or os.environ.get("AGEN_KEY"):
        return arg or os.environ["AGEN_KEY"]
    env = AKAR / "backend" / ".env"
    if env.exists():
        for baris in env.read_text(encoding="utf-8").splitlines():
            if baris.startswith("AGEN_KEY="):
                return baris.split("=", 1)[1].strip().strip("'\"") or None
    return None


def baca_transkrip(skenario: str) -> list[tuple[str, float, str]]:
    """[(pembicara, detik mulai, teks)] dari transkrip_uji/<S>.txt dan assets/rekaman/waktu.json."""
    baris = [b for b in (DATA / "transkrip_uji" / f"{skenario}.txt").read_text(encoding="utf-8").splitlines() if b.strip()]
    waktu = json.loads((REKAMAN / "waktu.json").read_text(encoding="utf-8"))[skenario]["baris"]
    if len(baris) != len(waktu):
        raise GalatAgen(f"{skenario}: {len(baris)} baris transkrip, {len(waktu)} baris di waktu.json.")
    hasil = []
    for b, w in zip(baris, waktu):
        nama, _, teks = b.partition(": ")
        hasil.append((PEMBICARA[nama], w["mulai"], teks.strip()))
    return hasil


def peta_skenario() -> dict[str, dict]:
    """id panggilan -> skenario_uji.json (id_skenario, expected_jawaban)."""
    return {
        f"CALL-{s['id_peserta']}-{s['bulan_layanan']}": s
        for s in json.loads((DATA / "skenario_uji.json").read_text(encoding="utf-8"))
    }


class StubAgen:
    def __init__(self, klien: httpx.Client, kunci: str, *, kecepatan=1.0, dering=3.0, tidur=time.sleep, cetak=print):
        self.klien = klien
        self.headers = {"X-Kunci-Agen": kunci}
        self.kecepatan = kecepatan
        self.dering = dering
        self.tidur = tidur
        self.cetak = cetak
        self.skenario = peta_skenario()

    # ---- HTTP ----

    def _kirim(self, jalur: str, **kw) -> httpx.Response:
        return self.klien.post(PREFIX + jalur, headers=self.headers, **kw)

    def lapor(self, id_: str, laporan: str, catatan: str | None = None) -> dict:
        """Lapor status; 409 jeda_belum_lewat diulang tiap detik (jeda WA diputuskan API)."""
        for _ in range(300):
            r = self._kirim(f"/panggilan/{id_}/status", json={"laporan": laporan, "catatan": catatan})
            if r.status_code == 409 and r.json()["galat"]["kode"] == "jeda_belum_lewat":
                self.tidur(1)
                continue
            if r.status_code != 200:
                raise GalatAgen(f"{id_} {laporan}: {r.status_code} {r.text}")
            return r.json()
        raise GalatAgen(f"{id_}: jeda WA tidak kunjung lewat.")

    # ---- satu tugas ----

    def jalankan_tugas(self, tugas: dict) -> bool:
        """Kerjakan satu tugas dari agen/ambil. True bila panggilan sudah final (hasil terkirim atau tidak terhubung)."""
        id_ = tugas["id"]
        sk = self.skenario.get(id_)
        sid = sk["id_skenario"] if sk else None
        self.cetak(f"[{id_}] tugas diambil: percobaan {tugas['percobaan']}, {tugas['skrip']['nama_penerima']} ({tugas['skrip']['hubungan']})")
        if not tugas["wa"]["lewati"]:
            self.cetak(f"[{id_}] tautan WA (tidak dibuka, kirim manual bila perlu): {tugas['wa']['tautan']}")
            self.lapor(id_, "wa_terkirim")
            self.tidur(tugas["jeda_wa_menit"] * 60)
        self.lapor(id_, "menelepon")
        if sid in TIDAK_DIANGKAT:
            self.tidur(self.dering)
            balasan = self.lapor(id_, "tidak_diangkat")
            if balasan["chat_cadangan"]:
                self.cetak(f"[{id_}] tidak diangkat 2 kali. Tautan chat cadangan: {balasan['chat_cadangan']['tautan']}")
                self.lapor(id_, "chat_cadangan_terkirim")
                return True
            self.cetak(f"[{id_}] tidak diangkat, kembali antre sampai {balasan['coba_lagi_setelah']}")
            return False
        self.lapor(id_, "tersambung")
        self.lapor(id_, "merekam")
        self.putar_percakapan(id_, sid, sk)
        return True

    def putar_percakapan(self, id_: str, sid: str | None, sk: dict | None) -> None:
        if sid in TANGKAP:
            baris = baca_transkrip(sid)
            total = json.loads((REKAMAN / "waktu.json").read_text(encoding="utf-8"))[sid]["total"]
            rekaman = (f"{sid}.mp3", (REKAMAN / f"{sid}.mp3").read_bytes())
        else:
            baris, total, rekaman = PERCAKAPAN_UMUM, PERCAKAPAN_UMUM[-1][1] + 4.0, None
        terkirim, sebelumnya = [], 0.0
        for i, (pembicara, mulai, teks) in enumerate(baris):
            self.tidur(max(0.0, mulai - sebelumnya) / self.kecepatan)
            sebelumnya = mulai
            terkirim.append({"detik": mulai, "pembicara": pembicara, "teks": teks})
            isi = {"baris": terkirim[-1:]}
            if sid in TANGKAP:
                isi["tangkapan_sementara"] = self.tangkapan(sid, sk, i)
            r = self._kirim(f"/panggilan/{id_}/transkrip", json=isi)
            if r.status_code != 204:
                raise GalatAgen(f"{id_} transkrip: {r.status_code} {r.text}")
            self.cetak(f"[{id_}] {mulai:5.1f}s {pembicara:9s} {teks[:70]}")
        self.tidur(max(0.0, total - sebelumnya) / self.kecepatan)
        berkas = {"rekaman": (rekaman[0], io.BytesIO(rekaman[1]), "audio/mpeg")} if rekaman else None
        r = self._kirim(f"/panggilan/{id_}/hasil", data={"transkrip": json.dumps(terkirim), "durasi": str(round(total))}, files=berkas)
        if r.status_code != 202:
            raise GalatAgen(f"{id_} hasil: {r.status_code} {r.text}")
        self.cetak(f"[{id_}] hasil terkirim ({round(total)} detik), API membaca jawaban")

    @staticmethod
    def tangkapan(sid: str, sk: dict, indeks: int) -> dict:
        """Isian panel yang sudah 'ditangkap' sampai baris ke-indeks, nilainya dari expected_jawaban."""
        jawaban = sk["expected_jawaban"]
        return {
            kunci: jawaban.get(kunci) for isian, baris in TANGKAP[sid].items() if baris <= indeks for kunci in ISIAN[isian]
        }

    # ---- loop ----

    def telepon_sekarang(self, skenario: str) -> str:
        id_ = next((i for i, s in self.skenario.items() if s["id_skenario"] == skenario), None)
        if id_ is None:
            raise GalatAgen(f"Skenario {skenario} tidak dikenal.")
        r = self.klien.post(f"{PREFIX}/panggilan/{id_}/mulai")
        if r.status_code != 200:
            raise GalatAgen(f"{id_} mulai: {r.status_code} {r.text}")
        self.cetak(f"[{id_}] ditandai Telepon sekarang")
        return id_

    def jalankan(self, skenario: str | None = None, interval=3.0, maks_putaran=None) -> None:
        target = self.telepon_sekarang(skenario) if skenario else None
        putaran, diam = 0, 0
        while maks_putaran is None or putaran < maks_putaran:
            putaran += 1
            r = self._kirim("/agen/ambil")
            if r.status_code == 401:
                raise GalatAgen("Kunci agen ditolak API (401 kunci_salah). Periksa AGEN_KEY.")
            if r.status_code == 204:
                diam += 1
                if diam % 10 == 1:
                    self.cetak("menunggu tugas (mode otomatis mati, di luar jam kerja, panggilan lain berjalan, atau antrean kosong)")
                self.tidur(interval)
                continue
            diam = 0
            tugas = r.json()
            final = self.jalankan_tugas(tugas)
            if target and tugas["id"] == target and final:
                self.cetak(f"[{target}] selesai")
                return


def main() -> int:
    ap = argparse.ArgumentParser(description="Stub agen suara (Kontrak B1)")
    ap.add_argument("--api", default="http://localhost:8000", help="alamat API (tanpa /api/v1)")
    ap.add_argument("--kunci", help="kunci agen (bawaan: AGEN_KEY dari environment atau backend/.env)")
    ap.add_argument("--skenario", help="sekali jalan untuk satu skenario, mis. S1")
    ap.add_argument("--interval", type=float, default=3.0, help="detik antar agen/ambil saat tidak ada tugas")
    ap.add_argument("--kecepatan", type=float, default=1.0, help="pengali kecepatan putar percakapan")
    ap.add_argument("--dering", type=float, default=3.0, help="detik berdering sebelum tidak diangkat (S5)")
    arg = ap.parse_args()
    kunci = muat_kunci(arg.kunci)
    if not kunci:
        print("Kunci agen kosong. Isi AGEN_KEY di backend/.env atau pakai --kunci.")
        return 1
    agen = StubAgen(httpx.Client(base_url=arg.api, timeout=60), kunci, kecepatan=arg.kecepatan, dering=arg.dering)
    try:
        agen.jalankan(arg.skenario, arg.interval)
    except GalatAgen as e:
        print(f"GALAT: {e}")
        return 1
    except httpx.HTTPError as e:
        print(f"API tidak bisa dihubungi di {arg.api} ({type(e).__name__}).")
        return 1
    except KeyboardInterrupt:
        print("dihentikan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
