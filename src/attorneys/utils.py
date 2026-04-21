from fastapi import UploadFile

from src.attorneys.models import Attorneys
from src.attorneys.schema import AttorneySchema
from src.core.file_utils import save_attorney_camera_file, save_attorney_document
from src.core.storage.storage_service import storage_service


def serialize_attorney(attorney: Attorneys) -> dict:
    attorney_data = AttorneySchema.model_validate(attorney).model_dump(mode='json')

    if attorney.file_name_path:
        attorney_data["file_name_path"] = storage_service.generate_download_url(
            attorney.file_name_path,
            file_name=attorney.file_name,
        )

    if attorney.camera_captured_file_path:
        attorney_data["camera_captured_file_path"] = storage_service.generate_download_url(
            attorney.camera_captured_file_path,
            file_name=attorney.camera_captured_file_name,
        )

    return attorney_data


async def save_attorney_document_file(attorney: Attorneys, document: UploadFile, rsrc_no: int) -> None:
    attorney.file_name, attorney.file_name_path = await save_attorney_document(
        document,
        rsrc_no=rsrc_no,
        job_no=attorney.job_no,
        attorney_id=attorney.id,
    )


async def save_attorney_camera_upload(attorney: Attorneys, camera_captured_file: UploadFile, rsrc_no: int) -> None:
    attorney.camera_captured_file_name, attorney.camera_captured_file_path = await save_attorney_camera_file(
        camera_captured_file,
        rsrc_no=rsrc_no,
        job_no=attorney.job_no,
        attorney_id=attorney.id,
    )
