"""Visit-pattern features of one patient-month, shared by the anomaly model, the backend seed, and the tests.

Standard library only. Feature keys (sesi, maks_minggu, ahad_libur, episode) are data keys and match
tools/aturan.py; the rule indicators computed here equal aturan.hitung_indikator (checked in uji_pola.py).
"""
from collections import Counter, defaultdict
from datetime import timedelta

FEATURES = ("sesi", "maks_minggu", "ahad_libur", "episode")
EPISODE_MAX = 7


def previous_month(month, n):
    year, mon = map(int, month.split("-"))
    mon -= n
    while mon <= 0:
        mon += 12
        year -= 1
    return f"{year:04d}-{mon:02d}"


def month_features(dates, active_months, month, holidays):
    """Raw features of one patient (at one hospital, when known) in one month.

    dates: session dates in that month; active_months: set of 'YYYY-MM' with sessions; holidays: set of dates.
    """
    per_week = Counter(d - timedelta(days=d.weekday()) for d in dates)
    episode = 1
    while episode < EPISODE_MAX and previous_month(month, episode) in active_months:
        episode += 1
    return {
        "sesi": len(dates),
        "maks_minggu": max(per_week.values()),
        "ahad_libur": sum(d.weekday() == 6 or d in holidays for d in dates),
        "episode": episode,
    }


def features_per_patient(sessions, month, holidays):
    """sessions: iterable of (key, date), e.g. key = (participant, hospital). Returns key -> features of that
    month for every key with sessions in it; other months only count towards `episode`."""
    dates = defaultdict(list)
    for key, day in sessions:
        dates[key].append(day)
    result = {}
    for key, days in sorted(dates.items()):
        this_month = [d for d in days if d.strftime("%Y-%m") == month]
        if this_month:
            result[key] = month_features(this_month, {d.strftime("%Y-%m") for d in days}, month, holidays)
    return result


def indicators(features):
    """(I1, I2, I3, I4) from raw features; equal to aturan.hitung_indikator."""
    return (
        features["sesi"] > 8,
        features["maks_minggu"] >= 3,
        features["episode"] >= 6,
        features["ahad_libur"] > 0,
    )
