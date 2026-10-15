from fastapi import APIRouter

from app.api import auth

# collects every route file, main only plugs this in once
# to add new routes make a file in this folder and add one include line below
api_router = APIRouter()
api_router.include_router(auth.router)  # registration, item 2