"""Diagnostic script to verify .env configuration and PostgreSQL connectivity.

Non-destructive: does not modify schema, tables, or records.
Security safe: strictly masks all passwords, API keys, and sensitive tokens.
"""

import sys
import os
import re

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def mask_url(url: str) -> str:
    """Mask credentials inside a database URL string."""
    if not url:
        return "<EMPTY>"
    # Pattern: dialect://user:password@host:port/dbname
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:********@", url)


def mask_secret(secret: str, show_chars: int = 4) -> str:
    """Mask a secret string preserving only prefix and suffix hints."""
    if not secret:
        return "<NOT_SET>"
    if len(secret) <= show_chars * 2:
        return "********"
    return f"{secret[:show_chars]}...{secret[-show_chars:]}"


def run_diagnostics():
    print("=" * 65)
    print("AI-Powered Task Management System - Environment & DB Diagnostics")
    print("=" * 65)

    # 1. Verify .env loading
    try:
        from app.config import settings
        print("[OK] Settings module loaded successfully from app.config")
    except Exception as exc:
        print(f"[ERROR] Failed to load application settings: {exc}")
        return False

    print("\n--- Environment Configuration Summary ---")
    print(f"App Name:             {settings.APP_NAME}")
    print(f"Environment:          {settings.ENVIRONMENT}")
    print(f"Debug Mode:           {settings.DEBUG}")
    print(f"Database Target:      {mask_url(settings.DATABASE_URL)}")
    print(f"JWT Secret:           {mask_secret(settings.JWT_SECRET_KEY, 3)} (Algorithm: {settings.JWT_ALGORITHM})")
    print(f"Access Token Expiry:  {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print(f"Gemini Model:         {settings.GEMINI_MODEL}")
    print(f"Gemini API Key:       {'Configured (' + mask_secret(settings.GEMINI_API_KEY, 3) + ')' if settings.is_ai_configured else 'Not Configured'}")

    # 2. Test PostgreSQL Connection with SQLAlchemy
    print("\n--- Testing Database Connectivity ---")
    from sqlalchemy import create_engine, text

    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    try:
        engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
        with engine.connect() as conn:
            # Simple non-destructive query
            result = conn.execute(text("SELECT 1")).scalar()
            
            # Retrieve database version if supported
            db_version = "Unknown"
            try:
                ver_res = conn.execute(text("SELECT version()")).scalar()
                if ver_res:
                    db_version = ver_res.split("\n")[0]
            except Exception:
                pass

            # Retrieve current database name
            current_db = "Unknown"
            try:
                db_name_res = conn.execute(text("SELECT current_database()")).scalar()
                if db_name_res:
                    current_db = db_name_res
            except Exception:
                pass

        print(f"[OK] Database connection successful! (Ping result: {result})")
        print(f"Connected Database:   {current_db}")
        print(f"Server Engine Info:   {db_version}")
        print("[OK] No schema or table modifications were made.")
        print("=" * 65)
        return True

    except Exception as exc:
        error_msg = str(exc)
        # Sanitize error message to ensure password is not leaked in raw psycopg traces
        if hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL:
            # Extract plain password if present and mask it
            match = re.search(r"://([^:]+):([^@]+)@", settings.DATABASE_URL)
            if match:
                raw_pwd = match.group(2)
                error_msg = error_msg.replace(raw_pwd, "********")

        print("[FAIL] Database connection failed.")
        print(f"Error Details: {error_msg}")
        print("=" * 65)
        return False


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
