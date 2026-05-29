import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_fast_audit_completes_quickly():
    result = subprocess.run(
        [sys.executable, "scripts/audit_download_packages.py", "--mode", "fast"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "mode: fast-canary:" in result.stdout
    assert "templates checked: 1" in result.stdout
    assert "violations: 0" in result.stdout

    elapsed_line = next(line for line in result.stdout.splitlines() if line.startswith("elapsed_seconds:"))
    elapsed = float(elapsed_line.split(":", 1)[1].strip())
    assert elapsed < 15, f"fast audit took too long: {elapsed:.2f}s"


def test_parallel_audit_across_multiple_slugs():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_download_packages.py",
            "--slugs",
            "community-impact,greenfield-farm",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "mode: explicit:community-impact,greenfield-farm" in result.stdout
    assert "templates checked: 2" in result.stdout
    assert "violations: 0" in result.stdout

    elapsed_line = next(line for line in result.stdout.splitlines() if line.startswith("elapsed_seconds:"))
    elapsed = float(elapsed_line.split(":", 1)[1].strip())
    assert elapsed < 10, f"multi-slug audit took too long: {elapsed:.2f}s"
