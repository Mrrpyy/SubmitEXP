"""Diagnostic endpoint for extension-to-backend integration (no database writes)."""

from datetime import datetime
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from point_calculator import calculate_assignment_points

router = APIRouter(prefix="/integration", tags=["integration"])

class SubmissionMetadata(BaseModel):
    # Do not accept screenshots, passwords, user IDs or arbitrary extra fields.
    model_config = ConfigDict(extra="forbid")

    assignment_title: str = Field(min_length=1, max_length=255)
    course_name: str | None = Field(default=None, max_length=150)
    submission_type: Literal["assignment", "quiz", "test", "exam"] = "assignment"
    due_at: datetime | None = None
    submitted_at: datetime | None = None

class ValidationResponse(BaseModel):
    accepted: bool
    submission_type: str
    message: str

@router.post("/validate", response_model=ValidationResponse)
def validate_metadata(body: SubmissionMetadata) -> ValidationResponse:
    """Confirm the extension can POST valid structured metadata.
    This is NOT an authenticated submission endpoint. It does not persist data
    or award points. Add those capabilities after login and point logic exist.
    """
    return ValidationResponse(
        accepted=True,
        submission_type=body.submission_type,
        message="Metadata validated (not saved; no points awarded).",
    )

class AssignmentPointsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_at: datetime
    submitted_at: datetime

class AssignmentPointsResponse(BaseModel):
    points: int
    message: str

@router.post(
    "/assignment-points-preview",
    response_model=AssignmentPointsResponse
)
def preview_assignment_points(
    body: AssignmentPointsRequest
) -> AssignmentPointsResponse:
    try:
        points = calculate_assignment_points(
            due_at=body.due_at,
            submitted_at=body.submitted_at
        )
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc
    return AssignmentPointsResponse(
        points=points,
        message="Preview only; no points awarded or saved."
    )
