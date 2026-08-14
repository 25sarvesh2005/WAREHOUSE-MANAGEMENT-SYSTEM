"""Production Environment & Configuration Verification Tool.

Validates that environment variables, security keys, and safe placeholders
are configured properly before deploying or launching the platform.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import dotenv_values

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def check_env_example_placeholders() -> list[str]:
    """Verify that .env.example contains only safe placeholders and no real secrets."""
    errors = []
    example_path = WORKSPACE_ROOT / ".env.example"
    if not example_path.exists():
        return ["Missing .env.example file in workspace root."]

    content = example_path.read_text(encoding="utf-8")
    
    # Check for exposed live secrets
    if re.search(r"AIzaSy[A-Za-z0-9_-]{33}", content):
        errors.append(".env.example contains a live Google API key!")
    if re.search(r"eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}", content):
        errors.append(".env.example contains a live JWT token!")
    if "postgres:postgres@" in content and "localhost" not in content and "127.0.0.1" not in content:
        errors.append(".env.example should use [PASSWORD] placeholder instead of real credentials.")

    return errors


def verify_active_configuration(env_dict: dict[str, str | None]) -> list[str]:
    """Verify the completeness and security of the active environment configuration."""
    errors = []
    app_env = (env_dict.get("APP_ENV") or "development").lower()

    # 1. Database URL
    db_url = env_dict.get("DATABASE_URL") or ""
    if not db_url:
        errors.append("DATABASE_URL is not set.")
    elif "[PASSWORD]" in db_url or "[PROJECT_REF]" in db_url:
        if app_env == "production":
            errors.append("DATABASE_URL contains unpopulated placeholder values in production mode.")

    # 2. JWT Secret Strength
    jwt_secret = env_dict.get("JWT_SECRET") or ""
    if not jwt_secret:
        errors.append("JWT_SECRET is not set.")
    elif len(jwt_secret) < 32:
        errors.append(f"JWT_SECRET is too short ({len(jwt_secret)} chars). Must be >= 32 chars.")
    elif jwt_secret in {"replace-with-long-random-secret", "secret", "change-me", "your-secret-key"}:
        if app_env == "production":
            errors.append("JWT_SECRET is using an insecure default placeholder in production.")

    # 3. Bootstrap admin password
    admin_pw = env_dict.get("BOOTSTRAP_ADMIN_PASSWORD") or ""
    if app_env == "production" and admin_pw in {"change-this-before-use", "admin123", "WhitfieldAdmin123!"}:
        errors.append("BOOTSTRAP_ADMIN_PASSWORD is using a default password in production mode.")

    # 4. AI configuration
    ai_enabled = (env_dict.get("AI_ENABLED") or "").lower() in {"true", "1", "yes"}
    ai_provider = env_dict.get("AI_PROVIDER") or "disabled"
    if ai_enabled and ai_provider == "google_genai":
        api_key = env_dict.get("GOOGLE_GENAI_API_KEY") or env_dict.get("GOOGLE_API_KEY") or ""
        if not api_key:
            errors.append("AI is enabled with google_genai provider but GOOGLE_GENAI_API_KEY is missing.")

    return errors


def main() -> int:
    print("==================================================")
    print(" Whitfield Ops: Environment Verification Audit    ")
    print("==================================================")

    # 1. Check .env.example
    example_errors = check_env_example_placeholders()
    if example_errors:
        print("[FAIL] .env.example check failed:")
        for err in example_errors:
            print(f"  - {err}")
        return 1
    print("[PASS] .env.example contains safe placeholders only.")

    # 2. Check active .env or process environment
    env_file = WORKSPACE_ROOT / ".env"
    file_vals = dotenv_values(env_file) if env_file.exists() else {}
    combined_env = {**file_vals, **os.environ}

    config_errors = verify_active_configuration(combined_env)
    if config_errors:
        print("[FAIL] Active environment configuration issues detected:")
        for err in config_errors:
            print(f"  - {err}")
        return 1

    app_env = combined_env.get("APP_ENV", "development")
    print(f"[PASS] Environment configuration verified for APP_ENV={app_env}.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
