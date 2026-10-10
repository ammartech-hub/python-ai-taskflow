"""End-to-End Live Verification Script for TaskFlow AI.

Tests all requirements against the running server at http://127.0.0.1:8000.
"""

import sys
import os
import time
import json
import urllib.request
import urllib.error

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://127.0.0.1:8000"

# Output encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def request(method: str, path: str, data: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = content
            return status, parsed
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = content
        return e.code, parsed
    except Exception as e:
        return 0, str(e)


def run_checks():
    print("=" * 70)
    print("TASKFLOW AI - LIVE ENDPOINT VERIFICATION")
    print("=" * 70)

    all_passed = True

    # 1. Health check
    status, body = request("GET", "/health")
    print(f"\n[1] Health Check: Status {status}")
    print(f"    Body: {body}")
    if status != 200 or not body.get("database_connected"):
        print("    [FAIL] Database is not connected!")
        all_passed = False
    else:
        print("    [PASS] Database is connected and healthy.")

    # 2. Login verification for seeded accounts
    # Use environment configured seed passwords from config.py defaults
    from app.config import settings
    admin_pw = settings.SEED_ADMIN_PASSWORD
    user_pw = settings.SEED_USER_PASSWORD
    alex_pw = "AlexPass123!"

    print("\n[2] Testing Authentication for Seeded Accounts:")
    users_to_test = [
        ("admin@taskflow.dev", admin_pw, "admin"),
        ("user@taskflow.dev", user_pw, "user"),
        ("alex@taskflow.dev", alex_pw, "user"),
    ]

    tokens = {}
    for email, pw, expected_role in users_to_test:
        s, b = request("POST", "/api/auth/login", {"email": email, "password": pw})
        if s == 200 and "access_token" in b:
            role = b["user"]["role"]
            tokens[email] = b["access_token"]
            print(f"    [PASS] Login {email} -> Status {s}, Role: {role}")
            if role != expected_role:
                print(f"    [WARN] Expected role {expected_role}, got {role}")
        else:
            print(f"    [FAIL] Login {email} failed! Status: {s}, Response: {b}")
            all_passed = False

    # 3. Invalid credentials test
    s, b = request("POST", "/api/auth/login", {"email": "user@taskflow.dev", "password": "WrongPassword999!"})
    print(f"\n[3] Invalid Credentials Test: Status {s}")
    if s == 401:
        print("    [PASS] Returned HTTP 401 Unauthorized for invalid password.")
    else:
        print(f"    [FAIL] Expected 401, got {s}: {b}")
        all_passed = False

    # 4. Duplicate email registration test
    s, b = request("POST", "/api/auth/register", {
        "name": "Duplicate User",
        "email": "user@taskflow.dev",
        "password": "NewPassword123!",
    })
    print(f"\n[4] Duplicate Email Registration Test: Status {s}")
    if s == 409:
        print("    [PASS] Duplicate email returned HTTP 409 Conflict.")
    else:
        print(f"    [FAIL] Expected 409, got {s}: {b}")
        all_passed = False

    # 5. Public registration with attempt to escalate to admin
    test_email = f"newuser_test_{int(time.time())}@taskflow.dev"
    s, b = request("POST", "/api/auth/register", {
        "name": "Regular Register Test",
        "email": test_email,
        "password": "Password123!",
        "role": "admin",  # Attacker attempt
    })
    print(f"\n[5] Registration Privilege Escalation Protection: Status {s}")
    if s == 201:
        registered_role = b.get("role")
        if registered_role == "user":
            print("    [PASS] Public registration assigned 'user' role despite 'admin' input.")
        else:
            print(f"    [FAIL] Public registration assigned privileged role: {registered_role}!")
            all_passed = False
    else:
        print(f"    [FAIL] Registration failed: {s} {b}")
        all_passed = False

    user_token = tokens.get("user@taskflow.dev")
    alex_token = tokens.get("alex@taskflow.dev")
    admin_token = tokens.get("admin@taskflow.dev")

    # 6. Task Management: Regular user creates task
    created_task_id = None
    if user_token:
        s, b = request("POST", "/api/tasks/", {
            "title": "Live Verification Task by Jane",
            "description": "Created during automated backend check.",
        }, token=user_token)
        print(f"\n[6] Task Creation by Regular User: Status {s}")
        if s == 201:
            created_task_id = b["id"]
            print(f"    [PASS] Task created successfully. Task ID: {created_task_id}, Status: {b['status']}")
        else:
            print(f"    [FAIL] Task creation failed: {s} {b}")
            all_passed = False

    # 7. Task Management: Regular user cannot view another user's task
    if alex_token and created_task_id:
        s, b = request("GET", f"/api/tasks/{created_task_id}", token=alex_token)
        print(f"\n[7] Cross-User Task Access (Alex accessing Jane's task): Status {s}")
        if s == 404:
            print("    [PASS] Access blocked with HTTP 404 Not Found.")
        else:
            print(f"    [FAIL] Expected 404, got {s}: {b}")
            all_passed = False

    # 8. Regular user cannot update task status
    if user_token and created_task_id:
        # Test PUT /api/tasks/{id} with status
        s, b = request("PUT", f"/api/tasks/{created_task_id}", {
            "title": "Jane Updated Title",
            "status": "In Progress",
        }, token=user_token)
        print(f"\n[8a] Regular User Updating Task Status via PUT: Status {s}")
        if s == 403:
            print("    [PASS] Blocked with HTTP 403 Forbidden.")
        else:
            print(f"    [FAIL] Expected 403, got {s}: {b}")
            all_passed = False

        # Test PATCH /api/tasks/{id}/status as regular user
        s, b = request("PATCH", f"/api/tasks/{created_task_id}/status", {
            "status": "In Progress",
        }, token=user_token)
        print(f"[8b] Regular User Updating Task Status via PATCH: Status {s}")
        if s == 403:
            print("    [PASS] Blocked with HTTP 403 Forbidden.")
        else:
            print(f"    [FAIL] Expected 403, got {s}: {b}")
            all_passed = False

    # 9. Admin can view across users and update status
    if admin_token and created_task_id:
        s, b = request("GET", f"/api/tasks/{created_task_id}", token=admin_token)
        print(f"\n[9a] Admin Viewing User Task: Status {s}")
        if s == 200:
            print("    [PASS] Admin can view task across users.")
        else:
            print(f"    [FAIL] Expected 200, got {s}: {b}")
            all_passed = False

        s, b = request("PATCH", f"/api/tasks/{created_task_id}/status", {
            "status": "In Progress",
        }, token=admin_token)
        print(f"[9b] Admin Updating Task Status to 'In Progress': Status {s}")
        if s == 200 and b["status"] == "In Progress":
            print("    [PASS] Admin successfully transitioned status to 'In Progress'.")
        else:
            print(f"    [FAIL] Expected 200 and 'In Progress', got {s}: {b}")
            all_passed = False

        # Admin advance to Testing
        s, b = request("PATCH", f"/api/tasks/{created_task_id}/status", {
            "status": "Testing",
        }, token=admin_token)
        print(f"[9c] Admin Updating Task Status to 'Testing': Status {s}")
        if s == 200 and b["status"] == "Testing":
            print("    [PASS] Admin successfully transitioned status to 'Testing'.")
        else:
            print(f"    [FAIL] Expected 200 and 'Testing', got {s}: {b}")
            all_passed = False

        # Admin advance to Completed
        s, b = request("PATCH", f"/api/tasks/{created_task_id}/status", {
            "status": "Completed",
        }, token=admin_token)
        print(f"[9d] Admin Updating Task Status to 'Completed': Status {s}")
        if s == 200 and b["status"] == "Completed":
            print("    [PASS] Admin successfully transitioned status to 'Completed'.")
        else:
            print(f"    [FAIL] Expected 200 and 'Completed', got {s}: {b}")
            all_passed = False

    # 10. Gemini AI Endpoint Verification
    if user_token:
        s, b = request("POST", "/api/tasks/generate-description", {
            "title": "Design user onboarding journey",
        }, token=user_token)
        print(f"\n[10] Gemini AI Description Generation: Status {s}")
        if s == 200 and "description" in b and len(b["description"]) > 10:
            print(f"    [PASS] AI generated description: {b['description'][:80]}...")
        elif s in [502, 503, 429]:
            print(f"    [INFO] AI returned expected upstream error code {s}: {b.get('detail')}")
            # Ensure no credentials leaked
            detail_str = str(b)
            if "AIza" in detail_str or "secret" in detail_str.lower() or "key" in detail_str.lower():
                print("    [FAIL] Potential secret in error response!")
                all_passed = False
            else:
                print("    [PASS] AI error handled gracefully without secret leakage.")
        else:
            print(f"    [FAIL] Unexpected response: {s} {b}")
            all_passed = False

    # 11. Transaction Rollback & Connection Recovery Test
    # Intentionally trigger an error (e.g. invalid JSON, 404, or duplicate)
    s1, _ = request("POST", "/api/auth/register", {"name": "X", "email": "admin@taskflow.dev", "password": "abc"}, token=None)
    # Immediately follow up with a legitimate query to verify connection is clean and not aborted
    s2, b2 = request("GET", "/health")
    s3, b3 = request("POST", "/api/auth/login", {"email": "user@taskflow.dev", "password": user_pw})
    print(f"\n[11] Database Session Health & Rollback Test:")
    print(f"    Trigger error status: {s1}")
    print(f"    Subsequent health status: {s2}")
    print(f"    Subsequent login status: {s3}")
    if s2 == 200 and s3 == 200:
        print("    [PASS] Connection pool cleanly recovered; transactions are not aborted!")
    else:
        print("    [FAIL] Connection pool experienced aborted transaction after error!")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] ALL 11 LIVE SYSTEM CHECKS PASSED PERFECTLY!")
    else:
        print("[ERROR] SOME LIVE CHECKS FAILED.")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
