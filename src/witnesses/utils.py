from typing import Optional
from fastapi import Request, Form, Depends
from src.witnesses.schema import WitnessUpdateSchema


async def get_witness_update_data_from_request(request: Request) -> WitnessUpdateSchema:
  
    form_data = await request.form()
    
    def get_value(key: str, default=None):
        value = form_data.get(key, default)
        if value is None or value == "":
            return default
        return value
    
    def get_int_value(key: str, default=None):
        value = get_value(key, default)
        if value is None:
            return default
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    return WitnessUpdateSchema(
        job_no=get_int_value("job_no"),
        witness_name=get_value("witness_name"),
        witness_email=get_value("witness_email"),
        actual_start_time=get_value("actual_start_time"),
        actual_end_time=get_value("actual_end_time"),
        read_sign_date=get_value("read_sign_date"),
        read_sign_to=get_int_value("read_sign_to"),
        read_on_text=get_value("read_on_text"),
        read_on_time=get_value("read_on_time"),
        read_off_text=get_value("read_off_text"),
        read_off_time=get_value("read_off_time")
    )

