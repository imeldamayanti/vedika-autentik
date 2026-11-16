"""Model anomali Vedika Autentik: fitur, bin, skor, dan alasan. Hanya pustaka standar.

Isolation Forest (tanpa label) dilatih di laptop dari data sampel BPJS (tahun di model['tahun']), lalu disimpan sebagai tabel:
satu skor per gabungan bin yang muncul pada minimal 10 bulan-pasien. Gabungan yang tidak ada di tabel
lebih jarang dari itu, jadi langsung dianggap tidak biasa. Model ini ikut memilih siapa yang ditelepon
(aturan ATAU model). Hasil konfirmasi tetap dari jawaban peserta, lewat tools/aturan.py.

Fitur hanya hal yang bisa dikonfirmasi peserta lewat telepon: pola kunjungan dan rujukan.
"""

FITUR = ("sesi", "maks_minggu", "ahad_libur", "episode", "tanpa_rujukan", "lintas_wilayah")
# Batas atas tiap bin (nilai <= batas). Nilai di atas batas terakhir masuk bin terakhir.
BATAS = {
    "sesi": (4, 8, 12),
    "maks_minggu": (2, 3),
    "ahad_libur": (0, 1),
    "episode": (2, 5),
    "tanpa_rujukan": (0, 0.999),
    "lintas_wilayah": (0, 0.999),
}
LABEL = {
    "sesi": (
        "1–4 sesi sebulan",
        "5–8 sesi sebulan",
        "9–12 sesi sebulan",
        "13 sesi atau lebih sebulan",
    ),
    "maks_minggu": (
        "paling banyak 2 sesi seminggu",
        "3 sesi dalam satu minggu",
        "4 sesi atau lebih dalam satu minggu",
    ),
    "ahad_libur": ("tanpa sesi hari Minggu", "1 sesi hari Minggu", "2 sesi atau lebih hari Minggu"),
    "episode": (
        "1–2 bulan berturut-turut",
        "3–5 bulan berturut-turut",
        "6 bulan atau lebih berturut-turut",
    ),
    "tanpa_rujukan": (
        "semua kunjungan dengan rujukan FKTP",
        "sebagian kunjungan tanpa rujukan FKTP",
        "semua kunjungan tanpa rujukan FKTP",
    ),
    "lintas_wilayah": (
        "dirujuk dari kab/kota yang sama",
        "sebagian dirujuk dari kab/kota lain",
        "semua dirujuk dari kab/kota lain",
    ),
}
JARANG = 0.10


def fitur_rujukan(kunjungan):
    """Pangsa kunjungan tanpa rujukan FKTP dan pangsa yang dirujuk dari kab/kota lain.

    kunjungan: daftar dict dengan `rujukan` (ada nomor rujukan FKTP) dan `lintas` (kab/kota perujuk beda).
    """
    n = len(kunjungan)
    return {
        "tanpa_rujukan": sum(not k["rujukan"] for k in kunjungan) / n,
        "lintas_wilayah": sum(k["lintas"] for k in kunjungan) / n,
    }


def fitur(fitur_pola, kunjungan):
    """Gabungkan fitur pola kunjungan (tools/pola.py) dengan fitur rujukan."""
    f = {k: fitur_pola[k] for k in FITUR[:4]}
    f.update(fitur_rujukan(kunjungan))
    return f


def bin_nilai(nama, nilai):
    batas = BATAS[nama]
    return next((i for i, b in enumerate(batas) if nilai <= b), len(batas))


def bin_fitur(f):
    return tuple(bin_nilai(k, f[k]) for k in FITUR)


def kunci(b):
    return "|".join(str(x) for x in b)


def persen(x):
    """Persen gaya Indonesia: satu desimal dengan koma, tanpa ',0'; tidak pernah menjadi 0 atau 100."""
    x = min(x, 99.9) if x < 100 else x
    if 0 < x < 0.1:
        return "kurang dari 0,1"
    return f"{x:.1f}".replace(".", ",").removesuffix(",0")


def nilai(model, f):
    """Skor dan keputusan: {skor, ditandai, langka}. Gabungan di luar tabel: skor None, langka, ditandai."""
    sel = model["sel"].get(kunci(bin_fitur(f)))
    if sel is None:
        return {"skor": None, "ditandai": True, "langka": True}
    return {"skor": sel["skor"], "ditandai": sel["skor"] >= model["ambang"], "langka": False}


def alasan(model, f, n=2):
    """Bin yang jarang secara nasional (pangsa < 10%), paling jarang dulu, lalu satu kalimat gabungan."""
    b = bin_fitur(f)
    jarang = []
    for nama, x in zip(FITUR, b):
        pangsa = model["marginal"][nama][x]
        if pangsa < JARANG:
            jarang.append((pangsa, FITUR.index(nama), nama, x))
    hasil = [
        {
            "fitur": nama,
            "teks": f"{LABEL[nama][x][0].upper()}{LABEL[nama][x][1:]}: hanya {persen(100 * p)}% tagihan bulanan fisioterapi nasional.",
        }
        for p, _, nama, x in sorted(jarang)[:n]
    ]
    sel = model["sel"].get(kunci(b))
    seberapa = (
        f"{persen(100 * sel['pangsa'])}% tagihan bulanan fisioterapi nasional {model['tahun']}"
        if sel
        else f"kurang dari {model['minimum_sel']} tagihan bulanan di data sampel BPJS {model['tahun']}"
    )
    return {"alasan": hasil, "gabungan": f"{_bagian_tidak_umum(model, b)} muncul pada {seberapa}."}


def _bagian_tidak_umum(model, b):
    """Bin yang bukan bin terbanyak fiturnya, sebagai satu frasa. Tanpa itu: 'Gabungan pola ini'."""
    bagian = [
        LABEL[nama][x]
        for nama, x in zip(FITUR, b)
        if model["marginal"][nama][x] < max(model["marginal"][nama])
    ]
    if not bagian:
        return "Gabungan pola ini"
    if len(bagian) <= 2:
        daftar = " dan ".join(bagian)
    else:
        daftar = ", ".join(bagian[:-1]) + ", dan " + bagian[-1]
    return f"Gabungan {daftar}"
