from fastapi import APIRouter
from app.api import admin, auth, history, integration, leaderboard, profile, student, submissions
# Register all API routers here.
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(integration.router)
api_router.include_router(submissions.router)
api_router.include_router(student.router)
api_router.include_router(admin.router)
api_router.include_router(profile.router)
api_router.include_router(leaderboard.router)
api_router.include_router(history.router)