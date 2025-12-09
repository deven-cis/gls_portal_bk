"""
Initialize relationships after all models are loaded to avoid circular imports.
"""

def init_relationships():
    """Call this after all models are imported to ensure all models are registered"""
    
    from src.cases.models import Cases  
    from src.witnesses.models import Witnesses  
    from src.witness_videos.models import WitnessVideos  # noqa: F401
    from src.attorneys.models import Attorneys  # noqa: F401
    from src.billings.models import Billings  # noqa: F401
    from src.equipment_time.models import EquipmentTime  # noqa: F401
    from src.additional_documents.models import AdditionalDocuments  # noqa: F401
    # Import Jobs last since it depends on all the above
    from src.jobs.models import Jobs  # noqa: F401
    
    # Now all models are loaded, relationships will work
    pass