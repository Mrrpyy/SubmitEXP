import pytest
from datetime import datetime, timezone

from point_calculator import calculate_assignment_points

DUE_DATE = "2026-10-25T23:59:00Z"

def test_assignment_submitted_early():
    # More than 24 hours early
    points = calculate_assignment_points(
        DUE_DATE, "2026-10-23T20:00:00Z"
    )
    assert points == 15

def test_assignment_exactly_24_hours_early():
    points = calculate_assignment_points(
        DUE_DATE, "2026-10-24T23:59:00Z"
    )
    assert points == 15

def test_assignment_submitted_on_time():
    # Less than 24 hours early
    points = calculate_assignment_points(
        DUE_DATE, "2026-10-25T20:00:00Z"
    )
    assert points == 10

def test_assignment_at_deadline():
    points = calculate_assignment_points(
        DUE_DATE, DUE_DATE
    )
    assert points == 10

def test_assignment_submitted_late():
    points = calculate_assignment_points(
        DUE_DATE, "2026-10-26T00:00:00Z"
    )
    assert points == 0

def test_assignment_datetime_objects():
    due = datetime(2026, 10, 25, 23, 59,
                   tzinfo=timezone.utc)
    submitted = datetime(2026, 10, 24, 20, 0,
                         tzinfo=timezone.utc)

    assert calculate_assignment_points(
        due, submitted
    ) == 15

def test_assignment_missing_timezone():
    with pytest.raises(ValueError):
        calculate_assignment_points(
            "2026-10-25T23:59:00",
            "2026-10-24T20:00:00"
        )

def test_assignment_invalid_date():
    with pytest.raises(ValueError):
        calculate_assignment_points(
            DUE_DATE, "invalid-date"
        )
