"""Klien Kontrak B: API memanggil mesin AI. Mesin tidak pernah mengirim label."""
import json

import httpx


class MesinGalat(Exception):
    def __init__(self, kode: str, pesan: str, status: int = 0):
        super().__init__(pesan)
        self.kode = kode
        self.pesan = pesan
        self.status = status


class KlienMesin:
    def __init__(self, klien: httpx.Client, kunci: str | None = None):
        self.klien = klien
        self.headers = {"X-Kunci-Layanan": kunci} if kunci else {}

    def _kirim(self, path: str, **kw) -> dict:
        try:
            r = self.klien.post(path, headers=self.headers, **kw)
        except httpx.HTTPError as e:
            raise MesinGalat("mesin_tidak_tersedia", f"Mesin tidak bisa dihubungi ({type(e).__name__}).") from e
        if r.status_code != 200:
            try:
                g = r.json()["galat"]
                raise MesinGalat(g["kode"], g["pesan"], r.status_code)
            except (ValueError, KeyError, TypeError):
                raise MesinGalat("mesin_galat", f"Mesin membalas {r.status_code}.", r.status_code)
        return r.json()

    def analisis(self, nama: str, isi: bytes, klaim: dict | None = None) -> dict:
        return self._kirim(
            "/v1/analisis",
            files={"file": (nama, isi)},
            data={"klaim": json.dumps(klaim or {})},
        )

    def bandingkan(self, nama_a: str, isi_a: bytes, nama_b: str, isi_b: bytes) -> dict:
        return self._kirim("/v1/bandingkan", files={"file_a": (nama_a, isi_a), "file_b": (nama_b, isi_b)})

    def sehat(self) -> bool:
        try:
            r = self.klien.get("/v1/kesehatan", headers=self.headers)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except (httpx.HTTPError, ValueError):
            return False
