from sqlalchemy import Column, DateTime, Integer, String, Boolean, Date, Numeric, LargeBinary
from sqlalchemy.types import Text
from sqlalchemy.orm import relationship
from src.core.models import Base


class Resources(Base):
    __tablename__ = "resources"   
   
    rsrc_no = Column(Integer, unique=True, index=True, nullable=False)
    person_no = Column(Integer, index=True, nullable=True)

    # Names
    full_name = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Contact info
    main_phone = Column(String(50), nullable=True)
    alt_phone = Column(String(50), nullable=True)
    fax = Column(Text, nullable=True)
    mobile = Column(String(50), nullable=True)
    sms_provider_no = Column(Integer, nullable=True)

    # Auth
    login_name = Column(String(150), index=True, nullable=True)
    login_password = Column(LargeBinary, nullable=True)
    email = Column(String(255), index=True, nullable=True)
    require_password_change = Column(Boolean, default=False, server_default='false')
    profile_image_url = Column(String(1024), nullable=True)
    
    # Status / security
    is_active = Column(Boolean, default=False, server_default='false')
    is_locked = Column(Boolean, default=False, server_default='false')
    try_login_cnt = Column(Integer, default=0, server_default='0')
    last_pwd_changed = Column(DateTime, nullable=True)
    session_id = Column(String(255), nullable=True)

    # Address
    salutation = Column(String(1024), nullable=True) 
    address = Column(String(1024), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    directions = Column(Text, nullable=True)

    # Resource details
    rsrc_type = Column(String(1024), nullable=True)
    warning = Column(Text, nullable=True)  
    # Dates
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    is_no_pay = Column(Boolean, default=False, server_default='false')
    priority_level = Column(String(1024), nullable=True)
    pay_rate_group = Column(String(1024), nullable=True)
    pay_group = Column(String(1024), nullable=True)
    commission_rate_cover = Column(Numeric(10, 4), nullable=True)
    commission_rate_no_cover = Column(Numeric(10, 4), nullable=True)
    is_self_scope = Column(Boolean, default=False, server_default='false')
    recurring_amt = Column(Numeric(12, 2), nullable=True)
    recurring_from = Column(Date, nullable=True)
    recurring_to = Column(Date, nullable=True)
    is_direct_deposit = Column(Boolean, default=False, server_default='false')
    work_schedule_sun = Column(String(1024), nullable=True)
    work_schedule_mon = Column(String(1024), nullable=True)
    work_schedule_tue = Column(String(1024), nullable=True)
    work_schedule_wed = Column(String(1024), nullable=True)
    work_schedule_thu = Column(String(1024), nullable=True)
    work_schedule_fri = Column(String(1024), nullable=True)
    work_schedule_sat = Column(String(1024), nullable=True)
    
    tasks = relationship("JobsTasks", back_populates="rsrc")