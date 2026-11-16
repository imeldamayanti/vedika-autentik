"""Unsupervised anomaly model for call selection: Isolation Forest on the real FKRTL sample.

Exported as a table, not as trees.

The forest is trained on the laptop from binned participant-month features. Only aggregates
leave it:
one score per feature-bin combination seen in at least MINIMUM_SAFE_CELL_COUNT participant-months,
national bin shares, and behaviour counts. Combinations rarer than that are not written; the shared
scorer (data-uji-konfirmasi/tools/anomali.py) treats them as unusual.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

from vedika_ai.claim_reference import MINIMUM_SAFE_CELL_COUNT, ClaimReferenceError
from vedika_ai.pola_reference import MINIMUM_GROUP_MONTHS, load_anomali

VERSION = "anomali-v1"
TARGET_SHARE = 0.015
TREES = 1000
SUBSAMPLE = 512
SEEDS = (7, 11, 23, 42, 99)
RARE_CODE_SHARE = 0.01
HOSPITAL_TARGET_SHARE = 0.05
# Only July-December: `episode` looks back 6 months, and a sample file starts in January.
WINDOW = tuple(f"{month:02d}" for month in range(7, 13))
HOSPITAL_FEATURES = (
    "dipicu",
    "sesi",
    "ahad",
    "tanpa_rujukan",
    "lintas_wilayah",
    "dx_langka",
    "cbg_langka",
)


def in_window(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Participant-months whose 6-month look-back lies inside the same sample file."""

    return [r for r in records if r["bulan"][5:] in WINDOW]


def year_span(records: list[dict[str, Any]]) -> str:
    """'2024', or '2023\u20132024' when the records cover several years."""

    years = sorted({r["bulan"][:4] for r in records})
    return years[0] if len(years) == 1 else f"{years[0]}\u2013{years[-1]}"


def _weight(records: list[dict[str, Any]]) -> float:
    return sum(r["bobot"] for r in records)


def bins(records: list[dict[str, Any]]) -> list[tuple[int, ...]]:
    anomali = load_anomali()
    return [anomali.bin_fitur(r["fitur_anomali"]) for r in records]


def forest_scores(rows: list[tuple[int, ...]], seed: int) -> list[float]:
    """Isolation Forest anomaly score per row (higher = more unusual). Needs the data group."""

    from sklearn.ensemble import IsolationForest

    forest = IsolationForest(n_estimators=TREES, max_samples=SUBSAMPLE, random_state=seed)
    forest.fit(rows)
    return [-s for s in forest.score_samples(rows)]


def top_share(records: list[dict[str, Any]], scores: list[float], share: float) -> set[int]:
    """Indices of the highest-scoring records holding `share` of the total weight."""

    total = _weight(records)
    chosen: set[int] = set()
    cumulative = 0.0
    for i in sorted(range(len(records)), key=lambda i: -scores[i]):
        if cumulative >= share * total:
            break
        chosen.add(i)
        cumulative += records[i]["bobot"]
    return chosen


def table(
    records: list[dict[str, Any]], rows: list[tuple[int, ...]], scores: list[float], minimum: int
) -> tuple[dict[str, dict[str, float]], float]:
    """Score and weight share per bin combination with >= minimum records, and share left out."""

    if minimum < MINIMUM_SAFE_CELL_COUNT:
        raise ClaimReferenceError(f"Minimum cell count must be at least {MINIMUM_SAFE_CELL_COUNT}.")
    anomali = load_anomali()
    total = _weight(records)
    groups: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[anomali.kunci(row)].append(i)
    cells: dict[str, dict[str, float]] = {}
    left_out = 0.0
    for key, members in groups.items():
        weight = sum(records[i]["bobot"] for i in members)
        if len(members) < minimum:
            left_out += weight
            continue
        cells[key] = {
            "skor": round(statistics.fmean(scores[i] for i in members), 4),
            "pangsa": round(weight / total, 6),
        }
    return cells, left_out / total


def threshold(cells: dict[str, dict[str, float]], left_out: float, target: float) -> float:
    """Score of the cell where flagged weight (cells at or above it plus unseen) hits target."""

    ordered = sorted(cells.values(), key=lambda c: -c["skor"])
    flagged = left_out
    for cell in ordered:
        flagged += cell["pangsa"]
        if flagged >= target:
            return cell["skor"]
    return ordered[-1]["skor"]


