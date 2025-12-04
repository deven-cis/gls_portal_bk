"""
Initialize relationships after all models are loaded to avoid circular imports.
"""

def init_relationships():
    """Call this after all models are imported"""
    from src.jobs.models import Jobs
    from src.cases.models import Cases
    
    # Now both models are loaded, relationships will work
    pass