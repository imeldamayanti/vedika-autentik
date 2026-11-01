from datetime import date

import pytest
from pydantic import ValidationError

from vedika_ai.indicators import IndicatorRequest, ServiceSession, calculate_indicators


def request(
    dates: list[date],
    *,
    current_month: str = "2026-08",
    active_months: list[str] | None = None,
    holidays: set[date] | None = None,
) -> IndicatorRequest:
    holidays = holidays or set()
    return IndicatorRequest(
        bulan=current_month,
        sesi=[ServiceSession(tanggal=value, hari_libur=value in holidays) for value in dates],
        bulan_aktif=active_months or [],
    )


def test_i1_requires_more_than_eight_sessions():
    eight = [date(2026, 8, day) for day in range(1, 9)]
    nine = [date(2026, 8, day) for day in range(1, 10)]

    assert calculate_indicators(request(eight)).i1 is False
    assert calculate_indicators(request(nine)).i1 is True


def test_i2_groups_sessions_by_monday_to_sunday():
    same_week = [date(2026, 8, 3), date(2026, 8, 5), date(2026, 8, 9)]
    split_at_monday = [date(2026, 8, 9), date(2026, 8, 10), date(2026, 8, 11)]

    assert calculate_indicators(request(same_week)).i2 is True
    assert calculate_indicators(request(split_at_monday)).i2 is False


def test_i3_requires_current_and_previous_five_consecutive_months_across_year():
    continuous = ["2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02"]
    with_gap = ["2025-08", "2025-09", "2025-10", "2025-12", "2026-01", "2026-02"]

    assert calculate_indicators(
        request([], current_month="2026-02", active_months=continuous)
    ).i3 is True
    assert calculate_indicators(
        request([], current_month="2026-02", active_months=with_gap)
    ).i3 is False


def test_i4_marks_sunday_and_explicit_holiday_dates():
    sunday = request([date(2026, 8, 16)])
    holiday = request(
        [date(2026, 8, 17)],
        holidays={date(2026, 8, 17)},
    )

    assert calculate_indicators(sunday).tanggal_libur == [date(2026, 8, 16)]
    assert calculate_indicators(holiday).tanggal_libur == [date(2026, 8, 17)]
    assert calculate_indicators(sunday).i4 is True
    assert calculate_indicators(holiday).i4 is True


def test_queue_requires_at_least_two_active_indicators():
    one_indicator = request(
        [date(2026, 8, 3), date(2026, 8, 5), date(2026, 8, 7)]
    )
    two_indicators = request(
        [date(2026, 8, day) for day in range(1, 10)]
    )

    assert calculate_indicators(one_indicator).indikator_aktif == ["I2"]
    assert calculate_indicators(one_indicator).masuk_antrean is False
    assert len(calculate_indicators(two_indicators).indikator_aktif) >= 2
    assert calculate_indicators(two_indicators).masuk_antrean is True


def test_sessions_outside_requested_month_are_rejected():
    with pytest.raises(ValidationError, match="bulan yang diminta"):
        request([date(2026, 7, 31)])

