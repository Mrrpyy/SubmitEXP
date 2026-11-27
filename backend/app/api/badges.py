from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import UserInfo
from app.api.roles import require_student
from app.db.connection import DatabaseNotConfigured, get_engine


# student badges, bascially student achievements

router = APIRouter(prefix="/badges", tags=["badges"])

EARLY_BIRD_HOURS = 24
WEEK_AHEAD_DAYS = 7
CLUTCH_HOURS = 1
HIGH_FIVE_COUNT = 5
ROLL_LENGTH = 3


class Badge(BaseModel):
    id: str
    name: str
    description: str
    earned: bool


class BadgeList(BaseModel):
    earned_count: int
    total: int
    badges: list[Badge]


def load_submissions(user_id: int) -> list[dict]:
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT due_at, submitted_at
                FROM submissions
                WHERE user_id = :user_id
                ORDER BY submitted_at ASC, submission_id ASC
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def time_early(row: dict) -> timedelta | None:
    due = row["due_at"]
    submitted = row["submitted_at"]
    if not isinstance(due, datetime) or not isinstance(submitted, datetime):
        return None
    return due - submitted


def has_roll(rows: list[dict]) -> bool:
    streak = 0
    for row in rows:
        early = time_early(row)
        if early is not None and early >= timedelta(0):
            streak += 1
            if streak >= ROLL_LENGTH:
                return True
        else:
            streak = 0
    return False


def compute_badges(rows: list[dict]) -> list[dict]:
    gaps = [time_early(row) for row in rows]
    known = [gap for gap in gaps if gap is not None]
    return [
        {'id': 'first_submission', 'name': 'First Submission',
         'description': 'Record your first submission.',
         'earned': len(rows) >= 1},
        {'id': 'early_bird', 'name': 'Early Bird',
         'description': f'Turn something in {EARLY_BIRD_HOURS}+ hours early.',
         'earned': any(gap >= timedelta(hours=EARLY_BIRD_HOURS) for gap in known)},
        {'id': 'high_five', 'name': 'High Five',
         'description': f'Record {HIGH_FIVE_COUNT} submissions.',
         'earned': len(rows) >= HIGH_FIVE_COUNT},
        {'id': 'week_ahead', 'name': 'Week Ahead',
         'description': f'Turn something in {WEEK_AHEAD_DAYS}+ days early.',
         'earned': any(gap >= timedelta(days=WEEK_AHEAD_DAYS) for gap in known)},
        {'id': 'clutch', 'name': 'Clutch',
         'description': f'Turn something in during the last {CLUTCH_HOURS} hour before the deadline.',
         'earned': any(timedelta(0) <= gap <= timedelta(hours=CLUTCH_HOURS) for gap in known)},
        {'id': 'on_a_roll', 'name': 'On a Roll',
         'description': f'Turn in {ROLL_LENGTH} assignments in a row without being late.',
         'earned': has_roll(rows)},
    ]


@router.get('', response_model=BadgeList)
def my_badges(user: UserInfo = Depends(require_student)) -> BadgeList:
    try:
        rows = load_submissions(user.user_id)
    except (DatabaseNotConfigured, SQLAlchemyError) as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Database is not available',
        ) from err
    badges = compute_badges(rows)
    return BadgeList(
        earned_count=sum(1 for badge in badges if badge['earned']),
        total=len(badges),
        badges=[Badge(**badge) for badge in badges],
    )
