"""Diagnostic endpoint for extension-to-backend integration (no database writes)."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/integration", tags=["integration"])


class SubmissionMetadata(BaseModel):
    # Do not accept screenshots, passwords, user IDs or arbitrary extra fields.
    model_config = ConfigDict(extra="forbid")

    assignment_title: str = Field(min_length=1, max_length=255)
    course_name: str | None = Field(default=None, max_length=150)
    submission_type: Literal["assignment", "test", "exam"] = "assignment"
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
