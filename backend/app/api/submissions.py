#Authenticated assignment submission and EXP awards.
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.api.auth import UserInfo, get_current_user
from app.db.connection import DatabaseNotConfigured, get_engine
from point_calculator import calculate_assignment_points

router = APIRouter(prefix="/submissions", tags=["submissions"])

class AssignmentSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canvas_course_id: int = Field(gt=0)
    canvas_assignment_id: int = Field(gt=0)
    assignment_title: str = Field(min_length=1, max_length=255)
    course_name: str | None = Field(default=None, max_length=150)
    due_at: datetime
    submitted_at: datetime

class AssignmentSubmissionResponse(BaseModel):
    submission_id: int
    points_awarded: int
    total_points: int
    current_level: int

@router.post(
    "/assignment",
    response_model=AssignmentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def award_assignment(
    body: AssignmentSubmissionRequest,
    user: UserInfo = Depends(get_current_user),
) -> AssignmentSubmissionResponse:
    try:
        points = calculate_assignment_points(
            body.due_at,
            body.submitted_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    # Store all database DATETIME values in UTC.
    due_utc = body.due_at.astimezone(
        timezone.utc
    ).replace(tzinfo=None)
    submitted_utc = body.submitted_at.astimezone(
        timezone.utc
    ).replace(tzinfo=None)
    try:
        # All database writes succeed or fail together.
        with get_engine().begin() as connection:

            result = connection.execute(
                text("""
                    INSERT INTO submissions (user_id,assignment_title,course_name,
                        submission_type,due_at,submitted_at,canvas_course_id,canvas_assignment_id)
                    VALUES (:user_id,:assignment_title,:course_name,'assignment',:due_at,:submitted_at,
                        :canvas_course_id,:canvas_assignment_id)
                """),
                {
                    "user_id": user.user_id,
                    "assignment_title": body.assignment_title,
                    "course_name": body.course_name,
                    "due_at": due_utc,
                    "submitted_at": submitted_utc,
                    "canvas_course_id": body.canvas_course_id,
                    "canvas_assignment_id": body.canvas_assignment_id,
                },
            )
            submission_id = int(result.lastrowid)
            connection.execute(
                text("""
                    INSERT INTO point_transactions (
                        submission_id,
                        points_awarded,
                        reason
                    )
                    VALUES (
                        :submission_id,
                        :points,
                        :reason
                    )
                """),
                {
                    "submission_id": submission_id,
                    "points": points,
                    "reason": "Assignment submission timing",
                },
            )
            connection.execute(
                text("""
                    INSERT INTO user_progress (
                        user_id,
                        total_points
                    )
                    VALUES (
                        :user_id,
                        :points
                    )
                    ON DUPLICATE KEY UPDATE
                        total_points = total_points + :points
                """),
                {
                    "user_id": user.user_id,
                    "points": points,
                },
            )
            progress = connection.execute(
                text("""
                    SELECT total_points, current_level
                    FROM user_progress
                    WHERE user_id = :user_id
                """),
                {"user_id": user.user_id},
            ).mappings().one()

            total_points = int(progress["total_points"])
            current_level = int(progress["current_level"])
    except IntegrityError as exc:
        # MySQL error 1062: duplicate unique key.
        if getattr(exc.orig, "args", ())[:1] == (1062,):
            raise HTTPException(
                status_code=409,
                detail="Points already recorded for this assignment",
            ) from exc

        raise HTTPException(
            status_code=503,
            detail="Database write failed",
        ) from exc
    except (DatabaseNotConfigured, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is not available",
        ) from exc
    return AssignmentSubmissionResponse(
        submission_id=submission_id,
        points_awarded=points,
        total_points=total_points,
        current_level=current_level,
    )
