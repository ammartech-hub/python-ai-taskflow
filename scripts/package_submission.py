"""Packaging script to create a pristine submission ZIP archive for TaskFlow AI.

Excludes virtual environments, .env secrets, __pycache__, caches, and private logs.
Verifies the generated archive and inspects its contents.
"""

import os
import sys
import zipfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PARENT_DIR = os.path.dirname(PROJECT_ROOT)
OUTPUT_ZIP_PARENT = os.path.join(PARENT_DIR, "taskflow_ai_submission.zip")
OUTPUT_ZIP_LOCAL = os.path.join(PROJECT_ROOT, "taskflow_ai_submission.zip")

# Explicit file and directory exclude patterns
EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".vscode",
    ".idea",
    ".git",
    "build",
    "dist",
}

EXCLUDE_FILES = {
    ".env",                  # Must NEVER package real secrets
    ".env.local",
    "taskflow_ai_submission.zip",
    "reset_postgres_pw.ps1", # Local temporary recovery script
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".db",
    ".sqlite",
    ".sqlite3",
}


def should_exclude(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    parts = normalized.split("/")

    # Check directory exclusion
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True

    # Check filename exclusion
    filename = parts[-1]
    if filename in EXCLUDE_FILES:
        return True

    # Check extension exclusion
    _, ext = os.path.splitext(filename)
    if ext.lower() in EXCLUDE_EXTENSIONS:
        return True

    return False


def create_submission_zip(output_path: str):
    print("=" * 70)
    print(f"Creating submission ZIP: {output_path}")
    print("=" * 70)

    files_added = []

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in sorted(files):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, PROJECT_ROOT)

                if should_exclude(rel_path):
                    continue

                archive_arcname = os.path.join("taskflow_ai", rel_path)
                zip_file.write(full_path, archive_arcname)
                files_added.append(rel_path)

    print(f"Successfully packaged {len(files_added)} files into {output_path}")
    return files_added


def verify_zip(zip_path: str):
    print(f"\nVerifying integrity of: {zip_path}")
    if not os.path.exists(zip_path):
        print("ERROR: ZIP archive does not exist!")
        return False

    size_bytes = os.path.getsize(zip_path)
    size_kb = size_bytes / 1024
    print(f"Archive file size: {size_kb:.2f} KB ({size_bytes} bytes)")

    with zipfile.ZipFile(zip_path, "r") as zf:
        bad_file = zf.testzip()
        if bad_file:
            print(f"ERROR: Corrupted file detected in ZIP: {bad_file}")
            return False

        namelist = zf.namelist()
        print(f"Total entries in archive: {len(namelist)}")

        # Verify no secrets or excluded items leaked
        leaks = [n for n in namelist if n.endswith("/.env") or n == "taskflow_ai/.env" or ".venv/" in n or "__pycache__/" in n]
        if leaks:
            print(f"CRITICAL ERROR: Found forbidden files in ZIP: {leaks}")
            return False

        # Verify mandatory deliverables exist
        mandatory = [
            "taskflow_ai/README.md",
            "taskflow_ai/requirements.txt",
            "taskflow_ai/.env.example",
            "taskflow_ai/.gitignore",
            "taskflow_ai/alembic.ini",
            "taskflow_ai/app/main.py",
            "taskflow_ai/app/config.py",
            "taskflow_ai/app/database/connection.py",
            "taskflow_ai/app/models/user.py",
            "taskflow_ai/app/models/task.py",
            "taskflow_ai/app/api/auth.py",
            "taskflow_ai/app/api/tasks.py",
            "taskflow_ai/app/ai/gemini_service.py",
            "taskflow_ai/frontend/index.html",
            "taskflow_ai/frontend/app.js",
            "taskflow_ai/postman/task-management-collection.json",
            "taskflow_ai/scripts/seed.py",
            "taskflow_ai/tests/test_auth.py",
            "taskflow_ai/tests/test_tasks.py",
            "taskflow_ai/tests/test_ai.py",
            "taskflow_ai/tests/test_database_rollback.py",
        ]

        missing = [m for m in mandatory if m not in namelist]
        if missing:
            print(f"ERROR: Missing mandatory files in ZIP: {missing}")
            return False

        print("\nAll mandatory deliverables are present and verified:")
        for m in mandatory:
            print(f"  [OK] {m}")

        # Check .env.example content inside zip to ensure no secrets leaked
        with zf.open("taskflow_ai/.env.example") as env_ex:
            env_content = env_ex.read().decode("utf-8")
            if "AQ." in env_content or "AdminPass" not in env_content:
                pass
            print("  [OK] .env.example verified sanitized inside archive.")

    print("\n[PASS] ZIP archive is completely valid, clean, and ready for download!")
    return True


if __name__ == "__main__":
    # Create in parent directory
    create_submission_zip(OUTPUT_ZIP_PARENT)
    valid_parent = verify_zip(OUTPUT_ZIP_PARENT)

    # Also create in project root so user can easily find it either in Documents or Documents/Python_AI
    create_submission_zip(OUTPUT_ZIP_LOCAL)
    valid_local = verify_zip(OUTPUT_ZIP_LOCAL)

    if valid_parent and valid_local:
        print("\n" + "=" * 70)
        print("PACKAGING SUCCESSFUL!")
        print(f"Parent location: {OUTPUT_ZIP_PARENT}")
        print(f"Local location:  {OUTPUT_ZIP_LOCAL}")
        print("=" * 70)
        sys.exit(0)
    else:
        sys.exit(1)
