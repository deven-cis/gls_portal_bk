from pydantic import BaseModel


class JobReassignRequestSchema(BaseModel):
    assignee_rsrc_no: int     
    job_id: int         
    reason: str         
