from datetime import datetime, timedelta, timezone

# Assignment EXP rules
ASSIGNMENT_BASE_POINTS = 10
ASSIGNMENT_EARLY_BONUS_POINTS = 5
ASSIGNMENT_EARLY_BONUS_THRESHOLD = timedelta(hours=24)
LATE_ASSIGNMENT_POINTS = 0

def _to_utc(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be an ISO 8601 timestamp"
            ) from exc
    if not isinstance(value, datetime):
        raise TypeError(
            f"{field_name} must be a datetime or ISO 8601 string"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must include a time zone"
        )
    return value.astimezone(timezone.utc)

def calculate_assignment_points(
    due_at: datetime | str,
    submitted_at: datetime | str,
) -> int:
# Calculate assignment EXP based on submission timing.
    due = _to_utc(due_at, "due_at")
    submitted = _to_utc(submitted_at, "submitted_at")
    time_early = due - submitted
# Late
    if time_early < timedelta(0):
        return LATE_ASSIGNMENT_POINTS
# Early bonus
    if time_early >= ASSIGNMENT_EARLY_BONUS_THRESHOLD:
        return (
            ASSIGNMENT_BASE_POINTS
            + ASSIGNMENT_EARLY_BONUS_POINTS
        )
# On time
    return ASSIGNMENT_BASE_POINTS
