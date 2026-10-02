"""Aturan label (PRD bagian 9). Port dari hitungLabel di data.js.

Satu-satunya tempat label dihitung. Mesin AI hanya mengirim sinyal.
"""

NAMA_LABEL = {
    "prioritas": "Prioritas",
    "cek": "Perlu dicek",
    "ulang": "Scan ulang",
    "lolos": "Lolos",
}

SARAN = {"lolos": "wajar", "ulang": "scanUlang", "cek": "klarifikasi", "prioritas": "telaah"}

ALASAN_SARAN = {
    "lolos": "Semua pemeriksaan bersih dan isi berkas cocok dengan klaim.",
    "ulang": "Berkas belum bisa dinilai. Hasil scan yang jelek bukan tanda kecurangan.",
    "cek": "Ada sinyal yang masih mungkin kelalaian administrasi. Beri rumah sakit kesempatan menjelaskan.",
    "prioritas": "Ada lebih dari satu sinyal kuat. Tim telaah perlu melihat kasus ini lebih dulu.",
}


def hitung_label(berkas: dict) -> str:
    if berkas["kualitas_scan"]["status"] == "scan_ulang":
        return "ulang"
    sinyal = [t for t in berkas["temuan"] if t["kekuatan"] != "info"]
    if not sinyal:
        return "lolos"
    kuat = sum(1 for t in sinyal if t["kekuatan"] == "kuat")
    # Tanda buatan AI hanya menaikkan urutan, tidak pernah jadi satu-satunya alasan Prioritas.
    selain_ai = sum(1 for t in sinyal if t["cek"] != "tanda_ai")
    if selain_ai and (kuat >= 2 or (kuat >= 1 and len(sinyal) >= 2)):
        return "prioritas"
    return "cek"