def marginal(
    records: list[dict[str, Any]], rows: list[tuple[int, ...]], minimum: int
) -> dict[str, list[float]]:
    """National weighted share of every bin of every feature; each bin needs >= minimum records."""

    anomali = load_anomali()
    total = _weight(records)
    result = {}
    for position, name in enumerate(anomali.FITUR):
        count = Counter(row[position] for row in rows)
        weight = Counter()
        for record, row in zip(records, rows, strict=True):
            weight[row[position]] += record["bobot"]
        size = len(anomali.BATAS[name]) + 1
        if any(count[b] < minimum for b in range(size)):
            raise ClaimReferenceError(f"A bin of {name} has fewer than {minimum} records.")
        result[name] = [round(weight[b] / total, 6) for b in range(size)]
    return result


def build_model(
    records: list[dict[str, Any]], minimum: int = MINIMUM_SAFE_CELL_COUNT, check_seeds: bool = True
) -> tuple[dict, dict]:
    """Train, tabulate and set the threshold. Returns (model, training facts for the evaluation)."""

    anomali = load_anomali()
    rows = bins(records)
    scores = forest_scores(rows, SEEDS[0])
    cells, left_out = table(records, rows, scores, minimum)
    model = {
        "versi": VERSION,
        "metode": "Isolation Forest tanpa label, ditabelkan per gabungan bin",
        "fitur": list(anomali.FITUR),
        "batas": {k: list(v) for k, v in anomali.BATAS.items()},
        "minimum_sel": minimum,
        "tahun": year_span(records),
        "target_pangsa": TARGET_SHARE,
        "ambang": round(threshold(cells, left_out, TARGET_SHARE), 4),
        "marginal": marginal(records, rows, minimum),
        "sel": dict(sorted(cells.items())),
        "pelatihan": {
            "pohon": TREES,
            "sampel_per_pohon": SUBSAMPLE,
            "seed": SEEDS[0],
            "bulan_pasien": len(records),
            "bulan": sorted({r["bulan"] for r in records}),
        },
    }
    raw = top_share(records, scores, TARGET_SHARE)
    unseen = [i for i, row in enumerate(rows) if anomali.kunci(row) not in cells]
    unseen_weight = sum(records[i]["bobot"] for i in unseen)
    facts = {
        "pangsa_gabungan_langka": round(left_out, 4),
        "gabungan_dalam_tabel": len(cells),
        "gabungan_langka_juga_ditandai_hutan": round(
            sum(records[i]["bobot"] for i in unseen if i in raw) / unseen_weight, 3
        )
        if unseen_weight
        else None,
        "jaccard_antar_seed": stability(records, rows, scores) if check_seeds else None,
    }
    return model, facts


def _flagged(model: dict, records: list[dict[str, Any]]) -> set[int]:
    anomali = load_anomali()
    return {
        i for i, r in enumerate(records) if anomali.nilai(model, r["fitur_anomali"])["ditandai"]
    }


def validate_over_time(
    train: list[dict[str, Any]], test: list[dict[str, Any]], minimum: int = MINIMUM_SAFE_CELL_COUNT
) -> dict[str, Any]:
    """Train on an earlier year, apply to a later one, compare with the later year's own model."""

    anomali = load_anomali()
    past, _ = build_model(train, minimum, check_seeds=False)
    present, _ = build_model(test, minimum, check_seeds=False)
    total = _weight(test)

    def share(indices) -> float:
        return round(100 * sum(test[i]["bobot"] for i in indices) / total, 2)

    by_past, by_present = _flagged(past, test), _flagged(present, test)
    unknown = [
        i
        for i, r in enumerate(test)
        if anomali.kunci(anomali.bin_fitur(r["fitur_anomali"])) not in past["sel"]
    ]
    return {
        "latih": sorted({r["bulan"][:4] for r in train}),
        "uji": sorted({r["bulan"][:4] for r in test}),
        "persen_ditandai_model_tahun_lalu": share(by_past),
        "persen_ditandai_model_tahun_ini": share(by_present),
        "jaccard": round(len(by_past & by_present) / len(by_past | by_present), 3),
        "persen_hanya_model_tahun_lalu": share(i for i in by_past if not test[i]["dipicu"]),
        "persen_gabungan_tak_dikenal_tahun_lalu": share(unknown),
    }


