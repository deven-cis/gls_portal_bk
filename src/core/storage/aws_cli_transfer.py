import tempfile
from pathlib import Path
from typing import Callable, Optional

from src.core.config import config
from src.core.storage.s3_transfer_common import find_binary, run_external_transfer


ENGINE_NAME = "awscli"


def get_binary() -> Optional[str]:
    return find_binary(config.AWS_CLI_BINARY or "aws")


def _build_temp_aws_cli_config() -> tempfile.NamedTemporaryFile:
    region = config.AWS_REGION or "us-east-1"
    aws_config = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=True)
    aws_config.write(
        "\n".join(
            [
                "[default]",
                f"region = {region}",
                "s3 =",
                f"    max_concurrent_requests = {config.AWS_CLI_S3_MAX_CONCURRENT_REQUESTS}",
                f"    multipart_chunksize = {config.AWS_CLI_S3_MULTIPART_CHUNKSIZE_MB}MB",
                f"    multipart_threshold = {config.AWS_CLI_S3_MULTIPART_THRESHOLD_MB}MB",
                f"    max_queue_size = {config.AWS_CLI_S3_MAX_QUEUE_SIZE}",
                "",
            ]
        )
    )
    aws_config.flush()
    return aws_config


def download_to_path(
    *,
    bucket_name: str,
    key: str,
    destination: Path,
    max_attempts: int,
    should_abort: Optional[Callable[[], bool]] = None,
    binary_path: Optional[str] = None,
) -> Path:
    resolved_binary = binary_path or get_binary()
    if not resolved_binary:
        raise FileNotFoundError("AWS CLI binary is not available")

    source_uri = f"s3://{bucket_name}/{key.lstrip('/')}"
    with _build_temp_aws_cli_config() as aws_config:
        run_external_transfer(
            command=[resolved_binary, "s3", "cp", source_uri, str(destination), "--only-show-errors"],
            engine=ENGINE_NAME,
            action="Downloading",
            source=source_uri,
            destination=str(destination),
            max_attempts=max_attempts,
            should_abort=should_abort,
            cleanup_path=destination,
            env_overrides={"AWS_CONFIG_FILE": aws_config.name},
        )
    return destination


def upload_path(
    *,
    bucket_name: str,
    source: Path,
    key: str,
    max_attempts: int,
    content_type: Optional[str] = None,
    binary_path: Optional[str] = None,
) -> None:
    resolved_binary = binary_path or get_binary()
    if not resolved_binary:
        raise FileNotFoundError("AWS CLI binary is not available")

    destination_uri = f"s3://{bucket_name}/{key.lstrip('/')}"
    command = [resolved_binary, "s3", "cp", str(source), destination_uri, "--only-show-errors"]
    if content_type:
        command.extend(["--content-type", content_type])
    with _build_temp_aws_cli_config() as aws_config:
        run_external_transfer(
            command=command,
            engine=ENGINE_NAME,
            action="Uploading",
            source=str(source),
            destination=destination_uri,
            max_attempts=max_attempts,
            env_overrides={"AWS_CONFIG_FILE": aws_config.name},
        )
