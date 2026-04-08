import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional

from src.core.config import config


UPLOAD_BASE_DIR = Path("uploads")


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

    @property
    def backend(self) -> str:
        return (config.STORAGE_BACKEND or "local").strip().lower()

    @property
    def is_s3(self) -> bool:
        return self.backend == "s3"

    def _get_s3_client(self):
        if not config.AWS_S3_BUCKET_NAME:
            raise RuntimeError("AWS_S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required when STORAGE_BACKEND=s3. Install backend requirements.") from exc

        client_kwargs = {}
        if config.AWS_REGION:
            client_kwargs["region_name"] = config.AWS_REGION
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY

        return boto3.client("s3", **client_kwargs)

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
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            upload_kwargs = {
                "Filename": str(source),
                "Bucket": config.AWS_S3_BUCKET_NAME,
                "Key": key,
            }
            if extra_args:
                upload_kwargs["ExtraArgs"] = extra_args
            self._get_s3_client().upload_file(**upload_kwargs)
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
            }
            if extra_args:
                upload_kwargs["ExtraArgs"] = extra_args
            self._get_s3_client().upload_fileobj(**upload_kwargs)
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

    def download_to_path(self, key: str, destination_path: str | Path) -> Path:
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if self.is_s3:
            self._get_s3_client().download_file(config.AWS_S3_BUCKET_NAME, key, str(destination))
            return destination

        shutil.copy2(str(key), str(destination))
        return destination


storage_service = StorageService()
