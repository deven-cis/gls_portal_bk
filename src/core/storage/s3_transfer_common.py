import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from src.core.config import config
from src.core.logger import logger


EXTERNAL_TRANSFER_ABORT_POLL_SECONDS = 2
EXTERNAL_TRANSFER_TERMINATE_TIMEOUT_SECONDS = 5
STALE_DOWNLOAD_ABORT_MESSAGE = "Download aborted because the merge request became stale"


def build_aws_env() -> dict[str, str]:
    env = os.environ.copy()
    if config.AWS_ACCESS_KEY_ID:
        env["AWS_ACCESS_KEY_ID"] = config.AWS_ACCESS_KEY_ID
    if config.AWS_SECRET_ACCESS_KEY:
        env["AWS_SECRET_ACCESS_KEY"] = config.AWS_SECRET_ACCESS_KEY
    if config.AWS_REGION:
        env["AWS_DEFAULT_REGION"] = config.AWS_REGION
        env["AWS_REGION"] = config.AWS_REGION
    return env


def find_binary(binary_name: str) -> Optional[str]:
    return shutil.which((binary_name or "").strip())


def is_retryable_transfer_error(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return any(
        marker in lowered
        for marker in (
            "timeout",
            "connection reset",
            "connection refused",
            "connection closed",
            "broken pipe",
            "eof",
            "tls",
            "ssl",
            "temporary failure",
            "i/o timeout",
            "deadline exceeded",
            "connection was closed",
        )
    )


def stop_process(process: subprocess.Popen, *, engine: str, reason: str) -> None:
    if process.poll() is not None:
        return
    logger.info("Stopping %s process: pid=%s reason=%s", engine, process.pid, reason)
    process.terminate()
    try:
        process.wait(timeout=EXTERNAL_TRANSFER_TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        logger.warning("Killing %s process after terminate timeout: pid=%s", engine, process.pid)
        process.kill()
        process.wait()


def run_external_transfer(
    *,
    command: list[str],
    engine: str,
    action: str,
    source: str,
    destination: str,
    max_attempts: int,
    should_abort: Optional[Callable[[], bool]] = None,
    cleanup_path: Optional[Path] = None,
    env_overrides: Optional[dict[str, str]] = None,
) -> None:
    for attempt in range(1, max_attempts + 1):
        if should_abort and should_abort():
            raise RuntimeError(STALE_DOWNLOAD_ABORT_MESSAGE)

        started_at = time.perf_counter()
        try:
            logger.info(
                "%s S3 object with %s: source=%s destination=%s attempt=%s/%s",
                action,
                engine,
                source,
                destination,
                attempt,
                max_attempts,
            )
            env = build_aws_env()
            if env_overrides:
                env.update(env_overrides)
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            while process.poll() is None:
                if should_abort and should_abort():
                    stop_process(
                        process,
                        engine=engine,
                        reason="merge request became stale during external S3 transfer",
                    )
                    if cleanup_path and cleanup_path.exists():
                        cleanup_path.unlink(missing_ok=True)
                    raise RuntimeError(STALE_DOWNLOAD_ABORT_MESSAGE)
                time.sleep(EXTERNAL_TRANSFER_ABORT_POLL_SECONDS)

            stdout, stderr = process.communicate()
            if process.returncode == 0:
                logger.info(
                    "%s S3 object successfully with %s: source=%s destination=%s attempt=%s/%s elapsed=%.2fs",
                    action,
                    engine,
                    source,
                    destination,
                    attempt,
                    max_attempts,
                    time.perf_counter() - started_at,
                )
                return

            error_summary = (stderr or stdout or "").strip().replace("\n", " ")
            error_summary = error_summary[:500] if error_summary else f"unknown {engine} error"
            if cleanup_path and cleanup_path.exists():
                cleanup_path.unlink(missing_ok=True)

            is_last_attempt = attempt >= max_attempts
            retryable = is_retryable_transfer_error(error_summary)
            if is_last_attempt or not retryable:
                raise RuntimeError(
                    f"{engine} exited with code {process.returncode}: {error_summary}"
                )

            backoff_seconds = min(attempt * 5, 30)
            logger.warning(
                "Retrying S3 %s with %s after transient error: source=%s destination=%s attempt=%s/%s backoff=%ss exit_code=%s error=%s",
                action.lower(),
                engine,
                source,
                destination,
                attempt,
                max_attempts,
                backoff_seconds,
                process.returncode,
                error_summary,
            )
            time.sleep(backoff_seconds)
        except RuntimeError:
            raise
        except Exception as exc:
            if cleanup_path and cleanup_path.exists():
                cleanup_path.unlink(missing_ok=True)
            raise RuntimeError(f"{engine} {action.lower()} failed unexpectedly: {exc}") from exc
