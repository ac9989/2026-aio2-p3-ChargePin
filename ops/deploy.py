"""Deploy pinned ChargePin images to EC2 with health-gated rollback."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.prod.yml"
STATE_DIR = ROOT / "ops" / "deploy-state"
STABLE_SHA = STATE_DIR / "last_successful_sha"


def compose(sha: str, *args: str) -> None:
    env = os.environ.copy()
    env["CHARGEPIN_DEPLOY_SHA"] = sha

    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), *args],
        cwd=ROOT,
        env=env,
        check=True,
    )


def validate(sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("A full 40-character commit SHA is required.")

    if not COMPOSE.is_file():
        raise FileNotFoundError(COMPOSE)

    if not (ROOT / ".env").is_file():
        raise FileNotFoundError("Production .env is required.")

    compose(sha, "config", "--quiet")


def start(sha: str) -> None:
    compose(sha, "pull", "backend", "frontend")
    compose(
        sha,
        "up", "-d",
        "--no-build",
        "--no-deps",
        "backend", "frontend",
        "--wait",
        "--wait-timeout", "180",
    )


def deploy(sha: str) -> int:
    if os.name != "posix":
        print("Actual deployment is supported on Linux only.")
        return 1

    import fcntl

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with (STATE_DIR / "deploy.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)

        previous = (
            STABLE_SHA.read_text(encoding="utf-8").strip()
            if STABLE_SHA.exists()
            else ""
        )

        if previous and not re.fullmatch(r"[0-9a-f]{40}", previous):
            raise ValueError("Invalid saved deployment SHA.")

        print(f"[DEPLOY] Target: {sha}")

        try:
            compose(sha, "pull", "backend", "frontend")
        except subprocess.CalledProcessError:
            print("[FAILED] Image pull failed. Existing service unchanged.")
            return 1

        try:
            compose(
                sha,
                "up", "-d",
                "--no-build",
                "--no-deps",
                "backend", "frontend",
                "--wait",
                "--wait-timeout", "180",
            )
        except subprocess.CalledProcessError:
            print("[FAILED] Deployment health check failed.")

            if previous and previous != sha:
                print(f"[ROLLBACK] Restoring {previous}")

                try:
                    start(previous)
                    print("[ROLLBACK] Previous version restored.")
                except subprocess.CalledProcessError:
                    print("[CRITICAL] Automatic rollback also failed.")
                    print("[CRITICAL] Manual recovery required.")
            else:
                print("[WARNING] No earlier successful version to restore.")

            return 1

        temporary = STABLE_SHA.with_suffix(".tmp")
        temporary.write_text(sha + "\n", encoding="utf-8")
        temporary.replace(STABLE_SHA)

        print(f"[SUCCESS] Healthy deployment: {sha}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sha", help="Full commit SHA to deploy")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate configuration without deploying",
    )
    args = parser.parse_args()

    validate(args.sha)

    if args.preflight:
        print("[PASS] Deployment configuration validated.")
        return 0

    return deploy(args.sha)


if __name__ == "__main__":
    raise SystemExit(main())