def outside_check(
    name: str, records: list[dict[str, Any]], model: dict, minimum: int = MINIMUM_SAFE_CELL_COUNT
) -> dict[str, Any] | None:
    """Apply the final table to a disease-specific sample (not used for training)."""

    if len(records) < minimum:
        return None
    total = _weight(records)
    flagged = _flagged(model, records)

    def share(indices) -> float:
        return round(100 * sum(records[i]["bobot"] for i in indices) / total, 2)

    return {
        "sampel": name,
        "bulan_pasien": len(records),
        "tahun": sorted({r["bulan"][:4] for r in records}),
        "persen_ditandai_model": share(flagged),
        "persen_dipicu_aturan": share(i for i, r in enumerate(records) if r["dipicu"]),
        "persen_hanya_model": share(i for i in flagged if not records[i]["dipicu"]),
    }


def stability(
    records: list[dict[str, Any]], rows: list[tuple[int, ...]], first: list[float]
) -> list[float]:
    """Jaccard overlap of the flagged set between the first seed and each other seed."""

    base = top_share(records, first, TARGET_SHARE)
    result = []
    for seed in SEEDS[1:]:
        other = top_share(records, forest_scores(rows, seed), TARGET_SHARE)
        result.append(round(len(base & other) / len(base | other), 3))
    return result


def _share(records: list[dict[str, Any]], total: float) -> float:
    return round(100 * _weight(records) / total, 2)


