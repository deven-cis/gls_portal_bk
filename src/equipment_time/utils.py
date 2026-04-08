from typing import List

from src.additional_documents.models import AdditionalDocuments
from src.core.storage_service import storage_service
from src.equipment_time.models import EquipmentTime
from src.equipment_time.schema import AdditionalDocumentResponseSchema, EquipmentTimeWithDocumentsSchema


def serialize_additional_document(doc: AdditionalDocuments) -> dict:
    doc_data = AdditionalDocumentResponseSchema.model_validate(doc).model_dump()

    if doc.file_path:
        doc_data["file_path"] = storage_service.generate_download_url(
            doc.file_path,
            file_name=doc.file_name,
        )

    return doc_data


def serialize_equipment_time_with_documents(
    equipment_time: EquipmentTime,
    documents: List[AdditionalDocuments],
) -> dict:
    equipment_time_data = EquipmentTimeWithDocumentsSchema(
        id=equipment_time.id,
        job_no=equipment_time.job_no,
        laptop_used=equipment_time.laptop_used,
        pip_used=equipment_time.pip_used,
        exhibit_tech=equipment_time.exhibit_tech,
        parking_cost=str(equipment_time.parking_cost) if equipment_time.parking_cost else "0.00",
        time_after=str(equipment_time.time_after) if equipment_time.time_after else None,
        camera_captured_file_name=equipment_time.camera_captured_file_name,
        camera_captured_file_path=(
            storage_service.generate_download_url(
                equipment_time.camera_captured_file_path,
                file_name=equipment_time.camera_captured_file_name,
            )
            if equipment_time.camera_captured_file_path
            else None
        ),
        documents=[serialize_additional_document(doc) for doc in documents],
    )
    return equipment_time_data.model_dump()
