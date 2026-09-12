# Single configuration module for the SMS backend.
#
# This file is git-ignored because it holds your local DB password.
# Copy config.example.py to config.py and fill in your values:
#   cp backend/config.example.py backend/config.py

# --- HTTP server ---
HOST = "127.0.0.1"
PORT = 8000

# --- MySQL connection ---
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "sms_app"          # dedicated least-privilege user created by scripts/setup_db.py
DB_PASSWORD = "CHANGE_ME"    # <-- set the password you chose for sms_app during setup
DB_NAME = "sms"

# --- Paths (relative to project root) ---
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "frontend", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")
CPP_ENGINE_PATH = os.path.join(BASE_DIR, "cpp_module", "build", "sms_engine.exe")
