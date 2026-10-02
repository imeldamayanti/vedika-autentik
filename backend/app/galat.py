"""Galat API dengan bentuk seragam: {"galat": {"kode", "pesan"}}."""


class Galat(Exception):
    def __init__(self, status: int, kode: str, pesan: str):
        super().__init__(pesan)
        self.status = status
        self.kode = kode
        self.pesan = pesan
