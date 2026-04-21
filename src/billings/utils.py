from typing import List

from src.additional_documents.models import AdditionalDocuments
from src.billings.models import Billings
from src.billings.schema import AdditionalDocumentResponseSchema, BillingWithDocumentsSchema
from src.core.storage.storage_service import storage_service


def serialize_additional_document(doc: AdditionalDocuments) -> dict:
    doc_data = AdditionalDocumentResponseSchema.model_validate(doc).model_dump()

    if doc.file_path:
        doc_data["file_path"] = storage_service.generate_download_url(
            doc.file_path,
            file_name=doc.file_name,
        )

    return doc_data


def serialize_billing_with_documents(billing: Billings, documents: List[AdditionalDocuments]) -> dict:
    billing_data = BillingWithDocumentsSchema(
        id=billing.id,
        job_no=billing.job_no,
        cancel_en_route=billing.cancel_en_route,
        cancel_setup=billing.cancel_setup,
        billing_notes=billing.billing_notes,
        videographer_hours_present=billing.videographer_hours_present,
        file_hours_length=billing.file_hours_length,
        camera_captured_file_name=billing.camera_captured_file_name,
        camera_captured_file_path=(
            storage_service.generate_download_url(
                billing.camera_captured_file_path,
                file_name=billing.camera_captured_file_name,
            )
            if billing.camera_captured_file_path
            else None
        ),
        documents=[serialize_additional_document(doc) for doc in documents],
    )
    return billing_data.model_dump()
