"""
Database sync handlers for Cases, Jobs, and Users tables.
Production use only - syncs from external database using SQL queries.
For CSV testing, use csv_sync.py
"""

from datetime import datetime
from typing import Dict, Any

from src.core.sync.sync_service import SyncService
from src.core.sync.config import get_sync_date_range
from src.core.logger import logger
from src.cases.models import Cases
from src.jobs.models import Jobs
from src.users.models import Users


def sync_cases(
    sync_service: SyncService = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict[str, int]:
    """
    Sync Cases table from external database (rb9_db).
    Filters by LastModified field from external database.
    
    Args:
        sync_service: SyncService instance (creates new if not provided)
        start_date: Start date for filtering (uses config default if None)
        end_date: End date for filtering (uses current time if None)
    
    Returns:
        Dictionary with sync statistics
    """
    if sync_service is None:
        sync_service = SyncService()
    
    if start_date is None or end_date is None:
        start_date, end_date = get_sync_date_range()
    
    try:
        # Query to fetch cases from external database (rb9_db) - using PascalCase column names
        external_query = """
            SELECT
                c.CaseNo,
                c.CaseShortName,
                c.CaseFullName,
                lt.ListValue AS CaseType,
                ls.ListValue AS Status,
                c.TrialDate,
                c.LastModified,
                c.LastModifiedBy,
                c.Entered,
                c.EnteredBy
            FROM Cases c
            LEFT JOIN Lists lt ON c.CaseType = lt.ListNo
            LEFT JOIN Lists ls ON c.Status = ls.ListNo
        """
        
        # Field mapping: External DB (PascalCase) -> Local DB (snake_case)
        field_mapping = {
            'CaseNo': 'case_no',
            'CaseShortName': 'case_short_name',
            'CaseFullName': 'case_full_name',
            'CaseType': 'case_type',
            'Status': 'status',
            'TrialDate': 'trial_date',
            'LastModifiedBy': 'last_modified_by',
            'EnteredBy': 'entered_by',
            'LastModified': 'last_modified_at',
            'Entered': 'entered_at'
        }
        
        stats = sync_service.sync_table(
            table_name='Cases',
            unique_field='case_no',
            external_query=external_query,
            local_model=Cases,
            field_mapping=field_mapping,
            date_field='LastModified',
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Cases sync completed: {stats}")
        return stats
    
    except Exception as e:
        logger.error(f"Failed to sync cases: {str(e)}", exc_info=True)
        raise


def sync_jobs(
    sync_service: SyncService = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict[str, int]:
    """
    Sync Jobs table from external database (rb9_db).
    Filters by LastModified field from external database.
    
    Args:
        sync_service: SyncService instance (creates new if not provided)
        start_date: Start date for filtering (uses config default if None)
        end_date: End date for filtering (uses current time if None)
    
    Returns:
        Dictionary with sync statistics
    """
    if sync_service is None:
        sync_service = SyncService()
    
    if start_date is None or end_date is None:
        start_date, end_date = get_sync_date_range()
    
    try:
        # Query to fetch jobs from external database (rb9_db) - using PascalCase column names
        external_query = """
            SELECT 
                j.JobNo,
                j.JobDate,
                j.StartTime,
                j.EndTime,
                j.TimezoneNo,
                j.Status,
                j.CaseNo,
                j.JobType,
                j.ScheduledByEmail,
                j.JobLocName,
                j.JobLocAddress,
                j.JobLocCity,
                j.JobLocState,
                j.JobLocZip,
                j.SchedulingNotesHtml,
                j.ZoomMeetingId,
                j.ConfirmationNotesHtml,
                j.CancelBy,
                j.CancelDate,
                j.CancelDetails,
                j.CancelReason,
                j.ComputedStatus,
                j.ActualSessionStartTime,
                j.ActualSessionEndTime,
                j.SessionDuration,
                j.SessionCompleted,
                j.VideoUploadDeadline,
                j.ExpectedVideoCount,
                j.MarkIsDoneCase,
                j.MarkIsDoneWitnesses,
                j.MarkIsDoneAttorneys,
                j.MarkIsDoneBillings,
                j.MarkIsDoneEquipmentTime,
                j.LastModified,
                j.LastModifiedBy,
                j.Entered,
                j.EnteredBy
            FROM Jobs j
        """
        
        # Field mapping: External DB (PascalCase) -> Local DB (snake_case)
        field_mapping = {
            'JobNo': 'job_no',
            'JobDate': 'job_date',
            'StartTime': 'start_time',
            'EndTime': 'end_time',
            'TimezoneNo': 'timezone_no',
            'Status': 'status',
            'CaseNo': 'case_no',
            'JobType': 'job_type',
            'ScheduledByEmail': 'scheduled_by_email',
            'JobLocName': 'job_loc_name',
            'JobLocAddress': 'job_loc_address',
            'JobLocCity': 'job_loc_city',
            'JobLocState': 'job_loc_state',
            'JobLocZip': 'job_loc_zip',
            'SchedulingNotesHtml': 'scheduling_notes_html',
            'ZoomMeetingId': 'zoom_meeting_id',
            'ConfirmationNotesHtml': 'confirmation_notes_html',
            'CancelBy': 'cancel_by',
            'CancelDate': 'cancel_date',
            'CancelDetails': 'cancel_details',
            'CancelReason': 'cancel_reason',
            'ComputedStatus': 'computed_status',
            'ActualSessionStartTime': 'actual_session_start_time',
            'ActualSessionEndTime': 'actual_session_end_time',
            'SessionDuration': 'session_duration',
            'SessionCompleted': 'session_completed',
            'VideoUploadDeadline': 'video_upload_deadline',
            'ExpectedVideoCount': 'expected_video_count',
            'MarkIsDoneCase': 'mark_is_done_case',
            'MarkIsDoneWitnesses': 'mark_is_done_witnesses',
            'MarkIsDoneAttorneys': 'mark_is_done_attorneys',
            'MarkIsDoneBillings': 'mark_is_done_billings',
            'MarkIsDoneEquipmentTime': 'mark_is_done_equipment_time',
            'LastModifiedBy': 'last_modified_by',
            'EnteredBy': 'entered_by',
            'LastModified': 'last_modified_at',
            'Entered': 'entered_at'
        }
        
        stats = sync_service.sync_table(
            table_name='jobs',
            unique_field='job_no',
            external_query=external_query,
            local_model=Jobs,
            field_mapping=field_mapping,
            date_field='LastModified',
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Jobs sync completed: {stats}")
        return stats
    
    except Exception as e:
        logger.error(f"Failed to sync jobs: {str(e)}", exc_info=True)
        raise


def sync_users(
    sync_service: SyncService = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict[str, int]:
    """
    Sync Users table from external database (rb9_db).
    Filters by LastModified field from external database.
    
    Args:
        sync_service: SyncService instance (creates new if not provided)
        start_date: Start date for filtering (uses config default if None)
        end_date: End date for filtering (uses current time if None)
    
    Returns:
        Dictionary with sync statistics
    """
    if sync_service is None:
        sync_service = SyncService()
    
    if start_date is None or end_date is None:
        start_date, end_date = get_sync_date_range()
    
    try:
        # Query to fetch users from external database (rb9_db) - using PascalCase column names
        external_query = """
            SELECT 
                u.UserNo,
                u.FullName,
                u.Email,
                u.LoginName,
                u.LoginPassword,
                u.RequirePasswordChange,
                u.ProfileImageUrl,
                u.LastModified,
                u.LastModifiedBy,
                u.Entered,
                u.EnteredBy
            FROM Users u
        """
        
        # Field mapping: External DB (PascalCase) -> Local DB (snake_case)
        field_mapping = {
            'UserNo': 'user_no',
            'FullName': 'full_name',
            'Email': 'email',
            'LoginName': 'login_name',
            'LoginPassword': 'login_password',
            'RequirePasswordChange': 'require_password_change',
            'ProfileImageUrl': 'profile_image_url',
            'LastModifiedBy': 'last_modified_by',
            'EnteredBy': 'entered_by',
            'LastModified': 'last_modified_at',
            'Entered': 'entered_at'
        }
        
        stats = sync_service.sync_table(
            table_name='users',
            unique_field='user_no',
            external_query=external_query,
            local_model=Users,
            field_mapping=field_mapping,
            date_field='LastModified',
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Users sync completed: {stats}")
        return stats
    
    except Exception as e:
        logger.error(f"Failed to sync users: {str(e)}", exc_info=True)
        raise

