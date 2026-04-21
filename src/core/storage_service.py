import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Optional

from src.core import aws_cli_transfer
from src.core.config import config
from src.core.logger import logger
from src.core.storage.s3_transfer_common import STALE_DOWNLOAD_ABORT_MESSAGE


UPLOAD_BASE_DIR = Path("uploads")
S3_TRANSFER_RETRY_ATTEMPTS = 3
S3_DOWNLOAD_RETRY_ATTEMPTS = 3
S3_STREAM_READ_CHUNK_SIZE = 64 * 1024 * 1024
S3_PROGRESS_LOG_INTERVAL_SECONDS = 10
S3_MAX_POOL_CONNECTIONS = 10
S3_UPLOAD_MAX_CONCURRENCY = 4
S3_UPLOAD_READ_TIMEOUT_SECONDS = 900
S3_UPLOAD_CONNECT_TIMEOUT_SECONDS = 60
S3_UPLOAD_MULTIPART_CHUNK_SIZE = 100 * 1024 * 1024
EXTERNAL_TRANSFER_ENGINES = {"awscli"}


@dataclass(frozen=True)
class StoredFile:
    storage_backend: str
    key: str
    file_name: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None


class StorageService:
    """
    Shared storage adapter for local files now and S3 later.

    Keep feature modules calling this service instead of adding S3 logic in each
    module. That lets witness videos, merged videos, billing/equipment files,
    attorney files, and profile pictures share one storage strategy.
    """

    def __init__(self) -> None:
        self._external_engine_health_logged: set[str] = set()

    @property
    def backend(self) -> str:
        return (config.STORAGE_BACKEND or "local").strip().lower()

    @property
    def is_s3(self) -> bool:
        return self.backend == "s3"

    @property
    def s3_download_engine(self) -> str:
        engine = (config.S3_DOWNLOAD_ENGINE or "boto3").strip().lower()
        return engine if engine in {"boto3", *EXTERNAL_TRANSFER_ENGINES} else "boto3"

    @property
    def s3_upload_engine(self) -> str:
        engine = (config.S3_UPLOAD_ENGINE or "boto3").strip().lower()
        return engine if engine in {"boto3", *EXTERNAL_TRANSFER_ENGINES} else "boto3"

    def _get_s3_client(
        self,
        *,
        connect_timeout: int = 120,
        read_timeout: int = 900,
    ):
        if not config.AWS_S3_BUCKET_NAME:
            raise RuntimeError("AWS_S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")

        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:
            raise RuntimeError("boto3 is required when STORAGE_BACKEND=s3. Install backend requirements.") from exc

        client_kwargs = {
            "config": BotoConfig(
                signature_version="s3v4",
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                max_pool_connections=S3_MAX_POOL_CONNECTIONS,
                retries={"max_attempts": 3, "mode": "adaptive"},
                tcp_keepalive=True
            )
        }
        if config.AWS_REGION:
            client_kwargs["region_name"] = config.AWS_REGION
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY

        return boto3.client("s3", **client_kwargs)

    def _get_s3_upload_client(self):
        return self._get_s3_client(
            connect_timeout=S3_UPLOAD_CONNECT_TIMEOUT_SECONDS,
            read_timeout=S3_UPLOAD_READ_TIMEOUT_SECONDS,
        )

    def _get_s3_transfer_config(self):
        try:
            from boto3.s3.transfer import TransferConfig
        except ImportError as exc:
            raise RuntimeError("boto3 is required when STORAGE_BACKEND=s3. Install backend requirements.") from exc

        return TransferConfig(
            multipart_threshold=50 * 1024 * 1024,
            multipart_chunksize=S3_UPLOAD_MULTIPART_CHUNK_SIZE,
            max_concurrency=S3_UPLOAD_MAX_CONCURRENCY,
            use_threads=True,
            max_io_queue=100,
        )

    def _is_retryable_s3_error(self, exc: Exception) -> bool:
        
        error_text = str(exc).lower()
        return any(
            marker in error_text
            for marker in (
                "ssl",
                "unexpected eof",
                "read timeout",
                "connection",
                "endpointconnectionerror",
                "connectionclosederror",
            )
        )

    def _get_external_transfer_binary(self, engine: str) -> Optional[str]:
        if engine == "awscli":
            return aws_cli_transfer.get_binary()
        return None

    def _log_external_transfer_health(self, engine: str) -> Optional[str]:
        binary_path = self._get_external_transfer_binary(engine)
        if engine not in EXTERNAL_TRANSFER_ENGINES:
            return binary_path
        if engine in self._external_engine_health_logged:
            return binary_path
        if binary_path:
            logger.info(
                "S3 transfer engine configured for %s and binary is available: binary=%s",
                engine,
                binary_path,
            )
        else:
            logger.warning(
                "S3 transfer engine configured for %s but binary was not found in PATH; boto3 fallback will be used",
                engine,
            )
        self._external_engine_health_logged.add(engine)
        return binary_path

    def _upload_path_with_boto3(
        self,
        source: Path,
        key: str,
        *,
        content_type: Optional[str] = None,
    ) -> None:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        transfer_config = self._get_s3_transfer_config()
        for attempt in range(1, S3_TRANSFER_RETRY_ATTEMPTS + 1):
            try:
                logger.info(
                    "Uploading local file to S3 with boto3: bucket=%s key=%s source=%s attempt=%s/%s",
                    config.AWS_S3_BUCKET_NAME,
                    key,
                    source,
                    attempt,
                    S3_TRANSFER_RETRY_ATTEMPTS,
                )
                upload_kwargs = {
                    "Filename": str(source),
                    "Bucket": config.AWS_S3_BUCKET_NAME,
                    "Key": key,
                    "Config": transfer_config,
                }
                if extra_args:
                    upload_kwargs["ExtraArgs"] = extra_args
                self._get_s3_upload_client().upload_file(**upload_kwargs)
                logger.info(
                    "Uploaded local file to S3 successfully with boto3: bucket=%s key=%s source=%s attempt=%s/%s",
                    config.AWS_S3_BUCKET_NAME,
                    key,
                    source,
                    attempt,
                    S3_TRANSFER_RETRY_ATTEMPTS,
                )
                return
            except Exception as exc:
                if attempt >= S3_TRANSFER_RETRY_ATTEMPTS:
                    logger.error(
                        "Failed to upload local file to S3 with boto3: bucket=%s key=%s source=%s attempt=%s/%s",
                        config.AWS_S3_BUCKET_NAME,
                        key,
                        source,
                        attempt,
                        S3_TRANSFER_RETRY_ATTEMPTS,
                        exc_info=True,
                    )
                    raise
                backoff_seconds = min(attempt * 5, 30)
                logger.warning(
                    "Retrying S3 upload with boto3 after transient error: bucket=%s key=%s source=%s attempt=%s/%s backoff=%ss error=%s",
                    config.AWS_S3_BUCKET_NAME,
                    key,
                    source,
                    attempt,
                    S3_TRANSFER_RETRY_ATTEMPTS,
                    backoff_seconds,
                    exc,
                )
                time.sleep(backoff_seconds)

    def _upload_path_with_external_engine(
        self,
        engine: str,
        source: Path,
        key: str,
        *,
        content_type: Optional[str] = None,
    ) -> None:
        binary_path = self._log_external_transfer_health(engine)
        if not binary_path:
            raise FileNotFoundError(f"{engine} binary is not available")

        upload_kwargs = {
            "bucket_name": config.AWS_S3_BUCKET_NAME,
            "source": source,
            "key": key,
            "max_attempts": S3_TRANSFER_RETRY_ATTEMPTS,
            "content_type": content_type,
            "binary_path": binary_path,
        }
        if engine == "awscli":
            aws_cli_transfer.upload_path(**upload_kwargs)
            return
        raise ValueError(f"Unsupported S3 upload engine: {engine}")

    def _download_to_path_with_boto3(
        self,
        key: str,
        destination: Path,
        *,
        should_abort: Optional[Callable[[], bool]] = None,
    ) -> Path:
        
        for attempt in range(1, S3_DOWNLOAD_RETRY_ATTEMPTS + 1):
            response = None
            try:
                if should_abort and should_abort():
                    raise RuntimeError(STALE_DOWNLOAD_ABORT_MESSAGE)
                logger.info(
                    "Downloading S3 object to local path with boto3: bucket=%s key=%s destination=%s attempt=%s/%s",
                    config.AWS_S3_BUCKET_NAME,
                    key,
                    destination,
                    attempt,
                    S3_DOWNLOAD_RETRY_ATTEMPTS,
                )
                response = self._get_s3_client().get_object(
                    Bucket=config.AWS_S3_BUCKET_NAME,
                    Key=key,
                )
                body = response["Body"]
                content_length = int(response.get("ContentLength") or 0)
                bytes_downloaded = 0
                last_progress_log_at = time.perf_counter()
                with open(destination, "wb") as output_file:
                    while True:
                        if should_abort and should_abort():
                            raise RuntimeError(STALE_DOWNLOAD_ABORT_MESSAGE)
                        chunk = body.read(S3_STREAM_READ_CHUNK_SIZE)
                        if not chunk:
                            break
                        output_file.write(chunk)
                        bytes_downloaded += len(chunk)

                        now = time.perf_counter()
                        if now - last_progress_log_at >= S3_PROGRESS_LOG_INTERVAL_SECONDS:
                            if content_length > 0:
                                percent = (bytes_downloaded / content_length) * 100
                                logger.info(
                                    "S3 download progress with boto3: bucket=%s key=%s destination=%s attempt=%s/%s downloaded=%s/%s bytes (%.1f%%)",
                                    config.AWS_S3_BUCKET_NAME,
                                    key,
                                    destination,
                                    attempt,
                                    S3_DOWNLOAD_RETRY_ATTEMPTS,
                                    bytes_downloaded,
                                    content_length,
                                    percent,
                                )
                            else:
                                logger.info(
                                    "S3 download progress with boto3: bucket=%s key=%s destination=%s attempt=%s/%s downloaded=%s bytes",
                                    config.AWS_S3_BUCKET_NAME,
                                    key,
                                    destination,
                                    attempt,
                                    S3_DOWNLOAD_RETRY_ATTEMPTS,
                                    bytes_downloaded,
                                )
                            last_progress_log_at = now
                logger.info(
                    "Downloaded S3 object successfully with boto3: bucket=%s key=%s destination=%s attempt=%s/%s bytes=%s",
                    config.AWS_S3_BUCKET_NAME,
                    key,
                    destination,
                    attempt,
                    S3_DOWNLOAD_RETRY_ATTEMPTS,
                    bytes_downloaded,
                )
                return destination
            except Exception as exc:
                if destination.exists():
                    destination.unlink(missing_ok=True)
                if response and response.get("Body") is not None:
                    try:
                        response["Body"].close()
                    except Exception:
                        pass

                if STALE_DOWNLOAD_ABORT_MESSAGE in str(exc):
                    logger.info(
                        "Stopped S3 download with boto3 because merge request became stale: bucket=%s key=%s destination=%s attempt=%s/%s",
                        config.AWS_S3_BUCKET_NAME,
                        key,
                        destination,
                        attempt,
                        S3_DOWNLOAD_RETRY_ATTEMPTS,
                    )
                    raise

                is_last_attempt = attempt >= S3_DOWNLOAD_RETRY_ATTEMPTS
                retryable = self._is_retryable_s3_error(exc)
                if is_last_attempt or not retryable:
                    logger.error(
                        "Failed to download S3 object with boto3: bucket=%s key=%s destination=%s attempt=%s/%s",
                        config.AWS_S3_BUCKET_NAME,
                        key,
                        destination,
                        attempt,
                        S3_DOWNLOAD_RETRY_ATTEMPTS,
                        exc_info=True,
                    )
                    raise

                backoff_seconds = attempt * 2
                logger.warning(
                    "Retrying S3 download with boto3 after transient error: bucket=%s key=%s attempt=%s/%s backoff=%ss error=%s",
                    config.AWS_S3_BUCKET_NAME,
                    key,
                    attempt,
                    S3_DOWNLOAD_RETRY_ATTEMPTS,
                    backoff_seconds,
                    exc,
                )
                time.sleep(backoff_seconds)
            finally:
                if response and response.get("Body") is not None:
                    try:
                        response["Body"].close()
                    except Exception:
                        pass

        return destination

    def _download_to_path_with_external_engine(
        self,
        engine: str,
        key: str,
        destination: Path,
        *,
        should_abort: Optional[Callable[[], bool]] = None,
    ) -> Path:
        binary_path = self._log_external_transfer_health(engine)
        if not binary_path:
            raise FileNotFoundError(f"{engine} binary is not available")

        download_kwargs = {
            "bucket_name": config.AWS_S3_BUCKET_NAME,
            "key": key,
            "destination": destination,
            "max_attempts": S3_DOWNLOAD_RETRY_ATTEMPTS,
            "should_abort": should_abort,
            "binary_path": binary_path,
        }
        if engine == "awscli":
            return aws_cli_transfer.download_to_path(**download_kwargs)
        raise ValueError(f"Unsupported S3 download engine: {engine}")

    def build_key(self, subfolder: str, original_file_name: str) -> tuple[str, str]:
        file_ext = Path(original_file_name).suffix
        stored_file_name = f"{uuid.uuid4()}{file_ext}"
        key = f"{subfolder.strip('/')}/{stored_file_name}"
        return stored_file_name, key

    def _local_subfolder(self, subfolder: str) -> str:
        """
        Keep local storage backward-friendly while S3 can use richer prefixes.

        Example:
        - S3:   attorneys/rsrc_no=12/job_no=134445/attorney_id=55/a.pdf
        - Local uploads folder stays: uploads/attorneys/a.pdf
        """
        return subfolder.strip("/").split("/", 1)[0]

    def upload_path(
        self,
        source_path: str | Path,
        *,
        subfolder: str,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> StoredFile:
        source = Path(source_path)
        stored_file_name, key = self.build_key(subfolder, file_name or source.name)

        if self.is_s3:
            upload_engine = self.s3_upload_engine
            logger.info(
                "Selected S3 upload engine: engine=%s bucket=%s key=%s source=%s",
                upload_engine,
                config.AWS_S3_BUCKET_NAME,
                key,
                source,
            )
            if upload_engine in EXTERNAL_TRANSFER_ENGINES:
                try:
                    self._upload_path_with_external_engine(
                        upload_engine,
                        source,
                        key,
                        content_type=content_type,
                    )
                except Exception as exc:
                    logger.warning(
                        "Falling back to boto3 upload after external engine failure: engine=%s bucket=%s key=%s source=%s error=%s",
                        upload_engine,
                        config.AWS_S3_BUCKET_NAME,
                        key,
                        source,
                        exc,
                    )
                    self._upload_path_with_boto3(source, key, content_type=content_type)
            else:
                self._upload_path_with_boto3(source, key, content_type=content_type)

            return StoredFile(
                storage_backend="s3",
                key=key,
                file_name=stored_file_name,
                content_type=content_type,
                file_size=source.stat().st_size if source.exists() else None,
            )

        upload_dir = UPLOAD_BASE_DIR / self._local_subfolder(subfolder)
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_file_name
        shutil.move(str(source), str(destination))
        return StoredFile(
            storage_backend="local",
            key=str(destination),
            file_name=stored_file_name,
            content_type=content_type,
            file_size=destination.stat().st_size if destination.exists() else None,
        )

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        *,
        subfolder: str,
        file_name: str,
        content_type: Optional[str] = None,
    ) -> StoredFile:
        stored_file_name, key = self.build_key(subfolder, file_name)

        if self.is_s3:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            upload_kwargs = {
                "Fileobj": fileobj,
                "Bucket": config.AWS_S3_BUCKET_NAME,
                "Key": key,
                "Config": self._get_s3_transfer_config(),
            }
            if extra_args:
                upload_kwargs["ExtraArgs"] = extra_args
            self._get_s3_upload_client().upload_fileobj(**upload_kwargs)
            return StoredFile(
                storage_backend="s3",
                key=key,
                file_name=stored_file_name,
                content_type=content_type,
            )

        upload_dir = UPLOAD_BASE_DIR / self._local_subfolder(subfolder)
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_file_name
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(fileobj, buffer)
        return StoredFile(
            storage_backend="local",
            key=str(destination),
            file_name=stored_file_name,
            content_type=content_type,
            file_size=destination.stat().st_size if destination.exists() else None,
        )

    def delete(self, key: str | None) -> bool:
        if not key:
            return False

        if self.is_s3:
            self._get_s3_client().delete_object(Bucket=config.AWS_S3_BUCKET_NAME, Key=key)
            return True

        path = Path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def copy(
        self,
        source_key: str,
        *,
        subfolder: str,
        file_name: str,
        content_type: Optional[str] = None,
        delete_source: bool = False,
    ) -> StoredFile:
        stored_file_name, destination_key = self.build_key(subfolder, file_name)

        if self.is_s3:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
                extra_args["MetadataDirective"] = "REPLACE"
            self._get_s3_client().copy_object(
                Bucket=config.AWS_S3_BUCKET_NAME,
                CopySource={"Bucket": config.AWS_S3_BUCKET_NAME, "Key": source_key},
                Key=destination_key,
                **extra_args,
            )
            if delete_source:
                self.delete(source_key)
            return StoredFile(
                storage_backend="s3",
                key=destination_key,
                file_name=stored_file_name,
                content_type=content_type,
            )

        source = Path(source_key)
        upload_dir = UPLOAD_BASE_DIR / self._local_subfolder(subfolder)
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_file_name
        shutil.copy2(str(source), str(destination))
        if delete_source:
            source.unlink(missing_ok=True)
        return StoredFile(
            storage_backend="local",
            key=str(destination),
            file_name=stored_file_name,
            content_type=content_type,
            file_size=destination.stat().st_size if destination.exists() else None,
        )

    def exists(self, key: str | None) -> bool:
        if not key:
            return False

        if self.is_s3:
            try:
                self._get_s3_client().head_object(Bucket=config.AWS_S3_BUCKET_NAME, Key=key)
                return True
            except Exception:
                return False

        return Path(key).exists()

    def generate_download_url(
        self,
        key: str,
        *,
        file_name: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> str:
        if self.is_s3:
            params = {"Bucket": config.AWS_S3_BUCKET_NAME, "Key": key}
            if file_name:
                params["ResponseContentDisposition"] = f'attachment; filename="{file_name}"'

            return self._get_s3_client().generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in or config.AWS_S3_PRESIGNED_URL_EXPIRE_SECONDS,
            )

        public_base = (config.PUBLIC_API_BASE_URL or "").rstrip("/")
        return f"{public_base}/{str(key).lstrip('/')}"

    def download_to_path(
        self,
        key: str,
        destination_path: str | Path,
        *,
        should_abort: Optional[Callable[[], bool]] = None,
    ) -> Path:
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if self.is_s3:
            selected_engine = self.s3_download_engine
            logger.info(
                "Selected S3 download engine: engine=%s bucket=%s key=%s destination=%s",
                selected_engine,
                config.AWS_S3_BUCKET_NAME,
                key,
                destination,
            )
            if selected_engine in EXTERNAL_TRANSFER_ENGINES:
                try:
                    return self._download_to_path_with_external_engine(
                        selected_engine,
                        key,
                        destination,
                        should_abort=should_abort,
                    )
                except Exception as exc:
                    if STALE_DOWNLOAD_ABORT_MESSAGE in str(exc):
                        logger.info(
                            "Stopped S3 download because merge request became stale before boto3 fallback: bucket=%s key=%s destination=%s",
                            config.AWS_S3_BUCKET_NAME,
                            key,
                            destination,
                        )
                        raise
                    logger.warning(
                        "Falling back to boto3 download after external engine failure: engine=%s bucket=%s key=%s destination=%s error=%s",
                        selected_engine,
                        config.AWS_S3_BUCKET_NAME,
                        key,
                        destination,
                        exc,
                    )
            return self._download_to_path_with_boto3(
                key,
                destination,
                should_abort=should_abort,
            )

        shutil.copy2(str(key), str(destination))
        return destination

    def create_multipart_upload(
        self,
        *,
        subfolder: str,
        file_name: str,
        content_type: Optional[str] = None,
    ) -> dict:
        if not self.is_s3:
            raise RuntimeError("S3 multipart upload is only available when STORAGE_BACKEND=s3")

        stored_file_name, key = self.build_key(subfolder, file_name)
        create_kwargs = {
            "Bucket": config.AWS_S3_BUCKET_NAME,
            "Key": key,
        }
        if content_type:
            create_kwargs["ContentType"] = content_type

        response = self._get_s3_client().create_multipart_upload(**create_kwargs)
        return {
            "key": key,
            "file_name": stored_file_name,
            "multipart_upload_id": response["UploadId"],
        }

    def generate_multipart_part_url(
        self,
        *,
        key: str,
        multipart_upload_id: str,
        part_number: int,
        expires_in: Optional[int] = None,
    ) -> str:
        if not self.is_s3:
            raise RuntimeError("S3 multipart upload is only available when STORAGE_BACKEND=s3")

        return self._get_s3_client().generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": config.AWS_S3_BUCKET_NAME,
                "Key": key,
                "UploadId": multipart_upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in or config.AWS_S3_PRESIGNED_URL_EXPIRE_SECONDS,
            HttpMethod="PUT",
        )

    def complete_multipart_upload(
        self,
        *,
        key: str,
        multipart_upload_id: str,
        parts: list[dict],
    ) -> None:
        if not self.is_s3:
            raise RuntimeError("S3 multipart upload is only available when STORAGE_BACKEND=s3")

        normalized_parts = [
            {"PartNumber": int(part["PartNumber"]), "ETag": part["ETag"]}
            for part in sorted(parts, key=lambda item: int(item["PartNumber"]))
        ]
        started_at = time.perf_counter()
        logger.info(
            "Completing S3 multipart upload: bucket=%s key=%s upload_id=%s parts=%s",
            config.AWS_S3_BUCKET_NAME,
            key,
            multipart_upload_id,
            len(normalized_parts),
        )
        try:
            self._get_s3_client().complete_multipart_upload(
                Bucket=config.AWS_S3_BUCKET_NAME,
                Key=key,
                UploadId=multipart_upload_id,
                MultipartUpload={"Parts": normalized_parts},
            )
        except Exception:
            logger.error(
                "Failed to complete S3 multipart upload: bucket=%s key=%s upload_id=%s parts=%s",
                config.AWS_S3_BUCKET_NAME,
                key,
                multipart_upload_id,
                len(normalized_parts),
                exc_info=True,
            )
            raise
        logger.info(
            "Completed S3 multipart upload in %.2fs: bucket=%s key=%s parts=%s",
            time.perf_counter() - started_at,
            config.AWS_S3_BUCKET_NAME,
            key,
            len(normalized_parts),
        )

    def abort_multipart_upload(self, *, key: str | None, multipart_upload_id: str | None) -> bool:
        if not key or not multipart_upload_id or not self.is_s3:
            return False

        self._get_s3_client().abort_multipart_upload(
            Bucket=config.AWS_S3_BUCKET_NAME,
            Key=key,
            UploadId=multipart_upload_id,
        )
        return True


storage_service = StorageService()
