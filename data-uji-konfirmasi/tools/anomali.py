"""Anomaly model anomali-v2: how rare a monthly physiotherapy claim pattern is among patients of the same age.

Standard library only, shared by the trainer (ai-service), the demo data, and the backend.

A pattern is six call-confirmable features cut into fixed bins. The model stores weighted pattern shares
nationally and per age group, only for cells with at least `minimum_cell` participant-months. For a group
of n participant-months:

    s = the group's share of the pattern (a small cell gets the group's leftover share, split by national share)
    p = (n * s + alpha * national share) / (n + alpha)
    score = -ln p

A pattern is flagged when score >= threshold. Patterns seen fewer than `minimum_cell` times nationally are not
in the table and are always flagged. Rules OR model choose who is called; the participant's answer decides
the outcome (tools/aturan.py). `hospital_funnel` compares a hospital's selected patients with the number
expected from its patients' ages.

Texts returned for verifiers are Indonesian.
"""
import math

FEATURES = ("sesi", "maks_minggu", "ahad_libur", "episode", "tanpa_rujukan", "lintas_wilayah")
BIN_UPPER_BOUNDS = {
    "sesi": (4, 8, 12),
    "maks_minggu": (2, 3),
    "ahad_libur": (0, 1),
    "episode": (2, 5),
    "tanpa_rujukan": (0, 0.999),
    "lintas_wilayah": (0, 0.999),
}
BIN_LABELS = {
    "sesi": ("1–4 sesi sebulan", "5–8 sesi sebulan", "9–12 sesi sebulan", "13 sesi atau lebih sebulan"),
    "maks_minggu": ("paling banyak 2 sesi seminggu", "3 sesi dalam satu minggu", "4 sesi atau lebih dalam satu minggu"),
    "ahad_libur": ("tanpa sesi hari Minggu", "1 sesi hari Minggu", "2 sesi atau lebih hari Minggu"),
    "episode": ("1–2 bulan berturut-turut", "3–5 bulan berturut-turut", "6 bulan atau lebih berturut-turut"),
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
AGE_GROUP_LABELS = {"<18": "di bawah 18 tahun", "18-39": "18–39 tahun", "40-59": "40–59 tahun", "60+": "60 tahun ke atas"}
RARE_SHARE = 0.10
Z_95, Z_99_8 = 1.96, 3.09


def referral_features(visits):
    """Share of visits without an FKTP referral, and share referred from another district."""
    n = len(visits)
    return {
        "tanpa_rujukan": sum(not v.get("referred", True) for v in visits) / n,
        "lintas_wilayah": sum(v.get("other_district", False) for v in visits) / n,
    }


def anomaly_features(pattern_features, visits):
    """The four visit-pattern features of tools/pola.py plus the two referral features."""
    features = {k: pattern_features[k] for k in FEATURES[:4]}
    features.update(referral_features(visits))
    return features


def bin_value(feature, value):
    bounds = BIN_UPPER_BOUNDS[feature]
    return next((i for i, bound in enumerate(bounds) if value <= bound), len(bounds))


def bin_features(features):
    return tuple(bin_value(k, features[k]) for k in FEATURES)


def cell_key(bins):
    return "|".join(str(b) for b in bins)


def age_group(age):
    if age is None:
        return None
    return "<18" if age < 18 else "18-39" if age < 40 else "40-59" if age < 60 else "60+"


def smoothed_share(n, alpha, stored, national, key):
    """Share of `key` in a group of n, shrunk towards the national share.

    `stored` holds the group's shares of its large-enough cells; every other key gets the group's
    leftover share, split in proportion to the national shares.
    """
    if key in stored:
        share = stored[key]
    else:
        national_left = sum(v for k, v in national.items() if k not in stored)
        share = max(0.0, 1 - sum(stored.values())) * national[key] / national_left if national_left else 0.0
    return (n * share + alpha * national[key]) / (n + alpha)


def probability(model, features, group):
    """Probability of the pattern in its group; None when the pattern is too rare to be in the table.

    A group the model does not know (e.g. unknown age) uses the national share.
    """
    key = cell_key(bin_features(features))
    if key not in model["patterns"]:
        return None
    stats = model["groups"].get(group)
    if stats is None:
        return model["patterns"][key]
    return smoothed_share(stats["n"], model["alpha"], stats["patterns"], model["patterns"], key)


def score(model, features, group):
    """{score, probability, flagged, rare}. A pattern outside the table: no score, rare, flagged."""
    p = probability(model, features, group)
    if p is None:
        return {"score": None, "probability": None, "flagged": True, "rare": True}
    value = round(-math.log(p), 4)
    return {"score": value, "probability": round(p, 6), "flagged": value >= model["threshold"], "rare": False}


def bin_shares(model, group, feature):
    """Share of every bin of one feature in a group (smoothed), or nationally for an unknown group."""
    national = {str(i): share for i, share in enumerate(model["marginal"][feature])}
    stats = model["groups"].get(group)
    if stats is None:
        return list(national.values())
    return [
        smoothed_share(stats["n"], model["alpha"], stats["marginal"][feature], national, str(i))
        for i in range(len(national))
    ]


def percent(x):
    """Indonesian percent: one decimal with a comma, no ',0', never rounded to 0 or 100."""
    x = min(x, 99.9) if x < 100 else x
    if 0 < x < 0.1:
        return "kurang dari 0,1"
    return f"{x:.1f}".replace(".", ",").removesuffix(",0")


def _patients(group):
    return f"pasien {AGE_GROUP_LABELS[group]}" if group in AGE_GROUP_LABELS else "pasien"


def _join(parts):
    if len(parts) <= 2:
        return " dan ".join(parts)
    return ", ".join(parts[:-1]) + ", dan " + parts[-1]


def reasons(model, features, group, n=2):
    """Up to n bins that are rare (< 10%) in the group, rarest first, and one sentence on the whole pattern."""
    bins = bin_features(features)
    shares = {name: bin_shares(model, group, name) for name in FEATURES}
    rare = sorted(
        (shares[name][b], i, name, b)
        for i, (name, b) in enumerate(zip(FEATURES, bins))
        if shares[name][b] < RARE_SHARE
    )
    rare_bins = [
        {
            "feature": name,
            "text": f"{BIN_LABELS[name][b][0].upper()}{BIN_LABELS[name][b][1:]}: hanya {percent(100 * share)}% "
            f"tagihan bulanan {_patients(group)}.",
        }
        for share, _, name, b in rare[:n]
    ]
    uncommon = [BIN_LABELS[name][b] for name, b in zip(FEATURES, bins) if shares[name][b] < max(shares[name])]
    subject = f"Gabungan {_join(uncommon)}" if uncommon else "Gabungan pola ini"
    p = probability(model, features, group)
    how_often = (
        f"{percent(100 * p)}% tagihan bulanan fisioterapi {_patients(group)} di data sampel BPJS {model['years']}"
        if p is not None
        else f"kurang dari {model['minimum_cell']} tagihan bulanan di data sampel BPJS {model['years']}"
    )
    return {"rare_bins": rare_bins, "pattern": f"{subject} muncul pada {how_often}."}


def hospital_funnel(model, rows):
    """Funnel-plot position of one hospital: selected patient-months against the number expected from age.

    rows: (group, selected) per patient-month at the hospital; selected = rules OR model. The z-score is
    widened by the model's overdispersion (Spiegelhalter's multiplicative adjustment), so the limits
    describe hospitals that stand out from the usual spread between hospitals, not from chance alone.
    """
    expected_rates = [model["groups"].get(group, model)["selected_rate"] for group, _ in rows]
    selected = sum(chosen for _, chosen in rows)
    expected = sum(expected_rates)
    variance = sum(p * (1 - p) for p in expected_rates) * model.get("overdispersion", 1.0)
    z = (selected - expected) / math.sqrt(variance) if variance else 0.0
    position = "above_99_8" if z > Z_99_8 else "above_95" if z > Z_95 else "within"
    return {"patient_months": len(rows), "selected": selected, "expected": round(expected, 1), "z": round(z, 2), "position": position}
