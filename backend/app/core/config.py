
import os
from pathlib import Path

from dotenv import load_dotenv

# Repository-level .env, not committed to Git.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', '')
