from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy.orm import Session

from src.core.logger import logger
from src.core.sync.rb9_database import Rb9DatabaseConnection
from src.core.database import SessionLocal
from src.core.timezone_utils import get_timezone_now
from src.core.sync.synchronization_configuration import get_table_config_stage2
from src.core.sync.validation_utils import (
    normalize_string,
)
from src.resources.utils import hash_password

if TYPE_CHECKING:
    from src.resources.models import Resources


class ResourceOnboardingSynchronizationService:
    
    # Fields that should never be updated during sync
    UPDATE_EXCLUDE_FIELDS = [
        'login_password', 
        'entered_at', 
        'entered_by',
        'last_modified_at',  
        'last_modified_by'   
    ]
    
    def __init__(self, rb9_db: Optional[Rb9DatabaseConnection] = None):
        self.rb9_db = rb9_db or Rb9DatabaseConnection()
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'emails_sent': 0
        }
    
    def _transform_field_names(self, rb9_record: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        mapped_record = {}
        for rb9_field, new_gls_field in field_mapping.items():
            if rb9_field in rb9_record:
                mapped_record[new_gls_field] = rb9_record[rb9_field]
        return mapped_record
    
    def _find_existing_resource(self, db: Session, rsrc_no: int) -> Optional['Resources']:
        from src.resources.models import Resources  # Lazy import
        
        return db.query(Resources).filter(Resources.rsrc_no == rsrc_no).first()
    
    def _detect_field_changes(
        self,
        existing_resource: 'Resources',
        mapped_record: Dict[str, Any],
        exclude_fields: list = None
    ) -> Dict[str, Any]:
        exclude_fields = exclude_fields or []
        exclude_fields.extend(self.UPDATE_EXCLUDE_FIELDS)
        
        changes = {}
        for field, new_value in mapped_record.items():
            if field in exclude_fields:
                continue
            
            existing_value = getattr(existing_resource, field, None)
            
            if existing_value != new_value:
                if existing_value is None and new_value is None:
                    continue
                if existing_value is None or new_value is None:
                    changes[field] = new_value
                else:
                    if str(existing_value) != str(new_value):
                        changes[field] = new_value
        
        return changes
    
    def synchronize_resources(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        # Lazy import to prevent circular import
        from src.resources.models import Resources
        
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0, 'emails_sent': 0}
        
        config_data = get_table_config_stage2('Resources')
        if not config_data:
            logger.error("No configuration found for Resources table in Stage 2")
            self.stats['errors'] = 1
            return self.stats
        
        unique_field = config_data['rb9_unique_field']
        query = config_data['query']
        date_field = config_data['date_field']
        field_mapping = config_data['field_mapping']
        date_field_table_alias = config_data.get('date_field_table_alias')
        
        try:
            logger.info("Starting Stage 1 Resources sync from rb9_db to new_gls_db")
            
            params = {}
            where_clauses = []
            date_field_qualified = f'{date_field_table_alias}."{date_field}"' if date_field_table_alias else f'"{date_field}"'
            
            if start_date:
                where_clauses.append(f'{date_field_qualified} >= :start_date')
                params['start_date'] = start_date
            
            if end_date:
                where_clauses.append(f'{date_field_qualified} <= :end_date')
                params['end_date'] = end_date
            
            if where_clauses:
                where_clause = " AND ".join(where_clauses)
                if 'WHERE' in query.upper():
                    query += f" AND {where_clause}"
                else:
                    query += f" WHERE {where_clause}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            logger.info(f"Fetching Resources from rb9_db...")
            logger.debug(f"Query: {query[:200]}...")
            
            rb9_records = self.rb9_db.execute_query(query, params)
            logger.info(f"Fetched {len(rb9_records)} Resources from rb9_db")
            
            if not rb9_records:
                logger.info("No Resources to sync")
                return self.stats
            
            db: Session = SessionLocal()
            try:
                for rb9_record in rb9_records:
                    # Use savepoint for each record to allow partial rollback - prevents data loss
                    savepoint = db.begin_nested()
                    rsrc_no = None
                    try:
                        rsrc_no = rb9_record.get(unique_field)
                        if not rsrc_no:
                            logger.warning(
                                f"[SKIP] Resource record missing {unique_field}. Record: {rb9_record}"
                            )
                            self.stats['skipped'] += 1
                            savepoint.rollback()
                            continue

                        try:
                            rsrc_no = int(rsrc_no)
                        except (TypeError, ValueError):
                            logger.warning(
                                f"[SKIP] Resource record has invalid {unique_field}={rsrc_no!r}. Record: {rb9_record}"
                            )
                            self.stats['skipped'] += 1
                            savepoint.rollback()
                            continue
                        
                        mapped_record = self._transform_field_names(rb9_record, field_mapping)
                        
                        # Normalize key string fields dynamically
                        string_fields = [
                            'full_name',
                            'first_name',
                            'middle_name',
                            'last_name',
                            'login_name',
                            'email',
                            'city',
                            'state',
                            'country',
                            'address',
                        ]
                        for field in string_fields:
                            if field in mapped_record and isinstance(mapped_record[field], str):
                                mapped_record[field] = normalize_string(mapped_record[field])
                        
                        existing_resource = self._find_existing_resource(db, rsrc_no)
                        logger.info(f"Resource with rsrc_no={rsrc_no} {'exists' if existing_resource else 'not found - will create'}")
                        
                        if existing_resource:
                            changes = self._detect_field_changes(existing_resource, mapped_record)
                            
                            if changes:
                                changed_fields = []
                                for field, value in changes.items():
                                    # Skip fields that should never be updated
                                    if field in self.UPDATE_EXCLUDE_FIELDS:
                                        continue
                                    if hasattr(existing_resource, field):
                                        old_value = getattr(existing_resource, field, None)
                                        setattr(existing_resource, field, value)
                                        changed_fields.append(f"{field}: {old_value} -> {value}")
                                
                                existing_resource.last_modified_at = get_timezone_now()
                                
                                # Commit savepoint first, then main transaction
                                savepoint.commit()
                                db.commit()
                                db.refresh(existing_resource)
                                
                                self.stats['updated'] += 1
                                logger.info(
                                    f"[SUCCESS] Updated Resource rsrc_no={rsrc_no}. "
                                    f"Changed fields: {', '.join(changed_fields)}"
                                )
                            else:
                                self.stats['skipped'] += 1
                                savepoint.rollback()
                                logger.debug(f"[SKIP] No changes for Resource rsrc_no={rsrc_no}")
                        else:
                            # Create new resource
                            existing_resource = self._find_existing_resource(db, rsrc_no)
                            if existing_resource:
                                logger.info(f"Resource rsrc_no={rsrc_no} already exists, skipping creation")
                                self.stats['skipped'] += 1
                                savepoint.rollback()
                                continue
                            temp_password = "test"
                            
                            # PRODUCTION CODE (commented for development):
                            # temp_password = generate_temporary_password()
                            # if not temp_password:
                            #     logger.error(
                            #         f"[ERROR] Failed to generate password for user_no={user_no}. "
                            #         f"Stopping processing for this record."
                            #     )
                            #     self.stats['errors'] += 1
                            #     savepoint.rollback()
                            #     continue
                            
                            hashed_password = hash_password(temp_password)
                            if not hashed_password:
                                logger.error(
                                    f"[ERROR] Failed to hash password for rsrc_no={rsrc_no}. "
                                    f"Stopping processing for this record."
                                )
                                self.stats['errors'] += 1
                                savepoint.rollback()
                                continue
                            
                            # Build resource data dynamically from mapped record
                            # Start with required/core fields, then copy all other mapped fields
                            # that exist on the Resources model.
                            resource_data = {
                                'rsrc_no': rsrc_no,
                                'login_password': hashed_password,
                                'entered_by': mapped_record.get('entered_by', 0),
                                'last_modified_by': mapped_record.get('last_modified_by', 0),
                                'is_active': mapped_record.get('is_active', False),
                            }

                            for field, value in mapped_record.items():
                                # Skip fields we already set explicitly
                                if field in resource_data:
                                    continue
                                if value is None:
                                    continue
                                # Only include fields that actually exist on the Resources model
                                if hasattr(Resources, field):
                                    resource_data[field] = value
                            
                            new_resource = Resources(**resource_data)
                            
                            db.add(new_resource)
                            # Commit savepoint first, then main transaction
                            savepoint.commit()
                            db.commit()
                            db.refresh(new_resource)
                            
                            self.stats['inserted'] += 1
                            logger.info(
                                f"[SUCCESS] Created new Resource rsrc_no={rsrc_no}, "
                                f"name={resource_data.get('full_name', 'N/A')}"
                            )
                            
                            # DEVELOPMENT MODE: Skip email sending
                            logger.debug(f"[DEV] Email sending skipped for rsrc_no={rsrc_no} (development mode)")
                            
                            # PRODUCTION CODE (commented for development):
                            # # Send welcome email (non-blocking - email failure doesn't stop sync)
                            # user_email = mapped_record.get('email')
                            # if user_email:
                            #     full_name = mapped_record.get('full_name', '')
                            #     first_name = full_name.split()[0] if full_name else 'User'
                            #     login_name = mapped_record.get('login_name') or user_email
                            #     
                            #     try:
                            #         email_sent = send_user_welcome_notification(
                            #             email=user_email,
                            #             first_name=first_name,
                            #             login_name=login_name,
                            #             temp_password=temp_password
                            #         )
                            #         
                            #         if email_sent:
                            #             self.stats['emails_sent'] += 1
                            #             logger.info(f"[EMAIL] Welcome email sent to {user_email}")
                            #         else:
                            #             logger.warning(
                            #                 f"[EMAIL] Failed to send welcome email to {user_email}. "
                            #                 f"User created successfully but email failed."
                            #             )
                            #     except Exception as email_error:
                            #         logger.warning(
                            #             f"[EMAIL] Exception sending email to {user_email}: {str(email_error)}. "
                            #             f"User created successfully but email failed."
                            #         )
                            # else:
                            #     logger.warning(
                            #         f"[SKIP] No email address for User user_no={user_no}, skipping welcome email"
                            #     )
                    
                    except Exception as e:
                        error_msg = (
                            f"[ERROR] Failed to process Resource record rsrc_no={rsrc_no}: {str(e)}. "
                            f"Record data: {rb9_record}. "
                            f"Rolling back transaction for this record only."
                        )
                        logger.error(error_msg, exc_info=True)
                        self.stats['errors'] += 1
                        
                        # Rollback savepoint (per-record transaction)
                        try:
                            savepoint.rollback()
                            logger.info(f"[RECOVERY] Successfully rolled back transaction for rsrc_no={rsrc_no}")
                        except Exception as rollback_error:
                            logger.error(
                                f"[CRITICAL] Failed to rollback savepoint for rsrc_no={rsrc_no}: {str(rollback_error)}. "
                                f"Attempting main transaction rollback."
                            )
                            try:
                                db.rollback()
                                logger.info(f"[RECOVERY] Main transaction rolled back successfully")
                            except Exception as main_rollback_error:
                                logger.critical(
                                    f"[CRITICAL] Failed to rollback main transaction: {str(main_rollback_error)}. "
                                    f"Database may be in inconsistent state. Manual intervention required."
                                )
                        continue
                
            finally:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Error closing database session: {str(close_error)}")
            
            logger.info(
                f"Stage 1 Resources sync completed: "
                f"Inserted={self.stats['inserted']}, "
                f"Updated={self.stats['updated']}, "
                f"Errors={self.stats['errors']}, "
                f"Skipped={self.stats['skipped']}, "
                f"EmailsSent={self.stats['emails_sent']}"
            )
        
        except Exception as e:
            logger.error(f"Failed to sync Resources in Stage 1: {str(e)}", exc_info=True)
            self.stats['errors'] += 1
            try:
                if 'db' in locals():
                    db.close()
            except Exception:
                pass
        
        return self.stats
