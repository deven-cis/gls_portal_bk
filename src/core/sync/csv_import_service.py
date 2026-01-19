# from src.core.sync.csv_import_service import sync_all_from_csv, sync_users_from_csv, sync_cases_from_csv, sync_jobs_from_csv

# # Sync all tables
# results = sync_all_from_csv()

# # Or sync individual tables
# users_stats = sync_users_from_csv('path/to/users.csv')
# cases_stats = sync_cases_from_csv('path/to/cases.csv')
# jobs_stats = sync_jobs_from_csv('path/to/jobs.csv')

import csv
import os
from typing import Dict, Any
from datetime import datetime

from src.core.logger import logger
from src.core.database import SessionLocal
from src.users.models import Users
from src.cases.models import Cases
from src.jobs.models import Jobs


def sync_users_from_csv(csv_file_path: str) -> Dict[str, int]:
    """Sync users from CSV file - simple approach like user_in.py."""
    stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
    
    if not csv_file_path or not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return stats
    
    session = SessionLocal()
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logger.info(f"CSV Headers: {reader.fieldnames}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Helper function to get value (like user_in.py)
                    def get_value(key):
                        val = row.get(key, '').strip()
                        return val if val else None
                    
                    # Get required fields (user_no and email are required, login_name is optional)
                    email = get_value('Email')
                    login_name = get_value('LoginName')
                    user_no = get_value('UserNo')
                    
                    # Validate required fields
                    if not email or not user_no:
                        logger.warning(
                            f"Row {row_num}: Skipping - Email='{email}', UserNo='{user_no}' "
                            f"(Email and UserNo are required)"
                        )
                        stats['skipped'] += 1
                        continue
                    
                    # If LoginName is empty, use email prefix as fallback (login_name is nullable in DB)
                    if not login_name and email:
                        login_name = email.split('@')[0]
                        logger.debug(f"Row {row_num}: LoginName was empty, using email prefix: {login_name}")
                    
                    try:
                        user_no = int(user_no)
                    except (ValueError, TypeError):
                        logger.warning(f"Row {row_num}: Invalid UserNo")
                        stats['skipped'] += 1
                        continue
                    
                    # Handle password encoding (like user_in.py)
                    password_str = get_value('LoginPassword')
                    password_bytes = None
                    if password_str:
                        password_bytes = password_str.encode('utf-8')
                    
                    # Get date fields from CSV
                    last_modified = get_value('LastModified')
                    entered = get_value('Entered')
                    last_modified_by = get_value('LastModifiedBy')
                    entered_by = get_value('EnteredBy')
                    
                    # Convert dates if provided
                    last_modified_at = None
                    entered_at = None
                    if last_modified:
                        try:
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                try:
                                    last_modified_at = datetime.strptime(last_modified, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    if entered:
                        try:
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                try:
                                    entered_at = datetime.strptime(entered, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    # Convert integers
                    try:
                        last_modified_by = int(last_modified_by) if last_modified_by else 0
                        entered_by = int(entered_by) if entered_by else 0
                    except (ValueError, TypeError):
                        last_modified_by = 0
                        entered_by = 0
                    
                    # Check if user exists
                    existing = session.query(Users).filter(Users.user_no == user_no).first()
                    
                    if existing:
                        # Update existing user
                        existing.full_name = get_value('FullName')
                        existing.email = email
                        existing.login_name = login_name
                        if password_bytes:
                            existing.login_password = password_bytes
                        if last_modified_at:
                            existing.last_modified_at = last_modified_at
                        existing.last_modified_by = last_modified_by
                        stats['updated'] += 1
                    else:
                        # Insert new user
                        new_user = Users(
                            user_no=user_no,
                            full_name=get_value('FullName'),
                            email=email,
                            login_name=login_name,
                            login_password=password_bytes,
                            entered_at=entered_at or datetime.utcnow(),
                            entered_by=entered_by,
                            last_modified_at=last_modified_at or datetime.utcnow(),
                            last_modified_by=last_modified_by,
                            is_archived=False
                        )
                        session.add(new_user)
                        stats['inserted'] += 1
                    
                    # Commit in batches
                    if (stats['inserted'] + stats['updated']) % 50 == 0:
                        session.commit()
                        logger.debug(f"Committed batch at row {row_num}")
                
                except Exception as e:
                    logger.error(f"Row {row_num}: Error - {str(e)}", exc_info=True)
                    stats['errors'] += 1
                    session.rollback()  # Rollback to clear bad session state
                    continue
        
        session.commit()
        logger.info(f"Users CSV sync complete: Inserted={stats['inserted']}, Updated={stats['updated']}, Errors={stats['errors']}, Skipped={stats['skipped']}")
    
    except Exception as e:
        session.rollback()
        logger.error(f"CSV sync failed: {str(e)}", exc_info=True)
        stats['errors'] += 1
    finally:
        session.close()
    
    return stats


def sync_cases_from_csv(csv_file_path: str) -> Dict[str, int]:
    """Sync cases from CSV file - simple approach like cases_in.py."""
    stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
    
    if not csv_file_path or not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return stats
    
    session = SessionLocal()
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logger.info(f"CSV Headers: {reader.fieldnames}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Helper function to get value (like user_in.py)
                    def get_value(key):
                        val = row.get(key, '').strip()
                        return val if val else None
                    
                    case_no = get_value('CaseNo')
                    if not case_no:
                        stats['skipped'] += 1
                        continue
                    
                    try:
                        case_no = int(case_no)
                    except (ValueError, TypeError):
                        logger.warning(f"Row {row_num}: Invalid CaseNo")
                        stats['skipped'] += 1
                        continue
                    
                    # Get date fields from CSV
                    last_modified = get_value('LastModified')
                    entered = get_value('Entered')
                    last_modified_by = get_value('LastModifiedBy')
                    entered_by = get_value('EnteredBy')
                    
                    # Convert dates if provided
                    last_modified_at = None
                    entered_at = None
                    if last_modified:
                        try:
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                try:
                                    last_modified_at = datetime.strptime(last_modified, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    if entered:
                        try:
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                try:
                                    entered_at = datetime.strptime(entered, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    # Convert integers
                    try:
                        last_modified_by = int(last_modified_by) if last_modified_by else 0
                        entered_by = int(entered_by) if entered_by else 0
                    except (ValueError, TypeError):
                        last_modified_by = 0
                        entered_by = 0
                    
                    # Check if exists
                    existing = session.query(Cases).filter(Cases.case_no == case_no).first()
                    
                    if existing:
                        existing.case_short_name = get_value('CaseShortName')
                        existing.case_full_name = get_value('CaseFullName')
                        existing.case_type = get_value('CaseType')
                        existing.status = get_value('Status')
                        case_number = get_value('CaseNumber')
                        if case_number:
                            try:
                                existing.case_number = int(case_number)
                            except (ValueError, TypeError):
                                pass
                        existing.case_status = get_value('CaseStatus')
                        if last_modified_at:
                            existing.last_modified_at = last_modified_at
                        existing.last_modified_by = last_modified_by
                        stats['updated'] += 1
                    else:
                        case_number = get_value('CaseNumber')
                        case_number_int = None
                        if case_number:
                            try:
                                case_number_int = int(case_number)
                            except (ValueError, TypeError):
                                pass
                        
                        new_case = Cases(
                            case_no=case_no,
                            case_short_name=get_value('CaseShortName'),
                            case_full_name=get_value('CaseFullName'),
                            case_type=get_value('CaseType'),
                            status=get_value('Status'),
                            case_number=case_number_int,
                            case_status=get_value('CaseStatus'),
                            entered_at=entered_at or datetime.utcnow(),
                            entered_by=entered_by,
                            last_modified_at=last_modified_at or datetime.utcnow(),
                            last_modified_by=last_modified_by,
                            is_archived=False
                        )
                        session.add(new_case)
                        stats['inserted'] += 1
                    
                    if (stats['inserted'] + stats['updated']) % 50 == 0:
                        session.commit()
                
                except Exception as e:
                    logger.error(f"Row {row_num}: Error - {str(e)}", exc_info=True)
                    stats['errors'] += 1
                    session.rollback()  # Rollback to clear bad session state
                    continue
        
        session.commit()
        logger.info(f"Cases CSV sync complete: Inserted={stats['inserted']}, Updated={stats['updated']}, Errors={stats['errors']}")
    
    except Exception as e:
        session.rollback()
        logger.error(f"CSV sync failed: {str(e)}", exc_info=True)
        stats['errors'] += 1
    finally:
        session.close()
    
    return stats


def sync_jobs_from_csv(csv_file_path: str) -> Dict[str, int]:
    """Sync jobs from CSV file - simple approach like jobs_in.py."""
    stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
    
    if not csv_file_path or not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return stats
    
    session = SessionLocal()
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logger.info(f"CSV Headers: {reader.fieldnames}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Helper function to get value (like user_in.py)
                    def get_value(key):
                        val = row.get(key, '').strip()
                        return val if val else None
                    
                    # Required: JobNo
                    job_no = get_value('JobNo')
                    if not job_no:
                        logger.warning(f"Row {row_num}: Skipping - JobNo is required")
                        stats['skipped'] += 1
                        continue
                    
                    try:
                        job_no = int(job_no)
                    except (ValueError, TypeError):
                        logger.warning(f"Row {row_num}: Invalid JobNo")
                        stats['skipped'] += 1
                        continue

                    # Status is required (column is NOT NULL) - default to 'Scheduled' if missing
                    status = get_value('JobStatus') or 'Scheduled'
                    
                    # Get date fields from CSV
                    last_modified = get_value('LastModified')
                    entered = get_value('Entered')
                    last_modified_by = get_value('LastModifiedBy')
                    entered_by = get_value('EnteredBy')
                    
                    # Convert dates if provided
                    last_modified_at = None
                    entered_at = None
                    if last_modified:
                        try:
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                try:
                                    last_modified_at = datetime.strptime(last_modified, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    if entered:
                        try:
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                try:
                                    entered_at = datetime.strptime(entered, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    # Convert integers
                    try:
                        last_modified_by = int(last_modified_by) if last_modified_by else 0
                        entered_by = int(entered_by) if entered_by else 0
                    except (ValueError, TypeError):
                        last_modified_by = 0
                        entered_by = 0
                    
                    # Check if exists
                    existing = session.query(Jobs).filter(Jobs.job_no == job_no).first()
                    
                    if existing:
                        existing.job_date = get_value('JobDate')
                        existing.start_time = get_value('StartTime')
                        existing.end_time = get_value('EndTime')
                        timezone_no = get_value('TimezoneNo')
                        if timezone_no:
                            try:
                                existing.timezone_no = int(timezone_no)
                            except (ValueError, TypeError):
                                pass

                        # Always set a non-null status
                        existing.status = status
                        case_no = get_value('CaseNo')
                        if case_no:
                            try:
                                case_no_int = int(case_no)
                                # Validate that the case exists before updating (foreign key constraint)
                                case_exists = session.query(Cases).filter(Cases.case_no == case_no_int).first()
                                if case_exists:
                                    existing.case_no = case_no_int
                                else:
                                    logger.warning(f"Row {row_num}: CaseNo {case_no_int} does not exist in cases table, keeping existing case_no")
                            except (ValueError, TypeError):
                                pass
                        existing.job_type = get_value('JobType')
                        existing.scheduled_by_email = get_value('ScheduledByEmail')
                        existing.job_loc_name = get_value('JobLocName')
                        existing.job_loc_address = get_value('JobLocAddress')
                        existing.job_loc_city = get_value('JobLocCity')
                        existing.job_loc_state = get_value('JobLocState')
                        existing.job_loc_zip = get_value('JobLocZip')
                        existing.scheduling_notes_html = get_value('SchedulingNotesHtml')
                        existing.zoom_meeting_id = get_value('ZoomMeetingId')
                        existing.confirmation_notes_html = get_value('ConfirmationNotesHtml')
                        if last_modified_at:
                            existing.last_modified_at = last_modified_at
                        existing.last_modified_by = last_modified_by
                        stats['updated'] += 1
                    else:
                        timezone_no = get_value('TimezoneNo')
                        timezone_no_int = None
                        if timezone_no:
                            try:
                                timezone_no_int = int(timezone_no)
                            except (ValueError, TypeError):
                                pass
                        
                        # CaseNo is NOT NULL in Jobs model - require it for new jobs
                        case_no = get_value('CaseNo')
                        case_no_int = None
                        if case_no:
                            try:
                                case_no_int = int(case_no)
                            except (ValueError, TypeError):
                                pass
                        if case_no_int is None:
                            logger.warning(f"Row {row_num}: Skipping - CaseNo is required for new job")
                            stats['skipped'] += 1
                            continue
                        
                        # Validate that the case exists in the database (foreign key constraint)
                        case_exists = session.query(Cases).filter(Cases.case_no == case_no_int).first()
                        if not case_exists:
                            logger.warning(f"Row {row_num}: Skipping - CaseNo {case_no_int} does not exist in cases table (foreign key violation)")
                            stats['skipped'] += 1
                            continue
                        
                        new_job = Jobs(
                            job_no=job_no,
                            job_date=get_value('JobDate'),
                            start_time=get_value('StartTime'),
                            end_time=get_value('EndTime'),
                            timezone_no=timezone_no_int,
                            status=status,
                            case_no=case_no_int,
                            job_type=get_value('JobType'),
                            scheduled_by_email=get_value('ScheduledByEmail'),
                            job_loc_name=get_value('JobLocName'),
                            job_loc_address=get_value('JobLocAddress'),
                            job_loc_city=get_value('JobLocCity'),
                            job_loc_state=get_value('JobLocState'),
                            job_loc_zip=get_value('JobLocZip'),
                            scheduling_notes_html=get_value('SchedulingNotesHtml'),
                            zoom_meeting_id=get_value('ZoomMeetingId'),
                            confirmation_notes_html=get_value('ConfirmationNotesHtml'),
                            entered_at=entered_at or datetime.utcnow(),
                            entered_by=entered_by,
                            last_modified_at=last_modified_at or datetime.utcnow(),
                            last_modified_by=last_modified_by,
                            is_archived=False
                        )
                        session.add(new_job)
                        stats['inserted'] += 1
                    
                    if (stats['inserted'] + stats['updated']) % 50 == 0:
                        session.commit()
                
                except Exception as e:
                    logger.error(f"Row {row_num}: Error - {str(e)}", exc_info=True)
                    stats['errors'] += 1
                    session.rollback()  # Rollback to clear bad session state
                    continue
        
        session.commit()
        logger.info(f"Jobs CSV sync complete: Inserted={stats['inserted']}, Updated={stats['updated']}, Errors={stats['errors']}")
    
    except Exception as e:
        session.rollback()
        logger.error(f"CSV sync failed: {str(e)}", exc_info=True)
        stats['errors'] += 1
    finally:
        session.close()
    
    return stats
