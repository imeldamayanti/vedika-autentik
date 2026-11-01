import pytest
from pydantic import ValidationError

from vedika_ai.answers import JawabanTerstruktur, classify_answer


def answer(**updates) -> JawabanTerstruktur:
    values = {
        "status_panggilan": "terjawab",
        "penerima": "peserta",
        "hubungan": None,
        "hadir": True,
        "jumlah_min": 8,
        "jumlah_maks": 8,
        "keyakinan": "tinggi",
        "tanda_bahaya": [],
        "membantah_tanggal_libur": False,
        "kutipan_kunci": "Delapan kali.",
        "ringkasan": "Peserta menyatakan hadir delapan kali.",
    }
    values.update(updates)
    return JawabanTerstruktur.model_validate(values)


@pytest.mark.parametrize(
    "danger",
    ["tanda_tangan_tanpa_layanan", "diminta_membayar", "layanan_berbeda"],
)
def test_answer_schema_accepts_only_prd_danger_flags(danger):
    assert answer(tanda_bahaya=[danger]).tanda_bahaya == [danger]

    with pytest.raises(ValidationError):
        answer(tanda_bahaya=["dugaan_umum"])


def test_answer_schema_rejects_partial_or_reversed_quantity_range():
    with pytest.raises(ValidationError, match="bersama-sama"):
        answer(jumlah_min=3, jumlah_maks=None)

    with pytest.raises(ValidationError, match="jumlah_min"):
        answer(jumlah_min=6, jumlah_maks=5)


@pytest.mark.parametrize(
    ("field", "malformed"),
    [
        ("jumlah_min", True),
        ("jumlah_maks", True),
        ("membantah_tanggal_libur", "false"),
    ],
)
def test_answer_schema_rejects_coerced_scalar_types(field, malformed):
    with pytest.raises(ValidationError):
        answer(**{field: malformed})


@pytest.mark.parametrize("field", ["tanda_bahaya", "kutipan_kunci", "hubungan"])
def test_answer_schema_requires_every_prd_output_field(field):
    values = answer().model_dump()
    del values[field]

    with pytest.raises(ValidationError):
        JawabanTerstruktur.model_validate(values)


@pytest.mark.parametrize(
    ("structured", "billed", "label", "action"),
    [
        (
            answer(
                status_panggilan="tidak_terhubung",
                penerima=None,
                hadir=None,
                jumlah_min=None,
                jumlah_maks=None,
                keyakinan=None,
            ),
            10,
            "Tidak terhubung",
            "Pantau. Tidak dihitung.",
        ),
        (
            answer(
                status_panggilan="menolak",
                hadir=None,
                jumlah_min=None,
                jumlah_maks=None,
                keyakinan=None,
                tanda_bahaya=["diminta_membayar"],
            ),
            10,
            "Menolak",
            "Pantau. Tidak dihitung.",
        ),
        (
            answer(hadir=False, jumlah_min=0, jumlah_maks=0),
            10,
            "Tidak sesuai",
            "Minta klarifikasi RS",
        ),
        (
            answer(tanda_bahaya=["tanda_tangan_tanpa_layanan"], keyakinan="rendah"),
            10,
            "Tidak sesuai",
            "Minta klarifikasi RS",
        ),
        (
            answer(jumlah_min=None, jumlah_maks=None),
            10,
            "Tidak yakin",
            "Pantau. Tidak dihitung.",
        ),
        (answer(keyakinan="rendah"), 10, "Tidak yakin", "Pantau. Tidak dihitung."),
        (answer(jumlah_min=2, jumlah_maks=3), 6, "Tidak sesuai", "Minta klarifikasi RS"),
        (answer(jumlah_min=8, jumlah_maks=9), 10, "Sesuai", "Tutup kasus"),
    ],
)
def test_label_rules_follow_prd_order(structured, billed, label, action):
    result = classify_answer(structured, billed)

    assert result.label == label
    assert result.langkah_disarankan == action


def test_difference_of_exactly_two_sessions_is_tolerated():
    result = classify_answer(answer(jumlah_min=7, jumlah_maks=8), billed_sessions=10)

    assert result.label == "Sesuai"


def test_billed_sessions_must_be_non_negative():
    with pytest.raises(ValueError, match="non-negatif"):
        classify_answer(answer(), billed_sessions=-1)