def behaviour(
    records: list[dict[str, Any]], model: dict, minimum: int = MINIMUM_SAFE_CELL_COUNT
) -> dict[str, Any]:
    """How the exported table behaves on real data. Every count is >= minimum or omitted."""

    anomali = load_anomali()
    total = _weight(records)
    months = sorted({r["bulan"] for r in records})
    for r in records:
        r["_tandai"] = anomali.nilai(model, r["fitur_anomali"])["ditandai"]

    def group(name: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if len(rows) < minimum:
            return None
        return {
            "kelompok": name,
            "bulan_pasien": len(rows),
            "kunjungan": sum(r["fitur"]["sesi"] for r in rows),
            "persen": _share(rows, total),
            "per_bulan_nasional": round(_weight(rows) / len(months)),
        }

    flagged = [r for r in records if r["_tandai"]]
    groups = [
        group("ditandai_model", flagged),
        group("dipicu_aturan", [r for r in records if r["dipicu"]]),
        group("keduanya", [r for r in flagged if r["dipicu"]]),
        group("hanya_model", [r for r in flagged if not r["dipicu"]]),
        group("hanya_aturan", [r for r in records if r["dipicu"] and not r["_tandai"]]),
        group("dipanggil_aturan_atau_model", [r for r in records if r["dipicu"] or r["_tandai"]]),
    ]
    only_model = [r for r in flagged if not r["dipicu"]]
    first_reason = Counter()
    for r in only_model:
        reasons = anomali.alasan(model, r["fitur_anomali"])["alasan"]
        first_reason[reasons[0]["fitur"] if reasons else "gabungan"] += 1
    cells = Counter(anomali.kunci(anomali.bin_fitur(r["fitur_anomali"])) for r in only_model)
    top_cells = [
        {
            "pola": [
                anomali.LABEL[name][int(b)]
                for name, b in zip(anomali.FITUR, key.split("|"), strict=True)
            ],
            "bulan_pasien": n,
        }
        for key, n in cells.most_common(5)
        if n >= minimum
    ]
    by_month = defaultdict(list)
    by_peer: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_month[r["bulan"]].append(r)
        by_peer[r["kelompok"]].append(r)
    monthly = [
        _share([r for r in rows if r["_tandai"]], _weight(rows))
        for _, rows in sorted(by_month.items())
    ]
    peers = [rows for rows in by_peer.values() if len(rows) >= MINIMUM_GROUP_MONTHS]
    rates = sorted(
        (_weight([r for r in rows if r["_tandai"]]) / _weight(rows) for rows in peers), reverse=True
    )
    peer_flagged = sorted(
        (_weight([r for r in rows if r["_tandai"]]) for rows in peers), reverse=True
    )
    top_decile = peer_flagged[: max(1, len(peer_flagged) // 10)]
    for r in records:
        del r["_tandai"]
    return {
        "bulan_pasien": len(records),
        "bulan": len(months),
        "kelompok": [g for g in groups if g],
        "alasan_pertama_hanya_model": [
            {"fitur": k, "bulan_pasien": n} for k, n in first_reason.most_common() if n >= minimum
        ],
        "pola_teratas_hanya_model": top_cells,
        "persen_bulanan": {"min": min(monthly), "maks": max(monthly)},
        "kelompok_rs": {
            "dengan_minimal_bulan_pasien": len(peers),
            "minimal_bulan_pasien": MINIMUM_GROUP_MONTHS,
            "tanpa_ditandai": sum(1 for x in rates if x == 0),
            "pangsa_di_10_persen_teratas": round(100 * sum(top_decile) / sum(peer_flagged), 1)
            if sum(peer_flagged)
            else 0,
        },
    }


def _rare_share(record: dict[str, Any], rare: set, kind: str, at: int) -> float:
    return sum((kind, code[at]) in rare for code in record["kode"]) / len(record["kode"])


def _profile(rows: list[dict[str, Any]], rare: set) -> dict[str, float]:
    """Weighted peer-group means of the hospital-level features."""

    weight = _weight(rows)

    def avg(value) -> float:
        return sum(value(r) * r["bobot"] for r in rows) / weight

    return {
        "dipicu": avg(lambda r: r["dipicu"]),
        "sesi": avg(lambda r: r["fitur"]["sesi"]),
        "ahad": avg(lambda r: r["fitur"]["ahad_libur"] > 0),
        "tanpa_rujukan": avg(lambda r: r["fitur_anomali"]["tanpa_rujukan"]),
        "lintas_wilayah": avg(lambda r: r["fitur_anomali"]["lintas_wilayah"]),
        "dx_langka": avg(lambda r: _rare_share(r, rare, "dx", 0)),
        "cbg_langka": avg(lambda r: _rare_share(r, rare, "cbg", 1)),
    }


def hospital_level(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Isolation Forest over peer groups with >= MINIMUM_GROUP_MONTHS participant-months.

    Returns counts only, never a group identity.
    """

    from sklearn.ensemble import IsolationForest

    visits = Counter()
    for r in records:
        for dx, cbg in r["kode"]:
            visits["dx", dx] += r["bobot"]
            visits["cbg", cbg] += r["bobot"]
    total_visits = {
        kind: sum(w for (k, _), w in visits.items() if k == kind) for kind in ("dx", "cbg")
    }
    rare = {key for key, w in visits.items() if w / total_visits[key[0]] < RARE_CODE_SHARE}

    by_peer: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_peer[r["kelompok"]].append(r)
    profiles = []
    for rows in by_peer.values():
        if len(rows) < MINIMUM_GROUP_MONTHS:
            continue
        profiles.append(_profile(rows, rare))
    scale = {}
    for name in HOSPITAL_FEATURES:
        values = [p[name] for p in profiles]
        quartiles = statistics.quantiles(values, n=4)
        scale[name] = (statistics.median(values), (quartiles[2] - quartiles[0]) or 1.0)
    matrix = [[(p[n] - scale[n][0]) / scale[n][1] for n in HOSPITAL_FEATURES] for p in profiles]
    scores = [
        -s
        for s in IsolationForest(n_estimators=500, random_state=SEEDS[0])
        .fit(matrix)
        .score_samples(matrix)
    ]
    count = round(len(profiles) * HOSPITAL_TARGET_SHARE)
    flagged = sorted(range(len(profiles)), key=lambda i: -scores[i])[:count]
    drivers = Counter(
        HOSPITAL_FEATURES[max(range(len(HOSPITAL_FEATURES)), key=lambda j: abs(matrix[i][j]))]
        for i in flagged
    )
    return {
        "kelompok_rs": len(profiles),
        "ditandai": count,
        "pemicu_utama": [{"fitur": k, "kelompok_rs": n} for k, n in drivers.most_common()],
        "median_nasional": {n: round(scale[n][0], 3) for n in HOSPITAL_FEATURES},
    }
