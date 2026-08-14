"""
Frontend Secret Audit Tool.

Scans browser-delivered source and build artifacts for backend-only secret
markers before launch. The audit intentionally avoids backend files and
documentation so it can fail only on values that could reach the browser.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_PATHS = (
    REPOSITORY_ROOT / "frontend" / "src",
    REPOSITORY_ROOT / "frontend" / "public",
    REPOSITORY_ROOT / "frontend" / ".output" / "public",
    REPOSITORY_ROOT / "frontend" / ".output" / "server",
)
SKIPPED_DIRECTORIES = {"node_modules", ".git", ".nitro", ".wrangler"}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".mjs",
    ".ts",
    ".tsx",
    ".txt",
}
FORBIDDEN_MARKERS = (
    "service_role",
    "SUPABASE_SERVICE_ROLE",
    "sb_secret_",
    "JWT_SECRET",
    "DATABASE_URL",
    "MIGRATION_DATABASE_URL",
    "postgresql://",
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "GOOGLE_GENAI_API_KEY",
    "GOOGLE_API_KEY",
    "AI_KEY",
    "CLOUDINARY_API_SECRET",
    "BOOTSTRAP_ADMIN_PASSWORD",
    "WhitfieldAdmin123!",
)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the frontend secret audit.

    Returns:
        argparse.Namespace: Parsed CLI options.
    """
    parser = argparse.ArgumentParser(description="Audit frontend artifacts for backend secrets.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional frontend paths to scan. Defaults to src/public/build output.",
    )
    return parser.parse_args()


def iter_candidate_files(paths: Iterable[Path]) -> Iterable[Path]:
    """
    Yield text-like files under the requested frontend scan paths.

    Args:
        paths: File or directory paths to inspect.

    Yields:
        Path: Candidate text files for marker scanning.
    """
    for path in paths:
        resolved = path.resolve()
        if not resolved.exists():
            continue
        if resolved.is_file() and resolved.suffix in TEXT_SUFFIXES:
            yield resolved
            continue
        if not resolved.is_dir():
            continue
        for candidate in resolved.rglob("*"):
            if any(part in SKIPPED_DIRECTORIES for part in candidate.parts):
                continue
            if candidate.is_file() and candidate.suffix in TEXT_SUFFIXES:
                yield candidate


def find_forbidden_markers(paths: Iterable[Path]) -> list[tuple[Path, str]]:
    """
    Find forbidden backend-secret markers in frontend-readable files.

    Args:
        paths: File or directory paths to inspect.

    Returns:
        list[tuple[Path, str]]: Matching file path and marker pairs.
    """
    findings: list[tuple[Path, str]] = []
    for candidate in iter_candidate_files(paths):
        try:
            content = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in FORBIDDEN_MARKERS:
            if marker in content:
                findings.append((candidate, marker))
    return findings


def main() -> None:
    """
    Run the frontend secret audit and exit non-zero on findings.

    Raises:
        SystemExit: Exit code 1 when forbidden markers are discovered.
    """
    args = parse_args()
    scan_paths = tuple(path for path in args.paths) or DEFAULT_SCAN_PATHS
    findings = find_forbidden_markers(scan_paths)
    if findings:
        print("Frontend secret audit failed:")
        for path, marker in findings:
            relative_path = path.relative_to(REPOSITORY_ROOT)
            print(f"  {relative_path}: contains forbidden marker {marker!r}")
        raise SystemExit(1)
    print("Frontend secret audit passed: no backend-only secret markers found.")


if __name__ == "__main__":
    main()
